# Phase P0.3 Summary: Vector Retrieval & Deterministic Grounding Gate

> **Status**: Complete  
> **Completed**: 2026-09-14  

---

## Objective

Implement the deterministic retrieval and grounding layer over the transcript corpus. Provide semantic retrieval against PostgreSQL 16 + pgvector using 768-dimensional `nomic-embed-text` embeddings from Ollama, enforce strict query normalization boundaries, define a typed evidence contract, and triage evidence through a fully deterministic Grounding Gate adhering to the canonical 4-tier taxonomy (`Strong`, `Limited`, `Conflicting`, `Insufficient`) with empirical thresholds (0.78 / 0.65). Expose a minimal backend API (`POST /api/v1/retrieval/search` and `/preview`) and verify with automated unit and live integration tests.

---

## Deliverables

| Deliverable | Status | Notes |
| :--- | :--- | :--- |
| `backend/app/retrieval/models.py` | ✅ | Typed contracts: `EvidenceItem`, `GroundingTier` (canonical 4 tiers), `SourceDiversity`, `GroundingDecision`, `RetrievalRequest`, `RetrievalResponse` |
| `backend/app/retrieval/query.py` | ✅ | Query normalization boundary: whitespace collapse, quote/unicode normalization, non-empty validation |
| `backend/app/retrieval/engine.py` | ✅ | `VectorRetrievalEngine`: query embedding via Ollama `nomic-embed-text` (768 dimensions), cosine similarity search via pgvector `<=>` operator over HNSW index, metadata join, deterministic scoring |
| `backend/app/retrieval/grounding.py` | ✅ | `GroundingGate`: deterministic triage enforcing Strong (>= 0.78), Limited ([0.65, 0.78)), Insufficient (< 0.65 or empty), and Conflicting (>= 0.78 with multi-guest divergence). Disallows synthesis and clears selected evidence on Insufficient |
| `backend/app/api/v1/retrieval.py` | ✅ | FastAPI routes: `POST /api/v1/retrieval/search` and `POST /api/v1/retrieval/preview` with error handling (422 Unprocessable Entity, 503 Unavailable) |
| `backend/app/main.py` | ✅ | Registered `retrieval.router` under `/api/v1` |
| `backend/tests/test_retrieval.py` | ✅ | 15 comprehensive unit and live integration tests covering normalization, gate tiers, episode independence, conflict detection, engine mappings, API endpoints, and live queries |

---

## Verification Results

| Check | Command / Verification | Result |
| :--- | :--- | :--- |
| Query Normalization | `pytest tests/test_retrieval.py -k "test_query"` | ✅ Whitespace, tabs, newlines collapsed; smart quotes normalized; empty queries raise ValueError |
| GroundingGate Tiers | `pytest tests/test_retrieval.py -k "test_grounding_gate"` | ✅ All 4 tiers (`Strong`, `Limited`, `Conflicting`, `Insufficient`) deterministically assigned according to thresholds |
| Episode Count Invariant | `test_grounding_gate_single_episode_can_be_strong` | ✅ Single episode with score >= 0.78 correctly receives Strong tier (episode count is diversity metadata, not a gate blocker) |
| Insufficient Refusal | `test_grounding_gate_insufficient_tier_low_score` | ✅ Score < 0.65 produces `can_synthesize=False` and `selected_evidence=[]` |
| Conflict Detection | `test_grounding_gate_conflicting_tier` | ✅ Opposing perspectives across distinct guests assign Conflicting tier without an LLM |
| Full Test Suite | `docker compose exec backend pytest -v` | ✅ **39 passed** in 0.59s (24 P0.1/P0.2 tests + 15 new P0.3 tests) |
| Live Supported Retrieval | `curl -s -X POST http://localhost:8000/api/v1/retrieval/search -d '{"query": "Feeling stuck? Here is how to know when it is time to leave your job"}'` | ✅ Returns 200 OK, `tier: "Limited"` (score 0.7510), 4 qualifying chunks, full episode/guest metadata |
| Live Strong Retrieval | `curl -s -X POST http://localhost:8000/api/v1/retrieval/search -d '{"query": "Feeling stuck? Here's how to know when it's time to leave your job | Ada Chen Rekhi"}'` | ✅ Returns 200 OK, `tier: "Strong"` (score 0.8628), `can_synthesize: true` |
| Live Insufficient Retrieval | `test_live_retrieval_insufficient_query` | ✅ Unrelated query (quantum chromodynamics) returns `tier: "Insufficient"`, `can_synthesize: false`, `selected_evidence: []` |

---

## Architectural Decisions & Constraints Preserved

1. **Deterministic Grounding Gate:**
   - Evaluates retrieved cosine similarity scores deterministically without invoking any LLM judge.
   - Strictly enforces canonical 4 tiers: `Strong`, `Limited`, `Conflicting`, `Insufficient`. All legacy aliases ("Weak") remain eradicated.
   - Refusal behavior: When top similarity score < 0.65 or no candidates exist, `can_synthesize` is set to `False` and `selected_evidence` is emptied to prevent hallucinated synthesis.

2. **Episode Count Invariant:**
   - Episode count is treated strictly as source-diversity metadata and presentation information, NOT a gating requirement for the `Strong` tier. A deep, highly relevant answer from a single authoritative interview receives `Strong` status.

3. **Pragmatic Conflict Detection:**
   - Detects whether qualifying evidence chunks (score >= 0.78) originate from $\ge 2$ distinct guests and contain contrastive/oppositional lexical patterns.
   - Operates deterministically without an expensive LLM judge.

4. **Independent Embeddings:**
   - Embeddings are generated with `nomic-embed-text` (768 dimensions) via Ollama, remaining completely separate from future answer generation providers (Anthropic / Ollama).

5. **Strict Scope Enforcement:**
   - Zero Pi Coding Agent code introduced.
   - Zero Pi subprocess bridge or RPC code introduced.
   - Zero LLM answer synthesis or chat/session management introduced.
   - Zero frontend UI components introduced.

---

## Next Steps

- Proceed to Phase P0.4: Pi Agent Core & Subprocess Bridge (validate minimal FastAPI-to-Pi stdio JSON-RPC bridge spike before full agent extension integration).
