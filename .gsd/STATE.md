---
updated: 2026-09-14T16:00:00Z
---

# Project State

## Current Position

**Milestone:** v0.1 — P0 Core Grounded Assistant  
**Phase:** P0.4 — Pi Coding Agent Bridge Validation Spike  
**Status:** ✅ Complete  
**Plan:** Plan P0.4 executed and verified  

---

## Last Action

Successfully executed and verified **Phase P0.4 (Pi Coding Agent Bridge Validation Spike)**:
- Defined project-local custom retrieval tool `transcript_retrieval` in `.pi/extensions/transcript_retrieval.ts` via Pi's `defineTool` API, querying `POST /api/v1/retrieval/search` and enforcing grounding directives.
- Implemented Python tool adapter in `backend/app/agent/retrieval_tool.py` providing `format_evidence_for_agent` and `execute_transcript_retrieval`, converting retrieval responses into structured XML with `<chunk>` citations or `<system_directive>NO_GROUNDED_EVIDENCE</system_directive>`.
- Built comprehensive automated test suite `backend/tests/test_agent_tool.py` (5 tests); verified full backend suite (44 tests) passing green.
- Implemented multi-turn spike execution runner in `spikes/run_pi_spike.mjs` using `@earendil-works/pi-coding-agent 0.85.1` headless SDK (`createAgentSession`, `ModelRuntime`, Ollama `llama3.1:8b`).
- Empirically validated Turn 1 (Ada Chen Rekhi question): tool invoked (157ms), returned 4 chunks (`Limited` tier, score 0.7474), Pi synthesized grounded response with source attribution.
- Empirically validated Turn 2 (out-of-domain quantum chromodynamics question): tool invoked (643ms), returned `Insufficient` tier (score 0.4492), Pi obeyed refusal directive without fabricating knowledge.
- Verified clean lifecycle: `session.dispose()` invoked, process exited with code 0, 0 orphaned Node.js/Pi processes.

---

## Next Steps

1. **Phase P0.5 Execution Planning:** Author execution plan for Phase P0.5 in `.gsd/phases/P0.5/PLAN.md`.
2. **GenerationProvider Abstraction:** Implement Ollama (default local) and Anthropic Claude (P0 cloud) generation provider toggle via `.env`.
3. **Session Management:** Implement `SessionManager` in PostgreSQL managing multi-turn conversation history and message persistence.
4. **FastAPI-to-Pi Production Bridge:** Implement production subprocess bridge / streaming runner for FastAPI.
5. **SSE Streaming Endpoint:** Implement `POST /api/v1/sessions/{id}/messages` with Server-Sent Events.
6. **Post-Generation Citation Validator:** Implement citation check ensuring verbatim provenance before delivery.

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

*None. Phase P0.3 complete and verified; environment is live.*

---

## Concerns & Watchlist

- **Pi Subprocess Bridge Risk:** Mandatory standalone validation spike scheduled as first task of Phase P0.4.

---

## Session Context

- Phase P0.3 implemented and verified.
- Containers running: `lenny_postgres` (healthy), `lenny_ollama` (up), `lenny_backend` (up).
- All P0.3 acceptance criteria satisfied.
- Full pytest suite: 39 passed in 0.59s.
- Strict constraint preserved: Zero P0.4 application code implemented.
