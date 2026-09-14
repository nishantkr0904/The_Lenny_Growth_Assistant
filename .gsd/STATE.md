---
updated: 2026-09-14T16:30:00Z
---

# Project State

## Current Position

**Milestone:** v0.1 — P0 Core Grounded Assistant  
**Phase:** P0.5 — Model Providers, Session Management & Multi-Turn Grounded Q&A  
**Status:** ✅ Complete  
**Plan:** Plan P0.5 executed and verified  

---

## Last Action

Successfully executed and verified **Phase P0.5 (Model Providers, Session Management & Multi-Turn Grounded Q&A)**:
- Implemented PostgreSQL-backed session and message store (`backend/app/sessions/store.py`, `models.py`) persisting sessions, message turns, and structured source references (`source_references` table).
- Implemented conversation-aware query rewriter (`backend/app/retrieval/rewriter.py`) resolving pronouns ("she", "that", "what about") from bounded conversation history ($N=6$ messages) without hallucinating answers.
- Implemented decoupled generation provider abstraction (`backend/app/providers/`): `OllamaGenerationProvider` (default local `llama3.1:8b`) and `AnthropicGenerationProvider` (official SDK `claude-3-5-sonnet-20241022`). Enforced strict configuration check: missing Anthropic credentials raise `ProviderConfigurationError` immediately without silent fallback.
- Implemented post-generation `CitationValidator` (`backend/app/agent/citation.py`) verifying cited chunk UUIDs against retrieved evidence and preventing hallucinated sources.
- Built production `QnAOrchestrator` (`backend/app/agent/orchestrator.py`) unifying session context, query rewriting, pgvector retrieval, GroundingGate triage, LLM synthesis, citation validation, and message persistence. Enforced deterministic refusal on `Insufficient` tier ($< 0.65$, bypasses LLM, latency < 300ms).
- Implemented FastAPI session routes (`POST /api/v1/sessions`, `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}`) and grounded Q&A endpoint (`POST /api/v1/sessions/{id}/messages`) supporting both structured JSON and Server-Sent Events (SSE `text/event-stream`).
- Added 22 new unit and integration tests; full backend test suite passes with 66 green tests.
- Empirically validated multi-turn live conversation against ingested transcripts: Scenario A (supported query), Scenario B (follow-up with pronoun resolution), Scenario C (unsupported refusal), and SSE streaming.

---

## Next Steps

1. **Phase P0.6 Planning:** Author execution plan for Phase P0.6 in `.gsd/phases/P0.6/PLAN.md`.
2. **React 18 + Vite Frontend Scaffold:** Initialize frontend client with TailwindCSS and modern responsive layout.
3. **Conversational Chat UI:** Build real-time streaming chat component consuming SSE endpoint (`POST /api/v1/sessions/{id}/messages`).
4. **Session Switcher & Provider Badge:** Build session drawer and active model provider status indicator.
5. **Evidence Badges & Citation Cards:** Render interactive grounding tier badges (`Strong`, `Limited`, `Conflicting`, `Insufficient`) and source inspector cards.
6. **Milestone v0.1 Audit:** Verify end-to-end user experience, startup reproducibility, and all P0 acceptance criteria.

---

## Active Decisions

| Decision | Choice | Status | Affects |
| :--- | :--- | :--- | :--- |
| **DECISION-001** | Pi Coding Agent 0.85.1 as cognitive core with mandatory P0.4 bridge spike | Accepted | P0.4, P0.5 |
| **DECISION-002** | Local PostgreSQL 16 + pgvector as single persistence engine | Verified in P0.1 | P0.1, P0.2, P0.3 |
| **DECISION-003** | Fixed `nomic-embed-text` (768-dim) Ollama embeddings decoupled from LLM | Verified in P0.1 | P0.2, P0.3 |
| **DECISION-004** | Anthropic Claude as selected P0 cloud provider; OpenAI deferred to P2 | Accepted | P0.5, P2.1 |
| **DECISION-005** | Deterministic 4-tier Grounding Gate (`GROUNDING_LIMITED_THRESHOLD = 0.65`) | Verified in P0.3 | P0.3, P0.5 |
| **DECISION-006** | Conversational flow order: Query Rewriting upstream of Retrieval | Accepted | P0.3, P0.5 |
| **DECISION-007** | Container PostgreSQL communication strictly on `postgres:5432` (`DATABASE_URL`) | Verified in P0.1 | P0.1 |
| **DECISION-008** | Dual-Origin Sandboxed `<iframe>` + Bleach sanitization for artifacts | Accepted | P1.2 |
| **DECISION-009** | Modular Monolith FastAPI backend + React 18 / Vite frontend | Verified in P0.1 | All |
| **DECISION-010** | Speaker-aware semantic chunking (~600 tokens, 100 overlap) | Verified in P0.2 | P0.2 |
| **DECISION-011** | Local-first zero-key demo default via containerized Ollama | Verified in P0.1 | P0.1, P0.6 |
| **DECISION-012** | RFC 7807 structured problem details; zero silent model fallbacks | Verified in P0.1 | P0.1, P0.5 |
| **DECISION-013** | GroundingGate single-episode independence (episode count is diversity metadata, not gate blocker) | Verified in P0.3 | P0.3, P0.5 |

---

## Blockers

*None. Phase P0.5 complete and verified; environment is live.*

---

## Concerns & Watchlist

- **Local Ollama CPU Inference Latency:** Prompt evaluation + token generation on containerized Ollama (CPU) requires ~50-59s for full multi-chunk synthesis. Mitigated by setting `OLLAMA_TIMEOUT_SECONDS: 180.0` and `max_tokens: 384`. Real-time SSE token streaming delivers tokens to the user as they are generated.
- **Cloud Provider Live Keys:** Anthropic integration verified via unit tests and strict configuration validation (zero silent fallback). Live cloud testing requires user to provide `ANTHROPIC_API_KEY`.

---

## Session Context

- Phase P0.5 implemented and verified.
- Containers running: `lenny_postgres` (healthy on port 5433), `lenny_ollama` (up), `lenny_backend` (up on port 8000).
- All P0.5 acceptance criteria satisfied.
- Full pytest suite: 66 passed in 1.93s.
- Strict constraint preserved: Zero P0.6 frontend or UI code implemented.

