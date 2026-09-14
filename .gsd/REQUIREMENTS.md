---
milestone: v0.1
updated: 2026-09-14T14:00:00Z
---

# Requirements

## Overview

Formal requirements derived from `SPEC.md`, `PRD.md`, `architecture.md`, `design.md`, and the `Forward-Deployed Engineer Take-Home Assignment` for traceability and verification coverage.

---

## Functional Requirements

| ID | Requirement | Priority | Source | Phase | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | **Session Creation & Persistence:** Create distinct conversational sessions with unique UUIDs, storing metadata and timestamps in PostgreSQL `sessions` table. | P0 | PRD FR-1, FR-12 | P0.1 | Pending |
| **REQ-02** | **Session Isolation:** Ensure conversations and messages are strictly isolated (`WHERE session_id = :id`) across server restarts and concurrent requests. | P0 | PRD FR-13, FR-14 | P0.1 | Pending |
| **REQ-03** | **Transcript Ingestion:** Load transcript markdown files from `data/transcripts/`, extract YAML frontmatter (episode, guest, title, URL), and extract text. | P0 | PRD FR-7, FR-8 | P0.2 | Pending |
| **REQ-04** | **Speaker-Aware Semantic Chunking:** Partition transcripts into ~600-token chunks with 100-token overlap, preserving speaker boundaries, episode metadata, and SHA-256 hash. | P0 | PRD FR-9, Arch §7 | P0.2 | Pending |
| **REQ-05** | **Fixed Vector Embeddings:** Generate 768-dimensional embeddings using Ollama `nomic-embed-text` and store in PostgreSQL `transcript_chunks` with HNSW index. | P0 | Arch §3.2, PRD Q2 | P0.2 | Pending |
| **REQ-06** | **Query Rewriting & Reference Resolution:** Prior to retrieval, rewrite the user query using the session's last $N=6$ message turns to resolve pronouns and implicit references. | P0 | PRD FR-3, Arch §6.2 | P0.3 | Pending |
| **REQ-07** | **Vector Retrieval Engine:** Perform semantic cosine similarity search (`<=>`) over indexed chunks with configurable `RETRIEVAL_TOP_K` (default 15) and metadata preservation. | P0 | PRD FR-10, Arch §8 | P0.3 | Pending |
| **REQ-08** | **Deterministic Grounding Gate:** Triage retrieved evidence into 4 canonical tiers: Strong ($\ge 0.78$), Limited ($0.65 \le S < 0.78$), Conflicting (opposing perspectives), Insufficient ($< 0.65$). | P0 | PRD FR-5, PRD §9 | P0.3 | Pending |
| **REQ-09** | **Deterministic Refusal:** When evidence is Insufficient, refuse immediately with an honest acknowledgment without invoking the LLM. | P0 | PRD FR-5, AC-5 | P0.3 | Pending |
| **REQ-10** | **Pi Subprocess Bridge Validation Spike:** Execute a minimal standalone validation spike (FastAPI spawns Pi 0.85.1, sends 1 turn, invokes retrieval tool, receives evidence, gets response, clean termination/reuse). | P0 | Arch §25.4 | P0.4 | Pending |
| **REQ-11** | **Decoupled Model Providers:** Abstract generation from embeddings: Ollama (`llama3.1:8b`) as default local provider; Anthropic Claude as selected P0 cloud provider via `.env`. | P0 | PRD FR-17, FR-18 | P0.5 | Pending |
| **REQ-12** | **SSE Streaming Grounded Q&A:** Stream synthesized answers via Server-Sent Events (`POST /api/v1/sessions/{id}/messages`), strictly constrained to retrieved evidence. | P0 | PRD FR-2, FR-4 | P0.5 | Pending |
| **REQ-13** | **Citation Verification:** Validate that every factual claim in the synthesized response maps to a retrieved chunk; attach structured citation metadata. | P0 | PRD FR-4, Arch §10 | P0.5 | Pending |
| **REQ-14** | **Evaluator UI & Status:** Provide a React 18 + Vite chat interface displaying active provider badge, session switcher, streaming responses, evidence tier badges, and citation cards. | P0 | PRD FR-19, Design §3 | P0.6 | Pending |
| **REQ-15** | **Automated Test Suite:** Comprehensive `pytest` test suite validating health endpoints, ingestion, retrieval, grounding gate, provider switching, and session isolation. | P0 | PRD AC-25, Assign §6 | P0.6 | Pending |
| **REQ-16** | **Ship 30 for 30 Content Writing Skill:** Generate ~1,250-word structured essays encoding 7 core principles (hook, narrative progression, skimmable formatting, takeaway, grounded claims). | P1 | PRD FR-21, FR-22 | P1.1 | Deferred |
| **REQ-17** | **Artifact Generation & Sandboxed Viewer:** Multi-format compiler emitting Markdown and HTML/CSS artifacts, rendered in an isolated `<iframe>` (`null` origin, strict CSP, Bleach sanitization). | P1 | PRD FR-24 - FR-38 | P1.2 | Deferred |
| **REQ-18** | **OpenAI Second Cloud Provider Integration:** Add OpenAI GPT-4o adapter to `GenerationProvider` layer. | P2 | PRD §7, Arch §9.3 | P2.1 | Deferred |
| **REQ-19** | **Resilience & Observability Hardening:** Full RFC 7807 error handling, correlation ID tracking, and corpus refresh automation. | P2 | PRD §7, Arch §27 | P2.2 | Deferred |

---

## Non-Functional Requirements

| ID | Requirement | Category | Target | Status |
| :--- | :--- | :--- | :--- | :--- |
| **NFR-01** | **One-Command Startup:** Entire system starts via `docker compose up -d` without manual configuration beyond copying `.env.example`. | Deployment | $\le 10$ minutes from clone | Pending |
| **NFR-02** | **Zero Cloud Dependencies (Demo):** Evaluator can execute full conversational demo using containerized Ollama without cloud API keys. | Operability | 100% functional locally | Pending |
| **NFR-03** | **Retrieval Latency:** Semantic vector search over full transcript corpus finishes under budget. | Performance | $\le 50$ ms | Pending |
| **NFR-04** | **Grounding Gate Latency:** Deterministic evidence scoring completes without LLM latency. | Performance | $\le 5$ ms | Pending |
| **NFR-05** | **HTML Security Isolation:** Rendered HTML cannot execute JavaScript, access parent window DOM, or exfiltrate cookies/localStorage. | Security | Complete script execution block | Pending |
| **NFR-06** | **Structured Observability:** All operations (API requests, retrieval, model inference, DB queries) logged as structured JSON with correlation IDs. | Observability | RFC 7807 compliant | Pending |
| **NFR-07** | **Resilience & No Silent Fallbacks:** Upstream failures (Ollama offline, DB down, Anthropic error) emit explicit error messages; no silent model fallbacks. | Reliability | Zero silent degradation | Pending |

---

## Architectural Constraints

| ID | Constraint | Description | Impact Area |
| :--- | :--- | :--- | :--- |
| **CON-01** | **Single Persistence Engine:** PostgreSQL 16 + `pgvector` (`VECTOR(768)`). No external vector DBs (Pinecone, Qdrant, Chroma). | Database, Retrieval |
| **CON-02** | **Fixed Embedding Model:** Ollama `nomic-embed-text` (768-dim) is immutable across all generation providers. | Embedding, Ingestion |
| **CON-03** | **Pi Integration Validation Gate:** The production stdio JSON-RPC bridge is an unvalidated implementation risk; Phase P0.4 minimal spike must succeed before building full agent subsystem. | Agent Subsystem |
| **CON-04** | **Canonical Evidence Terminology:** Strictly **Strong, Limited, Conflicting, Insufficient**. Threshold parameter is strictly `GROUNDING_LIMITED_THRESHOLD = 0.65`. | Grounding Gate, Config |
| **CON-05** | **Internal Database Networking:** Host port mapping (`HOST_PORT_POSTGRES=5432`) is host-side only; backend-to-postgres communication uses `postgres:5432` without modifying `DATABASE_URL`. | Networking, Docker |
| **CON-06** | **Conversational Flow Order:** User question → session context → query rewriting → retrieval → grounding gate → model synthesis → citation validation → response. | Orchestration |

---

## Traceability Matrix

| Requirement | SPEC Goal | Architecture Component | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| REQ-01 | Goal 2 | `SessionManager` + PostgreSQL | API test `POST /api/v1/sessions` | Pending |
| REQ-02 | Goal 2 | `SessionManager` (`WHERE session_id = :id`) | Concurrency / cross-session test | Pending |
| REQ-03 | Goal 1 | `scripts.ingest` (Frontmatter parser) | Corpus ingestion test | Pending |
| REQ-04 | Goal 1 | `SemanticChunker` | Chunk boundary & metadata test | Pending |
| REQ-05 | Goal 4 | `OllamaEmbeddingProvider` (768-dim) | Dimension & vector insert test | Pending |
| REQ-06 | Goal 2 | `QueryRewriter` | Pronoun resolution test | Pending |
| REQ-07 | Goal 1 | `RetrievalEngine` (`<=>` pgvector) | Golden query retrieval benchmark | Pending |
| REQ-08 | Goal 3 | `GroundingGate` (4 tiers) | Unit test against score thresholds | Pending |
| REQ-09 | Goal 3 | `GroundingGate` (Refusal logic) | Out-of-domain refusal test | Pending |
| REQ-10 | Goal 7 | `PiBridge` (subprocess JSON-RPC) | Standalone P0.4 bridge spike script | Pending |
| REQ-11 | Goal 4 | `GenerationProvider` (Ollama/Anthropic) | Provider toggle test via `.env` | Pending |
| REQ-12 | Goal 1 | FastAPI SSE streaming endpoint | SSE event stream capture | Pending |
| REQ-13 | Goal 1 | `CitationValidator` | Citation mapping audit | Pending |
| REQ-14 | Goal 7 | React 18 + Vite Frontend | Visual check & provider badge | Pending |
| REQ-15 | Goal 7 | Automated test suite | `pytest` test runner | Pending |
| REQ-16 | Goal 5 | `ship30_writer` Pi Extension [P1] | 1,250-word essay audit | Deferred |
| REQ-17 | Goal 6 | `ArtifactViewer` + Bleach [P1] | XSS injection verification | Deferred |
| REQ-18 | Goal 4 | `OpenAIProvider` [P2] | P2 toggle verification | Deferred |
| REQ-19 | Goal 7 | Observability & resilience [P2] | Chaos test / error logs | Deferred |

---

## Status Definitions

| Status | Meaning |
| :--- | :--- |
| **Pending** | Requirement defined and scheduled in active milestone |
| **In Progress** | Actively being implemented in the current phase |
| **Complete** | Implemented, empirically verified, and passed tests |
| **Blocked** | Impeded by unresolved technical risk or dependency |
| **Deferred** | Intentionally scheduled for subsequent milestone (P1 or P2) |
