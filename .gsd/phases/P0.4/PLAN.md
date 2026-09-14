# Phase P0.4 Plan: Pi Coding Agent Bridge Validation Spike

> **Phase**: P0.4 — Pi Coding Agent Bridge Validation Spike  
> **Status**: Ready to Execute  
> **Target**: Validate Pi 0.85.1 integration boundary with Ollama `llama3.1:8b`, project-local custom retrieval tool, real P0.3 retrieval layer, PostgreSQL + pgvector, real transcript evidence, Grounding Gate preservation, grounded answer synthesis, and clean process lifecycle.  

---

## 1. Context & Objective

The objective of Phase P0.4 is a **focused validation spike**, NOT the complete production FastAPI $\leftrightarrow$ Pi JSON-RPC bridge or session management subsystem. We must validate the highest-risk integration boundary before building full Q&A and session persistence:

```
User Query
    ↓
Pi Coding Agent 0.85.1
    ↓
Project-Local Custom Retrieval Tool (transcript_retrieval)
    ↓
Existing P0.3 Vector Retrieval Engine & Grounding Gate
    ↓
Retrieved Evidence Package (GroundingDecision + EvidenceItem[])
    ↓
Pi Cognitive Synthesis (Ollama / llama3.1:8b)
    ↓
One Source-Grounded Model Response
    ↓
Clean Session & Process Lifecycle (no hangs, no zombie processes)
```

### Critical Boundaries
- **In Scope:**
  - Validating Pi Coding Agent 0.85.1 runtime with Ollama `llama3.1:8b`.
  - Creating a project-local custom retrieval tool extension (`transcript_retrieval`) calling the existing P0.3 retrieval layer.
  - Ensuring the tool returns typed evidence preserving the GroundingGate decision (Strong, Limited, Conflicting, Insufficient).
  - Executing a real end-to-end turn against real ingested transcripts (`Ada Chen Rekhi` episode).
  - Verifying grounded response synthesis and source attribution.
  - Verifying insufficient evidence refusal behavior.
  - Verifying clean lifecycle and process termination.
  - Adding automated tests for the tool adapter and integration boundary.
- **Strictly Out of Scope:**
  - Full production FastAPI $\leftrightarrow$ Pi JSON-RPC subprocess daemon bridge.
  - Session manager, conversation history persistence in PostgreSQL.
  - SSE streaming endpoint.
  - Frontend integration.
  - Cloud model providers (Anthropic / OpenAI).
  - Artifact compiler or Ship30 tools.
  - Full 303-episode corpus ingestion.

---

## 2. Execution Tasks

### Task 1: Custom Retrieval Tool & Bridge Contracts
- Define the project-local tool interface for Pi Coding Agent (`transcript_retrieval`).
- Ensure the tool invokes the existing P0.3 retrieval engine (`POST /api/v1/retrieval/search` or direct python `VectorRetrievalEngine` / `GroundingGate`) rather than duplicating retrieval logic.
- Return structured XML/JSON evidence containing `tier`, `can_synthesize`, `top_score`, `reason`, `selected_evidence`, and source identifiers.
- Make refusal explicit when `can_synthesize is False`.
- Commit: `feat(phase-P0.4): custom retrieval tool for pi coding agent`

### Task 2: Project-Local Pi Tool Extension & Spike Runner
- Create `.pi/extensions/transcript_retrieval.ts` exporting a Pi extension with `defineTool` / `pi.registerTool`.
- Create a standalone spike execution script (`spikes/pi_retrieval_spike.mjs` or `.ts`) initializing Pi via `@earendil-works/pi-coding-agent`, configuring the Ollama `llama3.1:8b` model, attaching the custom retrieval tool, and executing one user turn.
- Commit: `feat(phase-P0.4): project-local pi extension and spike runner`

### Task 3: Focused Automated Tests
- Create `backend/tests/test_pi_bridge.py` or unit test suite validating:
  - Tool input validation (rejecting empty queries).
  - Proper invocation and reuse of existing P0.3 retrieval engine.
  - Structured evidence formatting and serialization.
  - Grounding decision preservation (Strong, Limited, Conflicting, Insufficient).
  - Insufficient evidence refusal behavior.
- Run test suite in Docker backend and verify all tests pass.
- Commit: `feat(phase-P0.4): automated test suite for pi retrieval tool`

### Task 4: Real End-to-End Live Validation Spike & Lifecycle Verification
- Execute live spike with query: *"According to the Lenny Podcast transcripts, what does Ada Chen Rekhi say about knowing when it is time to leave your job?"*
- Verify the exact execution chain:
  1. Pi launches.
  2. Pi invokes `transcript_retrieval`.
  3. Tool queries PostgreSQL pgvector and passes results through GroundingGate.
  4. Tool returns high-similarity evidence (Ada Chen Rekhi transcript on boiling frog / explore vs exploit).
  5. Pi generates grounded answer strictly referencing the evidence and attributing to Ada Chen Rekhi.
  6. Pi session terminates cleanly with zero hanging processes and exit code 0.
- Execute out-of-domain query (e.g. quantum chromodynamics) verifying refusal.
- Verify clean lifecycle: no hanging node processes, no broken stdio pipes.
- Commit: `feat(phase-P0.4): end-to-end pi retrieval validation spike`

### Task 5: Phase P0.4 Documentation & State Updates
- Create `.gsd/phases/P0.4/SUMMARY.md`.
- Update `.gsd/STATE.md`, `.gsd/ROADMAP.md`, `.gsd/JOURNAL.md`, `.gsd/TODO.md`, `.gsd/REQUIREMENTS.md`.
- Commit: `docs(phase-P0.4): complete pi coding agent bridge validation spike`
- Verify clean git working tree.

---

## 3. Verification Criteria

1. Pi Coding Agent 0.85.1 runs against local Ollama `llama3.1:8b`.
2. Custom tool `transcript_retrieval` is discovered and loaded by Pi.
3. Pi autonomously invokes `transcript_retrieval` for the podcast question.
4. Tool reuses the existing P0.3 retrieval engine and GroundingGate.
5. Real transcript evidence from PostgreSQL pgvector is returned to Pi.
6. Grounding decision is preserved (`Strong` or `Limited`).
7. Pi synthesizes one grounded response attributing to Ada Chen Rekhi without hallucinations.
8. Unanswerable query produces `Insufficient` tier and refusal.
9. Process exits cleanly with exit code 0 and zero zombie processes.
10. All existing backend tests (39 tests) remain green.
11. Working tree is clean and zero P0.5 code is introduced.
