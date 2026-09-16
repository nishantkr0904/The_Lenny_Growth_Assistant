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
  "2. SILENT TOOL EXECUTION: NEVER output internal planning, thoughts, monologue, or explanations of what tool you are calling. Do NOT say 'First, I need to call the transcript_retrieval tool...' or output tool names or JSON in your dialogue. Execute tools immediately and silently.\n" +
  "3. RESPONSES ARE FOR THE USER: Only output text intended for the end user AFTER tools have executed and evidence is returned.\n" +
  "4. ANSWER ONLY WHAT WAS ASKED: Address the specific user question directly. Do not generate tangential lists, unsolicited frameworks, or generic takeaways.\n" +
  "5. STRICT EVIDENCE BOUNDING: Every factual claim must be directly supported by explicit statements in the retrieved transcript chunks. Never extrapolate, speculate, or introduce concepts, metrics, or frameworks (such as north-star metrics or unmentioned tactics) not found in the excerpts.\n" +
  "6. CONCISE SYNTHESIS OVER ARTIFICIAL LISTS: Prefer a clear, concise 1-2 paragraph synthesis (or 2-3 tightly grounded bullet points if summarizing distinct points) directly citing the speaker/guest and episode. Never manufacture an arbitrary multi-item list (e.g. 7 takeaways) when the evidence only supports fewer core points.\n" +
  "7. INSUFFICIENT EVIDENCE: If the retrieved evidence is insufficient, or if the topic is not discussed in the transcripts, refuse plainly and state that there is no information on this topic in Lenny's Podcast transcripts. Make zero claims.\n" +
  "8. Maintain full provenance: mention the guest's name and episode title.";

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
let currentTurnToolExecuted = false;

function sanitizeResponseText(text) {
  if (!text) return "";
  let cleaned = text.replace(/```(?:json)?\s*\{\s*"name"\s*:\s*"transcript_retrieval"[\s\S]*?\}\s*```/gi, "");
  cleaned = cleaned.replace(/\{\s*"name"\s*:\s*"transcript_retrieval"[\s\S]*?\}/gi, "");
  cleaned = cleaned.replace(/^(?:First,\s*)?I (?:need to|will) call the (?:`?transcript_retrieval`?|retrieval) tool[^\n]*\n+/gim, "");
  return cleaned.trim();
}

const RETRIEVAL_URL = process.env.INTERNAL_RETRIEVAL_URL || "http://localhost:8000/api/v1/retrieval/search";

function extractDistinctiveTerms(text) {
  if (!text) return [];
  const terms = [];
  // Acronyms (e.g. LNO, PLG, PMF, OKRs, CAC, LTV, ARR, B2B, SLG)
  const acronyms = text.match(/\b(?:[A-Z0-9]{2,6}|[A-Z][a-z]{1,2}[A-Z]{1,2}|[A-Z]{2,4}s)\b/g) || [];
  for (const a of acronyms) {
    if (!/^\d+$/.test(a) && !terms.includes(a)) {
      terms.push(a);
    }
  }
  // Named frameworks/models/concepts preceding framework/model/method/etc.
  const fwMatches = text.matchAll(/\b([A-Za-z0-9_-]{2,15})\s+(?:framework|model|matrix|method|rule|principle|formula|playbook)\b/gi);
  for (const m of fwMatches) {
    const t = m[1];
    if (!terms.some((existing) => existing.toLowerCase() === t.toLowerCase())) {
      terms.push(t);
    }
  }
  return terms;
}

const COMMON_QUERY_STOP_WORDS = new Set([
  "what", "does", "mean", "about", "tell", "explain", "said", "says", "with",
  "from", "that", "this", "have", "more", "lenny", "podcast", "give", "good",
  "some", "when", "where", "which", "there", "their", "then", "into", "just",
  "write", "draft", "create", "essay", "summary", "article", "playbook", "artifact"
]);

function isMateriallyWeakerQuery(candidateQuery, authoritativeQuery) {
  if (!authoritativeQuery) return false;
  if (!candidateQuery) return true;
  if (candidateQuery.trim().toLowerCase() === authoritativeQuery.trim().toLowerCase()) return false;

  // 1. Pronoun check: candidate relies on pronouns
  if (/\b(she|he|they|her|his|them|it|that)\b/i.test(candidateQuery)) {
    return true;
  }

  // 2. Distinctive terms check: authoritative query has acronyms or frameworks missing from candidate
  const authDistinctive = extractDistinctiveTerms(authoritativeQuery);
  for (const term of authDistinctive) {
    const pat = new RegExp(`\\b${term}\\b`, "i");
    if (!pat.test(candidateQuery)) {
      return true; // Authoritative acronym or framework missing from candidate
    }
  }

  // 3. Substantive keyword check: candidate dropped significant non-stopwords
  const authWords = authoritativeQuery.toLowerCase().match(/\b[a-z0-9_-]{4,}\b/g) || [];
  const candLower = candidateQuery.toLowerCase();
  const missingWords = authWords.filter((w) => !COMMON_QUERY_STOP_WORDS.has(w) && !candLower.includes(w));
  if (
    missingWords.length > 0 &&
    candidateQuery.trim().split(/\s+/).length < authoritativeQuery.trim().split(/\s+/).length
  ) {
    return true;
  }

  return false;
}

function isStrongerDecision(decisionA, decisionB) {
  if (!decisionB) return true;
  if (!decisionA) return false;

  const tierRank = { Strong: 3, Conflicting: 2, Limited: 1, Insufficient: 0 };
  const rankA = tierRank[decisionA.tier] ?? -1;
  const rankB = tierRank[decisionB.tier] ?? -1;

  if (rankA !== rankB) {
    return rankA > rankB;
  }

  return (decisionA.top_score || 0) > (decisionB.top_score || 0);
}

async function executeRetrieval(query, topK = 5) {
  const res = await fetch(RETRIEVAL_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      top_k: topK,
    }),
  });
  if (!res.ok) {
    const errDetail = await res.text();
    throw new Error(`Retrieval service error (${res.status}): ${errDetail}`);
  }
  return await res.json();
}

function formatValidEvidenceXml(decision, evidence) {
  let conflictDirective = "";
  if (decision.tier === "Conflicting") {
    conflictDirective =
      "  <conflict_directive>\n    Divergent perspectives detected across guests. Synthesis must clearly contrast the differing viewpoints.\n  </conflict_directive>\n";
  }

  const chunksXml = (evidence || [])
    .map(
      (c) =>
        `  <chunk id="${c.chunk_id}" guest="${c.guest}" episode="${c.title}" score="${c.similarity_score}">\n` +
        `    <speaker>${c.speaker || c.guest}</speaker>\n` +
        `    <content>\n${c.content.trim()}\n    </content>\n` +
        `  </chunk>`,
    )
    .join("\n");

  return (
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
    `</retrieved_evidence>`
  );
}

function formatInsufficientEvidenceXml(decision) {
  return (
    `<retrieved_evidence status="INSUFFICIENT" tier="${decision.tier}" top_score="${decision.top_score}">\n` +
    `  <system_directive>\n` +
    `    NO_GROUNDED_EVIDENCE: The query is not covered in Lenny's Podcast transcripts.\n` +
    `    You are strictly FORBIDDEN from using general knowledge or guessing.\n` +
    `    You MUST inform the user that this topic is not discussed in Lenny's Podcast transcripts.\n` +
    `    Do not invent or cite any sources.\n` +
    `  </system_directive>\n` +
    `</retrieved_evidence>`
  );
}

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
    currentTurnToolExecuted = true;
    let parsedTopK = 5;
    if (params.top_k !== undefined && params.top_k !== null && params.top_k !== "") {
      const num = parseInt(params.top_k, 10);
      if (!isNaN(num)) {
        parsedTopK = Math.min(Math.max(num, 1), 25);
      }
    }

    let targetQuery = params.query;
    let queryOverridden = false;

    // Guard against degraded query: if candidate omits distinctive terms or relies on pronouns
    if (currentTurnRewrittenQuery && isMateriallyWeakerQuery(params.query, currentTurnRewrittenQuery)) {
      console.error(
        `[PI TOOL] Query degradation detected: "${params.query}" is materially weaker than authoritative "${currentTurnRewrittenQuery}". Overriding with authoritative query.`
      );
      targetQuery = currentTurnRewrittenQuery;
      queryOverridden = true;
    }

    console.error(`[PI TOOL] Executing transcript_retrieval query="${targetQuery}" (top_k=${parsedTopK})`);
    sendNotification("tool_call", { name: "transcript_retrieval", query: targetQuery });

    try {
      let data = await executeRetrieval(targetQuery, parsedTopK);
      let decision = data.decision;

      // If initial candidate was not already overridden, but yielded tier below Strong while an authoritative query exists:
      // evaluate authoritative query to guarantee stronger grounded evidence is used
      if (
        !queryOverridden &&
        currentTurnRewrittenQuery &&
        targetQuery !== currentTurnRewrittenQuery &&
        decision.tier !== "Strong"
      ) {
        console.error(
          `[PI TOOL] Initial query "${targetQuery}" yielded tier=${decision.tier} (score=${decision.top_score}); evaluating authoritative query "${currentTurnRewrittenQuery}"...`
        );
        try {
          const authData = await executeRetrieval(currentTurnRewrittenQuery, parsedTopK);
          if (isStrongerDecision(authData.decision, decision)) {
            console.error(
              `[PI TOOL] Authoritative query provided stronger evidence (tier=${authData.decision.tier}, score=${authData.decision.top_score}); using authoritative results.`
            );
            data = authData;
            decision = data.decision;
            targetQuery = currentTurnRewrittenQuery;
          }
        } catch (authErr) {
          console.error(`[PI TOOL] Authoritative query evaluation failed: ${authErr.message}`);
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
          content: [{ type: "text", text: formatInsufficientEvidenceXml(decision) }],
          details: decision,
        };
      }

      return {
        content: [{ type: "text", text: formatValidEvidenceXml(decision, currentTurnEvidence) }],
        details: decision,
      };
    } catch (err) {
      console.error(`[PI TOOL EXCEPTION] ${err.message}`);
      return {
        content: [{ type: "text", text: `Retrieval service error: ${err.message}` }],
      };
    }
  },
});

async function executeTurn(params) {
  const { user_prompt, rewritten_query, history = [], provider = "ollama", model_name, api_key } = params;

  currentTurnEvidence = [];
  currentTurnDecision = null;
  currentTurnRewrittenQuery = rewritten_query || null;
  currentTurnToolExecuted = false;

  const runtime = await ModelRuntime.create();
  let model;

  if (provider === "anthropic") {
    const apiKey = api_key || process.env.ANTHROPIC_API_KEY;
    if (!apiKey || apiKey.trim() === "") {
      throw new Error(
        "ProviderConfigurationError: Anthropic API key is required when provider=anthropic. " +
          "Zero silent fallback to Ollama is permitted. Please configure an API key in the UI.",
      );
    }
    runtime.setRuntimeApiKey("anthropic", apiKey);
    const targetModel = model_name || process.env.ANTHROPIC_MODEL || "claude-3-5-sonnet-20241022";
    model = runtime.getModel("anthropic", targetModel);
    if (!model) {
      const available = runtime.getModels().filter((m) => m.provider === "anthropic");
      model = available[0];
    }
  } else if (provider === "gemini" || provider === "google") {
    const apiKey = api_key || process.env.GEMINI_API_KEY;
    if (!apiKey || apiKey.trim() === "") {
      throw new Error(
        "ProviderConfigurationError: Google Gemini API key is required when provider=gemini. " +
          "Zero silent fallback to Ollama is permitted. Please configure an API key in the UI.",
      );
    }
    process.env.GEMINI_API_KEY = apiKey;
    try {
      runtime.setRuntimeApiKey("google", apiKey);
    } catch {}
    const targetModel = model_name || process.env.GEMINI_MODEL || "gemini-2.5-flash";
    model = runtime.getModel("google", targetModel);
    if (!model) {
      const available = runtime.getModels().filter((m) => m.provider === "google");
      model = available.find((m) => m.id.includes("flash")) || available[0];
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

  let preToolText = "";
  let postToolText = "";
  const unsubscribe = session.subscribe((event) => {
    if (event.type === "message_update" && event.assistantMessageEvent?.type === "text_delta") {
      const delta = event.assistantMessageEvent.delta;
      if (currentTurnToolExecuted) {
        postToolText += delta;
        sendNotification("token_delta", { delta });
      } else {
        preToolText += delta;
      }
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

    // If the tool call was missing or bypassed by the LLM, deterministically execute retrieval with authoritative query
    if (!currentTurnToolExecuted) {
      console.error(
        "[PI AGENT] Tool call was missing or bypassed by LLM. Deterministically executing retrieval with authoritative query..."
      );
      const deterministicQuery = currentTurnRewrittenQuery || user_prompt;
      sendNotification("tool_call", { name: "transcript_retrieval", query: deterministicQuery });

      try {
        const data = await executeRetrieval(deterministicQuery, 5);
        const decision = data.decision;
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
            response:
              "I could not find guidance on this topic in Lenny's Podcast transcripts. The transcripts focus on product management, growth, and company building from Lenny's interviews. Please feel free to ask a question related to Lenny's guests and discussions.",
            tier: "Insufficient",
            top_score: decision.top_score || 0.0,
            can_synthesize: false,
            decision,
            selected_evidence: [],
            model: `${model.provider}/${model.id}`,
          };
        }

        // Deterministically retrieved valid evidence; prompt session for grounded synthesis
        currentTurnToolExecuted = true;
        postToolText = "";
        const fallbackPrompt =
          `${formatValidEvidenceXml(decision, currentTurnEvidence)}\n\n` +
          `The above evidence was retrieved from Lenny's Podcast transcripts for the user question: "${user_prompt}".\n` +
          `Provide a concise, grounded synthesis directly answering the question based strictly on the retrieved chunks.`;

        console.error(`[PI AGENT] Synthesizing grounded response using deterministically retrieved evidence...`);
        await session.prompt(fallbackPrompt);
      } catch (err) {
        console.error(`[PI AGENT] Deterministic retrieval failed: ${err.message}`);
      }
    }

    const rawResponse = currentTurnToolExecuted ? postToolText : preToolText;
    const finalResponse = sanitizeResponseText(rawResponse);

    return {
      response: finalResponse,
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

export {
  extractDistinctiveTerms,
  isMateriallyWeakerQuery,
  isStrongerDecision,
  formatValidEvidenceXml,
  formatInsufficientEvidenceXml,
  executeRetrieval,
  executeTurn,
};
