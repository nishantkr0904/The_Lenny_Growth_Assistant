---
phase: P0.2
plan: 1
wave: 1
gap_closure: false
---

# Plan P0.2.1: Transcript Knowledge Pipeline & Ingestion

## Objective
Implement the complete transcript ingestion pipeline for the Lenny Podcast corpus. Extract YAML frontmatter metadata, normalize transcript text without aggressive summarization, segment into speaker-aware chunks (~600 tokens with 100-token overlap), generate deterministic SHA-256 content hashes, produce fixed 768-dimensional embeddings via Ollama `nomic-embed-text`, persist idempotently to PostgreSQL 16 + pgvector, provide an ingestion CLI (`python -m scripts.ingest`), expose a status endpoint (`GET /api/v1/ingest/status`), and build comprehensive automated tests.

## Context
Load these files for context:
- `.gsd/SPEC.md`
- `.gsd/REQUIREMENTS.md` (REQ-03, REQ-04, REQ-05, NFR-03)
- `.gsd/DECISIONS.md` (DECISION-002, DECISION-003, DECISION-007, DECISION-010)
- `architecture.md` (Section 7: Knowledge Ingestion Pipeline; Section 14.1: PostgreSQL DDL)
- `README.md` (Transcript Ingestion section, lines 248-266)

## Tasks

<task type="auto" effort="medium">
  <name>Frontmatter Parser & Text Normalizer</name>
  <files>
    backend/pyproject.toml
    backend/app/ingestion/__init__.py
    backend/app/ingestion/models.py
    backend/app/ingestion/parser.py
  </files>
  <action>
    Implement robust YAML frontmatter parsing and transcript text normalization.
    
    Steps:
    1. Update `backend/pyproject.toml` to explicitly include `pyyaml>=6.0.1`.
    2. Create `backend/app/ingestion/models.py`:
       - `EpisodeMetadata`: Pydantic model with fields:
         - `title`: str
         - `guest`: str
         - `publication_date`: Optional[date]
         - `source_path`: str (unique canonical path relative to corpus root)
         - `episode_url`: Optional[str]
         - `youtube_url`: Optional[str]
         - `description`: Optional[str]
         - `video_id`: Optional[str]
         - `duration_seconds`: Optional[float]
         - `duration`: Optional[str]
         - `view_count`: Optional[int]
         - `channel`: Optional[str]
         - `keywords`: list[str] = []
       - `RawTranscript`: model with `metadata: EpisodeMetadata` and `content: str`.
       - `ProcessedChunk`: model with `chunk_index: int`, `speaker: Optional[str]`, `content: str`, `content_hash: str`.
    3. Create `backend/app/ingestion/parser.py`:
       - `parse_transcript_file(file_path: Path, base_dir: Optional[Path] = None) -> RawTranscript`:
         - Read file content with UTF-8 encoding.
         - Split YAML frontmatter using standard `---` boundaries.
         - Safely parse YAML using `yaml.safe_load()`.
         - Fallback resilience: If frontmatter is missing or corrupted, infer `guest` from the parent directory name (e.g. `episodes/brian-chesky/` -> `Brian Chesky`) and `title` from directory/file name, logging a warning. Do not invent metadata when absent.
         - Parse `publish_date` safely into `datetime.date`.
         - Normalize text: clean non-standard whitespace, normalize Unicode quotes/dashes, preserve verbatim dialogue and speaker turns (`Speaker (timestamp):`). Strip obvious recurring sponsor break disclaimers if isolated, but never paraphrase or summarize transcript text.
  </action>
  <verify>
    Run a parser unit test or test script against `data/transcripts/episodes/brian-chesky/transcript.md` to confirm all frontmatter fields and dialogue content are extracted accurately.
  </verify>
  <done>
    `parse_transcript_file` successfully extracts `EpisodeMetadata` with all available fields and returns normalized transcript content.
  </done>
</task>

<task type="auto" effort="medium">
  <name>Speaker-Aware Semantic Chunker & Content Hasher</name>
  <files>
    backend/app/ingestion/chunker.py
  </files>
  <action>
    Implement speaker-aware dialogue chunking with context injection and deterministic SHA-256 hashing.
    
    Steps:
    1. Create `backend/app/ingestion/chunker.py`:
       - Define `SpeakerTurn`: `speaker: Optional[str]`, `timestamp: Optional[str]`, `text: str`.
       - Implement speaker turn parser:
         - Regex match speaker lines: `^([A-Za-z0-9 .'-]+?)(?:\s*\(([0-9:]+)\))?:\s*(.*)$`.
         - Handle continuation lines cleanly.
       - Implement `chunk_transcript(raw: RawTranscript, chunk_size: int = 600, chunk_overlap: int = 100) -> list[ProcessedChunk]`:
         - Estimate token counts using a word-to-token ratio (~1.33 tokens per word / ~0.75 words per token).
         - Aggregate consecutive speaker turns into windows of approximately 500-700 tokens (`target = chunk_size`).
         - Apply ~100-token sliding overlap across chunk boundaries to preserve conversational context.
         - Avoid cutting speaker turns mid-sentence where possible.
         - Discard or merge trivial/empty turns (< 10 words) into adjacent turns.
         - Context Injection: Prepend metadata preamble to every chunk:
           `[Episode: {title} | Guest: {guest} | Date: {publish_date}]`
         - Dominant Speaker attribution: identify the primary speaker in each chunk (or guest vs Lenny).
         - Deterministic SHA-256 content hashing:
           `content_hash = hashlib.sha256(f"{metadata.source_path}:{chunk_index}:{chunk_text}".encode('utf-8')).hexdigest()`.
  </action>
  <verify>
    Execute chunker tests on sample transcripts; verify chunk token estimates fall in 500-700 token window, overlap exists, preamble is present, and hashes are strictly deterministic.
  </verify>
  <done>
    `chunk_transcript` produces ordered, non-empty `ProcessedChunk` objects with context headers and unique SHA-256 content hashes.
  </done>
</task>

<task type="auto" effort="large">
  <name>Ollama Embedding Client, Ingestion Pipeline & CLI</name>
  <files>
    docker-compose.yml
    backend/app/db/schema.sql
    backend/app/db/init_db.py
    backend/app/ingestion/embeddings.py
    backend/app/ingestion/pipeline.py
    backend/app/api/v1/ingest.py
    backend/app/main.py
    backend/scripts/__init__.py
    backend/scripts/ingest.py
  </files>
  <action>
    Build the embedding generator, database persistence pipeline, CLI runner, and status API endpoint.
    
    Steps:
    1. Update `docker-compose.yml`:
       - Add `./data:/app/data:ro` to backend volume mounts so container can access `data/transcripts/`.
    2. Update `backend/app/db/schema.sql` and `init_db.py`:
       - Add nullable metadata columns to `episodes`:
         `description TEXT`, `video_id VARCHAR(64)`, `duration_seconds NUMERIC`, `duration VARCHAR(32)`, `view_count INT`, `channel VARCHAR(256)`.
       - Ensure `init_db.py` executes idempotent `ALTER TABLE episodes ADD COLUMN IF NOT EXISTS ...` so existing containers do not require recreating the database.
    3. Create `backend/app/ingestion/embeddings.py`:
       - `OllamaEmbeddingProvider`:
         - Calls `POST {OLLAMA_BASE_URL}/api/embeddings` with `{"model": "nomic-embed-text", "prompt": text}`.
         - Implements batch embedding `embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]`.
         - Asserts embedding length == 768.
         - Strictly decoupled from generation provider; handles network timeouts and retries cleanly.
    4. Create `backend/app/ingestion/pipeline.py`:
       - `IngestionPipeline`:
         - Discovers markdown files under `episodes/`.
         - Coordinates parsing, chunking, and deduplication.
         - Database persistence:
           - Upsert episode into `episodes` table `ON CONFLICT (source_path) DO UPDATE ... RETURNING id`.
           - Check existing chunk hashes: `SELECT content_hash FROM transcript_chunks WHERE episode_id = :ep_id`.
           - Filter out already-embedded chunks (idempotent deduplication).
           - Generate embeddings only for new/modified chunks.
           - Insert new chunks: `INSERT INTO transcript_chunks (episode_id, chunk_index, speaker, content, embedding, content_hash) VALUES (...) ON CONFLICT (content_hash) DO NOTHING`.
         - Metrics tracking: `files_discovered`, `episodes_parsed`, `chunks_created`, `chunks_skipped`, `embeddings_generated`, `failures`, `elapsed_seconds`.
    5. Create `backend/scripts/ingest.py` (CLI):
       - Executable via `python -m scripts.ingest` (or `python -m app.ingestion.cli`).
       - Arguments: `--data-dir`, `--limit`, `--batch-size`, `--dry-run`, `--force`.
       - Prints clean, structured progress summary to stdout.
    6. Create `backend/app/api/v1/ingest.py` and register in `backend/app/main.py`:
       - `GET /api/v1/ingest/status`: returns total episodes, total chunks, embedded chunks, index stats.
  </action>
  <verify>
    Execute ingestion with `--limit 3` against local Docker stack; verify 3 episodes and their chunks are persisted; verify embedding dimension is 768; verify running ingestion again skips existing chunks (100% idempotent); verify `GET /api/v1/ingest/status` returns accurate counts.
  </verify>
  <done>
    `python -m scripts.ingest` successfully runs, embeds via Ollama `nomic-embed-text`, stores in PostgreSQL with `VECTOR(768)`, achieves idempotency on re-run, and status endpoint reports live stats.
  </done>
</task>

<task type="auto" effort="medium">
  <name>Ingestion Automated Test Suite & Empirical Verification</name>
  <files>
    backend/tests/test_parser.py
    backend/tests/test_chunker.py
    backend/tests/test_embeddings.py
    backend/tests/test_ingestion.py
  </files>
  <action>
    Create comprehensive automated tests for all P0.2 components and verify the full ingestion pipeline.
    
    Steps:
    1. Create `backend/tests/test_parser.py`:
       - Test valid YAML frontmatter extraction (all fields).
       - Test missing frontmatter fallback to directory/file name.
       - Test malformed YAML handling (raises informative error).
       - Test date parsing variations.
    2. Create `backend/tests/test_chunker.py`:
       - Test speaker turn parsing (`Speaker (timestamp):`).
       - Test chunk size constraints (~500-700 tokens).
       - Test sliding overlap (~100 tokens).
       - Test context preamble injection.
       - Test deterministic SHA-256 content hashing across repeated calls.
       - Test chunk ordering preservation.
    3. Create `backend/tests/test_embeddings.py`:
       - Test `OllamaEmbeddingProvider` initialization and configuration.
       - Test embedding dimension validation (must be 768).
       - Test mock and live embedding generation.
    4. Create `backend/tests/test_ingestion.py`:
       - Test end-to-end ingestion flow on sample fixture transcripts.
       - Test idempotency: re-ingesting same files inserts 0 duplicate chunks.
    5. Run full test suite: `docker compose exec backend pytest -v`.
  </action>
  <verify>
    Run `docker compose exec backend pytest -v` and verify all tests pass with 0 failures.
  </verify>
  <done>
    All unit and integration tests pass, validating parser, chunker, hasher, embedding provider, and idempotent persistence.
  </done>
</task>

## Success Criteria
- [ ] YAML frontmatter parsed accurately with all available metadata fields.
- [ ] Speaker-aware chunker produces 500-700 token chunks with 100-token overlap and context headers.
- [ ] SHA-256 hashes are deterministic and prevent duplicate chunk inserts.
- [ ] Ollama `nomic-embed-text` generates 768-dimensional embeddings.
- [ ] Vectors stored in PostgreSQL `transcript_chunks` table with `VECTOR(768)`.
- [ ] CLI `python -m scripts.ingest` runs cleanly and reports progress metrics.
- [ ] Re-running ingestion is 100% idempotent (skips already-embedded chunks).
- [ ] `GET /api/v1/ingest/status` returns accurate corpus statistics.
- [ ] All automated tests pass in Docker container.
- [ ] Representative ingestion verified in PostgreSQL.
- [ ] Working tree clean, atomic task commits verified, zero P0.3 code implemented.
