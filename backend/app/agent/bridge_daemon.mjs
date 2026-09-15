/**
 * Production Pi Coding Agent JSON-RPC Bridge Daemon.
 *
 * Exposes Pi Coding Agent 0.85.1 as a long-running subprocess communicating
 * over stdio using JSON-RPC 2.0.
 *
 * Prevents stdout pollution by redirecting all console logging to stderr.
 */

import fs from "node:fs";
import readline from "node:readline";
import util from "node:util";

// Redirect all standard console output to stderr so stdout is purely JSON-RPC messages
console.log = (...args) => process.stderr.write(util.format(...args) + "\n");
console.info = (...args) => process.stderr.write(util.format(...args) + "\n");
console.warn = (...args) => process.stderr.write(util.format(...args) + "\n");
console.error = (...args) => process.stderr.write(util.format(...args) + "\n");

// Dynamically import Pi SDK (supports container and host installation paths)
let Type, createAgentSession, defineTool, ModelRuntime, SessionManager;

async function loadPiSdk() {
  const possiblePaths = [
    "/usr/lib/node_modules/@earendil-works/pi-coding-agent",
    "/usr/local/lib/node_modules/@earendil-works/pi-coding-agent",
    "/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent",
  ];

  for (const basePath of possiblePaths) {
    try {
      const coreModule = await import(`${basePath}/dist/index.js`);
      const aiModule = await import(`${basePath}/node_modules/@earendil-works/pi-ai/dist/index.js`);
      ({ createAgentSession, defineTool, ModelRuntime, SessionManager } = coreModule);
      Type = aiModule.Type;
      console.error(`[PI BRIDGE] Loaded Pi SDK from: ${basePath}`);
      return;
    } catch {
      // Try next path
    }
  }

  // Fallback: try bare imports
  try {
    const coreModule = await import("@earendil-works/pi-coding-agent");
    const aiModule = await import("@earendil-works/pi-ai");
    ({ createAgentSession, defineTool, ModelRuntime, SessionManager } = coreModule);
    Type = aiModule.Type;
    console.error("[PI BRIDGE] Loaded Pi SDK via standard module resolution");
    return;
  } catch (err) {
    console.error("[PI BRIDGE FATAL] Failed to import Pi SDK:", err.message);
    process.exit(1);
  }
}

await loadPiSdk();

const LENNY_SYSTEM_PROMPT =
  "You are the Lenny Growth Assistant, an authoritative AI assistant answering questions about product management, growth, and company building based STRICTLY on transcripts from Lenny's Podcast.\n\n" +
  "CORE OPERATIONAL MANDATES:\n" +
  "1. ALWAYS call the `transcript_retrieval` tool to retrieve evidence before formulating an answer. Do NOT answer from memory or general knowledge.\n" +
  "2. ANSWER ONLY WHAT WAS ASKED: Address the specific user question directly. Do not generate tangential lists, unsolicited frameworks, or generic takeaways.\n" +
  "3. STRICT EVIDENCE BOUNDING: Every factual claim must be directly supported by explicit statements in the retrieved transcript chunks. Never extrapolate, speculate, or introduce concepts, metrics, or frameworks (such as north-star metrics or unmentioned tactics) not found in the excerpts.\n" +
  "4. CONCISE SYNTHESIS OVER ARTIFICIAL LISTS: Prefer a clear, concise 1-2 paragraph synthesis (or 2-3 tightly grounded bullet points if summarizing distinct points) directly citing the speaker/guest and episode. Never manufacture an arbitrary multi-item list (e.g. 7 takeaways) when the evidence only supports fewer core points.\n" +
  "5. INSUFFICIENT EVIDENCE: If the retrieved evidence is insufficient, or if the topic is not discussed in the transcripts, refuse plainly and state that there is no information on this topic in Lenny's Podcast transcripts. Make zero claims.\n" +
  "6. Maintain full provenance: mention the guest's name and episode title.";

function ensureModelsConfig() {
  const configDir = process.env.HOME ? `${process.env.HOME}/.pi/agent` : "/root/.pi/agent";
  try {
    fs.mkdirSync(configDir, { recursive: true });
    const modelsPath = `${configDir}/models.json`;
    let existing = {};
    if (fs.existsSync(modelsPath)) {
      try {
        existing = JSON.parse(fs.readFileSync(modelsPath, "utf8"));
      } catch {}
    }

    const ollamaBaseUrl = (process.env.OLLAMA_BASE_URL || "http://ollama:11434").replace(/\/$/, "") + "/v1";
    const providers = existing.providers || {};
    providers.ollama = {
      baseUrl: ollamaBaseUrl,
      api: "openai-completions",
      apiKey: "ollama",
      models: [{ id: process.env.OLLAMA_MODEL || "llama3.1:8b" }],
    };

    fs.writeFileSync(modelsPath, JSON.stringify({ ...existing, providers }, null, 2));
    fs.writeFileSync(`${configDir}/SYSTEM.md`, LENNY_SYSTEM_PROMPT, "utf8");
    console.error(`[PI BRIDGE] Configured models.json with Ollama at ${ollamaBaseUrl}`);
  } catch (err) {
    console.error("[PI BRIDGE] Warning: could not write models.json:", err.message);
  }
}

ensureModelsConfig();

function sendJsonRpc(message) {
  process.stdout.write(JSON.stringify(message) + "\n");
}

function sendNotification(method, params) {
  sendJsonRpc({
    jsonrpc: "2.0",
    method,
    params,
  });
}

function sendResponse(id, result) {
  sendJsonRpc({
    jsonrpc: "2.0",
    id,
    result,
  });
}

function sendError(id, code, message, data = null) {
  sendJsonRpc({
    jsonrpc: "2.0",
    id,
    error: { code, message, data },
  });
}

// Tool tracking for current turn
let currentTurnEvidence = [];
let currentTurnDecision = null;
let currentTurnRewrittenQuery = null;

const RETRIEVAL_URL = process.env.INTERNAL_RETRIEVAL_URL || "http://localhost:8000/api/v1/retrieval/search";

const transcriptRetrievalTool = defineTool({
  name: "transcript_retrieval",
  label: "Transcript Retrieval",
  description:
    "Searches the Lenny's Podcast transcript corpus for source-grounded evidence. " +
    "You MUST invoke this tool before answering any question about Lenny's guests, interviews, or advice. " +
    "Do NOT answer from general knowledge.",
  parameters: Type.Object({
    query: Type.String({
      description: "Natural language search query regarding product, growth, or advice from podcast guests.",
    }),
    top_k: Type.Optional(
      Type.Number({
        description: "Maximum number of candidate evidence chunks to retrieve (default: 5).",
      }),
    ),
  }),

  async execute(_toolCallId, params) {
    const hasPronouns = /\b(she|he|they|her|his|them|it|that)\b/i.test(params.query);
    let targetQuery = params.query;
    if (hasPronouns && currentTurnRewrittenQuery && currentTurnRewrittenQuery !== params.query) {
      console.error(`[PI TOOL] Rewriting pronoun query "${params.query}" -> "${currentTurnRewrittenQuery}"`);
      targetQuery = currentTurnRewrittenQuery;
    }

    console.error(`[PI TOOL] Executing transcript_retrieval query="${targetQuery}" (top_k=${params.top_k || 5})`);
    sendNotification("tool_call", { name: "transcript_retrieval", query: targetQuery });

    try {
      let res = await fetch(RETRIEVAL_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: targetQuery,
          top_k: params.top_k || 5,
        }),
      });

      if (!res.ok) {
        const errDetail = await res.text();
        console.error(`[PI TOOL ERROR] HTTP ${res.status}: ${errDetail}`);
        return {
          content: [{ type: "text", text: `Retrieval service error (${res.status}): ${errDetail}` }],
        };
      }

      let data = await res.json();
      let decision = data.decision;

      // If initial query yielded Insufficient and we have a rewritten query anchor, retry
      if (
        (!decision.can_synthesize || decision.tier === "Insufficient") &&
        currentTurnRewrittenQuery &&
        targetQuery !== currentTurnRewrittenQuery
      ) {
        console.error(`[PI TOOL] Initial query yielded Insufficient; retrying with resolved query "${currentTurnRewrittenQuery}"`);
        const retryRes = await fetch(RETRIEVAL_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: currentTurnRewrittenQuery,
            top_k: params.top_k || 5,
          }),
        });
        if (retryRes.ok) {
          const retryData = await retryRes.json();
          if (retryData.decision && retryData.decision.can_synthesize) {
            data = retryData;
            decision = data.decision;
          }
        }
      }

      currentTurnDecision = decision;
      currentTurnEvidence = decision.can_synthesize ? (decision.selected_evidence || []) : [];

      sendNotification("tool_result", {
        tier: decision.tier,
        top_score: decision.top_score,
        can_synthesize: decision.can_synthesize,
        chunk_count: currentTurnEvidence.length,
      });

      if (!decision.can_synthesize || decision.tier === "Insufficient") {
        currentTurnEvidence = [];
        return {
          content: [
            {
              type: "text",
              text:
                `<retrieved_evidence status="INSUFFICIENT" tier="${decision.tier}" top_score="${decision.top_score}">\n` +
                `  <system_directive>\n` +
                `    NO_GROUNDED_EVIDENCE: The query is not covered in Lenny's Podcast transcripts.\n` +
                `    You are strictly FORBIDDEN from using general knowledge or guessing.\n` +
                `    You MUST inform the user that this topic is not discussed in Lenny's Podcast transcripts.\n` +
                `    Do not invent or cite any sources.\n` +
                `  </system_directive>\n` +
                `</retrieved_evidence>`,
            },
          ],
          details: decision,
        };
      }

      let conflictDirective = "";
      if (decision.tier === "Conflicting") {
        conflictDirective =
          "  <conflict_directive>\n    Divergent perspectives detected across guests. Synthesis must clearly contrast the differing viewpoints.\n  </conflict_directive>\n";
      }

      const chunksXml = currentTurnEvidence
        .map(
          (c) =>
            `  <chunk id="${c.chunk_id}" guest="${c.guest}" episode="${c.title}" score="${c.similarity_score}">\n` +
            `    <speaker>${c.speaker || c.guest}</speaker>\n` +
            `    <content>\n${c.content.trim()}\n    </content>\n` +
            `  </chunk>`,
        )
        .join("\n");

      const validXml =
        `<retrieved_evidence status="VALID" tier="${decision.tier}" top_score="${decision.top_score}">\n` +
        `  <system_directive>\n` +
        `    GROUNDING & SYNTHESIS RULES:\n` +
        `    - Directly answer the user's specific question using only the explicit facts in the chunks below.\n` +
        `    - Do NOT invent, extrapolate, or manufacture lists of takeaways merely because they appear in related chunks.\n` +
        `    - If the user asks why something is important, synthesize why the guest says it is important in a concise, coherent explanation (1-2 paragraphs). Do not add a long list of implementation details or tactics.\n` +
        `    - Every claim you make must be directly backed by the excerpts.\n` +
        `    - Attribute insights directly to the speaker/guest and episode title.\n` +
        `  </system_directive>\n` +
        conflictDirective +
        `${chunksXml}\n` +
        `</retrieved_evidence>`;


      return {
        content: [{ type: "text", text: validXml }],
        details: decision,
      };
    } catch (err) {
      console.error(`[PI TOOL EXCEPTION] ${err.message}`);
      return {
        content: [{ type: "text", text: `Retrieval service unreachable: ${err.message}` }],
      };
    }
  },
});

async function executeTurn(params) {
  const { user_prompt, rewritten_query, history = [], provider = "ollama", model_name } = params;

  currentTurnEvidence = [];
  currentTurnDecision = null;
  currentTurnRewrittenQuery = rewritten_query || null;

  const runtime = await ModelRuntime.create();
  let model;

  if (provider === "anthropic") {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey || apiKey.trim() === "") {
      throw new Error(
        "ProviderConfigurationError: ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. " +
          "Zero silent fallback to Ollama is permitted.",
      );
    }
    runtime.setRuntimeApiKey("anthropic", apiKey);
    const targetModel = model_name || process.env.ANTHROPIC_MODEL || "claude-3-5-sonnet-20241022";
    model = runtime.getModel("anthropic", targetModel);
    if (!model) {
      const available = runtime.getModels().filter((m) => m.provider === "anthropic");
      model = available[0];
    }
  } else {
    // Ollama default
    const targetModel = model_name || process.env.OLLAMA_MODEL || "llama3.1:8b";
    model = runtime.getModel("ollama", targetModel);
  }

  if (!model) {
    throw new Error(`Model not found for provider '${provider}': ${model_name || "default"}`);
  }

  const { session } = await createAgentSession({
    model,
    customTools: [transcriptRetrievalTool],
    noTools: "builtin",
    sessionManager: SessionManager.inMemory(),
  });

  if (session.agent && session.agent.state) {
    session.agent.state.systemPrompt = LENNY_SYSTEM_PROMPT;
  }

  let accumulatedText = "";
  const unsubscribe = session.subscribe((event) => {
    if (event.type === "message_update" && event.assistantMessageEvent?.type === "text_delta") {
      const delta = event.assistantMessageEvent.delta;
      accumulatedText += delta;
      sendNotification("token_delta", { delta });
    }
  });

  try {
    // Format prompt with context and rewritten query if available
    let turnPrompt = user_prompt;
    if (rewritten_query && rewritten_query !== user_prompt) {
      turnPrompt = `User Question: ${user_prompt}\nSearch Query: ${rewritten_query}\n(Note: Retrieve transcript evidence using '${rewritten_query}')`;
    }
    turnPrompt += "\n\nProvide a concise, evidence-grounded answer directly addressing what was asked. Do NOT invent unrequested lists of takeaways.";

    console.error(`[PI AGENT] Invoking Pi session with model ${model.provider}/${model.id}...`);
    await session.prompt(turnPrompt);


    return {
      response: accumulatedText,
      tier: currentTurnDecision ? currentTurnDecision.tier : "Insufficient",
      top_score: currentTurnDecision ? currentTurnDecision.top_score : 0.0,
      can_synthesize: currentTurnDecision ? currentTurnDecision.can_synthesize : false,
      decision: currentTurnDecision,
      selected_evidence: currentTurnEvidence,
      model: `${model.provider}/${model.id}`,
    };
  } finally {
    unsubscribe();
    session.dispose();
  }
}


// JSON-RPC Request Processing via stdin
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

rl.on("line", async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let msg;
  try {
    msg = JSON.parse(trimmed);
  } catch (err) {
    console.error("[PI BRIDGE] Failed to parse incoming JSON:", err.message);
    sendError(null, -32700, "Parse error: invalid JSON");
    return;
  }

  const { id, method, params = {} } = msg;

  if (method === "ping") {
    sendResponse(id, {
      status: "ok",
      agent: "pi-coding-agent",
      version: "0.85.1",
      provider: process.env.LLM_PROVIDER || "ollama",
    });
    return;
  }

  if (method === "shutdown") {
    sendResponse(id, { status: "shutting_down" });
    process.exit(0);
  }

  if (method === "execute_turn") {
    try {
      const result = await executeTurn(params);
      sendResponse(id, result);
    } catch (err) {
      console.error("[PI BRIDGE ERROR]", err.message);
      sendError(id, -32000, err.message);
    }
    return;
  }

  sendError(id, -32601, `Method not found: ${method}`);
});

console.error("[PI BRIDGE] Ready. Listening on stdin.");
sendNotification("ready", { status: "ready", version: "0.85.1" });
