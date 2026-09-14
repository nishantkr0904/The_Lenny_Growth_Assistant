# DECISIONS.md — Architecture Decision Records

> **Purpose**: Log significant technical and architectural decisions, rationale, and consequences.

---

## Decisions Log

### [DECISION-001] Pi Coding Agent as Cognitive Core with Production Bridge Validation Spike

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
The Take-Home Assignment allows choosing between the Anthropic Claude Agent SDK and Pi Coding Agent. The assistant must support local Ollama inference (`llama3.1:8b`) as the mandatory demo default and cloud providers as configurable alternatives.

#### Decision
Select Pi Coding Agent (`@earendil-works/pi-coding-agent 0.85.1`) as the cognitive core. Treat the production FastAPI-to-Pi stdio JSON-RPC bridge (`bridge.ts` / `bridge_client.py`) as an unvalidated implementation risk, requiring a minimal standalone validation spike in Phase P0.4 before building the full agent subsystem.

#### Rationale
- Pi Coding Agent is model-agnostic, natively interfacing with Ollama, Anthropic, and other providers without vendor lock-in.
- A completed local spike validated Pi 0.85.1 running with Ollama, registering a project-local custom retrieval tool, invoking it, receiving evidence, and producing a grounded response with clean interactive termination.
- The production stdio JSON-RPC bridge has not yet been validated and requires an explicit validation gate in P0.4.

#### Consequences
- Backend container requires a dual Python 3.11 + Node.js 20 runtime.
- If stdio JSON-RPC proves brittle under async FastAPI concurrency, fallback architecture wraps Pi in a lightweight local Express.js HTTP sidecar.

---

### [DECISION-002] Local PostgreSQL 16 + pgvector as Single Persistence Engine

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
The product requires storing relational state (sessions, messages, source citations) alongside high-dimensional vector embeddings for transcript chunks.

#### Decision
Use a single containerized PostgreSQL 16 instance with the `pgvector` extension (`pgvector/pgvector:pg16`). Reject dedicated vector databases (Pinecone, Qdrant, Chroma).

#### Rationale
- Eliminates dual-database synchronization, two connection pools, and distributed transaction complexity.
- Keeps deployment completely reproducible locally via standard Docker Compose without external SaaS accounts.
- HNSW cosine index (`<=>`) delivers sub-25ms retrieval over the full transcript corpus.

#### Consequences
- Vector queries and relational joins can execute in a single ACID transaction.
- Single database volume to back up or restore.

---

### [DECISION-003] Decoupled Model Architecture with Fixed 768-Dim Embeddings

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
The assignment requires flexible LLM configuration where the evaluator can switch the generation model without code changes. Switching models could potentially invalidate vector embeddings if generation and embeddings are coupled.

#### Decision
Strictly separate `GenerationProvider` from `EmbeddingProvider`. Fix `EmbeddingProvider` to Ollama `nomic-embed-text` generating 768-dimensional vectors stored in `VECTOR(768)`. Changing `LLM_PROVIDER` toggles generation only.

#### Rationale
- Re-indexing the entire transcript corpus upon every model change is slow, brittle, and unnecessary.
- 768-dimensional embeddings provide high semantic density and fast HNSW search.
- Zero silent model fallbacks: if the active generation provider fails, emit an explicit RFC 7807 error.

#### Consequences
- Ollama must always have `nomic-embed-text` pulled, even when cloud generation is active.
- Vector indices remain permanently valid across all generation providers.

---

### [DECISION-004] Anthropic Claude as P0 Cloud Provider; OpenAI Deferred to P2

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
The assignment requires at least one cloud provider in addition to local Ollama. We must define the scope boundaries for P0 versus future extensions.

#### Decision
Implement Anthropic Claude (`claude-3-5-sonnet-20241022`) as the sole cloud generation provider for P0. Design the `GenerationProvider` interface to accommodate OpenAI GPT-4o conceptually, but defer all OpenAI implementation to P2.

#### Rationale
- Satisfies all assignment requirements with one high-quality cloud provider.
- Prevents premature abstraction and avoids maintaining unnecessary API keys or stubs in P0.
- Keeps P0 focused on core grounding, retrieval, and evaluator reproducibility.

#### Consequences
- No `openai` SDK dependency in P0.
- `LLM_PROVIDER` in P0 supports `ollama` and `anthropic`.

---

### [DECISION-005] Deterministic 4-Tier Grounding Gate

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
LLMs are untrusted reasoning engines prone to hallucination when evidence is sparse or ambiguous. We need a deterministic gate to triage evidence before invoking the model.

#### Decision
Implement a deterministic Grounding Gate outside the LLM with 4 canonical tiers:
1. **Strong Evidence** ($\max(\text{score}) \ge 0.78$): Full synthesis with citations.
2. **Limited Evidence** ($0.65 \le \max(\text{score}) < 0.78$): Qualified answer highlighting evidence limitations.
3. **Conflicting Evidence**: Divergent viewpoints across distinct guests/episodes surfaced explicitly.
4. **Insufficient Evidence** ($\max(\text{score}) < 0.65$ or empty): Deterministic refusal without invoking the LLM.

Canonical threshold parameter: `GROUNDING_LIMITED_THRESHOLD = 0.65` (all legacy `weak` references removed; no aliases).

#### Rationale
- Refusing unsupported questions before calling the LLM saves tokens, reduces latency to <5ms, and guarantees zero hallucinated answers for out-of-domain queries.
- Clear, unambiguous terminology aligns product, architecture, and code.

#### Consequences
- Out-of-domain queries return immediate honest refusals with zero LLM inference cost.
- Thresholds are configurable via `.env` to allow empirical calibration.

---

### [DECISION-006] Conversational Flow Order: Query Rewriting Upstream of Retrieval

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
Multi-turn conversational follow-up questions often contain ambiguous references or pronouns (e.g., "What else did she say about that?").

#### Decision
Enforce the canonical pipeline sequence:
`User Question → Session Context → Query Rewriting / Reference Resolution → Vector Retrieval → Deterministic Grounding Gate → Pi/Model Synthesis → Citation Validation → Response`.

#### Rationale
- Retrieval must search for the resolved semantic concept, not the ambiguous pronoun.
- Grounding Gate must evaluate evidence retrieved for the rewritten query, not evaluate prior to retrieval.

#### Consequences
- The query rewriter uses the last $N=6$ conversation turns to formulate an expanded standalone query for pgvector.

---

### [DECISION-007] Container-to-Container PostgreSQL Communication on Standard Port

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
Docker Compose allows port mapping for host access. If the host port mapping modifies the internal connection string, container-to-container communication can break.

#### Decision
Keep internal backend-to-postgres communication strictly on the standard internal PostgreSQL port (`postgres:5432`). Support `HOST_PORT_POSTGRES=5432` as an optional host-side mapping only, without altering `DATABASE_URL`.

#### Rationale
- Prevents host port conflicts from breaking internal Docker container networking.
- Ensures identical behavior across different host operating systems and container setups.

#### Consequences
- Internal `DATABASE_URL` is consistently `postgresql+asyncpg://postgres:postgres@postgres:5432/lenny_assistant`.
- Host developers can connect to `localhost:${HOST_PORT_POSTGRES:-5432}` for local tooling.

---

### [DECISION-008] Dual-Origin Sandboxed Iframe + Bleach Sanitization for Artifact Rendering [P1]

**Date**: 2026-09-14  
**Status**: Accepted (Scheduled for P1)  

#### Context
The assistant generates Markdown and HTML/CSS artifacts. Generated HTML is untrusted and could introduce Cross-Site Scripting (XSS) or parent window DOM access.

#### Decision
Implement defense-in-depth:
1. Server-side HTML sanitization using Bleach (stripping `<script>`, `onload`, `onerror`, etc.).
2. Client-side rendering inside an `<iframe>` with `sandbox=""` (opaque `null` origin, completely disabling scripts, forms, and same-origin access) and strict CSP (`default-src 'none'; style-src 'unsafe-inline'`).

#### Rationale
- Neither layer alone provides complete security against advanced bypasses; together they provide airtight isolation for untrusted LLM-generated HTML.

#### Consequences
- Script execution is impossible inside the Artifact Viewer.
- CSS styling renders cleanly without affecting the host application styles.

---

### [DECISION-009] Modular Monolith Backend with React 18 / Vite Frontend

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
System architecture must balance development velocity, evaluator comprehension, and operational simplicity.

#### Decision
Build a modular monolith FastAPI application communicating with a decoupled React 18 + Vite frontend via REST and SSE. Reject microservices and distributed queues.

#### Rationale
- Eliminates distributed tracing, network serialization overhead, and multiple container failure points.
- Enables clear module boundaries in a single clean repository that an evaluator can understand in minutes.

#### Consequences
- Single backend container with clear directory structure (`app/api`, `app/core`, `app/db`, `app/services`, `app/agent`).

---

### [DECISION-010] Speaker-Aware Semantic Chunking

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
Lenny's Podcast transcripts are long conversational dialogues. Arbitrary fixed-token chunking cuts mid-sentence or separates speaker questions from answers.

#### Decision
Chunk transcripts into ~600-token blocks with 100-token overlap, respecting conversational turn boundaries, speaker labels (`Lenny:`, `Guest:`), and episode frontmatter metadata. Hash each chunk with SHA-256 for deduplication.

#### Rationale
- Preserves context of conversational exchanges while keeping chunks small enough for precise semantic retrieval.
- Enables exact sentence-level citation tracing back to the source transcript.

#### Consequences
- Ingestion pipeline maintains chunk index and speaker attribution per segment.

---

### [DECISION-011] Local-First Zero-Key Demo Default with Containerized Ollama

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
The assignment explicitly requires the submitted demo to run on local Ollama. Evaluators may not have pre-installed Ollama or cloud API keys.

#### Decision
Include Ollama as a standard service in `docker-compose.yml`. The default `.env.example` pre-configures `LLM_PROVIDER=ollama` and requires zero cloud keys.

#### Rationale
- Guarantees 100% reproducible zero-friction evaluation on any machine with Docker Desktop.
- Eliminates cloud service costs and network dependency during grading.

#### Consequences
- The initial startup downloads Ollama models (`llama3.1:8b` and `nomic-embed-text`) into a persistent Docker volume.

---

### [DECISION-012] RFC 7807 Structured Problem Details and No Silent Fallbacks

**Date**: 2026-09-14  
**Status**: Accepted  

#### Context
API errors must be actionable and informative for evaluators and client applications. Silent fallbacks (e.g., falling back to another model when cloud fails) mask critical configuration errors.

#### Decision
Adopt RFC 7807 Problem Details for all HTTP error responses (`type`, `title`, `status`, `detail`, `instance`). Strictly prohibit silent model fallbacks.

#### Rationale
- If Anthropic Claude is requested but the API key is missing or invalid, fail immediately with an explicit 401/502 error instructing how to configure `.env`.
- Prevents confusing silent degradation and makes troubleshooting immediate.

#### Consequences
- Clear, machine-readable error responses across all API endpoints.

---

*Last updated: 2026-09-14*
