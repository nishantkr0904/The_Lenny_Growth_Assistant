---
updated: 2026-09-14T14:35:00Z
---

# Project State

## Current Position

**Milestone:** v0.1 — P0 Core Grounded Assistant  
**Phase:** P0.2 — Transcript Knowledge Pipeline & Ingestion  
**Status:** Ready to Plan / Execute  
**Plan:** P0.1 completed; awaiting Phase P0.2 planning  

---

## Last Action

Successfully implemented and verified **Phase P0.1 (Foundation & Environment Setup)**:
- Generated `docker-compose.yml` with `postgres` (pgvector/pgvector:pg16), `ollama` (ollama/ollama:latest), and `backend` (FastAPI).
- Created `.env.example`, `.env` (configured with `HOST_PORT_POSTGRES=5433` avoiding local host port collision while keeping internal `DATABASE_URL` on `postgres:5432`), and `.gitignore`.
- Scaffolded `backend/` package (`pyproject.toml`, `Dockerfile`, `app/core/config.py`, `app/core/logging.py`, `app/db/session.py`, `app/db/init_db.py`).
- Applied canonical PostgreSQL DDL (`app/db/schema.sql`) creating `episodes`, `transcript_chunks` with `VECTOR(768)` and HNSW index, `sessions`, `messages`, `source_references`, and `artifacts`.
- Implemented and verified `GET /api/v1/health` testing PostgreSQL connectivity and Ollama server reachability.
- Ran automated test suite (`pytest`) inside backend container with 7 passing tests.
- Verified live responses via `curl -i http://localhost:8000/api/v1/health`.

---

## Next Steps

1. **Phase P0.2 Execution Planning:** Author execution plan for Phase P0.2 in `.gsd/phases/P0.2/PLAN.md`.
2. **Transcript Parser:** Implement YAML frontmatter parser and directory fallback.
3. **Semantic Chunker:** Implement speaker-aware dialogue chunker (~600 tokens, 100 overlap, SHA-256).
4. **Embedding Provider:** Implement fixed `OllamaEmbeddingProvider` (768-dim `nomic-embed-text`).
5. **Ingestion Script & Status Endpoint:** Implement `python -m scripts.ingest` and `GET /api/v1/ingest/status`.

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
