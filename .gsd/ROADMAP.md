---
milestone: v0.1
version: 0.1.0
updated: 2026-09-14T14:00:00Z
---

# Roadmap

> **Current Phase:** Phase P0.6 — Minimal Evaluator UI & Critical Automated Test Suite  
> **Status:** Ready to Plan  
> **Immediate Target:** Phase P0.6  

---

## Validation Status Boundary

```
VALIDATED BY SPIKE & PHASES P0.1–P0.5
─────────────────────────────────────────────
• Multi-container development stack (FastAPI + PostgreSQL 16 + pgvector + Ollama)
• Speaker-aware semantic chunker (~600 tokens, 100 overlap) and 768-dim embeddings
• Representative corpus ingestion (3 episodes, 109 chunks, HNSW index active)
• Vector retrieval engine (<=> cosine similarity) returning ranked evidence
• Deterministic Grounding Gate (Strong >= 0.78, Limited [0.65, 0.78), Conflicting, Insufficient < 0.65)
• Pi 0.85.1 headless SDK runtime + Ollama (llama3.1:8b) cognitive synthesis
• Project-local custom retrieval tool extension (`transcript_retrieval.ts`) via defineTool
• End-to-end tool invocation, pgvector query, and GroundingGate preservation
• Source-grounded answer generation with Ada Chen Rekhi citation
• Deterministic refusal enforcement on Insufficient evidence (NO_GROUNDED_EVIDENCE)
• Clean session lifecycle via session.dispose() with 0 orphan processes
• PostgreSQL session and message persistence layer (`sessions`, `messages`, `source_references`)
• Bounded working context window ($N=6$ messages) for deterministic history injection
• Conversation-aware query rewriting resolving pronouns and context without hallucinations
• Decoupled generation provider abstraction (`OllamaGenerationProvider`, `AnthropicGenerationProvider`)
• Strict provider configuration validation with zero silent model fallbacks
• Post-generation citation validation verifying cited chunks against retrieved evidence
• Production QnAOrchestrator coordinating rewriter, retrieval, GroundingGate, LLM, validator, and persistence
• Server-Sent Events (SSE) real-time streaming endpoint (`POST /api/v1/sessions/{id}/messages`)
• Multi-turn conversational Q&A tested against live transcripts (supported, follow-up, refusal)

NOT YET VALIDATED (IMPLEMENTATION-RISK ITEMS)
─────────────────────────────────────────────
• React 18 + Vite web evaluator user interface
• Real-time SSE streaming rendering in browser UI with auto-scroll
• Interactive evidence tier badge and citation inspector cards in frontend
• Dockerized Ollama GPU acceleration on Apple Silicon
• Full 303-episode corpus retrieval quality at scale
• Fixed 768-dim embedding quality across golden query suite
• Full transcript ingestion throughput and storage
```

> **Critical Integration Gate:** Phase P0.4 completed the integration validation spike of Pi 0.85.1 + Ollama + custom retrieval tool + P0.3 Grounding Gate; Phase P0.5 hardened this into the production backend Q&A engine.

---

## Must-Haves (from SPEC)

- [ ] **One-Command Startup:** Reproducible startup via Docker Compose (`docker compose up -d`) with zero committed secrets.
- [ ] **Zero-Key Local Demo:** Default demo running on containerized Ollama (`llama3.1:8b` + `nomic-embed-text`) requiring no cloud API keys.
- [x] **Cloud Provider Switch:** Clean generation switch to Anthropic Claude via `.env` without code changes or vector re-indexing (P0.5).
- [x] **Full Source Provenance:** Verified citations (episode number, guest, title, verbatim quote) attached to every retrieved evidence item (P0.3, P0.5).
- [x] **Deterministic Refusal:** Out-of-domain and ungrounded queries refused deterministically via Grounding Gate ($S < 0.65$) without calling the LLM (P0.3, P0.4, P0.5).
- [x] **Session Context & Isolation:** PostgreSQL-backed sessions preserving multi-turn context for follow-up questions while isolating independent chats (P0.5).
- [x] **Validated Pi Integration:** Proven end-to-end integration between Pi 0.85.1, custom retrieval tool, P0.3 Grounding Gate, and clean process lifecycle (P0.4, P0.5).
- [x] **Automated Test Suite:** `pytest` suite verifying critical endpoints, retrieval, grounding gate, provider toggle, and persistence (66 passed).

---

## Milestone v0.1: P0 Core Grounded Assistant

### Phase P0.1: Foundation & Environment Setup
**Status:** ✅ Complete  
**Objective:** Stand up the multi-container development environment, database schema, configuration management, and health verification endpoints.  
**Depends on:** None  
**Requirements:** REQ-01, REQ-02, CON-01, CON-02, CON-04, NFR-01, NFR-05  

**Plans:**
- [x] Plan P0.1.1: Multi-Container Foundation (Completed 2026-09-14)

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
**Status:** ✅ Complete  
**Objective:** Build semantic search, deterministic query normalization boundary, and the deterministic 4-tier grounding gate.  
**Depends on:** Phase P0.2  
**Requirements:** REQ-06, REQ-07, REQ-08, REQ-09, NFR-03, NFR-04  

**Plans:**
- [x] Plan P0.3.1: Vector Retrieval & Deterministic Grounding Gate (Completed 2026-09-14)

**Key Deliverables:**
- Deterministic query normalization boundary collapsing whitespace, normalizing quotes/Unicode, and rejecting empty queries (`backend/app/retrieval/query.py`).
- Vector retrieval engine executing cosine similarity (`<=>`) over `transcript_chunks` with HNSW index and joining episode metadata (`backend/app/retrieval/engine.py`).
- Deterministic Grounding Gate implementing the 4 canonical tiers (`backend/app/retrieval/grounding.py`):
  - Strong: $\max(\text{score}) \ge 0.78$ (single episode can be Strong; episode count is not a blocker)
  - Limited: $0.65 \le \max(\text{score}) < 0.78$ (`GROUNDING_LIMITED_THRESHOLD = 0.65`)
  - Conflicting: Multi-guest divergent perspectives with contrastive signals
  - Insufficient: $\max(\text{score}) < 0.65$ or empty $\implies$ deterministic refusal with `can_synthesize = False` and `selected_evidence = []`
- Backend API endpoints: `POST /api/v1/retrieval/search` and `POST /api/v1/retrieval/preview` (`backend/app/api/v1/retrieval.py`).
- Automated tests: 15 unit and live integration tests (`backend/tests/test_retrieval.py`), with all 39 test suite checks green.

**Verification:** Validated live retrieval against ingested transcripts returning ranked chunks and scores; verified Strong, Limited, and Insufficient tiers; verified out-of-domain query triggers deterministic refusal.

---

### Phase P0.4: Pi Agent Subprocess Bridge Validation Spike
**Status:** ✅ Complete  
**Objective:** Validate the integration boundary between Pi Coding Agent 0.85.1, Ollama `llama3.1:8b`, custom retrieval tool, and P0.3 Grounding Gate via a standalone minimal execution spike before building the full agent subsystem.  
**Depends on:** Phase P0.3  
**Requirements:** REQ-10, CON-03  

**Plans:**
- [x] Plan P0.4: Pi Coding Agent Bridge Validation Spike (Completed 2026-09-14)

**Key Deliverables:**
- Node.js environment configured with Pi Coding Agent (`@earendil-works/pi-coding-agent 0.85.1`).
- Project-local custom retrieval tool extension (`.pi/extensions/transcript_retrieval.ts`) registering `transcript_retrieval` tool via `defineTool`.
- Python agent tool adapter (`backend/app/agent/retrieval_tool.py`) providing `format_evidence_for_agent` and `execute_transcript_retrieval` with XML serialization and refusal directives.
- Automated test suite (`backend/tests/test_agent_tool.py`) validating formatting, engine coordination, and refusal behavior (5 tests).
- Standalone validation spike harness (`spikes/run_pi_spike.mjs`) executing multi-turn headless agent sessions against Ollama `llama3.1:8b`.
- Empirical validation of grounded synthesis on supported query (Ada Chen Rekhi) and honest refusal on out-of-domain query (quantum chromodynamics).
- Verified clean process lifecycle (`session.dispose()`, exit code 0, 0 orphan processes).

**Verification:** Script successfully completed multi-turn spike; autonomous tool call made (157ms); real evidence returned from PostgreSQL pgvector; GroundingGate tiers preserved; grounded response generated; ungrounded query refused; session cleanly disposed with zero zombie processes. Full backend test suite passing (44 passed).

---

### Phase P0.5: Model Providers, Session Management & Multi-Turn Grounded Q&A
**Status:** ✅ Complete  
**Objective:** Deliver end-to-end multi-turn grounded conversational Q&A with model provider switching, conversation-aware query rewriting, deterministic grounding enforcement, citation validation, and persistent PostgreSQL session storage.  
**Depends on:** Phase P0.4  
**Requirements:** REQ-06, REQ-11, REQ-12, REQ-13, NFR-07  

**Plans:**
- [x] Plan P0.5: Model Providers, Session Management & Multi-Turn Grounded Q&A (Completed 2026-09-14)

**Key Deliverables:**
- PostgreSQL session and message persistence layer (`backend/app/sessions/store.py`, `models.py`) with `sessions`, `messages`, and `source_references` tables.
- Bounded working context window ($N=6$ messages) for deterministic history injection into query rewriter and prompt synthesis.
- Conversation-aware query rewriting (`backend/app/retrieval/rewriter.py`) resolving pronouns and context across turns without adding unsupported facts.
- Decoupled `GenerationProvider` abstraction (`backend/app/providers/`): `OllamaGenerationProvider` (`llama3.1:8b`) as default local provider; `AnthropicGenerationProvider` (`claude-3-5-sonnet-20241022`) via official Anthropic SDK with strict error handling on missing credentials (zero silent fallback).
- Deterministic post-generation `CitationValidator` (`backend/app/agent/citation.py`) verifying cited chunks against retrieved evidence.
- Production `QnAOrchestrator` (`backend/app/agent/orchestrator.py`) unifying context, query rewriting, pgvector retrieval, GroundingGate triage, LLM synthesis, citation validation, and persistence. Enforces fast deterministic refusal on `Insufficient` tier (< 0.65, latency < 300ms).
- FastAPI endpoints for session lifecycle (`POST /api/v1/sessions`, `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}`) and conversational Q&A (`POST /api/v1/sessions/{id}/messages`) supporting both JSON and SSE streaming (`text/event-stream`).
- Automated tests: 22 new unit and integration tests (66 passed backend total).

**Verification:** Validated multi-turn live conversation against ingested transcripts: Scenario A (supported query with Strong tier), Scenario B (follow-up query with pronoun resolution), Scenario C (out-of-domain query with Insufficient refusal in 269ms), Scenario D (Anthropic provider configuration error and unit tests), and Scenario E (real-time SSE streaming). All 66 tests passing in 1.93s.

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
