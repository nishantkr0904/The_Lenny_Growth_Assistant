---
updated: 2026-09-14T18:00:00Z
---

# Project State

## Current Position

**Milestone:** v0.1 — P0 Core Grounded Assistant  
**Phase:** P0.6 — Evaluator-Facing Product Experience: React Q&A, Ship 30 for 30, and Safe Artifacts  
**Status:** ✅ Complete  
**Plan:** Plan P0.6 executed and verified  

---

## Last Action

Successfully executed and verified **Phase P0.6 (Evaluator-Facing Product Experience)**:
- Backend Artifact Engine & Bleach Sanitization implemented in `backend/app/artifacts/` (`models.py`, `compiler.py`, `store.py`) and API router `backend/app/api/v1/artifacts.py` registered in `backend/app/main.py`.
- Encoded all 7 canonical Ship 30 for 30 principles in `Ship30Writer`: Grabber Hook, 4A Progression, Skimmable Formatting, ~1,250 words, Actionable Takeaway checklist, Grounded Claims, and Curating the Experts credibility framing.
- Built defense-in-depth HTML sanitization: `bleach.clean()` strips unsafe tags/attributes/URIs, strict CSP injected into HTML5 boilerplate, and bare sandboxed `<iframe>` (`sandbox=""`) rendered on frontend with NO `allow-scripts` and NO `allow-same-origin`.
- Built full React 18 + Vite + TypeScript frontend SPA with TailwindCSS and Lucide React icons, containerized via multi-stage Nginx Dockerfile in `docker-compose.yml` on port 3000.
- Grounding trust UX: Header dynamic provider badge (`🟢 Ollama (llama3.1:8b)` vs `🟢 Anthropic (Claude 3.5 Sonnet)`), EvidenceIndicator badges (`Strong`, `Limited`, `Contrasting`), interactive `SourceDrawer` with verified quotes, and warm refusal card for `Insufficient` evidence with zero hallucinated citations.
- Complete automated verification: backend pytest suite (80 passed in 3.32s) and frontend test suite (8 passed in 890ms).
- Live browser E2E test via browser subagent verified all 11 user journeys cleanly.

---

## Next Steps

1. **Milestone Audit / P0 Acceptance Audit**: Review all P0 requirements and acceptance criteria against working live system.
2. **Phase P0.7 Preparation**: Do not begin implementation until explicitly directed.

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
| **DECISION-008** | Dual-Origin Sandboxed `<iframe>` (`sandbox=""`) + Bleach sanitization for artifacts | Verified in P0.6 | P0.6, P1.2 |
| **DECISION-009** | Modular Monolith FastAPI backend + React 18 / Vite frontend | Verified in P0.6 | All |
| **DECISION-010** | Speaker-aware semantic chunking (~600 tokens, 100 overlap) | Verified in P0.2 | P0.2 |
| **DECISION-011** | Local-first zero-key demo default via containerized Ollama | Verified in P0.1 | P0.1, P0.6 |
| **DECISION-012** | RFC 7807 structured problem details; zero silent model fallbacks | Verified in P0.1 | P0.1, P0.5 |
| **DECISION-013** | GroundingGate single-episode independence (episode count is diversity metadata, not gate blocker) | Verified in P0.3 | P0.3, P0.5 |
| **DECISION-014** | Unbuffered Nginx proxying for SSE streaming deltas (`proxy_buffering off;`) | Verified in P0.6 | P0.6 |

---

## Blockers

*None. Phase P0.6 complete and verified; environment is live.*

---

## Concerns & Watchlist

- **Local Ollama CPU Inference Latency:** Prompt evaluation + token generation on containerized Ollama (CPU) requires ~50-59s for full multi-chunk synthesis. Mitigated by setting `OLLAMA_TIMEOUT_SECONDS: 180.0` and `max_tokens: 384`. Real-time SSE token streaming delivers tokens to the user as they are generated.
- **Cloud Provider Live Keys:** Anthropic integration verified via unit tests and strict configuration validation (zero silent fallback). Live cloud testing requires user to provide `ANTHROPIC_API_KEY`.

---

## Session Context

- Phase P0.6 complete and verified.
- Containers running: `lenny_postgres` (healthy on port 5433), `lenny_ollama` (up on port 11434), `lenny_backend` (up on port 8000), `lenny_frontend` (up on port 3000).
- All P0.6 acceptance criteria satisfied.
- Full pytest suite: 80 passed in 3.32s.
- Frontend test suite: 8 passed in 890ms.
- Strict constraint preserved: Phase P0.7 NOT STARTED.
