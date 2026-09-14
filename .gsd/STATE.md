---
updated: 2026-09-14T16:30:00Z
---

# Project State

## Current Position

**Milestone:** v0.1 — P0 Core Grounded Assistant  
**Phase:** P0.5A — Targeted Architectural Correction: Production Pi Agent Integration  
**Status:** ✅ Complete  
**Plan:** Plan P0.5 and Correction Plan P0.5A executed and verified  

---

## Last Action

Successfully executed and verified **Phase P0.5A Targeted Architectural Correction (Production Pi Agent Integration)**:
- Upgraded backend container to include Node.js 22 runtime and `@earendil-works/pi-coding-agent@0.85.1`.
- Implemented production Pi bridge daemon (`backend/app/agent/bridge_daemon.mjs`) communicating over stdio using line-delimited JSON-RPC 2.0 (`execute_turn`, `stream_turn`, `ping`, `shutdown`). Redirected all console logging to stderr to guarantee zero stdout protocol corruption.
- Registered project-local `transcript_retrieval` tool in Pi via `defineTool`, delegating to FastAPI's authoritative P0.3 `/api/v1/retrieval/search` endpoint and preserving GroundingGate decisions, scores, and chunk metadata.
- Implemented Python bridge client (`backend/app/agent/pi_bridge.py`) with child process lifecycle management, concurrency serialization via `asyncio.Lock()`, and FastAPI lifespan termination (`backend/app/main.py`) ensuring zero orphan processes.
- Rewired production `QnAOrchestrator` (`backend/app/agent/orchestrator.py`): eliminated direct `self.provider.generate()` / `self.provider.stream()` calls. All turn generation and token streaming route through the Pi agent runtime.
- Preserved existing P0.1–P0.5 contracts: bounded context, query rewriting, pgvector cosine search, deterministic GroundingGate tiers (Strong, Limited, Conflicting, Insufficient), honest refusal without citations on Insufficient, and post-generation `CitationValidator`.
- Added 4 new tests in `backend/tests/test_pi_bridge.py`; full backend test suite passes with 70 green tests.
- Empirically validated on live Docker stack: Scenario A (supported Ada Chen Rekhi turn), Scenario B (follow-up with pronoun resolution), Scenario C (unsupported refusal with 0 citations), Scenario D (Anthropic configuration error), and Scenario E (real-time SSE streaming).

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

- Phase P0.5A architectural correction implemented and verified.
- Containers running: `lenny_postgres` (healthy on port 5433), `lenny_ollama` (up), `lenny_backend` (up on port 8000).
- All P0.5 and P0.5A acceptance criteria satisfied.
- Full pytest suite: 70 passed in 2.35s.
- Strict constraint preserved: Zero P0.6 frontend or UI code implemented.

