---
updated: 2026-09-14T15:15:00Z
---

# Project State

## Current Position

**Milestone:** v0.1 — P0 Core Grounded Assistant  
**Phase:** P0.2 — Transcript Knowledge Pipeline & Ingestion  
**Status:** ✅ Complete  
**Plan:** Plan P0.2.1 executed and verified  

---

## Last Action

Successfully implemented and verified **Phase P0.2 (Transcript Knowledge Pipeline & Ingestion)**:
- Parsed YAML frontmatter with directory fallback resilience and normalized transcript text (`backend/app/ingestion/parser.py`).
- Implemented speaker-aware semantic chunker (~600 tokens, 100-token overlap, context injection) with deterministic SHA-256 content hashing (`backend/app/ingestion/chunker.py`).
- Built decoupled `OllamaEmbeddingProvider` generating fixed 768-dimensional embeddings via `nomic-embed-text` (`backend/app/ingestion/embeddings.py`).
- Evolved `episodes` schema with metadata columns (`description`, `video_id`, `duration_seconds`, `duration`, `view_count`, `channel`) and configured `NullPool` in `backend/app/db/session.py`.
- Built end-to-end `IngestionPipeline` with batch embedding and idempotent database upserts (`backend/app/ingestion/pipeline.py`).
- Built ingestion CLI `python -m scripts.ingest` and corpus status endpoint `GET /api/v1/ingest/status` (`backend/scripts/ingest.py`, `backend/app/api/v1/ingest.py`).
- Added comprehensive unit and integration test suite (`tests/test_parser.py`, `tests/test_chunker.py`, `tests/test_embeddings.py`, `tests/test_ingestion.py`), with all 24 tests passing.
- Verified representative ingestion in PostgreSQL (3 episodes, 109 chunks, 109 vectors of length 768) and confirmed 100% idempotency upon re-run.

---

## Next Steps

1. **Phase P0.3 Execution Planning:** Author execution plan for Phase P0.3 in `.gsd/phases/P0.3/PLAN.md`.
2. **Query Rewriter:** Implement conversational reference resolution over last $N=6$ context turns.
3. **Vector Retrieval Engine:** Implement pgvector cosine similarity search (`<=>`) over indexed chunks.
4. **Deterministic Grounding Gate:** Implement 4-tier triage (Strong $\ge 0.78$, Limited $0.65 \le S < 0.78$, Conflicting, Insufficient $< 0.65$).
5. **Retrieval Preview Endpoint:** Implement `POST /api/v1/retrieval/preview`.

---

## Active Decisions

| Decision | Choice | Status | Affects |
| :--- | :--- | :--- | :--- |
| **DECISION-001** | Pi Coding Agent 0.85.1 as cognitive core with mandatory P0.4 bridge spike | Accepted | P0.4, P0.5 |
| **DECISION-002** | Local PostgreSQL 16 + pgvector as single persistence engine | Verified in P0.1 | P0.1, P0.2, P0.3 |
| **DECISION-003** | Fixed `nomic-embed-text` (768-dim) Ollama embeddings decoupled from LLM | Verified in P0.1 | P0.2, P0.3 |
| **DECISION-004** | Anthropic Claude as selected P0 cloud provider; OpenAI deferred to P2 | Accepted | P0.5, P2.1 |
| **DECISION-005** | Deterministic 4-tier Grounding Gate (`GROUNDING_LIMITED_THRESHOLD = 0.65`) | Verified in P0.1 | P0.3, P0.5 |
| **DECISION-006** | Conversational flow order: Query Rewriting upstream of Retrieval | Accepted | P0.3, P0.5 |
| **DECISION-007** | Container PostgreSQL communication strictly on `postgres:5432` (`DATABASE_URL`) | Verified in P0.1 | P0.1 |
| **DECISION-008** | Dual-Origin Sandboxed `<iframe>` + Bleach sanitization for artifacts | Accepted | P1.2 |
| **DECISION-009** | Modular Monolith FastAPI backend + React 18 / Vite frontend | Verified in P0.1 | All |
| **DECISION-010** | Speaker-aware semantic chunking (~600 tokens, 100 overlap) | Accepted | P0.2 |
| **DECISION-011** | Local-first zero-key demo default via containerized Ollama | Verified in P0.1 | P0.1, P0.6 |
| **DECISION-012** | RFC 7807 structured problem details; zero silent model fallbacks | Verified in P0.1 | P0.1, P0.5 |

---

## Blockers

*None. Phase P0.1 complete and verified; environment is live.*

---

## Concerns & Watchlist

- **Host Port Mapping:** Host port 5432 was occupied by an existing local container (`contractai_db`). `HOST_PORT_POSTGRES=5433` successfully resolved external access without altering internal `DATABASE_URL` (`postgres:5432`).
- **Pi Subprocess Bridge Risk:** Mandatory standalone validation spike scheduled for Phase P0.4.
- **Model Download on Ingestion:** Phase P0.2 will require `nomic-embed-text` pulled in Ollama container before running ingestion.

---

## Session Context

- Phase P0.1 implemented and verified.
- Containers running: `lenny_postgres` (healthy), `lenny_ollama` (up), `lenny_backend` (up).
- All P0.1 acceptance criteria satisfied.
- Strict constraint preserved: Zero P0.2 application code implemented.
