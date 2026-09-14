# TODO.md — Pending Items

> Quick capture of tasks, validation items, and milestones.

---

## Priority Levels

| Level | Use For |
| :--- | :--- |
| `high` 🔴 | Blocking items, critical P0 milestones |
| `medium` 🟡 | Standard phase tasks, P1 capabilities |
| `low` 🟢 | Nice-to-have, P2 hardening & optimizations |

---

## Active Items

### Phase P0.1 Foundation (Completed)
- [x] Author execution plan for Phase P0.1 `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Create `docker-compose.yml` (`postgres` with pgvector, `ollama`, `backend`) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Create `.env.example` with safe defaults and `.gitignore` `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Scaffold backend package (`backend/Dockerfile`, `backend/pyproject.toml`) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement PostgreSQL DDL (`backend/app/db/schema.sql`, `init_db.py`) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement FastAPI app factory with logging & Pydantic config `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement health check endpoint `GET /api/v1/health` testing DB and Ollama `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Verify startup via `docker compose up -d` and test health endpoint `high` 🔴 — 2026-09-14 ✓ 2026-09-14

### Phase P0.2 Ingestion & Embeddings (Completed)
- [x] Implement transcript parser with YAML frontmatter extraction `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement speaker-aware semantic chunker (~600 tokens, 100 overlap, SHA-256) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement fixed `OllamaEmbeddingProvider` (768-dim `nomic-embed-text`) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement CLI ingestion command `python -m scripts.ingest` `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement admin status endpoint `GET /api/v1/ingest/status` `medium` 🟡 — 2026-09-14 ✓ 2026-09-14

### Phase P0.3 Retrieval & Grounding Gate (Completed)
- [x] Implement deterministic query normalization boundary (whitespace collapse, quote/unicode normalization, non-empty validation) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement vector retrieval engine (pgvector cosine `<=>` top-k with HNSW index & metadata join) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement deterministic Grounding Gate (Strong $\ge 0.78$, Limited $0.65 \le S < 0.78$, Conflicting, Insufficient $< 0.65$) `high` 🔴 — 2026-09-14 ✓ 2026-09-14
- [x] Implement retrieval search & preview endpoints `POST /api/v1/retrieval/search` and `/preview` `medium` 🟡 — 2026-09-14 ✓ 2026-09-14
- [x] Build automated test suite for query normalization, gate tiers, and live queries (39 tests total) `high` 🔴 — 2026-09-14 ✓ 2026-09-14

### Phase P0.4 Pi Subprocess Bridge Spike (Critical Risk Gate)
- [ ] Create standalone bridge validation spike script `high` 🔴 — 2026-09-14
- [ ] Verify FastAPI parent can launch Pi 0.85.1 over stdio pipes `high` 🔴 — 2026-09-14
- [ ] Verify Pi invokes registered `transcript_retrieval` tool and receives evidence `high` 🔴 — 2026-09-14
- [ ] Verify parent process captures streamed response and exits/reuses cleanly `high` 🔴 — 2026-09-14
- [ ] Validate fallback to HTTP sidecar if stdio proves brittle `medium` 🟡 — 2026-09-14

### Phase P0.5 Providers & Grounded Q&A
- [ ] Implement `GenerationProvider` abstraction (Ollama default + Anthropic Claude) `high` 🔴 — 2026-09-14
- [ ] Implement `SessionManager` in PostgreSQL (session lifecycle + history hydration) `high` 🔴 — 2026-09-14
- [ ] Wire Pi Agent with production bridge and system grounding prompt `high` 🔴 — 2026-09-14
- [ ] Implement SSE streaming endpoint `POST /api/v1/sessions/{id}/messages` `high` 🔴 — 2026-09-14
- [ ] Implement post-generation citation validator `high` 🔴 — 2026-09-14

### Phase P0.6 Evaluator UI & Test Suite
- [ ] Scaffold React 18 + Vite frontend with TailwindCSS `high` 🔴 — 2026-09-14
- [ ] Build chat interface with SSE streaming and markdown rendering `high` 🔴 — 2026-09-14
- [ ] Implement session switcher sidebar and active provider status badge `high` 🔴 — 2026-09-14
- [ ] Implement evidence tier badges and citation cards `high` 🔴 — 2026-09-14
- [ ] Build automated `pytest` suite for API, retrieval, grounding, and sessions `high` 🔴 — 2026-09-14

### Phase P1 (Product Usefulness & Artifacts)
- [ ] Implement Ship 30 for 30 writing tool with 7 encoded principles `medium` 🟡 — 2026-09-14
- [ ] Implement artifact compiler (Markdown & HTML/CSS) `medium` 🟡 — 2026-09-14
- [ ] Implement split-pane Artifact Viewer with sandboxed `<iframe>` and Bleach `medium` 🟡 — 2026-09-14
- [ ] Add raw code view toggle and copy-to-clipboard `low` 🟢 — 2026-09-14

### Phase P2 (Hardening & Polish)
- [ ] Implement OpenAI GPT-4o provider adapter as second cloud LLM `low` 🟢 — 2026-09-14
- [ ] Implement automated transcript ingestion refresh pipeline `low` 🟢 — 2026-09-14
- [ ] Add dark/light mode toggle and responsive mobile refinements `low` 🟢 — 2026-09-14

---

*Last updated: 2026-09-14*
