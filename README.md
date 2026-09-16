# The Lenny Growth Assistant

An internal product and growth research assistant and structured artifact compiler built over the complete 303-episode transcript corpus of [Lenny's Podcast](https://www.lennyspodcast.com/).

The system provides source-grounded answers, conversational follow-up research, and structured deliverable generation (Ship 30 for 30 essays, Markdown executive briefs, and sandboxed HTML/CSS cards) — without requiring users to navigate transcript archives, prompt engineering, or model infrastructure.

This is not a generic chatbot. The transcript corpus is the sole source of truth. Every claim is validated against retrieved excerpts with guest and episode citations. A deterministic mathematical GroundingGate evaluates evidence before synthesis, refusing unsupported queries with zero citations rather than hallucinating.

---

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        Browser["Browser (React 18 + Vite SPA :3000)"]
    end

    subgraph Backend ["Application & Orchestration Layer"]
        FastAPI["FastAPI Orchestrator (:8000)"]
        Gate["GroundingGate (Cosine Similarity Tiers)"]
        Validator["CitationValidator (Proof Engine)"]
    end

    subgraph AgentRuntime ["Agent Runtime Layer"]
        Bridge["PiBridgeClient (Python)"]
        Daemon["bridge_daemon.mjs (stdio JSON-RPC)"]
        PiAgent["Pi Coding Agent (0.85.1)"]
        Tool["transcript_retrieval Tool"]
    end

    subgraph Storage ["Storage & Vector Layer"]
        Postgres[("PostgreSQL 16 + pgvector<br/>303 Episodes · 12,014 Chunks · HNSW Index")]
    end

    subgraph Models ["Inference Providers"]
        OllamaGen["Ollama: llama3.1:8b (Default Local Generation)"]
        AnthropicGen["Anthropic: claude-3-5-sonnet (Configured Cloud Provider)"]
        OllamaEmbed["Ollama: nomic-embed-text (Fixed 768-dim Embedding)"]
    end

    Browser -->|REST / Real-Time SSE Stream| FastAPI
    FastAPI -->|Semantic Vector Search| Postgres
    Postgres -.->|Generate Query Vector| OllamaEmbed
    FastAPI -->|Evaluate Similarity| Gate
    Gate -->|Strong / Limited Tier| Bridge
    Gate -->|Insufficient Tier| FastAPI
    Bridge <-->|stdio JSON-RPC| Daemon
    Daemon <--> PiAgent
    PiAgent --> Tool
    Tool -->|Bounded Chunk Fetch| Postgres
    PiAgent -->|Local Synthesis| OllamaGen
    PiAgent -.->|Cloud Synthesis| AnthropicGen
    FastAPI -->|Validate Grounding & Chunk IDs| Validator
    FastAPI -->|Persist Sessions & Messages| Postgres
```

---

## Why This Exists

Lenny's Podcast contains hundreds of hours of high-signal discussions with top practitioners from Airbnb, Stripe, Figma, Slack, and Uber. However, turning this archive into actionable strategy creates significant friction:

- **Discovery friction:** Locating specific tactics (e.g., pricing migrations, B2B onboarding loops, or founder-led sales) requires remembering titles, scrubbing audio, or relying on keyword search.
- **Synthesis friction:** Reconciling conversational dialogue across multiple episodes — or contrasting conflicting viewpoints across guests — requires hours of manual cross-referencing.
- **Reuse friction:** Converting podcast insights into team strategy memos or thought-leadership content usually strips attribution and risks accidental paraphrase errors.

The Lenny Growth Assistant eliminates these bottlenecks by grounding every answer in verbatim transcript chunks, maintaining multi-turn context, and compiling insights directly into presentation-ready deliverables.

---

## What It Does

- **Source-grounded Q&A:** Natural-language answers synthesized strictly from retrieved transcript evidence, complete with guest and episode attribution.
- **Context-aware follow-up:** Multi-turn conversational research with deterministic pronoun and entity resolution (e.g., resolving "Why did she recommend that?" to the guest discussed in the previous turn).
- **Deterministic refusal:** Mathematical gating that immediately refuses out-of-domain queries ($S < 0.65$) with zero citations, completely avoiding LLM hallucination.
- **Interactive citation drawer:** Slide-out evidence inspector displaying exact chunk text, guest name, episode title, chunk ID, and cosine similarity score.
- **Ship 30 for 30 essays:** Transforms grounded research into ~1,250-word structured essays following 7 core Ship 30 principles (hook, clear thesis, 1-3-1 cadence, single-sentence paragraphs, bullet transitions, and actionable takeaways).
- **Markdown & HTML/CSS artifacts:** Compiles executive summaries, decision matrices, and visual cards rendered alongside the chat.
- **Artifact workspace:** Live preview, raw source inspection, one-click clipboard copying, and file export (`.md` / `.html`).
- **Interactive Provider Selector & Cloud API Key Configuration:** Switch between `Ollama · Local` (`llama3.1:8b`), `Google Gemini · Cloud` (`gemini-2.5-flash`), and `Anthropic · Cloud` (`claude-3-5-sonnet`) directly in the UI Header. Evaluators can configure their cloud API keys via an in-app popover modal with live pre-flight validation against provider endpoints without modifying `.env` or restarting containers. Strictly enforces zero silent fallback if cloud credentials are missing.
- **Session Lifecycle & Cascade Deletion:** Create and switch between multiple research sessions, or delete individual sessions with a single click in the sidebar, with automated relational cascade across messages, sources, and artifacts in PostgreSQL.
- **Adaptive Light / Dark Mode:** Full UI theme switcher (Sun / Moon) in the header with high-contrast, polished styling across chat, sidebar, citation drawers, and artifact viewers, persisted in browser `localStorage`.
- **Local-first with cloud flexibility:** Runs 100% locally with Ollama (`llama3.1:8b`) with zero cloud dependencies or API keys required, while supporting clean configuration-driven switching to Google Gemini or Anthropic Claude.

---

## Trust Model & Grounding Gate

The fundamental architecture premise is that **the LLM is an untrusted reasoning engine, never a knowledge store**. The transcript corpus is the sole source of truth.

```
Transcript Corpus → pgvector Semantic Search → GroundingGate (Cosine Similarity)
    ├── Strong (S ≥ 0.78)        ──► Pi Agent Synthesis ──► CitationValidator ──► Grounded Answer + Citations
    ├── Limited (0.65 ≤ S < 0.78) ──► Pi Agent Synthesis ──► CitationValidator ──► Qualified Answer + Citations
    ├── Conflicting (S ≥ 0.78)    ──► Pi Agent Synthesis ──► CitationValidator ──► Balanced Multi-Guest Synthesis
    └── Insufficient (S < 0.65)   ──► Immediate Refusal ──► Zero Citations Returned (LLM Never Called)
```

### Evidence Tiers

| Evidence Tier | Similarity Condition ($S$) | System Behavior | Citation Output |
|:---|:---|:---|:---|
| **Strong** | Top similarity $S \ge 0.78$ | Full synthesis anchored strictly in transcript excerpts | Full guest & episode citations |
| **Limited** | $0.65 \le S < 0.78$ | Qualified synthesis explicitly noting partial evidence | Verified matching citations |
| **Conflicting** | $S \ge 0.78$ across opposing perspectives | Balanced synthesis contrasting both viewpoints | Citations for each perspective |
| **Insufficient** | $S < 0.65$ or zero matching chunks | Immediate deterministic refusal; LLM is never invoked | Exactly zero citations (no leaks) |

### Non-Negotiable Grounding Invariants

1. **No generic-knowledge fallback:** If Lenny's guests did not discuss a topic, the assistant does not draw upon general LLM pretraining.
2. **Zero citations on refusal:** When evidence is Insufficient, the system returns a clean refusal message with zero citations in both the API response and the database, preventing low-similarity chunks from masquerading as evidence.
3. **Automated citation validation:** The `CitationValidator` cross-checks every cited claim against the retrieved transcript chunk IDs and timestamps before returning the final response.

---

## Architecture

The system operates across three isolated tiers: the **React 18 SPA**, the **FastAPI Orchestrator**, and the **Pi Coding Agent Runtime**.

```
Browser (React 18 + Vite)
    ↓  (HTTP POST / Server-Sent Events)
FastAPI Backend (:8000)
    ↓  (Deterministic Query Rewriting + pgvector Search)
PostgreSQL 16 + pgvector (:5432)
    ↓  (HNSW Similarity Evaluation)
GroundingGate (Evidence Check)
    ↓  (stdio JSON-RPC IPC Bridge)
Pi Coding Agent Runtime (Node.js daemon · Pi 0.85.1)
    ↓  (transcript_retrieval Tool + Constrained Prompting)
Model Inference (Ollama llama3.1:8b or Anthropic Claude 3.5 Sonnet)
    ↓  (Streamed Text Generation)
CitationValidator (Provenance & Quote Verification)
    ↓  (SSE Tokens + Relational DB Commit)
React UI (Live Stream + Citation Drawer + Artifact Viewer)
```

### The Pi Agent Boundary

FastAPI does not call LLMs directly to generate answers. All synthesis is mediated by the **Pi Coding Agent** (`@earendil-works/pi-coding-agent` v0.85.1).

A persistent Python bridge client (`PiBridgeClient`) spawns and manages a long-lived Node.js daemon (`bridge_daemon.mjs`) communicating over bidirectional stdio JSON-RPC. The Pi agent is equipped with a custom tool extension (`transcript_retrieval`), enforcing bounded tool execution over validated transcript chunks.

### Provider Separation & Strict Decoupling

Generation is strictly decoupled from vector indexing:

- **Generation Provider** (controlled by `LLM_PROVIDER`):
  - `ollama` *(default)*: Local inference (`llama3.1:8b`), zero cloud credentials required.
  - `anthropic` *(cloud)*: Anthropic Claude (`claude-3-5-sonnet-20241022`), enabled via `ANTHROPIC_API_KEY`.
- **Corpus Embedding** *(fixed)*:
  - Fixed to `nomic-embed-text` (768 dimensions) running via Ollama.
  - Switching generation providers (e.g. from Ollama to Anthropic) **never** invalidates vector embeddings and **never** requires re-ingesting the corpus.
- **No silent fallback:** If the configured cloud provider fails (e.g., missing API key, rate limit, or timeout), the system fails loudly with an explicit error. It never silently degrades to a fallback model.

---

## Key Engineering Decisions

| Decision | Rationale |
|:---|:---|
| **Pi Coding Agent as Runtime** | Provides a bounded, auditable tool-use execution loop with clean process isolation, rather than unstructured prompt-chaining in application code. |
| **Deterministic Grounding Outside LLM** | Math-based cosine similarity gates evaluation before model invocation. Eliminates hallucinated confidence and guarantees refusal on out-of-domain queries. |
| **Fixed Embedding Model (`nomic-embed-text`)** | Vector search indexing is decoupled from generation models. Switching from local Ollama to Anthropic Claude incurs zero re-indexing or database downtime. |
| **Strict Provider Separation (No Silent Fallback)** | Ensures transparent failure over unpredictable degradation. Evaluators know exactly which model served an answer without hidden fallbacks or unexpected cloud bills. |
| **Single Unified Storage (PostgreSQL 16 + pgvector)** | Co-locates relational session state, message history, generated artifacts, and vector embeddings in one ACID-compliant engine, avoiding dual-database sync drift. |
| **Bounded Session Context & Query Rewriting** | Resolves conversational references (e.g., "she", "that framework") deterministically using bounded recent history, avoiding token waste and context dilution. |
| **Sandboxed Artifact Iframe (`sandbox=""`)** | LLM-generated HTML/CSS is treated as untrusted input. Stripped of scripts by Bleach, rendered in an iframe with null origin and strict CSP (`default-src 'none'; style-src 'unsafe-inline'`). |
| **Transcript Evidence as Untrusted Data** | Retrieved text is injected inside bounded `<evidence>` XML tags rather than raw system instructions, mitigating prompt injection risks from podcast content. |

---

## Product Experience

The user workflow transitions smoothly from natural-language inquiry to structured deliverable:

1. **Inquire:** Enter a product or growth question in the conversational workspace.
2. **Retrieve & Gate:** The backend searches pgvector chunks, calculates cosine similarity, and assigns an evidence tier (`Strong`, `Limited`, `Conflicting`, or `Insufficient`).
3. **Stream & Synthesize:** For grounded tiers, Pi streams tokens in real time via Server-Sent Events (SSE). Out-of-domain queries refuse immediately.
4. **Inspect Evidence:** Click any citation badge to slide out the evidence drawer, revealing guest details, episode titles, chunk IDs, similarity scores, and verbatim quotes.
5. **Follow-Up:** Continue the conversation naturally. The deterministic query rewriter resolves pronouns and expands context across turns.
6. **Compile Deliverables:** Trigger artifact generation to transform grounded findings into a Ship 30 for 30 essay, Markdown brief, or visual HTML card.
7. **Inspect & Export:** Toggle between rendered **Preview** and raw **Source** views, copy to clipboard, or download files directly.

---

## Artifacts & Security Sandbox

The application supports three structured artifact formats compiled from grounded research:

| Artifact Type | Format | Target Length / Structure | Use Case |
|:---|:---|:---|:---|
| **Ship 30 for 30 Essay** | Markdown | ~1,250 words · 7 core principles | Thought-leadership essays, strategy playbooks, newsletters |
| **Markdown Summary** | Markdown | Scannable sections · Bullet matrices | Executive briefings, decision memos, team handoffs |
| **HTML/CSS Card** | HTML5 + CSS | Self-contained responsive component | Visual scorecards, framework widgets, presentation embeds |

### Artifact Viewer Capabilities

- **Preview Tab:** Formatted Markdown presentation or sandboxed HTML rendering.
- **Source Tab:** Clean, syntax-highlighted raw source code.
- **Copy:** One-click copy of raw source to clipboard with toast confirmation.
- **Download:** Direct browser download as `.md` or `.html`.

### Security Sandbox Model

Generated HTML is treated as potentially adversarial code:

- **Pre-render sanitization:** Python `bleach` strips dangerous tags (`<script>`, `<object>`, `<iframe>`, `<form>`) and inline event handlers (`onclick`, `onerror`, `onload`).
- **Strict iframe sandboxing:** Rendered in an `<iframe>` with `sandbox=""` (no `allow-scripts`, no `allow-same-origin`, no `allow-forms`, no `allow-popups`).
- **Opaque null origin:** The iframe cannot access parent application cookies, local storage, or DOM.
- **Injected Content Security Policy:** Enforces `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">`.

---

## Data Pipeline & Retrieval Engineering

The ingestion pipeline transforms raw episode transcripts into a searchable semantic knowledge graph:

```
Markdown Transcripts + YAML Frontmatter (ChatPRD Corpus)
    ↓
Metadata Extraction (Guest, Episode Title, Publication Date, Topics)
    ↓
Speaker-Aware Semantic Chunking (~600 tokens, 100-token overlap, speaker preambles)
    ↓
Batch Embeddings (nomic-embed-text via Ollama /api/embed, 32 chunks/batch)
    ↓
PostgreSQL 16 + pgvector Storage (12,014 Chunks · 768 Dimensions)
    ↓
HNSW Vector Index (m=16, ef_construction=64, vector_cosine_ops)
```

### Verified Corpus Metrics

- **Total Episodes:** 303 episodes
- **Total Chunks:** 12,014 transcript chunks
- **Total Embeddings:** 12,014 vectors (zero NULL embeddings)
- **Vector Dimensionality:** 768 dimensions (`nomic-embed-text`)
- **Index Type:** HNSW (`idx_chunks_embedding_hnsw`) with cosine distance

---

## Tech Stack

| Layer | Component | Version / Specification | Role |
|:---|:---|:---|:---|
| **Frontend** | React | 18.2 | Component-driven conversational UI |
| | TypeScript | 5.2 | Type safety and schema synchronization |
| | Vite | 5.2 | High-performance bundling and HMR |
| | TailwindCSS | 3.4 | Consistent typography and utility styling |
| | Lucide React | 0.344 | Interface iconography |
| **Backend** | Python | 3.11 | Application runtime |
| | FastAPI | 0.110 | Asynchronous REST and SSE routing |
| | SQLAlchemy | 2.0 (asyncpg) | Asynchronous ORM and relational persistence |
| | Pydantic | 2.6 | Request/response data validation and settings |
| | Bleach | 6.1 | Defense-in-depth HTML sanitization |
| **Agent Runtime** | Pi Coding Agent | 0.85.1 | Tool-equipped agent core (`@earendil-works/pi-coding-agent`) |
| | Node.js Daemon | stdio JSON-RPC | Persistent bridge process (`bridge_daemon.mjs`) |
| **Database** | PostgreSQL | 16 | Relational session, message, and artifact storage |
| | pgvector | 0.7.0 | Dense vector similarity search with HNSW indexing |
| **Models** | Ollama | Latest | Containerized local model runtime |
| | Llama 3.1 | 8b | Default local generation model |
| | Nomic Embed Text | 768-dim | Fixed corpus embedding model |
| | Anthropic Claude | Claude 3.5 Sonnet | Optional cloud generation provider |
| **Deployment** | Docker Compose | V2 | Multi-container orchestration |

---

## Quick Start

### Prerequisites

- **Git**
- **Docker Desktop** (macOS/Windows) or **Docker Engine + Compose V2** (Linux)
- **Disk Space:** ~8 GB for Docker container images and local model weights
- **RAM:** $\ge 16\text{ GB}$ recommended for local Ollama inference

The canonical workflow runs entirely inside Docker Compose with zero cloud API keys required.

### Step 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/nishantkr0904/The_Lenny_Growth_Assistant.git
cd The_Lenny_Growth_Assistant

# Copy the canonical environment template
cp .env.example .env
```

### Step 2: Start All Services

```bash
docker compose up -d
```

### Step 3: Pull Local Ollama Models (First Run Only)

```bash
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text
```

### Step 4: Ingest Transcript Corpus

The repository includes the full 303-episode transcript corpus in `data/transcripts/`. Run the ingestion pipeline to populate PostgreSQL and pgvector:

```bash
# Ingest full corpus (303 episodes, 12,014 chunks with 768-dim embeddings)
docker compose exec backend python -m scripts.ingest

# Optional: Run a quick 5-episode smoke test instead of the full corpus
docker compose exec backend python -m scripts.ingest --limit 5
```

### Step 5: Access the Application

Once running, access the local services:

- **Web Workspace:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Environment Configuration

All application configuration is managed via `.env` (derived from `.env.example`). No secrets are committed to the repository.

### Default Local Configuration (Ollama)

```env
# Runtime
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]

# Database (Internal Docker network URL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/lenny_growth

# Generation Provider (Local Ollama default)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT_SECONDS=180.0

# Fixed Corpus Embedding Configuration
EMBED_MODEL=nomic-embed-text
EMBED_DIMENSIONS=768

# Grounding & Retrieval Thresholds
RETRIEVAL_TOP_K=15
GROUNDING_STRONG_THRESHOLD=0.78
GROUNDING_LIMITED_THRESHOLD=0.65
```

### Optional Cloud Configuration (Google Gemini & Anthropic)

To switch generation to Google Gemini or Anthropic Claude via `.env` at boot, update `.env`:

```env
# Google Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Anthropic Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

> **Note on Provider Switching & Live Validation:**
> - Evaluators can also configure and switch providers live in the running UI Header popover.
> - Submitting an API key triggers live pre-flight validation against provider endpoints (`generativelanguage.googleapis.com` or `api.anthropic.com`).
> - If validation fails, active provider remains unchanged (Ollama) and an explicit error is shown.
> - Switching `LLM_PROVIDER` affects generation only; corpus embeddings remain strictly fixed to `nomic-embed-text` via Ollama at 768 dimensions in PostgreSQL pgvector.
> - Zero silent fallback: If an unconfigured cloud provider is invoked, the backend returns an explicit error without falling back to Ollama.

---

## Testing & Verification

The codebase maintains full automated and manual test coverage across every architectural boundary.

### 1. Automated Backend Test Suite (pytest)

The backend suite covers API routing, GroundingGate evaluation, Pi RPC bridge communication, batch embeddings, chunking, rewriter logic, HTML sanitization, and session isolation.

```bash
docker compose exec backend pytest -v
```

**Result: 122 passed in 11.9s**

| Test Module | Tests | Scope Covered | Status |
|:---|:---|:---|:---|
| `test_agent_tool.py` | 5 | Pi tool extension, retrieval schema, parameter handling | **PASS** |
| `test_artifacts.py` | 5 | Ship 30 essay, Markdown summary, and HTML card compilation | **PASS** |
| `test_audit_matrix.py` | 8 | Grounding taxonomy, artifact compilation integrity, lexical bounds | **PASS** |
| `test_chunker.py` | 4 | Speaker turn segmentation, 600-token boundaries, overlap | **PASS** |
| `test_citation.py` | 6 | Provenance verification, zero citations on refusal | **PASS** |
| `test_config.py` | 3 | Pydantic settings validation, port mappings | **PASS** |
| `test_conversational_intent.py` | 5 | Casual greetings routing, knowledge query dispatch, artifact safety | **PASS** |
| `test_embeddings.py` | 5 | Batch `/api/embed` processing, dimensionality enforcement | **PASS** |
| `test_gemini.py` | 8 | Google Gemini generate, streaming, live key validation, factory resolution | **PASS** |
| `test_health.py` | 4 | Readiness probes, database and provider connectivity | **PASS** |
| `test_ingestion.py` | 4 | Pipeline execution, idempotency, deduplication | **PASS** |
| `test_parser.py` | 4 | Frontmatter extraction, metadata normalization | **PASS** |
| `test_pi_bridge.py` | 10 | Stdio JSON-RPC lifecycle, tool query preservation, compound routing | **PASS** |
| `test_providers.py` | 7 | Ollama, Anthropic, Gemini adapters, unconfigured selection rejections, live validation | **PASS** |
| `test_qna_api.py` | 5 | Q&A endpoints, empty query rejection, SSE headers | **PASS** |
| `test_retrieval.py` | 23 | HNSW cosine search, GroundingGate tiers, uppercase acronym boost | **PASS** |
| `test_rewriter.py` | 5 | Conversational pronoun resolution, multi-turn state | **PASS** |
| `test_security_sanitization.py` | 6 | Bleach script stripping, event handler removal, CSP injection | **PASS** |
| `test_sessions.py` | 5 | Session CRUD, multi-session isolation, cascading session deletion | **PASS** |
| **Total Backend** | **122** | **Complete backend coverage** | **PASS** |

### 2. Automated Frontend Test Suite (Vitest)

```bash
cd frontend && npm test
```

**Result: 18 passed (18 tests in `components.test.tsx`)**
- Chat interface rendering and input submission
- Live token streaming state transitions
- Citation badge rendering and click interactions
- Citation drawer expansion and quote inspection
- Artifact Viewer tab toggling (Preview vs. Source)
- Copy-to-clipboard action with visual toast
- Session list navigation and new session creation
- Session deletion with relational cascade and event isolation
- Grounding status badge display (`Strong`, `Limited`, `Contrasting`, `Insufficient`)
- Conversational greeting display without refusal card or citation badges
- Refusal card display on out-of-domain queries
- Create Artifact action gating on valid grounded evidence
- Provider selector popover rendering and active state toggle
- Cloud Anthropic API key configuration modal, validation, and status masking
- Light / Dark Mode toggle button rendering and theme switching
- Theme preference persistence across application reloads (`localStorage`)

### 3. Manual UI Verification Matrix

The application has been verified end-to-end across the 11 user journeys documented in [`docs/manual_ui_test_plan.md`](docs/manual_ui_test_plan.md):

| # | User Journey | Target Behavior | Result |
|:---|:---|:---|:---|
| **1** | **Clean Startup & Empty State** | Welcome state, prompt chips, grounding disclaimer | **PASS** |
| **2** | **Out-of-Domain Refusal Flow** | Insufficient evidence ($S < 0.65$), refusal text, zero citations | **PASS** |
| **3** | **Real Grounded Q&A Flow** | Real-time SSE streaming, grounding pill, verified citations | **PASS** |
| **4** | **Citation Drawer & Evidence Inspector** | Drawer slide-out, chunk ID, verbatim excerpt, similarity score | **PASS** |
| **5** | **Context-Aware Follow-Up Flow** | Pronoun rewriting ("she" $\to$ prior guest), grounded follow-up | **PASS** |
| **6** | **Ship 30 for 30 Artifact Creation** | 250–300 word atomic essay, headline, hook, takeaway | **PASS** |
| **7** | **Artifact Viewer & Tab Switching** | Live preview / raw source tabs, copy to clipboard, download | **PASS** |
| **8** | **Session History & Switching** | Session list sidebar, active session switching, state persistence | **PASS** |
| **9** | **Error State & Recovery** | Malformed inputs, empty submissions, graceful notifications | **PASS** |
| **10** | **Provider Indicator & Toggle** | Active provider pill (`Ollama` vs `Anthropic`), status | **PASS** |
| **11** | **End-to-End Responsive Layout** | Clean rendering, responsive breakpoints, drawer overlays | **PASS** |

---

## Repository Structure

```text
the-lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── agent/            # Pi Coding Agent bridge daemon & Q&A orchestrator
│   │   ├── api/v1/           # Health, Ingest, Retrieval, Sessions, Artifacts endpoints
│   │   ├── artifacts/        # Ship 30 compiler, HTML sanitizer, CSP enforcer
│   │   ├── core/             # Configuration & logging infrastructure
│   │   ├── db/               # PostgreSQL / pgvector connection & initialization
│   │   ├── ingestion/        # Markdown parser, recursive chunker, nomic embeddings
│   │   ├── models/           # Pydantic schemas and database models
│   │   ├── providers/        # Generation providers (Ollama, Anthropic)
│   │   ├── retrieval/        # pgvector HNSW search engine, rewriter, CitationValidator
│   │   └── security/         # Bleach HTML sanitizer and strict CSP enforcement
│   ├── data/transcripts/     # Curated Markdown transcripts (303 episodes)
│   ├── scripts/
│   │   └── ingest.py         # CLI entrypoint for transcript ingestion and re-indexing
│   ├── tests/                # 111 automated pytest unit, integration, and security tests
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/       # Chat, CitationDrawer, ArtifactViewer, SessionList
│   │   ├── services/         # SSE streaming client and REST API service
│   │   └── tests/            # 11 Vitest component unit tests
│   ├── nginx.conf            # Reverse proxy configuration with unbuffered SSE streaming
│   └── Dockerfile
├── .pi/                      # Pi Coding Agent extensions (transcript_retrieval.ts)
├── agent_transcripts/        # AI coding agent trajectory logs and failed attempt resolutions
├── docs/                     # Documentation & manual UI test plan (11 user journeys)
├── docker-compose.yml        # Multi-container orchestration (postgres, ollama, backend, frontend)
├── .env.example              # Canonical environment configuration template (zero secrets)
├── PRD.md                    # Authoritative Product Requirements Document
├── architecture.md           # System Architecture & Technical Specifications
└── design.md                 # UI/UX & Interaction Design Specifications
```

---

## Documentation Index

| Document | Purpose |
|:---|:---|
| [`PRD.md`](PRD.md) | Authoritative product requirements, user personas, functional specifications, and acceptance criteria. |
| [`architecture.md`](architecture.md) | Technical architecture specification, data models, IPC bridge mechanics, security boundaries, and runtime topology. |
| [`design.md`](design.md) | UI/UX design specifications, component taxonomy, interaction flows, accessibility standards, and trust badges. |
| [`docs/manual_ui_test_plan.md`](docs/manual_ui_test_plan.md) | Step-by-step 11-journey evaluator test plan with reproduction procedures and expected behaviors. |
| [`agent_transcripts/README.md`](agent_transcripts/README.md) | Trajectory logs, technical blockers encountered during construction, and engineering resolutions. |

---

## Security Architecture

- **Untrusted HTML isolation:** All LLM-generated HTML/CSS is sanitized via Python `bleach` and rendered inside an isolated `<iframe>` with `sandbox=""` and a strict Content Security Policy (`default-src 'none'; style-src 'unsafe-inline'`). JavaScript execution and same-origin DOM access are completely prevented.
- **Transcripts as data, not instructions:** Retrieved transcript text is injected into model prompts inside delimited `<evidence>` XML blocks, mitigating indirect prompt injection attacks from transcript content.
- **Zero secrets in source:** No API keys or credentials are baked into images or repository files. All configuration loads from environment variables, with `.env.example` containing safe local defaults.
- **Strict provider error handling:** Missing credentials or connection dropouts produce immediate, explicit error messages. The system never silently fails over to unintended cloud services.
- **Multi-session isolation:** All database operations enforce strict session scoping (`WHERE session_id = :id`), preventing conversational state leakage across sessions.

---

## Deferred Scope & Future Enhancements

The current implementation satisfies all core research and artifact generation requirements. The following items represent deferred P2 capabilities:

- **Artifact version history & in-app editing:** The current implementation compiles immutable artifacts with raw source view, clipboard copying, and file download. Direct in-browser rich text editing is deferred.
- **Automated corpus refresh:** Transcripts are ingested via the idempotent CLI pipeline (`python -m scripts.ingest`). Automated scraping of newly released episodes via RSS is deferred.
- **Additional cloud providers:** Anthropic Claude 3.5 Sonnet and Google Gemini 2.5 Flash are fully implemented and verified. OpenAI GPT-4o adapter is deferred.
- **Mobile-native UI layout:** The web application is optimized for desktop product and growth research workflows.

---

## Source Attribution & Disclaimer

- The podcast transcript corpus is sourced from [ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts).
- Podcast audio and transcript content belong to [Lenny Rachitsky](https://www.lennyspodcast.com/) and the respective podcast guests.
- The Lenny Growth Assistant is an independent research project providing a search, synthesis, and artifact generation interface over publicly available transcript archives.

---

*The Lenny Growth Assistant is fully implemented, containerized, and verified across all functional, architectural, and security requirements.*
