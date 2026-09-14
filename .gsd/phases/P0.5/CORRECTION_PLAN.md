# Phase P0.5 Architectural Correction Plan: Production Pi Agent Bridge

> **Objective:** Put Pi Coding Agent 0.85.1 genuinely into the production Q&A execution path of `QnAOrchestrator`, replacing direct LLM generation calls while preserving all existing P0.5 behaviors, contracts, grounding tiers, and test suites.

---

## 1. Context & Rationale

Phase P0.4 validated Pi Coding Agent 0.85.1 + Ollama `llama3.1:8b` + custom `transcript_retrieval` tool in a standalone spike harness.
The audit of Phase P0.5 revealed that while all functional features (sessions, rewriting, providers, GroundingGate, citation validation, SSE) were implemented and verified, `QnAOrchestrator` called `self.provider.generate()` / `self.provider.stream()` directly in Python rather than invoking Pi as the cognitive agent layer.

This targeted architectural correction establishes:
```
FastAPI Gateway (POST /api/v1/sessions/{id}/messages)
    │
    ▼
QnAOrchestrator
    │
    ▼
PiBridgeClient (Python IPC Client managing Node.js daemon lifecycle)
    │ stdio JSON-RPC
    ▼
Pi Agent Runtime (backend/app/agent/bridge_daemon.mjs)
    │ createAgentSession + customTools
    ▼
transcript_retrieval Tool Extension
    │ HTTP POST /api/v1/retrieval/search
    ▼
Existing P0.3 VectorRetrievalEngine + GroundingGate
    │ (Returns structured XML evidence + GroundingDecision)
    ▼
Pi Cognitive Synthesis (Ollama llama3.1:8b / Anthropic Claude)
    │ (Attribution to guest/episode; refusal on NO_GROUNDED_EVIDENCE)
    ▼
Pi Response & Token Stream
    │ JSON-RPC deltas & final result
    ▼
Existing CitationValidator (Validates citations against retrieved chunks)
    │
    ▼
Existing SessionStore (Persists message & source_references to PostgreSQL)
    │
    ▼
FastAPI Response Boundary (Structured JSON or SSE text/event-stream)
```

---

## 2. Implementation Tasks

### Task 1: Container Environment & Dependencies
- Update `backend/Dockerfile` to install Node.js 22 and `@earendil-works/pi-coding-agent@0.85.1` globally, ensuring the container has the native runtime for Pi.
- Configure `/root/.pi/agent/models.json` inside the container dynamically to point Ollama to `http://ollama:11434/v1`.

### Task 2: Production Pi JSON-RPC Bridge Daemon (`backend/app/agent/bridge_daemon.mjs`)
- Implement long-running Node.js process using stdio JSON-RPC.
- Route all internal logging (`console.log`, `info`, `warn`) to `stderr` to prevent stdout protocol corruption.
- Register `transcript_retrieval` tool via `defineTool` pointing to `http://localhost:8000/api/v1/retrieval/search`.
- Support provider selection (`ollama` or `anthropic`) with strict API key validation (fails immediately with `ProviderConfigurationError` if `ANTHROPIC_API_KEY` is missing; zero silent fallback).
- Support methods:
  - `ping`: Health check returning Pi version and model configuration.
  - `execute_turn`: Run a conversational turn with user prompt, bounded history, and optional query rewriter context; emit token deltas and tool events; return final answer with retrieved evidence.
  - `shutdown`: Clean session disposal and process exit.

### Task 3: Python Pi Bridge Client (`backend/app/agent/pi_bridge.py`)
- Implement `PiBridgeClient` managing the child process lifecycle with `asyncio.create_subprocess_exec`.
- Provide request/response RPC protocol with line-delimited JSON.
- Implement concurrency lock (`asyncio.Lock()`) for safe turn serialization.
- Provide `execute_turn(...)` and `stream_turn(...)` async generators.
- Implement automatic restart and clean shutdown (`close()`) with zero orphan processes.

### Task 4: Rewire `QnAOrchestrator` to Pi Agent Runtime
- Update `backend/app/agent/orchestrator.py` to delegate turn execution to `PiBridgeClient` instead of `provider.generate()`.
- Pass bounded conversation history and rewritten query to Pi.
- Capture tool execution results from Pi, validate citations via `CitationValidator`, and persist to PostgreSQL via `SessionStore`.
- Update SSE streaming to yield Pi's real-time token deltas and tool events.

### Task 5: Testing & Verification
- Unit and integration tests for `PiBridgeClient` and `QnAOrchestrator` confirming Pi is genuinely executed.
- Live E2E tests for:
  - Scenario A: Supported query (Ada Chen Rekhi) $\to$ Pi invokes tool $\to$ generates grounded answer.
  - Scenario B: Follow-up query $\to$ Pi resolves context $\to$ generates grounded answer.
  - Scenario C: Unsupported query $\to$ Pi receives `NO_GROUNDED_EVIDENCE` $\to$ outputs honest refusal without general knowledge hallucination.
  - Scenario D: Provider switching and Anthropic missing key error handling.
- Verify zero orphan processes after execution.
- Ensure full backend test suite passes.

---

## 3. Atomic Commit Plan
1. `feat(phase-P0.5A): add container node22 runtime and production pi bridge daemon`
2. `feat(phase-P0.5A): route qna orchestration through pi agent runtime`
3. `test(phase-P0.5A): verify production pi execution and lifecycle`
4. `docs(phase-P0.5A): document production pi architecture and update gsd state`
