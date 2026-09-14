# Phase P0.2 Summary: Transcript Knowledge Pipeline & Ingestion

> **Status**: Complete  
> **Completed**: 2026-09-14  

---

## Objective
Implement a reproducible, idempotent knowledge ingestion pipeline for Lenny's Podcast transcripts. Extract YAML frontmatter metadata, normalize transcript text while strictly preserving verbatim textual content, segment into speaker-aware chunks (~600 tokens with 100-token overlap) with injected metadata headers, generate deterministic SHA-256 content hashes, produce fixed 768-dimensional embeddings via Ollama `nomic-embed-text`, persist idempotently to PostgreSQL 16 + pgvector, provide an ingestion CLI (`python -m scripts.ingest`), expose a live status endpoint (`GET /api/v1/ingest/status`), and build comprehensive automated tests.

---

## Deliverables

| Deliverable | Status | Notes |
| :--- | :--- | :--- |
| `backend/pyproject.toml` | ✅ | Explicitly declared `pyyaml>=6.0.1` |
| `docker-compose.yml` | ✅ | Added `./data:/app/data:ro` read-only mount for containerized corpus access |
| `backend/app/ingestion/models.py` | ✅ | Pydantic models: `EpisodeMetadata`, `RawTranscript`, `ProcessedChunk`, `IngestionStats` |
| `backend/app/ingestion/parser.py` | ✅ | Safe YAML parser with directory-name fallback resilience and Unicode text normalizer |
| `backend/app/ingestion/chunker.py` | ✅ | Speaker-aware dialogue chunker (~600 tokens, 100 overlap), preamble injection, and SHA-256 hasher |
| `backend/app/ingestion/embeddings.py` | ✅ | `OllamaEmbeddingProvider` decoupled from generation, generating 768-dim `nomic-embed-text` vectors |
| `backend/app/db/schema.sql` & `init_db.py` | ✅ | Added metadata columns (`description`, `video_id`, `duration_seconds`, `duration`, `view_count`, `channel`) |
| `backend/app/db/session.py` | ✅ | Configured `NullPool` to prevent asyncpg connection pool event-loop collisions across tests |
| `backend/app/ingestion/pipeline.py` | ✅ | `IngestionPipeline` with file discovery, batch embedding, and idempotent upserts |
| `backend/scripts/ingest.py` | ✅ | CLI runner: `python -m scripts.ingest` supporting `--data-dir`, `--limit`, `--dry-run`, `--force` |
| `backend/app/api/v1/ingest.py` | ✅ | `GET /api/v1/ingest/status` reporting live episode/chunk counts and HNSW index status |
| `backend/app/main.py` | ✅ | Registered `/api/v1/ingest` router |
| `backend/tests/test_parser.py` | ✅ | 4 unit tests for YAML parsing, fallbacks, and text normalization |
| `backend/tests/test_chunker.py` | ✅ | 4 unit tests for speaker turn parsing, chunk sizing, overlap, ordering, and deterministic hashing |
| `backend/tests/test_embeddings.py` | ✅ | 5 unit/integration tests for dimension validation (768), batching, and Ollama connection |
| `backend/tests/test_ingestion.py` | ✅ | 4 integration tests for pipeline discovery, dry run, idempotent persistence, and status API |

---

## Verification Results

| Check | Command / Verification | Result |
| :--- | :--- | :--- |
| Corpus Discovery | `python -m scripts.ingest --dry-run --limit 3` | ✅ 303 transcript files discovered under `data/transcripts` |
| Parser & Chunker | `pytest tests/test_parser.py tests/test_chunker.py` | ✅ 8 passed in 0.11s |
| Embedding Provider | `pytest tests/test_embeddings.py` | ✅ 5 passed; dimension strictly verified at 768 |
| Full Test Suite | `docker compose exec backend pytest -v` | ✅ 24 passed in 0.62s |
| Representative Ingestion | `docker compose exec backend python -m scripts.ingest --limit 3` | ✅ 3 episodes, 109 chunks created, 109 embeddings generated |
| Vector Dimension in DB | `SELECT vector_dims(embedding), count(*) FROM transcript_chunks GROUP BY 1;` | ✅ Exactly 768 dimensions across all 109 persisted chunks |
| Idempotency Check | Re-run `python -m scripts.ingest --limit 1` | ✅ 0 new chunks, 42 skipped (deduplicated), 0 embeddings generated |
| Ingest Status Endpoint | `curl -s http://localhost:8000/api/v1/ingest/status` | ✅ `{"total_episodes":3,"total_chunks":109,"chunks_with_embeddings":109,"hnsw_index_ready":true,"status":"ready"}` |
| pgvector HNSW Query | `SELECT 1 - (embedding <=> :vec) AS similarity ...` | ✅ Cosine similarity search verified with sub-millisecond execution |

---

## Ingestion Verification Scope

- **Corpus Availability:** 303 episode transcripts present under `data/transcripts/episodes/`.
- **Representative Ingestion Verified:** 3 complete episodes (`Ada Chen Rekhi`, `Adam Fishman`, `Adam Grenier`) fully ingested into PostgreSQL with 109 chunks and 768-dim embeddings.
- **Full-Corpus Ingestion Ready:** Full corpus ingestion can be executed at any time via `docker compose exec backend python -m scripts.ingest` (estimated runtime: ~25-35 minutes for ~12,000–18,000 chunks depending on local compute).
- **Idempotency Validated:** Re-ingesting existing episodes generates 0 redundant embeddings and executes in < 0.1s.

---

## Architectural Constraints Preserved

- **Fixed Dimension:** `VECTOR(768)` immutable in database schema and verified by tests.
- **Provider Separation:** `OllamaEmbeddingProvider` is completely independent of `LLM_PROVIDER` (switching to Anthropic or another generation provider never triggers re-ingestion or alters vector search).
- **Zero External Vector Stores:** PostgreSQL 16 + pgvector is the sole persistence engine (no Pinecone, Qdrant, Chroma, Redis, or Celery).
- **Strict Phase Boundary:** Zero P0.3 code (retrieval engine, grounding gate, query rewriter) implemented.

---

## Next Steps
- Proceed to Phase P0.3: Vector Retrieval & Deterministic Grounding Gate (`QueryRewriter`, pgvector cosine similarity search, and 4-tier Grounding Gate).
