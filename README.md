# The Lenny Growth Assistant

An internal product and growth research assistant over a curated corpus of [Lenny's Podcast](https://www.lennyspodcast.com/) transcripts. It provides source-grounded answers, conversational follow-up research, and structured artifact generation — without requiring users to understand retrieval pipelines, prompting, or model infrastructure.

This is not a generic chatbot. Every answer is traceable to what was actually said on the podcast.

---

## Why This Exists

Lenny's Podcast is one of the richest publicly available sources of product and growth expertise — hundreds of episodes featuring practitioners from Airbnb, Slack, Figma, Stripe, and others. The problem is access and synthesis:

- **Discovery is manual.** Finding which episode discussed "how to set up your first growth team" requires scrubbing through hours of recordings or hoping a search engine surfaces the right clip.
- **Synthesis is labor-intensive.** Extracting a coherent answer from a conversational transcript — and cross-referencing it with what other guests said — takes significant effort.
- **Reuse is fragile.** Sharing insights typically means copying quotes into a doc, losing attribution, and hoping the paraphrase is faithful.

The Lenny Growth Assistant removes search friction, synthesis labor, and content creation overhead by grounding every response in the transcript corpus and making sources inspectable.

---

## What It Does

### Core Capabilities

- **Source-grounded Q&A** — Ask product and growth questions; receive answers anchored exclusively in transcript evidence with episode and guest citations.
- **Follow-up research** — Multi-turn sessions preserve conversational context. Ask "What else did she say about that?" and the system resolves the reference.
- **Honest failure behavior** — When evidence is insufficient, the assistant refuses or qualifies rather than hallucinating. This is a product decision, not a bug.
- **Ship 30 for 30 essays** — Transform grounded insights into ~1,250-word essays following Ship 30 for 30 writing principles: strong hook, clear progression, skimmable formatting, actionable takeaway.
- **Markdown and HTML/CSS artifacts** — Generate structured written content and visual cards, rendered in a safe in-app Artifact Viewer alongside the chat.
- **Copy and download** — Export generated artifacts as raw source for use in external tools.
- **Configurable model providers** — Run locally with Ollama (zero cloud dependencies) or switch to Anthropic Claude for stronger inference. Provider switching requires only an environment variable change.

### Not Included (by design)

- General AI advice outside the transcript corpus
- Real-time podcast ingestion
- Multi-tenant enterprise features
- Autonomous background agents
- Mobile-native application

---

## Core Product Flow

```
Question (natural language)
    ↓
Retrieval (pgvector semantic search over transcript chunks)
    ↓
Grounding Gate (deterministic evidence evaluation)
    ↓
Synthesis (Pi Coding Agent + LLM, constrained to evidence)
    ↓
Answer + Source Citations (episode, guest, relevant excerpt)
    ↓
Follow-up (session context maintained)
    ↓
Artifact Generation (optional: essay, markdown, HTML/CSS)
```

**Trust model:** The transcript corpus is the sole source of truth. The LLM is an untrusted reasoning engine, not a knowledge store. A deterministic grounding gate evaluates evidence *before* the LLM generates a single word — Strong evidence triggers full synthesis, Limited evidence triggers qualified answers, and Insufficient evidence triggers an immediate refusal without calling the model.

---

## Architecture

```mermaid
graph TD
    subgraph DockerCompose ["Docker Compose"]
        FE["Frontend<br/>React 18 + Vite + TypeScript"]
        BE["FastAPI Backend<br/>Python · Orchestration · API"]
        PG["PostgreSQL 16 + pgvector<br/>Sessions · Messages · Vectors"]
        OL["Ollama<br/>Generation + Embedding"]
    end

    User -->|Port 3000| FE
    FE -->|REST + SSE| BE
    BE -->|SQL + Vector Search| PG
    BE -->|IPC/RPC Bridge| Pi["Pi Coding Agent<br/>Tool-equipped Agent"]
    Pi -->|generate / stream| OL
    Pi -->|embed| OL
    BE -.->|Cloud generation<br/>when configured| Cloud["Anthropic Claude<br/>or OpenAI"]
```

### Key Architectural Decisions

**Pi Coding Agent** serves as the cognitive core — a tool-equipped agent invoked via an IPC/RPC bridge from the FastAPI backend. Pi executes bounded tools (`transcript_retrieval`, `ship30_writer`, `artifact_compiler`) against validated evidence. It does not have unbounded access to general knowledge.

**Provider separation** is strict:

```
GenerationProvider (routed by LLM_PROVIDER)
├── OllamaGenerationProvider  (default — local, zero API keys)
├── AnthropicProvider          (P0 cloud provider)
└── OpenAIProvider             (P2 — second cloud extension)

EmbeddingProvider (fixed — not affected by LLM_PROVIDER)
└── OllamaEmbeddingProvider
    └── nomic-embed-text (768 dimensions)
```

Switching `LLM_PROVIDER` changes only the generation model. Corpus embeddings always use `nomic-embed-text` via Ollama at 768 dimensions. Changing generation providers never invalidates the vector index and never requires re-ingestion. Silent fallbacks between providers are prohibited.

---

## Grounding & Trust

The grounding gate enforces four evidence tiers using deterministic cosine similarity thresholds — not an LLM judge:

| Evidence Tier | Condition | System Behavior |
|---------------|-----------|-----------------|
| **Strong** | Top similarity ≥ 0.78 | Full synthesis with citations |
| **Limited** | 0.65 ≤ similarity < 0.78 | Qualified answer noting limited evidence |
| **Conflicting** | ≥ 0.78 but opposing perspectives across guests | Balanced presentation of both viewpoints |
| **Insufficient** | < 0.65 or no chunks returned | Deterministic refusal — LLM is never called |

**Source diversity** (number of distinct episodes cited) is a presentation and confidence signal, not a requirement for Strong evidence. A single episode with high-relevance discussion can constitute Strong evidence.

---

## Data Source

**Transcript corpus:** [ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts)

The corpus contains ~250–300 episodes of Lenny's Podcast transcripts in Markdown format with YAML frontmatter (guest name, episode title, topics). The repository is publicly available and maintained separately. This project does not claim ownership of the transcript content.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS |
| Backend | Python, FastAPI |
| Agent | Pi Coding Agent (`@earendil-works/pi-coding-agent`) |
| Database | PostgreSQL 16 with pgvector extension |
| Embedding | Ollama + `nomic-embed-text` (768-dim) |
| Local generation | Ollama (`llama3.1:8b` default) |
| Cloud generation | Anthropic Claude 3.5 Sonnet (P0), OpenAI GPT-4o (P2) |
| Deployment | Docker Compose |

---

## Prerequisites

- **Git**
- **Docker Desktop** (macOS/Windows) or **Docker Engine + Compose** (Linux)
  - Docker Compose V2 (`docker compose` subcommand)
- **Disk space:** ~8 GB for Docker images and model weights
- **RAM:** ≥ 16 GB recommended for local Ollama inference with an 8B model
- **Network:** Initial setup downloads Docker images and the Ollama model

The canonical local path uses Docker Compose exclusively. No cloud API key is required for the default demo.

---

## Quick Start

> **Implementation status:** The application is currently in the documentation and design phase. The commands below describe the *intended* evaluator workflow as specified in `architecture.md`. They will work once the application code is implemented.

```bash
# 1. Clone repository
git clone https://github.com/nishantkr0904/The_Lenny_Growth_Assistant.git
cd The_Lenny_Growth_Assistant

# 2. Copy default environment (pre-configured for local Ollama — no cloud keys needed)
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. Run one-time transcript ingestion
docker compose exec backend python -m scripts.ingest

# 5. Open the application
open http://localhost:3000
```

Setup targets under 10 minutes under documented prerequisites. Actual time varies with image and model download speeds.

---

## Environment Configuration

The `.env.example` file will contain all configurable variables with safe defaults and no secrets.

### Generation Provider

```env
# Local demo (default — zero cloud credentials required)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b
```

### Corpus Embedding (fixed)

```env
# Always uses Ollama nomic-embed-text regardless of LLM_PROVIDER
EMBED_MODEL=nomic-embed-text
EMBED_DIMENSIONS=768
```

### Cloud Provider (optional)

```env
# Anthropic Claude (generation only)
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=<your-anthropic-api-key>
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# OpenAI (generation only — P2)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=<your-openai-api-key>
# OPENAI_MODEL=gpt-4o
```

The default local path does not require any cloud API key.

---

## Provider Configuration

| Provider | `LLM_PROVIDER` value | API Key Required | Status |
|----------|---------------------|------------------|--------|
| Ollama (local) | `ollama` | No | Default — mandatory for submitted demo |
| Anthropic Claude | `anthropic` | Yes (`ANTHROPIC_API_KEY`) | P0 cloud provider |
| OpenAI | `openai` | Yes (`OPENAI_API_KEY`) | P2 — second cloud extension |

**No silent fallback.** If a selected cloud provider is unavailable or missing an API key, the system returns an explicit error message. It never silently degrades to a different provider.

### Host-Native Ollama (Optional Escape Hatch)

On Apple Silicon Macs, containerized Ollama cannot access Metal GPU acceleration and falls back to CPU inference (3–5x slower). If you have Ollama installed natively with models pre-cached:

```env
# 1. Comment out the 'ollama' service in docker-compose.yml
# 2. Point to host Ollama:
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

This is an optional developer/performance optimization, not the canonical evaluator path.

---

## Transcript Ingestion

The ingestion pipeline transforms raw podcast transcripts into searchable knowledge:

```
Transcript Markdown files (with YAML frontmatter)
    ↓
Metadata extraction (guest, episode title, topics, publication date)
    ↓
Speaker-aware semantic chunking (~600 tokens, 100-token overlap)
    ↓
Embedding generation (nomic-embed-text via Ollama, 768 dimensions)
    ↓
Storage in PostgreSQL + pgvector (HNSW index, cosine distance)
```

The corpus yields approximately 12,000–18,000 chunks. An HNSW index ensures vector search executes in < 25ms. Every chunk retains its source episode, guest, speaker label, and position for full provenance traceability.

Corpus refresh is a documented manual re-ingestion process. Automated refresh is a future capability.

---

## Artifacts

The assistant generates three artifact types from grounded research:

| Type | Format | Use Case |
|------|--------|----------|
| **Ship 30 for 30 Essay** | Markdown (~1,250 words) | Structured thought-leadership content |
| **Markdown Summary** | Markdown | Bullet points, frameworks, matrices |
| **HTML/CSS Card** | HTML + inline CSS | Visually rich, responsive content cards |

### Artifact Viewer

Generated artifacts render in an in-app viewer alongside the chat:

- **Preview** — Rendered output (Markdown or HTML)
- **Source** — Raw source code
- **Copy** — Copy source to clipboard
- **Download/Export** — Save as file

**Security:** Generated HTML is treated as untrusted output. It renders inside a sandboxed `<iframe>` with:
- Bare `sandbox` attribute (no permissions granted)
- No `allow-scripts` — JavaScript execution is completely blocked
- No `allow-same-origin` — opaque `null` origin prevents access to parent application
- CSP: `default-src 'none'; style-src 'unsafe-inline'`
- Pre-render HTML sanitization to strip `<script>`, `onclick`, `onerror`, `javascript:` URIs

Artifact editing and version history are planned as P2 capabilities.

---

## Development

> **Implementation status:** Application code has not been implemented yet. The project is currently in the documentation and design phase. The workflow below describes the intended development approach.

### Intended Project Structure

```
├── frontend/          # React 18 + Vite + TypeScript SPA
├── backend/           # Python FastAPI application
│   ├── api/           # Route handlers
│   ├── core/          # Configuration, providers, grounding gate
│   ├── models/        # Pydantic schemas and DB models
│   ├── services/      # Business logic
│   └── scripts/       # Ingestion pipeline
├── tests/             # Unit, integration, E2E tests
├── docker-compose.yml
├── .env.example
├── PRD.md
├── architecture.md
└── design.md
```

---

## Testing

### Planned Testing Strategy

| Level | Scope | Framework |
|-------|-------|-----------|
| **Unit** | Chunking, grounding gate thresholds, HTML sanitization, citation validation, provider factory | `pytest` |
| **Integration** | pgvector queries, API endpoints, ingestion pipeline, provider adapters | `pytest` + Testcontainers |
| **E2E** | Chat flow, artifact viewer sandbox, golden evaluation queries | Playwright |

Tests are not yet implemented. The test architecture is documented in `architecture.md` §21.

---

## Project Documentation

| Document | Purpose |
|----------|---------|
| [PRD.md](PRD.md) | Authoritative product contract — user, problem, requirements, acceptance criteria, implementation phases |
| [architecture.md](architecture.md) | System architecture — schema, APIs, component boundaries, ingestion/retrieval flow, agent routing, security, deployment |
| [design.md](design.md) | UX and interaction design — information architecture, user flows, screen specifications, component taxonomy, trust patterns |

---

## Implementation Priorities

| Priority | Scope | Key Deliverables |
|----------|-------|-----------------|
| **P0** | Core research loop | Transcript ingestion, retrieval, grounding gate, Pi agent integration, grounded Q&A, session persistence, Ollama provider, Anthropic provider |
| **P1** | Artifacts and product completeness | Ship 30 for 30 skill, artifact generation, Artifact Viewer (Preview/Source/Copy/Download), streaming UI, error states, session management |
| **P2** | Advanced / later | Artifact editing, version history, OpenAI provider, automated corpus refresh, mobile optimization |

---

## Security

- **Generated HTML is untrusted.** All LLM output is treated as potentially adversarial. HTML artifacts render in a strict sandbox with no script execution.
- **Transcripts are untrusted input.** Injected as data inside `<evidence>` XML tags, never as system instructions. The system prompt explicitly prevents interpreting evidence content as commands.
- **Secrets are never committed.** API keys load from environment variables. `.env.example` contains safe defaults only.
- **Provider errors are explicit.** Missing API keys, unavailable services, and model timeouts produce specific, actionable error messages. The system never silently switches providers.
- **Sessions are isolated.** All database queries enforce `WHERE session_id = :id`. Messages from one session cannot leak into another.

---

## Known Validation Items

These are implementation-phase validation items, not bugs. They represent documented assumptions that require empirical confirmation:

| Item | Risk | Documented In |
|------|------|---------------|
| **Pi Coding Agent RPC integration** | Pi's `--mode rpc` API surface and custom extension registration must be validated against actual behavior. Fallback: HTTP sidecar if RPC differs. | architecture.md §25.3–25.4 |
| **Grounding gate threshold calibration** | Cosine similarity thresholds (0.78 Strong, 0.65 Limited) are initial estimates requiring empirical tuning against the actual corpus. | architecture.md §8.3 |
| **Embedding quality validation** | `nomic-embed-text` performance on conversational podcast transcripts needs validation with known-answer queries. | architecture.md §25.2 |
| **Chunk size validation** | ~600-token / 100-token overlap default needs benchmarking against 400-token alternative. | architecture.md §25.2 |
| **Containerized Ollama on Apple Silicon** | Docker-based Ollama cannot access Metal GPU, resulting in CPU-only inference (3–5x slower). Host-native escape hatch documented. | architecture.md §20.1 |

---

## Source Attribution

The transcript corpus is sourced from the [ChatPRD/lennys-podcast-transcripts](https://github.com/ChatPRD/lennys-podcast-transcripts) repository. This project does not claim ownership of the podcast content. All generated answers include explicit attribution to the original episode and guest.

---

*This README reflects the current repository state. The project is in the documentation and design phase. Application implementation will follow the phased plan documented in PRD.md §18.*
