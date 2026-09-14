# SPEC.md — Project Specification

> **Status**: `FINALIZED`
>
> ⚠️ **Planning Lock**: Specification is frozen. No implementation code may deviate from this specification without an explicit documentation amendment.

---

## Vision

The Lenny Growth Assistant is an internal product and growth research assistant built over Lenny's Podcast transcripts. It empowers product managers, growth leads, founders, and engineers to query accumulated practitioner knowledge, receive strictly source-grounded answers with verifiable citations, conduct conversational follow-up research, and generate reusable content artifacts (Ship 30 for 30 essays, Markdown notes, HTML/CSS cards) without requiring users to understand retrieval pipelines, prompting strategies, or model infrastructure.

---

## Goals

1. **Strictly Source-Grounded Q&A** — Deliver accurate, high-fidelity answers to product and growth questions anchored exclusively in transcript evidence with episode number, guest name, title, and verbatim excerpt citations.
2. **Conversational Multi-Turn Research** — Preserve session context across multi-turn interactions, resolving follow-up references and pronouns seamlessly while isolating distinct sessions.
3. **Honest Failure & Refusal Behavior** — Enforce a deterministic 4-tier grounding gate (Strong, Limited, Conflicting, Insufficient) that triggers qualified responses for limited evidence and immediate deterministic refusal without calling the LLM when evidence is insufficient ($S < 0.65$).
4. **Flexible & Decoupled Model Configuration** — Decouple generation from embedding: default to containerized Ollama (`llama3.1:8b`) for a zero-key local evaluation demo, support Anthropic Claude as the selected P0 cloud provider via `.env`, and keep embeddings strictly fixed on Ollama `nomic-embed-text` (768-dim) across all providers.
5. **Ship 30 for 30 Content Writing Skill [P1]** — Transform grounded answers into ~1,250-word essays that rigorously encode the 7 Ship 30 for 30 writing principles with strong hooks, clear progression, skimmable formatting, and actionable takeaways.
6. **In-App Sandboxed Artifact Viewer [P1]** — Generate clean Markdown and HTML/CSS artifacts, rendered in an isolated dual-origin sandboxed `<iframe>` (`null` origin, strict CSP, Bleach sanitization) that completely blocks script execution.
7. **Evaluator-Ready Reproducibility** — Provide one-command local startup via Docker Compose (`docker compose up -d`) with containerized PostgreSQL 16 + pgvector, Ollama, and FastAPI, supported by comprehensive structured logs, health endpoints, and automated tests.

---

## Non-Goals (Out of Scope)

- **Arbitrary Web Search / Open Internet Fallback** — Dilutes the product promise. When the transcript corpus lacks evidence, the system refuses cleanly rather than hallucinating or querying the open web.
- **General AI Advice Outside the Corpus** — The LLM is an untrusted reasoning engine, not a knowledge base. Unanchored general product advice is strictly prohibited.
- **OpenAI Provider Implementation in P0** — OpenAI remains a conceptual P2 second-cloud-provider extension. Anthropic is the sole P0 cloud provider. Zero OpenAI code or stubs in P0.
- **Multi-Tenant Administration & RBAC** — Enterprise access control is unnecessary for the internal evaluator scope; sessions are isolated by UUID.
- **Autonomous Background Agents or Multi-Agent Committees** — Unbounded multi-agent loops introduce latency and nondeterminism. The architecture is a single agent with bounded deterministic tools.
- **Real-Time Podcast Audio Ingestion / Transcription** — The corpus is derived from the static transcript repository; audio processing is out of scope.
- **Fine-Tuning Pipelines** — Model weights are not updated; RAG preserves verifiable source citations down to exact chunk boundaries.
- **External SaaS Integrations (Slack, Notion, Discord)** — Increases attack surface and dependency sprawl without evaluator value.
- **Kubernetes / Distributed Microservices** — Docker Compose provides complete reproducibility for local deployment without microservice network overhead.
- **Mobile-Native Applications** — Responsive web application covers all evaluation requirements.

---

## Users & Primary Personas

1. **Product Managers & Growth Leads** — Need quick, authoritative answers to tactical and strategic questions (e.g., PLG vs. sales-led, first growth hire, retention metrics) backed by practitioner testimony from top tech leaders.
2. **Founders & Operators** — Seeking battle-tested frameworks from guests like Brian Chesky, Elena Verna, and Shreyas Doshi for pricing, positioning, and hiring.
3. **Technical Evaluator / Client Engineer** — Testing the system's architecture, reproducibility, code quality, agent integration, grounding discipline, security posture, and operability under both local and cloud LLMs.

---

## Constraints

- **Persistence & Vector Search:** Single PostgreSQL 16 instance with `pgvector` (`pgvector/pgvector:pg16`). `VECTOR(768)` is fixed for all corpus chunks. No external vector databases (Pinecone, Qdrant, Chroma).
- **Decoupled Providers:** `EmbeddingProvider` is fixed to Ollama `nomic-embed-text` (768-dim) running in Docker Compose. Changing `LLM_PROVIDER` only switches generation, never embeddings.
- **Local Demo Invariant:** Default configuration must start and run via `docker compose up -d` without requiring any cloud API keys.
- **Deterministic Grounding Gate:** Evaluates evidence outside the LLM prior to generation:
  - Strong: $\max(\text{score}) \ge 0.78$
  - Limited: $0.65 \le \max(\text{score}) < 0.78$ (`GROUNDING_LIMITED_THRESHOLD = 0.65`)
  - Conflicting: Opposing perspectives across retrieved chunks
  - Insufficient: $\max(\text{score}) < 0.65$ or empty $\implies$ deterministic refusal before LLM call
- **Canonical Terminology:** Strictly **Strong, Limited, Conflicting, Insufficient**. The threshold parameter is strictly `GROUNDING_LIMITED_THRESHOLD` (no `weak` references or compatibility aliases).
- **Conversational Flow Order:** User question → session context → query rewriting / reference resolution → retrieval → deterministic grounding gate → model synthesis → citation validation → response.
- **Host Port Mapping:** PostgreSQL container-to-container communication remains on the standard internal port (`postgres:5432`). Host port configuration (`HOST_PORT_POSTGRES=5432`) is an optional host-side mapping and must not alter `DATABASE_URL`.
- **Pi Integration & Validation Boundary:**
  - *Validated by Spike:* Pi 0.85.1 + Ollama + llama3.1:8b + project-local custom retrieval tool + tool invocation + evidence returned + grounded answer + follow-up + clean interactive lifecycle.
  - *Unvalidated Implementation Risk:* The production FastAPI-to-Pi stdio JSON-RPC subprocess bridge (`bridge.ts` / `bridge_client.py`). Must be validated via a minimal standalone bridge spike in Phase P0.4 before relying on it for the full agent subsystem. (Documented fallback: lightweight HTTP sidecar).
- **Artifact Security Boundary [P1]:** Rendered HTML must be isolated in an `<iframe>` with `sandbox=""` (`null` origin, no scripts, no same-origin) plus server-side Bleach sanitization.
- **Secret Management:** `.env` excluded by `.gitignore`; `.env.example` provides safe defaults; zero committed secrets.

---

## Success Criteria

- [ ] **One-Command Startup:** `docker compose up -d` from a clean clone brings up PostgreSQL, Ollama, backend, and frontend without errors.
- [ ] **Zero-Key Local Demo:** Default system answers queries and conducts follow-ups using local Ollama without any cloud API keys.
- [ ] **Cloud Provider Switch:** Switching `LLM_PROVIDER=anthropic` routes generation to Claude without code changes or vector re-indexing.
- [ ] **Deterministic Refusal:** Unsupported/out-of-domain questions are refused deterministically with zero hallucinated claims.
- [ ] **Source Provenance:** Every factual answer includes verified citations (episode number, guest name, title, verbatim quote).
- [ ] **Session Context & Isolation:** Follow-up questions resolve prior context (e.g., "What else did she say?"); distinct sessions remain strictly isolated in PostgreSQL.
- [ ] **Pi Bridge Validation:** FastAPI spawns Pi 0.85.1, executes a turn over the subprocess bridge, invokes a retrieval tool, receives evidence, streams the response, and exits/reuses cleanly.
- [ ] **Automated Test Suite:** `pytest` suite passes, verifying health endpoints, ingestion, retrieval, grounding gate, provider toggle, and session persistence.
- [ ] **Ship 30 for 30 Skill [P1]:** Generates ~1,250-word structured essays adhering to the 7 core principles.
- [ ] **Sandboxed Artifact Viewer [P1]:** Safely renders Markdown and HTML/CSS artifacts; XSS payloads are neutralized.

---

## User Stories

### Story 1: Tactical Product Research
- **As a** Product Manager
- **I want to** ask questions like "How should I structure my first growth team according to Elena Verna?"
- **So that** I receive actionable insights backed directly by what practitioners stated on the podcast, complete with source citations.

### Story 2: Multi-Turn Deep Dive
- **As a** Founder
- **I want to** ask follow-up questions like "What metrics did she recommend tracking for that?"
- **So that** I can explore a topic iteratively without retyping full context.

### Story 3: Honest Refusal
- **As an** Evaluator
- **I want to** ask out-of-domain questions like "What is the best recipe for chocolate cake?" or "How does quantum computing work?"
- **So that** the assistant immediately and honestly acknowledges that the transcript corpus does not contain this information.

### Story 4: Content Transformation [P1]
- **As a** Growth Marketer
- **I want to** command "Turn this into a Ship 30 for 30 essay"
- **So that** the grounded discussion is structured into a publishable ~1,250-word essay with a strong hook, actionable takeaways, and cited sources.

### Story 5: Visual Artifact Generation [P1]
- **As an** Operator
- **I want to** request an HTML/CSS comparison table or KPI card
- **So that** I can preview the rendered component safely beside my chat and export the code.

---

## Technical Requirements Summary

| Requirement | Priority | Architectural Mechanism | Traceability |
| :--- | :--- | :--- | :--- |
| Single PostgreSQL + pgvector persistence | P0 | PostgreSQL 16 `VECTOR(768)` | FR-12, FR-13 |
| Ingestion of Lenny transcripts | P0 | Frontmatter parser + semantic chunker | FR-7, FR-8, FR-9 |
| Fixed 768-dim embedding provider | P0 | Ollama `nomic-embed-text` | Architecture §3.2 |
| Vector retrieval engine | P0 | pgvector cosine similarity `<=>` | FR-10 |
| Query rewriting / reference resolution | P0 | Upstream of retrieval using session history | FR-3, Architecture §6.2 |
| Deterministic 4-tier Grounding Gate | P0 | Strong, Limited, Conflicting, Insufficient | FR-5, PRD §9 |
| Pi subprocess bridge validation spike | P0 | FastAPI ↔ Pi stdio JSON-RPC proof | FR-16, Architecture §25.4 |
| Decoupled model providers | P0 | Ollama default + Anthropic Claude P0 cloud | FR-17, FR-18 |
| Multi-turn session persistence | P0 | PostgreSQL `sessions` + `messages` | FR-1, FR-2, FR-14 |
| SSE streaming Q&A with citations | P0 | FastAPI SSE + citation validation | FR-4, Architecture §10 |
| Minimal evaluator UI & test suite | P0 | React 18 + Vite chat UI + pytest | FR-19, Assignment §6 |
| Ship 30 for 30 writing skill | P1 | Pi Extension encoding 7 principles | FR-21, FR-22, FR-23 |
| Artifact generation & sandboxed viewer | P1 | Compiler + sandboxed `<iframe>` | FR-24 - FR-30, FR-36 |
| OpenAI second cloud provider | P2 | `OpenAIProvider` extension | PRD §7, Architecture §9.3 |
| Resilience & UX polish | P2 | Full failure mode coverage, mobile polish | PRD §7, Architecture §27 |

---

*Last updated: 2026-09-14 — Status: FINALIZED*
