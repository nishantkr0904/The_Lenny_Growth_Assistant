# PRD — The Lenny Growth Assistant

**Version:** 1.0  
**Author:** Forward Deployed Engineer  
**Status:** Draft — Pending Team Review  
**Last Updated:** 2026-09-13

---

## 1. Product Summary

The Lenny Growth Assistant is an **internal product and growth research assistant** that enables practitioners to ask complex product and growth questions against a curated corpus of Lenny's Podcast transcripts, receive source-grounded answers, transform insights into structured written content, and generate renderable Markdown/HTML artifacts — all without requiring the user to understand retrieval pipelines, prompt engineering, model infrastructure, or agent orchestration.

**Product Promise:**

> Help product and growth practitioners quickly turn Lenny's Podcast knowledge into trustworthy, source-grounded research and reusable content — without manually searching transcripts, stitching together quotes, or understanding AI infrastructure.

This is **not** a generic chatbot, a general-purpose AI advisor, a replacement for listening to Lenny's Podcast, or an autonomous product manager. The assistant's knowledge boundary is the transcript corpus. Everything it says should be traceable back to what was actually said on the podcast.

**Decision:** We position the product as a focused research tool rather than a general AI assistant because a narrow, trustworthy tool is more valuable than a broad, unreliable one — especially for a team that needs to cite sources and make decisions based on expert advice.

---

## 2. Discovery / Forward Deployment Brief

### User

The primary user is an **internal product or growth practitioner** — a product manager, growth lead, researcher, founder, or operator — working inside a product organization. They are experienced enough to ask sophisticated product and growth questions, but time-constrained enough that manually searching through hundreds of hours of podcast transcripts is impractical.

**Secondary users** (acknowledged but not designing for separately): content marketers who need to produce grounded thought-leadership content, and engineering leaders evaluating product strategy frameworks mentioned on the podcast.

### Problem

Lenny's Podcast represents one of the richest publicly available corpuses of product and growth expertise — hundreds of episodes featuring top practitioners from companies like Airbnb, Slack, Figma, Stripe, and many others. The problem is **access and synthesis**:

- **Discovery is manual.** Finding which episode discussed "how to set up your first growth team" or "when to pivot your pricing strategy" requires remembering episode titles, scrubbing through 60-90 minute recordings, or hoping search engines surface the right clip.
- **Synthesis is labor-intensive.** Even when you find the right episode, extracting a coherent, actionable answer from a conversational transcript — and cross-referencing it with what other guests said about the same topic — takes significant effort.
- **Reuse is fragile.** Sharing insights with your team typically means copying quotes into a doc, losing attribution, and hoping your paraphrase is faithful to what was actually said.

### Job to Be Done

> **When** I'm making a product or growth decision and want to know what experienced practitioners have said about a specific topic,  
> **I want** to ask a natural-language question and get a grounded, source-attributed answer synthesized from relevant podcast episodes,  
> **So that** I can make better-informed decisions quickly, share trustworthy insights with my team, and optionally turn those insights into polished written content.

### Why Now / Why This Product

The transcript corpus now exists in a structured, machine-readable format (the ChatPRD/lennys-podcast-transcripts repository). Modern retrieval-augmented generation and agent architectures make it feasible to build a high-quality, grounded assistant without requiring fine-tuning or massive infrastructure. The combination of available data, mature tooling, and a clear user need creates a narrow window to demonstrate a forward-deployed solution.

### Product Promise

The assistant removes three things from the practitioner's workflow:

1. **Search friction** — no more guessing which episode to listen to
2. **Synthesis labor** — the assistant cross-references multiple episodes and presents a coherent answer
3. **Content creation overhead** — grounded insights can be transformed directly into reusable written artifacts

**Success means:** A practitioner asks a product/growth question, gets a trustworthy answer they can cite in a strategy doc within 60 seconds, and optionally generates a polished essay they can share with their team — all without leaving the application.

---

## 3. Goals and Non-Goals

### Goals

1. **Grounded, source-attributed answers** to product and growth questions from Lenny's Podcast transcripts
2. **Conversational follow-up** that maintains session context across multiple turns
3. **Explicit source traceability** — every claim linked to episode and guest
4. **Content transformation** — turn grounded insights into Ship 30 for 30-style essays
5. **Artifact generation and in-app rendering** — produce Markdown and HTML/CSS artifacts viewable within the application
6. **Reproducible local demo** — evaluator runs `docker compose up` and has a working system with no cloud dependencies
7. **Cloud-provider readiness** — switch to Anthropic Claude or OpenAI without code changes
8. **Honest failure behavior** — the assistant acknowledges when it doesn't have enough evidence rather than hallucinating

### Non-Goals

- **General AI advisor.** The assistant does not answer questions outside the transcript corpus using general knowledge.
- **Real-time podcast ingestion.** The system works against a static (periodically refreshable) corpus, not a live feed.
- **Multi-tenant enterprise platform.** No RBAC, no multi-org, no billing.
- **Autonomous background agents.** No unsupervised tasks running without user interaction.
- **Mobile-native application.** Responsive web only.
- **Fine-tuned models.** We use off-the-shelf models with retrieval augmentation.

---

## 4. Success Metrics

All metrics below are **targets for the take-home scope**. We do not claim production telemetry.

### Grounding Metrics (Target)

| Metric | Target | Why It Matters | How to Measure |
|--------|--------|----------------|----------------|
| Source attribution rate | ≥ 95% of supported answers include at least one episode/guest citation | The core product promise is grounded answers. An answer without a source is a failure. | Manual review of 20 test queries |
| Unsupported-question refusal rate | 100% of out-of-corpus questions produce a "not enough evidence" response | Prevents hallucination and preserves trust boundary. | 10 known out-of-corpus test queries |
| Retrieval precision (top-5) | ≥ 3 of 5 retrieved chunks are relevant to the query | Poor retrieval undermines answer quality. | Manual spot-check with known-answer queries |

### Product Usefulness Metrics (Target)

| Metric | Target | Why It Matters | How to Measure |
|--------|--------|----------------|----------------|
| Time to useful answer | < 30 seconds for Ollama; < 15 seconds for cloud | Users abandon slow tools. | Stopwatch on demo queries |
| Essay generation completion | Ship 30 for 30 essay generated with all required elements present | The writing skill must produce a complete, well-structured artifact. | Manual review against Ship 30 for 30 criteria |
| Artifact render success | 100% of generated Markdown/HTML renders correctly in the Artifact Viewer | Broken rendering undermines trust. | Visual inspection of 5 generated artifacts |

### Operational Metrics (Acceptance)

| Metric | Target | Why It Matters | How to Measure |
|--------|--------|----------------|----------------|
| Fresh-clone startup | Evaluator can start the system using documented steps in < 10 minutes | Reproducibility is a hard requirement. | Follow README from a clean machine |
| Local demo (no cloud keys) | Full demo path works without any API keys | Evaluator should not need to sign up for anything. | Run demo with empty cloud-key configuration |
| Test suite pass rate | 100% | Automated tests are a deliverable. | `pytest` / equivalent test runner |
| Graceful degradation | All failure scenarios produce structured error messages, not crashes | The system must handle real-world failure modes. | Trigger each failure scenario manually |

---

## 5. Product Principles

1. **Grounding over generality.** A trustworthy answer sourced from one episode is more valuable than a fluent answer sourced from nowhere. We will always prefer "I don't have enough evidence for that" over plausible-sounding hallucination.

2. **Source traceability is a feature, not a footnote.** Every claim should be traceable to what was actually said on the podcast. Attribution is not a nice-to-have — it's the core trust mechanism.

3. **Local-first, cloud-ready.** The evaluator experience must work entirely offline with Ollama. Cloud providers add capability, not dependency.

4. **Opinionated simplicity over configurable complexity.** We make strong default choices (one agent framework, one database, one retrieval strategy) rather than building an abstraction layer for every possible option.

5. **Honest about boundaries.** The assistant tells you what it knows, what it doesn't, and where the evidence comes from. It never silently switches to general knowledge.

6. **Ship the handoff.** Documentation, reproducibility, and operational visibility are part of the product — not afterthoughts.

---

## 6. Target User and Core User Journey

### Primary User Profile

**Role:** Product Manager, Growth Lead, or Founder at a product-led company  
**Experience:** 2-10 years in product/growth roles  
**Context:** Preparing for a strategy discussion, researching a specific growth tactic, or writing an internal brief  
**Technical sophistication:** Can use a web application and evaluate an answer's quality, but should not need to understand prompts, models, or retrieval pipelines  
**Frequency:** Uses the tool when a specific product/growth question arises — perhaps 2-5 times per week during active research phases

### Core User Journey

```
┌─────────────────────────────────────────────────────────────┐
│  1. User opens the application and starts a new chat session │
│     → Session is created with a unique ID and persisted      │
├─────────────────────────────────────────────────────────────┤
│  2. User asks a product/growth question                      │
│     "What do the best growth teams look like according       │
│      to Lenny's guests?"                                     │
├─────────────────────────────────────────────────────────────┤
│  3. Agent determines the task type (Q&A)                     │
│     → Routes to retrieval + generation                       │
├─────────────────────────────────────────────────────────────┤
│  4. Relevant transcript chunks are retrieved                 │
│     → Ranked by relevance, with source metadata preserved    │
├─────────────────────────────────────────────────────────────┤
│  5. Retrieved evidence is evaluated for grounding            │
│     → If sufficient: generate answer                         │
│     → If insufficient: acknowledge gap                       │
├─────────────────────────────────────────────────────────────┤
│  6. Grounded answer is generated with source citations       │
│     "According to Elena Verna (episode X) and Andrew Chen    │
│      (episode Y), the best growth teams..."                  │
│     → Sources displayed with episode/guest information       │
├─────────────────────────────────────────────────────────────┤
│  7. User asks a follow-up question                           │
│     "How does that compare to what Brian Balfour said?"      │
│     → Session context is preserved                           │
│     → Retrieval is augmented with conversational history     │
├─────────────────────────────────────────────────────────────┤
│  8. User optionally requests content transformation          │
│     "Turn this into a Ship 30 for 30 essay"                  │
│     → Writing skill produces ~1,250-word essay               │
│     → Essay is grounded in transcript evidence               │
├─────────────────────────────────────────────────────────────┤
│  9. User optionally requests artifact generation             │
│     "Generate this as an HTML artifact"                      │
│     → Markdown or HTML/CSS artifact is generated             │
│     → Rendered safely in the in-app Artifact Viewer          │
└─────────────────────────────────────────────────────────────┘
```

**Why this workflow is prioritized:** It represents the highest-value path from question to actionable output. Each step addresses a real friction point (search → synthesis → reuse), and the optional content transformation and artifact generation extend the value without adding complexity to the core Q&A loop. The journey is linear and composable — every step builds on the previous one, and the user can exit at any point with a useful result.

---

## 7. Product Scope

### P0 — Core (Must-have for evaluator acceptance)

| Capability | Rationale |
|------------|-----------|
| Grounded transcript Q&A with source attribution | The primary product promise. Without this, there is no product. |
| Conversational follow-ups with session context | Assignment requirement; essential for natural research workflows. |
| Session persistence in PostgreSQL | Assignment requirement; conversations must survive server restarts. |
| Unsupported-question acknowledgment | Core trust mechanism; prevents hallucination. |
| Local Ollama demo | Mandatory for the submitted demo per assignment. |
| Cloud LLM integration (at least one) | Assignment requirement; distinct from Ollama. |
| Provider configuration without code changes | Assignment requirement; operational flexibility. |
| Knowledge base ingestion with source traceability | Foundation for grounded answers; assignment requirement. |
| FastAPI backend with structured errors and health endpoint | Assignment requirement; API quality. |
| Docker Compose one-command startup | Assignment requirement; reproducibility. |
| `.env.example` with safe defaults | Assignment requirement; no committed secrets. |

### P1 — Important for product usefulness

| Capability | Rationale |
|------------|-----------|
| Ship 30 for 30 writing skill | Assignment requirement; differentiates from "just search." |
| Markdown artifact generation | Assignment requirement; extends content reuse. |
| HTML/CSS artifact generation | Assignment requirement; enables rich rendering. |
| In-app Artifact Viewer with safe rendering | Assignment requirement; keeps the user in the application. |
| Meaningful automated tests | Assignment requirement; validates system behavior. |

### P2 — Hardening (Useful but deferrable)

| Capability | Rationale |
|------------|-----------|
| Rich structured logging and observability | Important for operations, not critical for demo. |
| Comprehensive resilience (all failure modes) | Core failure modes in P0; edge cases here. |
| UX polish and responsive design | Functional UI in P0; polish here. |
| Accessibility considerations | Important but depth can scale with time. |
| Corpus refresh automation | Initial load in P0; automated refresh is operational maturity. |
| Additional provider integrations | One cloud provider in P0; more here. |

### Out of Scope

| Exclusion | Reason |
|-----------|--------|
| Arbitrary web search / internet research | Weakens grounding; violates the corpus-boundary principle; adds implementation risk without proportionate value. |
| User-uploaded knowledge bases | Increases scope significantly; changes the retrieval architecture; the assignment specifies Lenny's transcripts. |
| Multi-tenant administration / RBAC | Enterprise complexity disproportionate to a take-home; no multi-user requirement in the assignment. |
| Autonomous background agents | The assignment requires a conversational assistant, not unsupervised agents; adds complexity without clear evaluator value. |
| Fine-tuning custom models | Off-the-shelf models with good retrieval are sufficient; fine-tuning introduces training infrastructure, data pipeline, and evaluation overhead. |
| Real-time podcast ingestion | The corpus is a static GitHub repository; real-time ingestion requires audio-to-text infrastructure unrelated to the core product value. |
| Mobile-native applications | Responsive web is sufficient; native apps multiply engineering effort without evaluator benefit. |
| Complex analytics dashboards | Usage analytics require production traffic; premature for a take-home. |
| External SaaS integrations (Slack, Notion, etc.) | Increases attack surface and dependency count without demonstrating core product judgment. |
| Kubernetes or microservice deployment | Docker Compose is explicitly preferred; K8s adds operational complexity without proportionate benefit for a single-machine demo. |

---

## 8. Functional Requirements

### 8.1 Conversational Assistant

**FR-1:** The user can start a new chat session via the UI. Each session receives a unique identifier.

**FR-2:** The user can send natural-language questions about product management and growth topics. The assistant responds with answers grounded in the transcript corpus.

**FR-3:** Follow-up questions within a session preserve conversational context. The system uses a bounded working window plus query rewriting to resolve references and pronouns (e.g., "What else did she say about that?" after discussing Elena Verna on growth teams), while the full conversation remains persisted and retrievable.

**FR-4:** The assistant displays source information (episode title, guest name, and relevant quote or excerpt reference) alongside every supported answer.

**FR-5:** The assistant explicitly acknowledges when the transcript corpus does not contain sufficient evidence to answer a question. It does not fall back to general LLM knowledge.

**FR-6:** The assistant handles ambiguous questions by asking for clarification or noting the ambiguity, rather than guessing.

### 8.2 Knowledge / Grounding

**FR-7:** The knowledge base is built from the transcripts in the [ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts) repository. The `episodes/` directory contains per-guest subdirectories with transcript markdown files.

**FR-8:** Transcripts are ingested with their metadata preserved: guest name, episode title, topics, and any YAML frontmatter. This metadata must be available for source attribution.

**FR-9:** Ingested content is chunked and indexed for semantic retrieval. The chunking strategy must balance:
- **Chunk size:** Large enough to preserve conversational context and argument structure; small enough for precise retrieval.
- **Overlap:** Sufficient to avoid splitting key arguments across chunk boundaries.
- **Metadata preservation:** Every chunk retains its source episode, guest, and position information.

**FR-10:** Retrieval returns the top-N most relevant chunks for a given query, ranked by semantic similarity. The number N should be configurable.

**FR-11:** A corpus refresh strategy must be defined. At minimum: a documented manual process to re-ingest from the repository. Automated refresh is P2.

**Assumption:** The transcript repository is relatively stable and does not change frequently enough to require real-time synchronization.

### 8.3 Session and Persistence

**FR-12:** Sessions, messages, timestamps, and user metadata are persisted in PostgreSQL.

**FR-13:** Each session maintains independent context. Messages from Session A do not leak into Session B.

**FR-14:** Conversation history is retrievable — a user can return to a previous session and see the full message history.

**FR-15:** Session metadata includes at minimum: session ID, creation timestamp, last activity timestamp, and message count.

**Decision:** Use a local PostgreSQL instance via Docker Compose rather than requiring Supabase or Railway. This ensures the evaluator doesn't need to create external accounts, and the demo is fully self-contained.

**Why:** Reproducibility and zero-external-dependency setup are more important for evaluator experience than the convenience of a hosted database.

**Trade-off:** We lose managed backups, connection pooling, and dashboard visibility that a hosted service provides. These are acceptable trade-offs for a take-home.

### 8.4 Agent and Model Configuration

**FR-16:** The agent layer is built using **Pi Coding Agent**.

**Decision:** Pi Coding Agent over Anthropic Claude Agent SDK.

**Why:** The assignment permits either. Pi Coding Agent provides a capable, model-agnostic agent framework that supports tool use and multi-step reasoning. This aligns with our local-first principle — the agent framework should not be coupled to a specific cloud provider's SDK.

**Rejected alternative:** Anthropic Claude Agent SDK — would more tightly couple the agent layer to Anthropic's model ecosystem, which conflicts with our requirement for configurable providers.

**FR-17:** The system supports at least three provider configurations:
1. **Ollama (local)** — mandatory for the submitted demo. Runs a locally available model (e.g., Llama 3, Mistral, or similar) that works comfortably on consumer hardware (P0 default).
2. **Anthropic Claude (cloud)** — selected P0 cloud provider when API keys are configured.
3. **OpenAI (cloud)** — conceptual P2 second-cloud extension.

**Assumption:** At minimum one cloud provider (Anthropic Claude is selected for P0) must be fully integrated. The second (OpenAI) is a P2 extension. Both are configurable via environment variables without code changes.

**FR-18:** The active provider is selected through environment configuration (e.g., `LLM_PROVIDER=ollama` or `LLM_PROVIDER=anthropic`). Switching providers requires only changing the configuration — no application code changes.

**FR-19:** The currently active provider is visible in the UI or system status, so the evaluator can confirm which model is in use.

**FR-20:** Fallback behavior when a configured provider is unavailable is documented. The system should produce a clear error message rather than silently failing or switching providers without user awareness.

**Trade-off: Local-first demo vs. cloud capability**

| Dimension | Ollama (Local) | Cloud (Claude/OpenAI) |
|-----------|---------------|----------------------|
| Evaluator setup | Zero cloud dependency, no API key needed | Requires account and API key |
| Inference quality | Dependent on local hardware; smaller models may produce weaker answers | Stronger models available (Claude Opus, GPT-4o) |
| Latency | Dependent on hardware; potentially slower | Generally faster with good connectivity |
| Cost | Free | Per-token cost |
| Privacy | No data leaves the machine | Data sent to cloud provider |
| Reproducibility | Highly reproducible | Subject to API availability and rate limits |

**Decision:** Default to Ollama for the submitted demo. The cloud provider path exists for evaluators who want to test with a stronger model.

**Why:** Reproducibility and zero-friction evaluator experience outweigh the potential quality improvement from cloud models for the demo path.

### 8.5 Ship 30 for 30 Skill

**FR-21:** The assistant includes a dedicated writing skill (not an ad-hoc prompt) that transforms grounded insights into a Ship 30 for 30-style essay.

**FR-22:** The writing skill encodes the actual Ship 30 for 30 principles rather than relying on a generic "write an essay" prompt. Key principles to encode:

1. **Strong hook** — The opening must immediately capture attention. Use a specific, counterintuitive, or provocative statement rather than a generic introduction. The Ship 30 for 30 methodology emphasizes that the hook determines whether anyone reads the rest.
2. **Clear narrative progression** — The essay follows a logical arc. Ship 30 for 30 encourages the 4A paths (Actionable, Analytical, Aspirational, Anthropological) and proven structural approaches (How-To steps, Lessons Learned, Mistakes, Frameworks). The skill should select an appropriate approach based on the content.
3. **Skimmable formatting** — Use headings, bullets, selective bold emphasis, and numbered lists. A reader should be able to scan the essay and extract value without reading every word. Ship 30 for 30 teaches that Digital Writers write for scanners first, readers second.
4. **Approximately 1,250 words** — Substantial enough to develop an argument but concise enough to hold attention.
5. **Specific, useful takeaway** — End with something the reader can actually do, not a vague conclusion. The Ship 30 for 30 framework insists on actionable endings.
6. **Claims grounded in the transcript knowledge base** — Every substantive claim should reference what was said on the podcast. The essay is a content artifact, not an opinion piece.
7. **Credibility framing** — Ship 30 for 30 identifies three types of credibility: "I'm the expert," "I'm curating the experts," and "I'm speaking from personal experience." For this skill, the credibility stance is always "curating the experts" — the essay synthesizes what Lenny's Podcast guests have said.

**FR-23:** The writing skill is invoked explicitly by the user (e.g., "turn this into a Ship 30 for 30 essay" or via a dedicated UI action). It uses the current conversation context and retrieved evidence as its source material.

**Decision:** The skill is a structured tool with encoded writing principles, not a one-off prompt.

**Why:** The assignment explicitly says to "read the linked source, identify the relevant writing principles, and encode them in the skill rather than relying on an unstructured one-off prompt." A well-defined skill is also more testable, maintainable, and consistent than prompt-level instructions.

### 8.6 Artifact Generation

**FR-24:** When requested, the assistant generates Markdown documents based on the current conversation and grounded evidence.

**FR-25:** When requested, the assistant generates complete HTML/CSS snippets — self-contained, renderable artifacts with appropriate styling.

**FR-26:** Generated artifacts include source attribution metadata — the user should know which transcript evidence informed the artifact.

**FR-27:** Generated HTML is treated as **untrusted output** (see §12 Security). The artifact generation pipeline does not inherently guarantee safe output; the rendering layer must enforce safety.

### 8.7 Artifact Viewer

**FR-28:** The frontend includes an Artifact Viewer that renders generated Markdown and HTML/CSS artifacts inline, alongside the chat interface (similar to Claude Artifacts). The viewer does not redirect to another application or display only raw code.

**FR-29:** The Artifact Viewer supports:
- Rendered Markdown (headings, lists, bold, italic, code blocks, links)
- Rendered HTML/CSS (layout, typography, color, basic interactivity)
- Copy-to-clipboard for the raw source

**FR-30:** Generated HTML is rendered in a sandboxed context (see §12). The viewer clearly separates trusted application UI from untrusted generated content.

---

## 9. Grounding and Trust Model

Grounding is the most important product characteristic of this assistant. It is a **product decision**, not merely an implementation detail. The user must be able to trust the boundary of the assistant's knowledge.

### Evidence Tiers and Expected Behavior

| Scenario | Expected Behavior |
|----------|-------------------|
| **A. Strong relevant evidence exists** | Answer using the evidence. Cite the specific episode(s) and guest(s). Use direct quotes or close paraphrases with attribution. |
| **B. Multiple relevant episodes exist** | Synthesize across episodes while preserving source traceability. Each distinct claim is attributed to its source. "Elena Verna emphasizes X (ep. 47), while Casey Winters argues Y (ep. 89)." |
| **C. Sources disagree or offer contrasting perspectives** | Explicitly surface the disagreement. Do not falsely merge conflicting views into one consensus opinion. "There are two schools of thought here: [Guest A] argues X because..., while [Guest B] counters with Y because..." |
| **D. Limited evidence exists** | Qualify the answer. "Based on limited discussion in [episode], [guest] briefly mentioned X, but this wasn't explored in depth. I'd recommend listening to the full episode for more context." |
| **E. No adequate evidence exists** | Clearly state that the available transcript material does not provide enough support to answer the question. Do not hallucinate. Do not switch to general knowledge. |
| **F. Question is outside the corpus** | Explain the corpus limitation. "My knowledge is limited to Lenny's Podcast transcripts. This question about [topic] isn't covered in the episodes I have access to." |

### Why This Is a Product Decision

General-purpose LLMs can answer almost any question — fluently and confidently — regardless of whether their answer is correct. For a research tool, this is dangerous. A product manager who quotes "what Elena Verna said" in a strategy presentation needs to know that Elena Verna actually said it.

By making grounding a hard product boundary, we:
- Prevent the assistant from becoming an unreliable oracle
- Give users a clear mental model of what the tool can and cannot do
- Make the failure mode ("I don't know") more useful than the alternative (plausible but wrong)
- Differentiate from generic chatbots that answer everything without accountability

**Assumption:** Users would rather get "I don't have enough evidence" than a confident but unsourced answer. This assumption is based on the product positioning as a research tool, not a brainstorming companion.

---

## 10. Failure and Unsupported-Question Behavior

The assistant must handle failure gracefully. Each failure mode should produce a structured, user-friendly response — not a crash, a generic error, or silence.

| Failure Scenario | Expected Behavior |
|-----------------|-------------------|
| **Empty retrieval** (no relevant chunks found) | "I searched through the Lenny's Podcast transcripts but couldn't find relevant discussion on [topic]. You might try rephrasing your question or asking about a related topic." |
| **Model timeout** | "The model took too long to respond. This can happen with complex questions on local hardware. Please try again, or consider switching to a cloud provider for faster responses." |
| **Ollama unavailable** | "The local Ollama service isn't available. Please ensure the Ollama container is running (`docker compose up ollama`) or switch to a cloud provider in the configuration." |
| **Missing API keys** (cloud provider selected but no key) | "Cloud provider [X] is selected but no API key is configured. Please add your API key to the `.env` file or switch to the Ollama provider for local inference." |
| **Database connection failure** | "Unable to connect to the database. Your message hasn't been saved. Please check the PostgreSQL service." |
| **Out-of-corpus question** | See §9, Scenario F. Transparent, helpful refusal. |
| **Ambiguous question** | "I want to make sure I give you the most relevant answer. Could you clarify whether you're asking about [interpretation A] or [interpretation B]?" |

**Decision:** Failure messages are specific and actionable, not generic. Each failure mode has a distinct response template.

**Why:** Generic "something went wrong" messages don't help users or evaluators diagnose problems. Specific messages demonstrate operational maturity and respect the user's time.

---

## 11. UX / Interaction Requirements

### Layout

**FR-31:** The application uses a split-pane layout:
- **Left/main pane:** Chat interface for conversational interaction
- **Right/side pane:** Artifact Viewer for rendering generated content (appears on demand)

**FR-32:** The chat interface supports:
- New session creation
- Message input with multiline support
- Streaming or chunked response display (the response appears progressively, not after a long wait)
- Clear visual distinction between user messages and assistant responses
- Source citations displayed inline or in a collapsible section
- Loading/thinking state indicator

**FR-33:** The application is responsive and usable on desktop screens. Mobile optimization is P2.

### Interaction States

**FR-34:** The UI clearly communicates:
- **Idle** — ready for input
- **Processing** — the assistant is thinking/generating
- **Error** — something went wrong, with a specific message
- **Artifact available** — a generated artifact can be viewed in the side pane

### Provider Visibility

**FR-35:** The active model/provider is visible in the UI (e.g., in a status bar or settings panel), so the evaluator can confirm which model is running.

---

## 12. Security and Safety Requirements

### Trust Boundaries

| Boundary | Classification | Rationale |
|----------|---------------|-----------|
| Transcript content | **Untrusted input** to the LLM | Transcripts may contain adversarial or confusing content that could influence model behavior. |
| LLM-generated text | **Untrusted output** | Model output may contain hallucinations, prompt injection payloads, or unsafe HTML. |
| Generated HTML/CSS artifacts | **Untrusted output** | Must be sandboxed before rendering in the application. |
| API credentials | **Secrets** | Never committed to the repository; loaded from environment variables. |
| User/session data | **Isolated** | Sessions must not leak across users or session boundaries. |

### Generated HTML Isolation Strategy

**FR-36:** Generated HTML artifacts are rendered in a sandboxed iframe with the `sandbox` attribute. The sandbox restricts:
- Script execution (`allow-scripts` NOT included by default)
- Form submission
- Navigation of the parent frame
- Access to parent DOM

**FR-37:** As an additional layer, generated HTML is sanitized before rendering to remove known dangerous elements and attributes (e.g., `<script>`, `onclick`, `onerror`, `javascript:` URIs).

**FR-38:** The Artifact Viewer clearly separates trusted application UI from untrusted generated content. The user should understand that the rendered content is generated, not part of the application itself.

**Decision:** Defense in depth — sandboxed iframe AND sanitization. Either layer alone has known bypasses; together they provide reasonable protection for a take-home scope.

**Why:** The assignment explicitly requires a "reasonable isolation or sanitization strategy." We choose both because the implementation cost is low and the security benefit is meaningful.

### Prompt Injection Mitigation

**FR-39:** Retrieved transcript content is passed to the LLM as clearly delimited context, not as system instructions. The system prompt explicitly instructs the model to treat retrieved content as source material to be analyzed, not as commands to be executed.

**FR-40:** The application does not execute arbitrary code or commands based on model output. Tool calls are restricted to predefined, validated tools.

### Secret Management

**FR-41:** The repository includes a `.env.example` file with safe defaults (e.g., Ollama as default provider, no real API keys). No real secrets are committed to version control. The `.gitignore` file excludes `.env`.

---

## 13. Non-Functional Requirements

| Requirement | Priority | Target | Rationale |
|-------------|----------|--------|-----------|
| **Reproducibility** | P0 | Fresh clone → working system in < 10 min using only documented steps | Core evaluator requirement. |
| **Reliability** | P0 | System handles all defined failure modes without crashing | Demonstrates operational maturity. |
| **Observability** | P1 | Structured JSON logs covering model calls, retrieval, DB operations, and errors | Enables diagnosis without a debugger. |
| **Maintainability** | P1 | Clear separation of concerns; modular agent/retrieval/persistence layers | Another engineer can understand and extend the code. |
| **Testability** | P1 | Critical paths covered by automated tests; manual test plan for UI | Assignment deliverable. |
| **Security** | P1 | Untrusted output sandboxed; secrets managed; sessions isolated | See §12. |
| **Responsiveness** | P2 | Streaming/progressive response display; < 30s for local, < 15s for cloud | Slow tools get abandoned. |
| **Accessibility** | P2 | Semantic HTML, keyboard navigation, sufficient color contrast | Good practice; evaluated but depth scales with time. |
| **Graceful degradation** | P0 | Missing services produce clear errors, not crashes | Assignment explicitly requires this for missing keys, unavailable Ollama, timeouts, empty retrieval, DB failures. |
| **Configuration** | P0 | All environment-specific values configurable via `.env`; no hardcoded secrets or provider URLs | Assignment requirement. |
| **Source traceability** | P0 | Every retrieved chunk preserves its origin metadata through the entire pipeline | Foundation of the grounding model. |

---

## 14. Assumptions

These assumptions are explicitly labeled because the client brief does not fully specify them. Each represents a reasonable default that should be validated if this product moves beyond the take-home.

| # | Assumption | Impact if Wrong | Mitigation |
|---|-----------|----------------|------------|
| A1 | The transcript repository is relatively stable — new episodes are added periodically, not continuously. | If transcripts change frequently, the corpus may become stale faster than expected. | Document the refresh process; design ingestion to be re-runnable. |
| A2 | A single user interacts with the system at a time during evaluation. We do not need concurrent multi-user support. | If multiple evaluators test simultaneously, session isolation bugs could surface. | Session isolation is enforced by design; concurrency testing is P2. |
| A3 | The evaluator's machine can run Ollama with a 7-8B parameter model (e.g., Llama 3 8B, Mistral 7B). | If the evaluator's hardware is too constrained, the local demo may be unusable. | Document hardware recommendations; ensure the cloud path is a clear fallback. |
| A4 | Transcript markdown files in the repository follow a consistent format with YAML frontmatter containing episode metadata (title, guest, topics). | If format is inconsistent, the ingestion pipeline may fail to extract metadata. | Build ingestion with defensive parsing; handle missing metadata gracefully. |
| A5 | Users ask questions that can be reasonably answered from podcast transcripts — not highly technical implementation questions or questions requiring real-time data. | If users expect the assistant to answer implementation questions (e.g., "write me a SQL query"), they will be disappointed. | Clear product positioning and onboarding copy set expectations. |
| A6 | One cloud LLM provider (Anthropic Claude selected for P0; OpenAI as P2 extension) is sufficient to satisfy the assignment requirement. | Minimal risk — the assignment says "at least one." | Implement the provider abstraction to make adding a second provider straightforward. |
| A7 | Ship 30 for 30 writing principles can be reliably encoded in a structured skill/tool definition rather than requiring model fine-tuning. | If the model consistently fails to follow the writing principles via prompting, output quality will suffer. | Provide explicit structural guidance (headings, word count targets, required elements) rather than relying on style mimicry. |
| A8 | PostgreSQL running in Docker Compose is sufficient for the evaluation. Hosted PostgreSQL (Supabase, Railway) is not required. | If the evaluator expects a hosted database, they may be confused. | Document the decision rationale; note hosted as a future option. |

---

## 15. Risks and Trade-offs

### Risk 1: Hallucination / Grounding Drift

**Likelihood:** Medium. LLMs are inherently prone to generating plausible but unsourced content, especially when retrieved evidence is tangentially relevant.

**Impact:** High. A hallucinated attribution ("Elena Verna said X" when she didn't) fundamentally breaks the product promise.

**Mitigation:**
- System prompt explicitly instructs the model to answer only from provided context
- Retrieved evidence is clearly delimited in the prompt
- The model is instructed to say "I don't have enough evidence" when context is insufficient
- Automated test cases validate refusal behavior on known out-of-corpus queries

**Residual risk:** No prompt-level mitigation is 100% reliable. Some hallucination is possible, especially with weaker local models.

**Trade-off:** Stronger grounding instructions reduce the model's flexibility and may cause it to refuse some answerable questions. We accept this because false refusal is less harmful than false attribution.

### Risk 2: Local Model Quality

**Likelihood:** High. 7-8B parameter models running on consumer hardware produce noticeably weaker outputs than cloud models (Claude Opus, GPT-4o).

**Impact:** Medium. Answers may be less coherent, less well-structured, or more prone to hallucination.

**Mitigation:**
- Choose the strongest model that runs comfortably on the target hardware
- Structure prompts to compensate for weaker model capability (shorter, more explicit instructions)
- Document the quality trade-off; provide the cloud path as an alternative
- Ship 30 for 30 skill uses explicit structural templates to compensate for model limitations

**Residual risk:** Some queries may produce unsatisfying answers on local hardware. This is an inherent trade-off of local-first.

### Risk 3: Cloud Model Cost

**Likelihood:** Low for evaluation (minimal queries). High for hypothetical production use.

**Impact:** Low for take-home. Could be significant at scale.

**Mitigation:** Cloud is optional and clearly documented as incurring per-token cost. Default is free local inference.

### Risk 4: Model Latency

**Likelihood:** Medium-High for local inference (dependent on hardware). Low for cloud.

**Impact:** Medium. Slow responses degrade UX and may cause evaluator frustration.

**Mitigation:** Streaming responses (progressive display). Clear loading indicators. Document expected latency ranges. Health endpoint includes model-readiness check.

### Risk 5: Retrieval Quality

**Likelihood:** Medium. Semantic search over conversational transcripts is harder than over structured documents. Transcripts contain filler, tangents, and loose conversational structure.

**Impact:** High. Poor retrieval means poor answers, regardless of model quality.

**Mitigation:**
- Thoughtful chunking strategy that respects conversational boundaries
- Metadata-enriched chunks (guest, episode, topic) to improve retrieval precision
- Configurable top-N to balance precision vs. recall
- Manual testing with known-answer queries during development

**Residual risk:** Some queries will retrieve partially relevant chunks, leading to weaker answers. This is inherent in RAG over conversational content.

### Risk 6: Long Transcript Context

**Likelihood:** Medium. Individual podcast transcripts can be very long (60-90 minutes of conversation), and some questions may require information spread across a transcript.

**Impact:** Medium. Context windows have limits; chunking necessarily loses some cross-transcript coherence.

**Mitigation:** Intelligent chunking with overlap. Episode-level metadata preserved so the user can go to the full source.

### Risk 7: Source Attribution Correctness

**Likelihood:** Medium. The model might attribute a statement to the wrong guest or episode, especially when multiple sources are retrieved.

**Impact:** High. Incorrect attribution is worse than no attribution.

**Mitigation:** Attribution metadata is passed alongside the content, not generated by the model. The model is instructed to reference the provided metadata, not to invent source information.

### Risk 8: Conflicting Transcript Advice

**Likelihood:** Medium-High. Different guests on Lenny's Podcast genuinely disagree on topics like growth strategy, pricing, hiring, etc.

**Impact:** Medium. Falsely merging conflicting views into one consensus undermines trust.

**Mitigation:** The grounding model (§9, Scenario C) explicitly requires surfacing disagreements rather than synthesizing false consensus.

### Risk 9: Stale Corpus

**Likelihood:** Low for the take-home (static corpus). Medium for hypothetical ongoing use.

**Impact:** Low. The corpus represents accumulated wisdom, not time-sensitive data.

**Mitigation:** Document the refresh process. Design ingestion to be re-runnable.

### Risk 10: Database Failure

**Likelihood:** Low (Docker-managed PostgreSQL is reliable for single-machine use).

**Impact:** Medium. Messages won't be persisted; sessions won't load.

**Mitigation:** Health endpoint checks DB connectivity. Structured error messages on connection failure. Docker Compose restart policies.

### Risk 11: Ollama Unavailable

**Likelihood:** Medium (evaluator may not have Ollama installed, or may not have pulled the required model).

**Impact:** High. Blocks the primary demo path.

**Mitigation:** README includes explicit Ollama setup instructions. Docker Compose includes Ollama as a containerized service by default. Clear error message when Ollama is unreachable. Cloud provider documented as alternative.

### Risk 12: Model Timeout

**Likelihood:** Medium (especially with complex queries on local hardware).

**Impact:** Medium. User waits indefinitely or gets an unhelpful error.

**Mitigation:** Configurable timeout. Structured timeout error with actionable suggestion. Streaming response to show progress.

### Risk 13: Missing API Keys

**Likelihood:** Medium (evaluator may not configure cloud keys).

**Impact:** Low if Ollama default works. High if only cloud is available and keys are missing.

**Mitigation:** Default to Ollama (no keys required). Clear error message when cloud provider is selected but keys are absent. `.env.example` documents which keys are optional vs. required.

### Risk 14: Generated HTML Security

**Likelihood:** Medium. LLMs can generate HTML containing scripts, event handlers, or other active content.

**Impact:** High if unsandboxed. Could lead to XSS in the application context.

**Mitigation:** Sandboxed iframe rendering + HTML sanitization. See §12 for details.

**Why proportionate:** Two defense layers (sandbox + sanitization) is reasonable for a take-home. A production system might add CSP headers, separate-origin rendering, and more sophisticated sanitization.

### Risk 15: Prompt Injection via Transcript Content

**Likelihood:** Low-Medium. Transcript content is from real podcast conversations, not adversarial. However, transcripts could inadvertently contain patterns that influence model behavior.

**Impact:** Medium. Could cause the model to ignore system instructions or produce unexpected output.

**Mitigation:** Retrieved content is clearly delimited from system instructions. The system prompt explicitly marks retrieved text as "source material to analyze" rather than "instructions to follow."

**Residual risk:** No delimiter-based approach is fully robust against sophisticated injection. Proportionate for the corpus and use case.

### Risk 16: Sensitive Data / Secret Leakage

**Likelihood:** Low. The transcript corpus is publicly available. The main risk is accidental API key commits.

**Impact:** High if API keys are leaked.

**Mitigation:** `.gitignore` excludes `.env`. `.env.example` contains only placeholder values. Pre-commit checks recommended. Agent transcripts must be scrubbed before commit (per assignment requirement).

### Risk 17: Over-Engineering the Agent Layer

**Likelihood:** Medium. It's tempting to build a sophisticated multi-agent system with complex routing.

**Impact:** Medium. Increases implementation time, debugging difficulty, and evaluator comprehension effort.

**Mitigation:** Start with the simplest agent architecture that satisfies the requirements: one agent with distinct tools for Q&A, writing, and artifact generation. Add complexity only when a concrete requirement demands it.

**Decision:** Favor a single-agent, multi-tool architecture over a multi-agent system.

**Why:** The assignment requires clear skill boundaries, not agent-to-agent coordination. A single agent with well-defined tools is simpler to build, test, debug, and explain.

### Risk 18: Evaluation/Demo Reliability

**Likelihood:** Medium. Docker, Ollama, and model downloads can fail in unfamiliar environments.

**Impact:** High. If the evaluator can't start the system, nothing else matters.

**Mitigation:** Tested on a clean machine. Minimal dependencies. Clear prerequisites. Health endpoint. Troubleshooting section in README.

### Risk 19: Scope Creep

**Likelihood:** High (inherent in take-home assignments with broad requirements).

**Impact:** High. Trying to build everything results in nothing working well.

**Mitigation:** Explicit P0/P1/P2 prioritization. Scope boundaries documented. Features deferred with reasoning.

### Risk 20: Operational Handoff

**Likelihood:** Low (documentation is a deliverable we control).

**Impact:** Medium. Poor documentation means the evaluator can't understand or extend the system.

**Mitigation:** README, architecture.md, design.md, inline code documentation, and this PRD. The handoff documentation is part of the product, not an afterthought.

---

## 16. Key Product and Architecture Decisions

### Decision 1: Pi Coding Agent over Anthropic Claude Agent SDK

**Choice:** Pi Coding Agent  
**Rejected:** Anthropic Claude Agent SDK  
**Rationale:** Pi Coding Agent is model-agnostic, which aligns with the assignment's requirement for configurable LLM providers. Using the Claude Agent SDK would couple the agent framework to Anthropic's ecosystem, making Ollama and OpenAI integration less natural. Pi Coding Agent allows us to use any model as the agent's backbone while maintaining a consistent tool interface.

### Decision 2: Local PostgreSQL via Docker Compose over Hosted Database

**Choice:** Docker Compose-managed PostgreSQL  
**Rejected:** Supabase, Railway  
**Rationale:** The assignment permits but does not require hosted databases. A Docker Compose-managed instance eliminates external account requirements, ensures reproducibility, and simplifies the evaluator's setup. Hosted PostgreSQL remains a viable deployment option for production use.

### Decision 3: Local-First Demo Default

**Choice:** Ollama as the default provider in the submitted demo  
**Rejected:** Cloud-first default  
**Rationale:** Zero cloud dependency during evaluation means no API keys, no cost, no external service availability risk. The evaluator experience is fully controlled and reproducible. Cloud providers are available as opt-in alternatives.

### Decision 4: Single Agent with Multiple Tools over Multi-Agent System

**Choice:** One agent with tools for Q&A, writing, and artifact generation  
**Rejected:** Multiple specialized agents with an orchestrator  
**Rationale:** The product has three skills (Q&A, writing, artifact generation) that share the same conversational context. A single agent with tool routing is simpler to build, test, and debug. The assignment evaluates "clear skill boundaries" and "reliable routing" — which is achievable with tool definitions, not agent-to-agent communication.

### Decision 5: Sandboxed Iframe + Sanitization for Artifact Security

**Choice:** Defense in depth — sandboxed `<iframe>` AND HTML sanitization  
**Rejected:** Sanitization alone; Sandbox alone; Separate-origin rendering  
**Rationale:** Either layer alone has known bypasses. Together they provide reasonable security for a take-home. Separate-origin rendering (serving artifacts from a different domain) is more secure but adds deployment complexity disproportionate to the scope.

### Decision 6: RAG over Long-Context Window

**Choice:** Retrieval-Augmented Generation with chunked embeddings  
**Rejected:** Loading entire transcripts into a long context window  
**Rationale:** The total corpus is too large for any single context window. Even individual episodes can be 30,000+ tokens. RAG provides precise, efficient retrieval from the full corpus while keeping each request within model limits. Long-context approaches would require selecting a single episode upfront, which defeats the cross-episode synthesis capability.

---

## 17. Acceptance Criteria

### Session Management

**AC-1:** Given a user opens the application, when they click "New Chat," then a new session is created with a unique ID, persisted in PostgreSQL, and the chat interface is ready for input.

**AC-2:** Given two active sessions (A and B), when a message is sent in Session A, then Session B's conversation history is not affected.

**AC-3:** Given a session with 5 messages, when the server is restarted and the user returns to the session, then all 5 messages are displayed in order with correct timestamps.

### Grounded Retrieval and Q&A

**AC-4:** Given a question about a topic covered in the transcripts (e.g., "What did Brian Chesky say about founder mode?"), when the assistant responds, then the response includes at least one specific source citation (episode/guest).

**AC-5:** Given a question about a topic NOT covered in the transcripts (e.g., "What's the best recipe for chocolate cake?"), when the assistant responds, then the response clearly states that the transcript corpus does not contain relevant information. It does not hallucinate an answer.

**AC-6:** Given a follow-up question that references a previous answer (e.g., "What else did she say?"), when the assistant responds, then it correctly resolves the reference using session context.

### Provider Switching

**AC-7:** Given `LLM_PROVIDER=ollama` in the environment configuration, when the user sends a query, then the response is generated using the local Ollama model.

**AC-8:** Given `LLM_PROVIDER=anthropic` and a valid `ANTHROPIC_API_KEY`, when the user sends a query, then the response is generated using Anthropic Claude.

**AC-9:** Given `LLM_PROVIDER=anthropic` and NO `ANTHROPIC_API_KEY`, when the system starts, then a clear error message indicates the missing API key.

### Ollama Demo

**AC-10:** Given a fresh clone of the repository and Ollama installed with the documented model, when `docker compose up` is executed, then the system starts and serves the application without requiring any cloud API keys.

### Failure Handling

**AC-11:** Given Ollama is not running, when the user sends a query with `LLM_PROVIDER=ollama`, then the response is a structured error explaining that Ollama is unavailable, with instructions to start it.

**AC-12:** Given the PostgreSQL container is stopped, when the user sends a query, then the response is a structured error indicating the database connection failure.

**AC-13:** Given a query that retrieves no relevant chunks, when the assistant responds, then it acknowledges the lack of evidence rather than generating an unsourced answer.

### Ship 30 for 30 Writing Skill

**AC-14:** Given a grounded Q&A exchange, when the user requests "Turn this into a Ship 30 for 30 essay," then the assistant generates an essay that:
- Is approximately 1,250 words (±200 words)
- Opens with a strong hook (not a generic introduction)
- Follows a clear narrative progression with headings
- Uses skimmable formatting (bullets, bold emphasis)
- Ends with a specific, useful takeaway
- Grounds substantive claims in transcript sources

### Artifact Generation

**AC-15:** Given a conversation with grounded content, when the user requests a Markdown artifact, then a valid Markdown document is generated and renderable in the Artifact Viewer.

**AC-16:** Given a conversation with grounded content, when the user requests an HTML/CSS artifact, then a complete, self-contained HTML/CSS document is generated and rendered safely in the Artifact Viewer.

### Artifact Viewer

**AC-17:** Given a generated Markdown artifact, when displayed in the Artifact Viewer, then headings, lists, bold text, and code blocks render correctly.

**AC-18:** Given a generated HTML artifact containing a `<script>` tag, when displayed in the Artifact Viewer, then the script does NOT execute (sandboxing is enforced).

### PostgreSQL Persistence

**AC-19:** Given a session with messages, when the PostgreSQL database is queried directly, then session records, message records, and timestamps are present and correctly structured.

### API Quality

**AC-20:** Given an invalid request body, when submitted to the API, then a structured JSON error response is returned with a 4xx status code and a descriptive error message.

**AC-21:** Given a `GET /health` request, when the system is operational, then a 200 response with database connectivity and model availability status is returned.

### Docker Compose and Configuration

**AC-22:** Given a fresh clone with only `.env.example` copied to `.env`, when `docker compose up` is executed, then all services start without errors (assuming Ollama is installed per documentation).

**AC-23:** Given the `.env.example` file, then it contains all configurable variables with safe defaults and no real secrets.

### Observability

**AC-24:** Given a query that triggers retrieval, model inference, and database persistence, when the structured logs are examined, then each step is logged with sufficient detail to diagnose issues (timestamp, operation, duration, outcome).

### Automated Tests

**AC-25:** Given the test suite, when executed with the documented test command, then all tests pass, covering at minimum: API endpoint behavior, retrieval correctness, session isolation, provider configuration, and error handling.

---

## 18. Implementation Phases

These phases are organized around product capability and risk reduction, not technology layers.

### Phase 1 — Foundation & Product Contract

**Objective:** Establish the project structure, database schema, API skeleton, and product contract.

**Capabilities:**
- PRD, architecture.md, design.md drafted
- FastAPI application skeleton with health endpoint
- PostgreSQL schema for sessions and messages
- Docker Compose configuration for all services
- `.env.example` with safe defaults
- Basic structured logging

**Key validation:** `docker compose up` starts all services; health endpoint returns 200.

**Exit criteria:** A fresh clone can start the system, hit the health endpoint, and confirm database connectivity.

**Risks addressed:** Reproducibility, evaluator first-impression, database foundation.

### Phase 2 — Transcript Knowledge Pipeline

**Objective:** Ingest Lenny's Podcast transcripts into a searchable knowledge base with full source traceability.

**Capabilities:**
- Transcript loading from the repository
- Metadata extraction from YAML frontmatter and directory structure
- Chunking strategy with configurable chunk size and overlap
- Embedding generation and vector indexing
- Semantic search endpoint
- Source metadata preserved through the pipeline

**Key validation:** A known-answer query retrieves relevant chunks with correct source attribution.

**Exit criteria:** Retrieval returns relevant, source-attributed chunks for 10 test queries.

**Risks addressed:** Retrieval quality, source traceability, chunking correctness.

### Phase 3 — Agent Layer & Model Routing

**Objective:** Establish the Pi Coding Agent framework with configurable model providers.

**Capabilities:**
- Pi Coding Agent integration with tool definitions
- Ollama provider (default local)
- Cloud provider (Anthropic Claude as P0 cloud provider; OpenAI as P2 extension)
- Provider switching via environment configuration
- System prompt with grounding instructions
- Provider visibility in status/config

**Key validation:** Same query produces an answer using Ollama and using a cloud provider (if key available).

**Exit criteria:** Provider switching works without code changes; agent routes to the correct model.

**Risks addressed:** Provider configuration, agent framework viability, local-first demo.

### Phase 4 — Grounded Conversational Assistant

**Objective:** Deliver the core Q&A experience with grounding, source attribution, and follow-up support.

**Capabilities:**
- End-to-end Q&A: question → retrieval → generation → sourced answer
- Session context preservation for follow-up questions
- Source citation display (episode, guest)
- Unsupported-question acknowledgment
- Conversation persistence in PostgreSQL
- Basic chat UI

**Key validation:** Full conversational flow works end-to-end; unsupported questions are refused; follow-ups use context.

**Exit criteria:** All AC-1 through AC-6 pass.

**Risks addressed:** Grounding drift, hallucination, session isolation, core product promise.

### Phase 5 — Ship 30 for 30 Writing Skill

**Objective:** Implement the dedicated content writing skill as a structured tool.

**Capabilities:**
- Ship 30 for 30 writing tool with encoded principles
- Invocation from conversational context
- ~1,250-word output with hook, progression, formatting, takeaway
- Grounded claims with source references
- Integration with agent tool routing

**Key validation:** Generated essay meets all Ship 30 for 30 criteria (AC-14).

**Exit criteria:** Three test essays reviewed against the criteria checklist.

**Risks addressed:** Writing quality, skill encoding vs. ad-hoc prompting.

### Phase 6 — Artifact Generation & Viewer

**Objective:** Enable Markdown and HTML/CSS artifact generation with safe in-app rendering.

**Capabilities:**
- Markdown artifact generation
- HTML/CSS artifact generation
- Artifact Viewer (side pane)
- Sandboxed iframe rendering
- HTML sanitization
- Copy-to-clipboard
- Raw source view toggle

**Key validation:** Generated artifacts render correctly; `<script>` tags are blocked; sandbox is enforced (AC-15 through AC-18).

**Exit criteria:** Artifacts render safely; no script execution in the viewer.

**Risks addressed:** Generated HTML security, XSS, rendering correctness.

### Phase 7 — UX Polish

**Objective:** Elevate the UI from functional to polished.

**Capabilities:**
- Streaming response display
- Loading/thinking indicators
- Error state UI (specific messages, not generic)
- Responsive layout refinements
- Session management UI (list, switch, create sessions)
- Provider indicator in UI
- Keyboard accessibility basics

**Key validation:** Evaluator can navigate the full workflow without confusion.

**Exit criteria:** UI is clean, states are clear, errors are specific.

**Risks addressed:** Evaluator impression, UX confusion, accessibility basics.

### Phase 8 — Hardening, Observability & Handoff

**Objective:** Ensure the system is robust, observable, tested, and well-documented.

**Capabilities:**
- Comprehensive structured logging (model calls, retrieval, DB, errors)
- All failure modes handled gracefully (AC-11 through AC-13)
- Meaningful automated test suite (AC-25)
- Manual UI test plan
- README finalized with architecture overview, setup, troubleshooting
- architecture.md and design.md finalized
- Agent transcripts collected and scrubbed
- Demo video recorded

**Key validation:** Test suite passes; fresh-clone setup works; all failure scenarios produce correct error messages.

**Exit criteria:** All acceptance criteria pass. Repository is ready for submission.

**Risks addressed:** Operational handoff, demo reliability, test coverage, documentation completeness.

---

## 19. Open Questions / Future Decisions

These are questions that could influence implementation but do not need to be resolved before work begins. They should be tracked and decided as they become relevant.

| # | Question | Default Assumption | When to Decide |
|---|----------|-------------------|----------------|
| Q1 | Which specific Ollama model should be the default? | Llama 3 8B (good balance of quality and hardware requirements) | Phase 3, after testing on target hardware |
| Q2 | What embedding model should we use for vector indexing? | `nomic-embed-text` (768 dimensions) via Ollama — fixed for all generation providers; resolved in architecture.md §3.2 A-4 | Resolved |
| Q3 | Should the vector store be a dedicated system (e.g., ChromaDB, pgvector) or an in-memory solution? | pgvector extension for PostgreSQL (single database dependency) | Phase 2, during architecture design |
| Q4 | How should we handle transcripts that lack YAML frontmatter? | Fall back to directory-name parsing for guest name; mark metadata as incomplete | Phase 2, during ingestion |
| Q5 | Should the cloud provider integration support both Anthropic AND OpenAI, or just one? | Anthropic Claude is the selected P0 cloud provider; OpenAI is a P2 extension | Phase 3 |
| Q6 | What chunk size and overlap work best for conversational transcripts? | ~600-token chunks, 100-token overlap (refined in architecture.md §7; validation against 400-token alternative planned in §25.2) | Resolved — see architecture.md |
| Q7 | Should the frontend be a separate React/Next.js application or server-rendered? | Separate frontend (React/Vite) communicating with the FastAPI backend via API | Phase 1, during project setup |

---

## 20. Definition of Done

The product is complete and ready for submission when:

- [x] All P0 and P1 capabilities are implemented and functional
- [x] All acceptance criteria (AC-1 through AC-25) pass
- [x] `docker compose up` starts the full system from a fresh clone
- [x] The Ollama demo path works without any cloud API keys
- [x] At least one cloud LLM provider is integrated and functional (with appropriate key)
- [x] Ship 30 for 30 essays meet the writing criteria
- [x] Artifact Viewer renders Markdown and HTML safely
- [x] Generated HTML is sandboxed (script execution blocked)
- [x] PostgreSQL persists sessions, messages, and metadata
- [x] Structured logging covers model, retrieval, database, and error events
- [x] Automated test suite passes (80 pytest + 8 Vitest = 88 tests)
- [x] Manual UI test plan is documented (docs/manual_ui_test_plan.md)
- [x] README enables a fresh evaluator to set up, run, test, and troubleshoot
- [x] architecture.md documents the system design
- [x] design.md documents UI/UX decisions
- [x] Agent transcripts are collected and scrubbed of secrets (agent_transcripts/)
- [x] `.env.example` is complete with safe defaults
- [x] No secrets are committed to the repository
- [ ] 2-3 minute demo video is recorded and uploaded (Evaluator submission step)
- [x] Repository structure ready for public GitHub release

---

*This PRD serves as the authoritative product contract for The Lenny Growth Assistant. Implementation decisions should reference this document. Significant deviations require updating the PRD with rationale.*
