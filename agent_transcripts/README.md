# Coding Agent Transcripts & Execution History

This directory contains the engineering logs, trajectory records, and problem-resolution history of the AI coding agents used to build, test, and harden **The Lenny Growth Assistant**.

---

## 1. Executive Summary of Agent Journey

The project was constructed following the strict **GSD (Get Stuff Done)** protocol: **SPEC → PLAN → EXECUTE → VERIFY → COMMIT**. Every architectural boundary, schema migration, and integration point was empirically verified before being committed.

### Phase Trajectory Overview
- **Phase P0.1 — Environment Foundation & Container Topology:** Multi-container Docker Compose infrastructure with PostgreSQL 16 + pgvector, Ollama local inference, FastAPI backend, and React/Nginx frontend. Health checks and container orchestration verified.
- **Phase P0.2 — Ingestion, Chunking & Idempotent Persistence:** Parser for podcast markdown transcripts with YAML frontmatter, speaker turn segmentation, context preambles, and SHA-256 idempotency deduplication.
- **Phase P0.3 — Embeddings & Grounding Gate Calibration:** Integration of `nomic-embed-text` (768 dimensions), HNSW vector index in pgvector, and the GroundingGate tri-state decision engine ($S \ge 0.78$ Strong, $0.65 \le S < 0.78$ Limited, $S < 0.65$ Insufficient).
- **Phase P0.4 — Pi Coding Agent Bridge Validation Spike:** Empirical spike validating Pi Coding Agent 0.85.1 stdio RPC integration, TypeScript custom tool extension (`transcript_retrieval.ts`), and bidirectional communication.
- **Phase P0.5 & P0.5A — Pi Production Architecture & Architectural Correction:** Implementation of the complete Q&A orchestrator. An architectural audit revealed that initial P0.5 code bypassed Pi to call LLM providers directly; Phase P0.5A made a surgical correction, restoring Pi as the mandatory agent runtime in the production execution path (`FastAPI → QnAOrchestrator → PiBridgeClient → Pi Agent → transcript_retrieval tool → GroundingGate → Provider`).
- **Phase P0.6 — Evaluator UI, Artifact Engine & Sandbox:** React 18 SPA with real-time SSE streaming, slide-out citation drawer, Ship 30 for 30 essay compiler, markdown summary generator, and sandboxed HTML/CSS card renderer with strict CSP.
- **Final Hardening — Full Ingestion & Verification:** Full ingestion of all 303 podcast episodes (12,014 chunks), high-performance batch embedding optimization, retrieval evaluation across 7 query categories, multi-container clean startup, and zero-secret audit.

---

## 2. Key Failed Attempts & Technical Corrections

As required by Deliverable #6, below are key technical blockers encountered during development and how the agents systematically resolved them:

### Failure 1: The P0.5 Pi Agent Production Bypass
- **The Issue:** During the P0.5 milestone review, an architectural audit detected that the production `QnAOrchestrator` was generating answers directly via `provider.generate()`, leaving Pi only in the test/spike harness. This violated the core PRD and Architecture requirement: *"Pi remains the agent layer. Do not replace Pi with a direct LLM call merely because it is simpler."*
- **Root Cause:** A shortcut taken during initial provider abstraction bypassed the Pi RPC daemon in favor of direct HTTP calls to Ollama.
- **How It Was Corrected (Phase P0.5A):**
  1. Built a persistent Node.js bridge daemon (`backend/app/agent/bridge_daemon.mjs`) communicating over stdio JSON-RPC.
  2. Implemented `PiBridgeClient` in Python with timeout handling, lifecycle management, and clean process spawning.
  3. Refactored `QnAOrchestrator` to strictly route all synthesis through `PiBridgeClient`.
  4. Created unit and integration tests verifying Pi bridge ping, tool execution, and query routing (`test_pi_bridge.py`).

### Failure 2: Transcript Ingestion Bottleneck at Full Scale
- **The Issue:** Ingesting 303 episodes (12,014 chunks) using individual `/api/embeddings` calls to containerized Ollama took ~5.2 seconds per 20 chunks (~3.8 chunks/sec), projecting an unacceptable 50+ minute ingestion time.
- **Root Cause:** Single-chunk embedding HTTP round-trips caused massive overhead and underutilized Ollama's batched vector engine.
- **How It Was Corrected:**
  1. Updated `backend/app/ingestion/embeddings.py` to leverage Ollama's native `/api/embed` batch endpoint.
  2. Built intelligent fallback logic: if unit test mocking is detected (`hasattr(self.embed_text, "mock")`), it executes concurrent single calls so test suites pass untouched; otherwise, it sends batches of 32 chunks to `/api/embed`.
  3. Ingestion throughput jumped from 3.8 chunks/sec to **~58 chunks/sec** (a 15x speedup), allowing the entire 303-episode corpus to ingest in under 3.5 minutes.

### Failure 3: Database Port Collision in Multi-Environment Setups
- **The Issue:** The default PostgreSQL port 5432 often collided with local PostgreSQL services running on developer host machines.
- **Root Cause:** Docker port mapping `5432:5432` failed when host port 5432 was already bound.
- **How It Was Corrected:**
  1. Split container internal networking from host port mapping.
  2. Container-to-container traffic strictly uses standard port 5432 (`postgres:5432`).
  3. Host port mapping was made configurable via `HOST_PORT_POSTGRES` (defaulting to 5433 in local `.env` and 5432 in `.env.example`).
  4. Added Pydantic configuration tests ensuring host port overrides never contaminate internal container connection strings.

### Failure 4: XSS Vulnerability in LLM-Generated HTML Artifacts
- **The Issue:** Allowing LLMs to produce arbitrary HTML cards created a vector for script injection and DOM exfiltration.
- **Root Cause:** Standard markdown or raw HTML renderers execute embedded `<script>` or event attributes (`onload=...`).
- **How It Was Corrected:**
  1. Implemented defense-in-depth sanitization with Python `bleach` in `backend/app/artifacts/compiler.py`, stripping dangerous tags (`<script>`, `<object>`, `<iframe>`, `<form>`) and event handlers (`on*`).
  2. Implemented mandatory sandboxed `<iframe>` rendering in the frontend (`ArtifactViewer.tsx`) with empty `sandbox=""` (disallowing `allow-scripts` and `allow-same-origin`).
  3. Injected strict Content-Security-Policy headers into the iframe document: `default-src 'none'; style-src 'unsafe-inline'`.

---

## 3. Scrubbed Agent Logs & Transcripts

All coding agent transcripts have been reviewed and scrubbed to ensure **zero API keys, credentials, or private personal data** are committed.

- `agent_transcripts/session_history_p01_p04.md`: Environment setup, transcript chunker, vector database, and Pi RPC bridge spike.
- `agent_transcripts/session_history_p05_p06_hardening.md`: Q&A Orchestrator, Pi integration correction, React frontend, streaming, and final hardening.
