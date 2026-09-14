---
phase: P0.3
plan: 1
wave: 1
gap_closure: false
---

# Plan P0.3.1: Vector Retrieval & Deterministic Grounding Gate

## Objective
Implement the deterministic vector retrieval and evidence grounding layer over the ingested Lenny's Podcast transcript corpus in PostgreSQL 16 + pgvector. Provide query normalization, semantic cosine similarity search (`<=>`) using fixed 768-dim `nomic-embed-text` embeddings generated via Ollama, typed serializable evidence objects with source metadata, and a deterministic 4-tier Grounding Gate (Strong, Limited, Conflicting, Insufficient) that enforces honesty and refusal before any synthesis. Expose `POST /api/v1/retrieval/search` and verify with automated unit and integration tests.

## Context
Load these files for context:
- `.gsd/SPEC.md`
- `.gsd/REQUIREMENTS.md` (REQ-06, REQ-07, REQ-08, REQ-09, NFR-03, NFR-04)
- `.gsd/DECISIONS.md` (DECISION-002, DECISION-003, DECISION-005, DECISION-006)
- `architecture.md` (Sections 6.6, 8.2, 8.3: Retrieval Engine & Grounding Gate)
- `PRD.md` (Section 9: Grounding Gate & Refusal Scenarios)

## Tasks

<task type="auto" effort="medium">
  <name>Retrieval Data Models, Query Normalizer & Vector Retrieval Engine</name>
  <files>
    backend/app/retrieval/__init__.py
    backend/app/retrieval/models.py
    backend/app/retrieval/query.py
    backend/app/retrieval/engine.py
  </files>
  <action>
    Implement typed evidence models, query normalization boundary, and the pgvector retrieval engine.
    
    Steps:
    1. Create `backend/app/retrieval/models.py`:
       - `EvidenceItem`: Pydantic model with fields:
         - `chunk_id`: str / UUID
         - `episode_id`: str / UUID
         - `title`: str
         - `guest`: str
         - `publication_date`: Optional[date]
         - `source_path`: str
         - `chunk_index`: int
         - `speaker`: Optional[str]
         - `content`: str
         - `similarity_score`: float
         - `source_identifier`: str (e.g. `{guest} - {title} [Chunk #{chunk_index}]`)
         - `excerpt`: str (concise excerpt of substantive text)
       - `GroundingTier`: Enum string with canonical values: `Strong`, `Limited`, `Conflicting`, `Insufficient`. (Strictly NO "Weak" or aliases).
       - `SourceDiversity`: model with `episode_count`, `guest_count`, `guests: list[str]`, `episodes: list[str]`.
       - `GroundingDecision`: model with:
         - `tier`: GroundingTier
         - `can_synthesize`: bool
         - `top_score`: float
         - `confidence_score`: float
         - `selected_evidence`: list[EvidenceItem]
         - `source_diversity`: SourceDiversity
         - `reason`: str
       - `RetrievalRequest`: model with `query: str`, `top_k: int = 15`.
       - `RetrievalResponse`: model with `query: str`, `normalized_query: str`, `decision: GroundingDecision`, `evidence: list[EvidenceItem]`.
    2. Create `backend/app/retrieval/query.py`:
       - `normalize_query(query: str) -> str`:
         - Strip leading/trailing whitespace.
         - Normalize internal whitespace runs.
         - Replace smart quotes and irregular Unicode characters.
         - Reject empty or whitespace-only queries by raising `ValueError`.
    3. Create `backend/app/retrieval/engine.py`:
       - `VectorRetrievalEngine`:
         - Uses `OllamaEmbeddingProvider` to embed queries into 768-dim vectors.
         - Executes HNSW-indexed cosine distance query (`<=>`) joining `transcript_chunks` and `episodes`:
           `1 - (c.embedding <=> :query_vec) AS similarity_score`.
         - Orders by cosine distance ascending (`similarity_score DESC`).
         - Limits results to configurable `top_k` (default 15).
         - Maps query results into serializable `EvidenceItem` objects with provenance metadata.
  </action>
  <verify>
    Run a test script or quick query in the container to verify that `VectorRetrievalEngine` retrieves ranked chunks with similarity scores and metadata for an ingested episode.
  </verify>
  <done>
    `VectorRetrievalEngine` produces ordered `list[EvidenceItem]` with accurate metadata and scores between 0 and 1.
  </done>
</task>

<task type="auto" effort="medium">
  <name>Deterministic Grounding Gate & Conflict Detection</name>
  <files>
    backend/app/retrieval/grounding.py
  </files>
  <action>
    Implement the 4-tier deterministic Grounding Gate logic.
    
    Steps:
    1. Create `backend/app/retrieval/grounding.py`:
       - `GroundingGate`:
         - Uses canonical thresholds:
           - `STRONG_THRESHOLD = settings.GROUNDING_STRONG_THRESHOLD` (default 0.78)
           - `LIMITED_THRESHOLD = settings.GROUNDING_LIMITED_THRESHOLD` (default 0.65)
         - `triage(evidence: list[EvidenceItem]) -> GroundingDecision`:
           - If `not evidence` or `top_score < LIMITED_THRESHOLD` (0.65):
             - Tier: `Insufficient`
             - `can_synthesize`: `False`
             - `reason`: "Insufficient evidence in Lenny's Podcast transcripts to support an answer."
             - `selected_evidence`: empty list (refusal prevents hallucination).
           - If `LIMITED_THRESHOLD <= top_score < STRONG_THRESHOLD` (0.65 <= S < 0.78):
             - Tier: `Limited`
             - `can_synthesize`: `True`
             - `reason`: "Limited or tangential evidence found in corpus; synthesis must state limitations."
             - `selected_evidence`: top candidates above threshold.
           - If `top_score >= STRONG_THRESHOLD` (S >= 0.78):
             - Evaluate conflict signal:
               - Check distinct guests in top high-scoring chunks ($S \ge 0.75$).
               - If multiple distinct guests ($\ge 2$) present opposing perspectives (divergent claims or contrastive lexical signals across distinct sources), assign `Conflicting`:
                 - Tier: `Conflicting`
                 - `can_synthesize`: `True`
                 - `reason`: "Materially divergent viewpoints found across distinct podcast guests; both perspectives must be surfaced."
               - Otherwise:
                 - Tier: `Strong`
                 - `can_synthesize`: `True`
                 - `reason`: "Strong evidence found directly addressing the question."
             - `selected_evidence`: top 5 deduplicated candidate chunks.
  </action>
  <verify>
    Execute unit tests with controlled synthetic `EvidenceItem` fixtures at scores 0.85, 0.72, and 0.50 to verify GroundingGate outputs Strong, Limited, and Insufficient tiers accurately.
  </verify>
  <done>
    `GroundingGate` deterministically classifies evidence into the 4 canonical tiers without LLM inference.
  </done>
</task>

<task type="auto" effort="medium">
  <name>Retrieval API Endpoints</name>
  <files>
    backend/app/api/v1/retrieval.py
    backend/app/main.py
  </files>
  <action>
    Expose REST endpoints for retrieval and evidence triage.
    
    Steps:
    1. Create `backend/app/api/v1/retrieval.py`:
       - `POST /api/v1/retrieval/search`:
         - Accepts `RetrievalRequest(query: str, top_k: int = 15)`.
         - Validates and normalizes query.
         - Executes `VectorRetrievalEngine.search(normalized_query, top_k)`.
         - Passes evidence to `GroundingGate.triage(evidence)`.
         - Returns `RetrievalResponse`.
       - `POST /api/v1/retrieval/preview` as alias to `/search` satisfying both API conventions.
    2. Register router in `backend/app/main.py`:
       - `app.include_router(retrieval_router, prefix="/api/v1")`.
  </action>
  <verify>
    Send HTTP POST to `http://localhost:8000/api/v1/retrieval/search` via `curl` with a growth query and an out-of-domain query; verify responses match the schema.
  </verify>
  <done>
    API endpoints return 200 OK with query, grounding decision, scores, and evidence items.
  </done>
</task>

<task type="auto" effort="medium">
  <name>Retrieval Automated Test Suite & Empirical Verification</name>
  <files>
    backend/tests/test_retrieval.py
  </files>
  <action>
    Build unit and integration tests for query normalization, retrieval scoring, GroundingGate tiers, and API endpoints.
    
    Steps:
    1. Create `backend/tests/test_retrieval.py`:
       - Test query normalization (strips whitespace, Unicode quotes).
       - Test empty/whitespace query rejection (raises ValueError/HTTP 422).
       - Test GroundingGate threshold boundaries (0.78, 0.65, below 0.65).
       - Test Insufficient refusal (`can_synthesize == False`).
       - Test Conflicting tier when distinct guests present opposing perspectives.
       - Test `VectorRetrievalEngine` with mock and live embeddings.
       - Test `POST /api/v1/retrieval/search` endpoint via `TestClient`.
    2. Run full test suite: `docker compose exec backend pytest -v`.
  </action>
  <verify>
    Run `docker compose exec backend pytest -v` and verify all tests pass.
  </verify>
  <done>
    Full test suite passes with 0 failures, verifying retrieval engine and Grounding Gate.
  </done>
</task>

## Success Criteria
- [ ] Query normalizer rejects empty queries and cleans text deterministically.
- [ ] `VectorRetrievalEngine` generates 768-dim query embedding and executes cosine search (`<=>`).
- [ ] Retrieval returns ordered `EvidenceItem` records with complete provenance metadata.
- [ ] `GroundingGate` strictly implements 4 canonical tiers: Strong, Limited, Conflicting, Insufficient.
- [ ] Thresholds 0.78 and 0.65 are strictly enforced without LLM latency.
- [ ] Out-of-domain queries ($S < 0.65$) produce `Insufficient` with `can_synthesize=False`.
- [ ] `POST /api/v1/retrieval/search` and `/preview` return valid RFC-compliant responses.
- [ ] All automated tests pass inside Docker container.
- [ ] Real queries against ingested episodes verified live.
- [ ] Working tree clean, atomic task commits verified, zero P0.4 code implemented.
