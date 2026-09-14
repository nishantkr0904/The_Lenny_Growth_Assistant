# Phase P0.5 Plan: Model Providers, Session Management & Multi-Turn Grounded Q&A

> **Phase**: P0.5 — Model Providers, Session Management & Multi-Turn Grounded Q&A  
> **Status**: Ready to Execute  
> **Target**: Turn the validated P0.4 Pi + retrieval spike into the production-oriented backend Q&A foundation with PostgreSQL session persistence, conversation-aware query rewriting, generation provider abstraction (Ollama default, Anthropic cloud), Grounding Gate preservation, post-generation citation validation, and streaming-capable Q&A API boundary.  

---

## 1. Context & Objective

Phase P0.4 validated the core integration loop of Pi Coding Agent 0.85.1 with Ollama `llama3.1:8b`, custom retrieval tool, and the P0.3 Grounding Gate.

Phase P0.5 establishes the **production backend Q&A subsystem**:
```
User Query
    ↓
FastAPI Gateway (POST /api/v1/sessions/{id}/messages)
    ↓
Session Manager (Hydrate bounded working context from PostgreSQL: last N=6 turns)
    ↓
Conversation-Aware Query Rewriter (Resolve pronouns/implicit references for retrieval)
    ↓
P0.3 Vector Retrieval Engine (Cosine <=> pgvector over HNSW index)
    ↓
Deterministic Grounding Gate (Authoritative triage: Strong / Limited / Conflicting / Insufficient)
    ↓
Pi Cognitive Layer / Q&A Orchestrator
    ↓
Generation Provider (Ollama llama3.1:8b default / Anthropic Claude P0 cloud via .env)
    ↓
Post-Generation Citation Validator (Verify cited sources against retrieved chunks)
    ↓
Persistence Layer (Save user & assistant messages, source_references, latency, tier)
    ↓
Response Boundary (JSON or Server-Sent Events SSE text/event-stream)
```

---

## 2. Architectural Boundaries & Non-Negotiable Rules

1. **P0.3 Retrieval Engine Single Source of Truth:** Reuse `VectorRetrievalEngine` and `GroundingGate` from `backend/app/retrieval/`. Zero duplicate vector SQL or embedding logic.
2. **Deterministic Grounding Gate:** The model NEVER overrides `Strong`, `Limited`, `Conflicting`, or `Insufficient`.
3. **Refusal on Insufficient Evidence:** When `can_synthesize is False` ($S < 0.65$), LLM synthesis is bypassed entirely, returning a deterministic honest refusal. No web search, no general knowledge fallback, no hallucinations.
4. **Pi Agent Core:** The cognitive loop, system grounding instructions, and structured evidence delivery follow the validated P0.4 pattern.
5. **Decoupled Providers:** Generation provider (`OllamaGenerationProvider` / `AnthropicGenerationProvider`) is separate from embedding provider (`Ollama / nomic-embed-text` fixed at 768 dimensions).
6. **No Silent Fallback:** If `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` is missing/invalid, fail immediately with a clear configuration error. Zero silent fallback to Ollama.
7. **Zero Exposed Secrets:** API keys are never logged, persisted, or returned in API responses.
8. **Strict Phase Boundaries:** Zero frontend (P0.6), zero Ship30 (P1.1), zero artifacts (P1.2), zero OpenAI (P2.1).

---

## 3. Implementation Tasks

### Task 1: Session & Message Persistence Layer
- **Files**: `backend/app/sessions/models.py`, `backend/app/sessions/store.py`, `backend/app/sessions/__init__.py`
- Utilize existing PostgreSQL tables: `sessions`, `messages`, `source_references`.
- Implement `SessionStore`:
  - `create_session(title, db) -> SessionModel`
  - `get_session(session_id, db) -> SessionModel | None`
  - `list_sessions(limit, db) -> list[SessionModel]`
  - `save_message(session_id, role, content, evidence_tier, latency_ms, model_used, db) -> MessageModel`
  - `save_source_references(message_id, references, db) -> None`
  - `get_recent_messages(session_id, limit=6, db) -> list[MessageModel]` (Bounded working context in chronological order)
- Commit: `feat(phase-P0.5): session and message persistence layer`

### Task 2: Conversation Context & Query Rewriting
- **Files**: `backend/app/retrieval/rewriter.py`, `backend/app/retrieval/__init__.py`
- Implement `ConversationQueryRewriter`:
  - If conversation history is empty or question is standalone $\implies$ returns normalized query.
  - If conversation history contains prior turns $\implies$ uses context (last $N=6$ messages) to resolve pronouns ("she", "that", "what about his advice on...") into a self-contained search query.
  - Is isolated from answer synthesis: rewriter only transforms queries for retrieval and never generates facts or answers.
- Commit: `feat(phase-P0.5): conversation context and query rewriting`

### Task 3: Generation Provider Abstraction & Anthropic Support
- **Files**: `backend/app/providers/base.py`, `backend/app/providers/ollama.py`, `backend/app/providers/anthropic.py`, `backend/app/providers/factory.py`, `backend/app/providers/__init__.py`, `backend/pyproject.toml`
- Add `anthropic>=0.20.0` to `backend/pyproject.toml`.
- Define `GenerationProvider` base interface with async `generate(...)` and async generator `stream(...)`.
- Implement `OllamaGenerationProvider` connecting to `OLLAMA_BASE_URL` with `OLLAMA_MODEL` (`llama3.1:8b`).
- Implement `AnthropicGenerationProvider` using the official `anthropic` SDK with `ANTHROPIC_MODEL` (`claude-3-5-sonnet-20241022`).
- Implement `get_generation_provider()`:
  - If `LLM_PROVIDER == "anthropic"`: validates `ANTHROPIC_API_KEY`. If missing, raises `ProviderConfigurationError("Anthropic API key is not configured")`.
  - Default: `OllamaGenerationProvider`.
- Commit: `feat(phase-P0.5): generation provider abstraction and anthropic support`

### Task 4: Pi Cognitive Q&A Orchestrator & Citation Validator
- **Files**: `backend/app/agent/citation.py`, `backend/app/agent/orchestrator.py`
- Implement `CitationValidator`:
  - Scans model output for citations (`[chunk-id]` or guest/episode references).
  - Verifies that all cited references correspond to chunks in `selected_evidence`.
  - Builds structured citation records linking back to `transcript_chunks(id)`.
  - Flags ungrounded citations if fabricated.
- Implement `QnAOrchestrator`:
  - Encapsulates the cognitive Q&A pipeline:
    1. Persist user message in DB.
    2. Hydrate bounded session history (last 6 messages).
    3. Run conversation-aware query rewriting.
    4. Execute P0.3 `VectorRetrievalEngine` search.
    5. Evaluate `GroundingGate` triage.
    6. If `Insufficient`: construct deterministic refusal message, bypass LLM, save assistant message, return/stream refusal.
    7. If `Strong` / `Limited` / `Conflicting`: format system prompt with strict grounding constraints and XML evidence chunks.
    8. Invoke generation provider (with streaming or non-streaming).
    9. Run post-generation citation validation.
    10. Persist assistant message and source references in DB.
    11. Yield structured response or SSE events (`thinking`, `evidence`, `delta`, `citation`, `done`).
- Commit: `feat(phase-P0.5): production qna orchestrator and citation validator`

### Task 5: Q&A API Endpoints
- **Files**: `backend/app/api/v1/sessions.py`, `backend/app/main.py`
- Endpoints:
  - `POST /api/v1/sessions`: Create new session with optional title.
  - `GET /api/v1/sessions`: List recent sessions with message counts.
  - `GET /api/v1/sessions/{id}`: Retrieve session details and messages.
  - `POST /api/v1/sessions/{id}/messages`: Send user message.
    - If `stream: false` $\implies$ returns JSON payload matching architecture spec: `session_id`, `message_id`, `role`, `content`, `grounding`, `sources`, `latency_ms`, `model_used`.
    - If `stream: true` $\implies$ returns `text/event-stream` (SSE) emitting `thinking`, `evidence`, `delta`, `citation`, `done`.
- Register sessions router in `backend/app/main.py`.
- Commit: `feat(phase-P0.5): session and streaming qna api endpoints`

### Task 6: Focused Automated Test Suite
- **Files**: `backend/tests/test_sessions.py`, `backend/tests/test_rewriter.py`, `backend/tests/test_providers.py`, `backend/tests/test_citation.py`, `backend/tests/test_qna_api.py`
- Unit and integration tests covering:
  - Session and message CRUD, bounded context window ($N=6$).
  - Query rewriting with and without history; pronoun resolution.
  - Provider abstraction: Ollama generation/streaming, Anthropic initialization, missing API key configuration error.
  - Citation validation: valid citations, missing chunks, ungrounded claims.
  - Q&A API: session creation, message execution (JSON and SSE), refusal on Insufficient tier.
- Run `docker compose exec backend pytest -v` (ensure all tests pass).
- Commit: `test(phase-P0.5): automated test suite for qna subsystem`

### Task 7: Real End-to-End Live Validation & Documentation
- Execute real multi-turn verification against running stack:
  - **Scenario A (Supported Query):** Question regarding Ada Chen Rekhi $\to$ verified session, message persistence, retrieval, grounding, citation, response.
  - **Scenario B (Follow-up Query):** Query with pronouns ("What about when she...") $\to$ verified query rewriting and multi-turn context preservation.
  - **Scenario C (Unsupported Query):** Out-of-domain quantum chromodynamics $\to$ verified deterministic refusal without LLM hallucination.
  - **Scenario D (Cloud Provider Validation):** Verified configuration error on missing Anthropic key, clean provider switching via `LLM_PROVIDER`.
- Audited processes and database records.
- Document phase in `.gsd/phases/P0.5/SUMMARY.md`.
- Update `.gsd/STATE.md`, `.gsd/ROADMAP.md`, `.gsd/REQUIREMENTS.md`, `.gsd/TODO.md`, `.gsd/JOURNAL.md`.
- Commit: `docs(phase-P0.5): complete production qna foundation`

---

## 4. Acceptance Criteria

1. PostgreSQL `sessions`, `messages`, and `source_references` tables are populated and queried via `SessionStore`.
2. Working conversation context is strictly bounded (last $N=6$ messages).
3. Follow-up queries with pronouns are rewritten into standalone retrieval queries.
4. P0.3 `VectorRetrievalEngine` and `GroundingGate` are reused without duplication.
5. `GenerationProvider` decouples Ollama (`llama3.1:8b`) and Anthropic (`claude-3-5-sonnet-20241022`).
6. Selecting `LLM_PROVIDER=anthropic` with missing key raises a clear configuration error; zero silent fallbacks.
7. Post-generation citation validation ensures citations map to retrieved chunks.
8. Insufficient evidence triggers deterministic refusal without LLM synthesis.
9. `POST /api/v1/sessions` and `POST /api/v1/sessions/{id}/messages` work for both JSON and SSE streaming.
10. All automated backend tests pass.
11. Clean git working tree with zero committed secrets.
12. Stop condition adhered to: Zero P0.6 or P1 code.
