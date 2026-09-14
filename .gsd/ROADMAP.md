---
milestone: v0.1
version: 0.1.0
updated: 2026-09-14T14:00:00Z
---

# Roadmap

> **Current Phase:** P0.3 — Vector Retrieval & Deterministic Grounding Gate  
> **Status:** Ready to Plan / Execute  
> **Immediate Target:** Phase P0.3  

---

## Validation Status Boundary

```
VALIDATED BY SPIKE
─────────────────────────────────────────────
• Pi 0.85.1 execution against Ollama (llama3.1:8b)
• Project-local custom retrieval tool registration
• Tool invocation by Pi upon receiving user turn
• Ingestion of retrieval evidence returned by tool
• Grounded answer synthesis referencing evidence
• Multi-turn follow-up handling preserving context
• Clean interactive process lifecycle

NOT YET VALIDATED (IMPLEMENTATION-RISK ITEMS)
─────────────────────────────────────────────
• Production FastAPI-to-Pi stdio JSON-RPC bridge (bridge.ts / bridge_client.py)
• Dockerized Pi runtime inside backend container
• Dockerized Ollama GPU acceleration on Apple Silicon
• Full corpus retrieval quality at scale
• Fixed 768-dim embedding quality across golden query suite
• Grounding threshold calibration (0.78 / 0.65)
• Full transcript ingestion throughput and storage
```

> **Critical Integration Gate:** Phase P0.4 is dedicated to a minimal standalone validation spike of the FastAPI-to-Pi subprocess bridge before any full agent subsystem is built.

---

## Must-Haves (from SPEC)

- [ ] **One-Command Startup:** Reproducible startup via Docker Compose (`docker compose up -d`) with zero committed secrets.
- [ ] **Zero-Key Local Demo:** Default demo running on containerized Ollama (`llama3.1:8b` + `nomic-embed-text`) requiring no cloud API keys.
- [ ] **Cloud Provider Switch:** Clean generation switch to Anthropic Claude via `.env` without code changes or vector re-indexing.
- [ ] **Full Source Provenance:** Verified citations (episode number, guest, title, verbatim quote) attached to every factual response.
- [ ] **Deterministic Refusal:** Out-of-domain and ungrounded queries refused deterministically via Grounding Gate ($S < 0.65$) without calling the LLM.
- [ ] **Session Context & Isolation:** PostgreSQL-backed sessions preserving multi-turn context for follow-up questions while isolating independent chats.
- [ ] **Validated Pi Subprocess Bridge:** Proven round-trip IPC between FastAPI and Pi 0.85.1 with tool callback and clean process lifecycle.
- [ ] **Automated Test Suite:** `pytest` suite verifying critical endpoints, retrieval, grounding gate, provider toggle, and persistence.

---

## Milestone v0.1: P0 Core Grounded Assistant

### Phase P0.1: Foundation & Environment Setup
**Status:** ✅ Complete  
**Objective:** Stand up the multi-container development environment, database schema, configuration management, and health verification endpoints.  
**Requirements:** REQ-01, REQ-02, NFR-01, NFR-02  

**Plans:**
- [x] Plan P0.1.1: Foundation & Environment Setup (Completed 2026-09-14)

**Key Deliverables:**
- `docker-compose.yml` defining `postgres` (pgvector/pgvector:pg16), `ollama`, and `backend` services.
- `.env.example` with safe defaults (`GROUNDING_LIMITED_THRESHOLD=0.65`, `HOST_PORT_POSTGRES=5432`, `LLM_PROVIDER=ollama`).
- `.gitignore` configured to ignore `.env` and `data/transcripts/`.
- Backend package scaffold (`backend/Dockerfile`, `backend/pyproject.toml`).
- PostgreSQL relational + pgvector DDL (`backend/app/db/schema.sql`, `init_db.py`) with `VECTOR(768)`.
- FastAPI app factory with structured logging, CORS, and Pydantic settings (`app/core/config.py`).
- Comprehensive health endpoint `GET /api/v1/health` checking PostgreSQL connectivity (`SELECT 1`) and Ollama reachability (`http://ollama:11434/api/tags`).

**Verification:** `docker compose up -d` brings up all services; `curl http://localhost:8000/api/v1/health` returns `{"status":"ok","database":"connected","ollama":"reachable"}`.

---

### Phase P0.2: Transcript Knowledge Pipeline & Ingestion
**Status:** ✅ Complete  
**Objective:** Ingest Lenny's Podcast transcripts into PostgreSQL with metadata extraction, speaker-aware chunking, and 768-dim embeddings.  
**Depends on:** Phase P0.1  
**Requirements:** REQ-03, REQ-04, REQ-05, NFR-03  

**Plans:**
- [x] Plan P0.2.1: Transcript Knowledge Pipeline & Ingestion (Completed 2026-09-14)

**Key Deliverables:**
- Transcript parser extracting YAML frontmatter (title, guest, episode number, URL, date) and falling back to directory names if frontmatter is absent (`backend/app/ingestion/parser.py`).
- Speaker-aware semantic chunker (~600 tokens, 100-token overlap, SHA-256 content hashing, preamble injection) (`backend/app/ingestion/chunker.py`).
- Fixed `OllamaEmbeddingProvider` generating 768-dimensional embeddings via `nomic-embed-text` (`backend/app/ingestion/embeddings.py`).
- CLI ingestion command: `python -m scripts.ingest` supporting idempotent runs, limits, and dry runs (`backend/scripts/ingest.py`).
- Admin status endpoint: `GET /api/v1/ingest/status` reporting total episodes, chunks, and index stats (`backend/app/api/v1/ingest.py`).
- Automated tests covering parser, chunker, embeddings, pipeline, and API endpoint (`backend/tests/`).

**Verification:** Ingested representative episodes; verified 109 chunks with `VECTOR(768)` in PostgreSQL; verified HNSW cosine index query; verified 100% idempotency upon re-run.

---

### Phase P0.3: Vector Retrieval & Deterministic Grounding Gate
**Status:** ⬜ Not Started  
**Objective:** Build semantic search, conversational query rewriting, and the deterministic 4-tier grounding gate.  
**Depends on:** Phase P0.2  
**Requirements:** REQ-06, REQ-07, REQ-08, REQ-09, NFR-03, NFR-04  

**Key Deliverables:**
- Query rewriter resolving pronouns and follow-up context against the session's prior turns.
- Vector retrieval engine executing cosine similarity (`<=>`) over `transcript_chunks` with configurable `RETRIEVAL_TOP_K` (default 15).
- Deterministic Grounding Gate implementing the 4 canonical tiers:
  - Strong: $\max(\text{score}) \ge 0.78$
  - Limited: $0.65 \le \max(\text{score}) < 0.78$ (`GROUNDING_LIMITED_THRESHOLD = 0.65`)
  - Conflicting: Divergent viewpoints across distinct guests/episodes
  - Insufficient: $\max(\text{score}) < 0.65$ or empty $\implies$ deterministic refusal
- Test/eval endpoint: `POST /api/v1/retrieval/preview` returning retrieved chunks, scores, and tier classification.

**Verification:** Test retrieval preview with known-answer queries (verifying Strong tier) and out-of-domain queries (verifying Insufficient tier and refusal).

---

### Phase P0.4: Pi Agent Subprocess Bridge Validation Spike
**Status:** ⬜ Not Started  
**Objective:** Validate the production FastAPI-to-Pi stdio JSON-RPC bridge via a standalone minimal execution spike before building the full agent subsystem.  
**Depends on:** Phase P0.3  
**Requirements:** REQ-10, CON-03  

**Key Deliverables:**
- Node.js environment configured with Pi Coding Agent (`@earendil-works/pi-coding-agent 0.85.1`).
- Minimal bridge spike script (`tests/spikes/test_pi_bridge_spike.py` / `backend/app/agent/bridge.ts` prototype).
- Registration of a single test retrieval tool (`transcript_retrieval`) returning structured XML evidence.
- Full round-trip test: FastAPI parent process launches Pi over stdio pipes, sends one user question, observes tool call, injects tool result, receives streamed tokens, and cleanly terminates or resets the child process.
- Empirical RPC protocol documentation and boundary validation.
- Architectural fallback contingency: If stdio JSON-RPC demonstrates pipe buffering or desync issues under async load, wrap Pi as an internal Express.js HTTP sidecar.

**Verification:** Script successfully completes one multi-step turn, invokes tool, receives evidence, prints response stream, and exits cleanly with zero zombie processes.

---

### Phase P0.5: Model Providers, Session Management & Multi-Turn Grounded Q&A
**Status:** ⬜ Not Started  
**Objective:** Deliver end-to-end multi-turn grounded conversational Q&A with model provider switching and persistent session storage.  
**Depends on:** Phase P0.4  
**Requirements:** REQ-11, REQ-12, REQ-13, NFR-07  

**Key Deliverables:**
- `GenerationProvider` abstraction with `OllamaGenerationProvider` (`llama3.1:8b`) and `AnthropicProvider` (`claude-3-5-sonnet-20241022`), cleanly selected via `LLM_PROVIDER`.
- `SessionManager` handling session creation, message persistence, and last $N=6$ context window hydration in PostgreSQL.
- Production Pi Agent integration wiring the validated subprocess bridge to the full `transcript_retrieval` tool and system grounding prompts.
- SSE streaming endpoint: `POST /api/v1/sessions/{id}/messages` streaming synthesized response tokens, evidence tier metadata, and source citations.
- Post-generation citation validation verifying that all cited claims correspond to retrieved chunks.

**Verification:** Send multi-turn conversational questions (question $\to$ answer with citations $\to$ follow-up referencing prior answer); toggle `LLM_PROVIDER` to Anthropic and verify behavior; test out-of-domain refusal.

---

### Phase P0.6: Minimal Evaluator UI & Critical Automated Test Suite
**Status:** ⬜ Not Started  
**Objective:** Deliver a clean, responsive evaluator web interface and comprehensive automated test suite.  
**Depends on:** Phase P0.5  
**Requirements:** REQ-14, REQ-15, NFR-06  

**Key Deliverables:**
- React 18 + Vite + TailwindCSS frontend in `frontend/`.
- Chat interface with real-time SSE token streaming, Markdown rendering, and autoscroll.
- Session sidebar: create new session, view session history, switch active sessions.
- Status bar displaying active generation provider badge (`Ollama (local)` or `Anthropic (cloud)`).
- Grounding visibility: Evidence tier badge (Strong, Limited, Conflicting, Insufficient) and expandable citation cards showing episode title, guest, and quotes.
- RFC 7807 structured error toasts (e.g., Ollama offline, missing API keys).
- Automated test suite (`pytest`) covering health checks, ingestion, retrieval scoring, grounding gate triage, provider configuration, and session isolation.

**Verification:** Execute `pytest`; interact with the UI in browser at `http://localhost:3000`; test end-to-end Q&A, follow-ups, provider indicator, and citations.

---

## Milestone v0.2: P1 Product Usefulness & Artifacts

### Phase P1.1: Ship 30 for 30 Content Writing Skill [P1]
**Status:** ⬜ Deferred  
**Objective:** Implement the dedicated content writing tool encoding the 7 Ship 30 for 30 writing principles into ~1,250-word grounded essays.  
**Depends on:** Milestone v0.1  
**Requirements:** REQ-16  

---

### Phase P1.2: Artifact Generation & Sandboxed Viewer [P1]
**Status:** ⬜ Deferred  
**Objective:** Implement Markdown and HTML/CSS artifact generation with a split-pane in-app viewer isolated via sandboxed `<iframe>` (`null` origin, strict CSP, Bleach sanitization).  
**Depends on:** Phase P1.1  
**Requirements:** REQ-17, NFR-05  

---

### Phase P1.3: Evaluator Polish & Extended Test Verification [P1]
**Status:** ⬜ Deferred  
**Objective:** Refine artifact copying/exporting, manual UI test plans, and edge-case test coverage.  
**Depends on:** Phase P1.2  

---

## Milestone v0.3: P2 Hardening & Extensions

### Phase P2.1: OpenAI Cloud Provider Integration [P2]
**Status:** ⬜ Deferred  
**Objective:** Implement OpenAI GPT-4o adapter as a secondary cloud provider option.  
**Depends on:** Milestone v0.2  
**Requirements:** REQ-18  

---

### Phase P2.2: Advanced Observability, Resilience Hardening & Automated Refresh [P2]
**Status:** ⬜ Deferred  
**Objective:** Ingestion refresh pipeline, comprehensive chaos resilience, and detailed metrics tracking.  
**Depends on:** Phase P2.1  
**Requirements:** REQ-19  

---

### Phase P2.3: UX & Accessibility Polish [P2]
**Status:** ⬜ Deferred  
**Objective:** Mobile view transitions, dark/light theme polish, and WCAG AA accessibility compliance.  
**Depends on:** Phase P2.2  

---

## Progress Summary
 
| Phase | Milestone | Priority | Status | Plans | Complete |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0.1 Foundation & Environment** | v0.1 | P0 | ✅ Complete | 1/1 | 100% |
| **P0.2 Ingestion & Embeddings** | v0.1 | P0 | ✅ Complete | 1/1 | 100% |
| **P0.3 Retrieval & Grounding Gate** | v0.1 | P0 | ⬜ Not Started | 0/2 | — |
| **P0.4 Pi Subprocess Bridge Spike** | v0.1 | P0 | ⬜ Not Started | 0/1 | — |
| **P0.5 Providers & Grounded Q&A** | v0.1 | P0 | ⬜ Not Started | 0/2 | — |
| **P0.6 Evaluator UI & Test Suite** | v0.1 | P0 | ⬜ Not Started | 0/2 | — |
| **P1.1 Ship 30 for 30 Skill** | v0.2 | P1 | ⬜ Deferred | 0/1 | — |
| **P1.2 Artifacts & Sandboxed Viewer**| v0.2 | P1 | ⬜ Deferred | 0/2 | — |
| **P1.3 Evaluator Polish** | v0.2 | P1 | ⬜ Deferred | 0/1 | — |
| **P2.1 OpenAI Cloud Integration** | v0.3 | P2 | ⬜ Deferred | 0/1 | — |
| **P2.2 Resilience & Refresh** | v0.3 | P2 | ⬜ Deferred | 0/1 | — |
| **P2.3 UX & A11y Polish** | v0.3 | P2 | ⬜ Deferred | 0/1 | — |

---

## Timeline

| Phase | Started | Completed | Duration |
| :--- | :--- | :--- | :--- |
| P0.1 | 2026-09-14 | 2026-09-14 | ~1h |
| P0.2 | 2026-09-14 | 2026-09-14 | ~45m |
| P0.3 | — | — | — |
| P0.4 | — | — | — |
| P0.5 | — | — | — |
| P0.6 | — | — | — |
