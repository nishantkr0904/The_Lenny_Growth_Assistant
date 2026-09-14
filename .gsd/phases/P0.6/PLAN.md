# Phase P0.6 Plan: Evaluator-Facing Product Experience (React Q&A, Ship 30 for 30, and Safe Artifacts)

> **Phase**: P0.6 — Evaluator-Facing Product Experience: React Q&A, Ship 30 for 30, and Safe Artifacts  
> **Status**: Ready to Execute  
> **Target**: Turn the validated backend foundation into a polished, responsive, evaluator-facing research workspace featuring multi-turn conversational Q&A, real-time SSE streaming, GroundingGate trust UX, actionable citation cards, Ship 30 for 30 writing transformation, and a sandboxed, hardened Artifact Viewer (Markdown and HTML) with bare iframe isolation and Bleach sanitization.

---

## 1. Context & Objective

Phases P0.1–P0.5A established and verified the core backend foundation:
- Multi-container environment (PostgreSQL 16 + pgvector, Ollama `llama3.1:8b` + `nomic-embed-text`, FastAPI backend).
- Ingested transcripts with speaker-aware semantic chunking and 768-dim embeddings.
- P0.3 Vector retrieval engine with deterministic 4-tier GroundingGate.
- Pi Coding Agent 0.85.1 running natively as the production agent runtime via stdio JSON-RPC 2.0 daemon, invoking custom `transcript_retrieval` tool.
- Decoupled model provider abstraction (Ollama local default, Anthropic Claude cloud).
- PostgreSQL session and message persistence with bounded context and query rewriting.
- CitationValidator and real-time SSE streaming endpoint (`POST /api/v1/sessions/{id}/messages`).

Phase P0.6 delivers the **evaluator-facing product experience**:
```
User (Browser @ http://localhost:3000)
    ↓
React 18 + Vite Frontend SPA (TailwindCSS, Lucide React)
    ↓
FastAPI Application Gateway (/api/v1)
    ├── /health (Provider & DB status)
    ├── /sessions (CRUD sessions)
    ├── /sessions/{id}/messages (SSE streaming Q&A via Pi Agent)
    └── /artifacts (Ship 30 for 30 & HTML/Markdown compiler with Bleach sanitization)
    ↓
Contextual UI Panels
    ├── AnswerBlock + EvidenceIndicator (Strong, Limited, Conflicting, Insufficient refusal)
    ├── CitationDrawer (Source cards with verified quotes & episode provenance)
    └── ArtifactViewer (Preview / Source tabs, bare sandboxed <iframe> with strict CSP, copy & export)
```

---

## 2. Architectural Boundaries & Non-Negotiable Rules

1. **Pi Remains Production Agent Layer:** The production Q&A path continues executing turns through `PiBridgeClient` and Pi Coding Agent 0.85.1. No direct provider calls from the frontend or bypasses in the backend.
2. **P0.3 Retrieval Single Source of Truth:** pgvector similarity search and deterministic GroundingGate remain authoritative. No client-side retrieval or duplicated vector search.
3. **Deterministic Refusal on Insufficient Evidence:** When GroundingGate evaluates to `Insufficient` (< 0.65), the backend emits honest refusal with zero citations. The frontend displays the warm refusal card and never hallucinates general knowledge.
4. **Decoupled Providers:** Default remains containerized Ollama. Switching to Anthropic Claude occurs strictly via `LLM_PROVIDER=anthropic` in `.env` without frontend changes. Missing credentials fail explicitly with zero silent fallback.
5. **Ship 30 for 30 Writing Principles Encoded:** Encodes the 7 canonical principles: Grabber Hook, Clear Progression (4A paths), Skimmable Formatting, ~1,250 words target, Specific Takeaway, Grounded Claims, and "Curating the Experts" credibility framing.
6. **Defense-in-Depth HTML Security:** Generated HTML is treated as untrusted. Sanitized on backend via `bleach` (stripping `<script>`, `<object>`, `<embed>`, `<iframe>`, forms, `javascript:`, inline `on*` event handlers) + injected with strict Content Security Policy (`default-src 'none'`) + rendered in frontend inside a bare sandboxed `<iframe>` (`sandbox=""` with NO `allow-scripts` and NO `allow-same-origin`).
7. **Clean Lifecycle & Zero Leaks:** No orphan processes, no memory leaks in event listeners, clean disposal.

---

## 3. Implementation Tasks

### Task 1: Backend Artifact Engine & Bleach Sanitization
- **Files**:
  - `backend/pyproject.toml` (add `bleach>=6.1.0`)
  - `backend/app/artifacts/models.py` (Pydantic request/response schemas)
  - `backend/app/artifacts/compiler.py` (Markdown, Ship 30 for 30 writer, HTML/CSS compiler with strict CSP & Bleach sanitization)
  - `backend/app/artifacts/store.py` (PostgreSQL `artifacts` table CRUD)
  - `backend/app/artifacts/__init__.py`
  - `backend/app/api/v1/artifacts.py` (`POST /api/v1/artifacts`, `GET /api/v1/artifacts/{id}`, `GET /api/v1/sessions/{id}/artifacts`)
  - `backend/app/main.py` (register artifacts router)
  - `backend/tests/test_artifacts.py` & `backend/tests/test_security_sanitization.py`
- **Verification**: `docker compose exec backend pytest tests/test_artifacts.py tests/test_security_sanitization.py -v`.

### Task 2: Frontend App Shell & Layout Scaffold
- **Files**:
  - `frontend/package.json` (React 18, Vite, TailwindCSS, Lucide React)
  - `frontend/vite.config.ts` (API proxy to `/api/v1`)
  - `frontend/tailwind.config.js` & `frontend/src/index.css`
  - `frontend/src/types/index.ts` (Session, Message, Citation, Artifact, EvidenceTier, ProviderStatus)
  - `frontend/src/services/api.ts` (Typed API client for health, sessions, messages, artifacts)
  - `frontend/src/components/layout/AppShell.tsx` (Header with ProviderBadge, responsive 3-panel split)
  - `frontend/src/components/layout/Header.tsx`
  - `frontend/src/components/sessions/SessionSidebar.tsx` & `SessionItem.tsx`
- **Verification**: `npm run build` in `frontend/` succeeds without errors.

### Task 3: Conversational Q&A, SSE Streaming & Grounding Trust UX
- **Files**:
  - `frontend/src/hooks/useChat.ts` (SSE streaming reader, messages accumulator)
  - `frontend/src/components/chat/ConversationView.tsx`
  - `frontend/src/components/chat/Composer.tsx`
  - `frontend/src/components/chat/AnswerBlock.tsx`
  - `frontend/src/components/chat/EvidenceIndicator.tsx` (Strong, Limited, Conflicting)
  - `frontend/src/components/chat/RefusalCard.tsx` (Insufficient evidence)
  - `frontend/src/components/chat/CitationBadge.tsx`
  - `frontend/src/components/chat/SourceDrawer.tsx` & `SourceCard.tsx`
  - `frontend/src/components/chat/LoadingState.tsx` & `ErrorBanner.tsx`
- **Verification**: Verify SSE streaming, follow-ups, and citation drawer.

### Task 4: Ship 30 for 30 Transformation & Artifact Generation
- **Files**:
  - `frontend/src/components/artifacts/ArtifactAction.tsx` ("Create Artifact" button on grounded turns)
  - `frontend/src/components/artifacts/ArtifactTypeSelector.tsx` (Modal/popover: Ship 30 essay, Markdown brief, HTML card)
  - `frontend/src/hooks/useArtifacts.ts`
- **Verification**: Trigger artifact generation from conversation; verify payload creation.

### Task 5: Safe Sandboxed Artifact Viewer & Export Actions
- **Files**:
  - `frontend/src/components/artifacts/ArtifactViewer.tsx` (Preview / Source tabs, copy, export)
  - `frontend/src/components/artifacts/SafeHtmlPreview.tsx` (Bare sandboxed `<iframe>` with `srcdoc`)
  - `frontend/src/components/artifacts/MarkdownPreview.tsx` (Styled typography)
  - `frontend/src/components/artifacts/ArtifactSourceView.tsx` (Raw syntax)
  - `frontend/src/tests/` (Vitest tests for frontend components, security sanitization, and iframe sandbox)
- **Verification**: Vitest test suite passes; security test confirms script tags and event handlers are neutralized.

### Task 6: Docker Compose Integration, Documentation & End-to-End Verification
- **Files**:
  - `frontend/Dockerfile` & `docker-compose.yml` (add `frontend` container service on port 3000)
  - `README.md` (evaluator quickstart, architecture diagram, security notes)
  - `architecture.md` (update frontend and artifact viewer verification)
  - `.gsd/STATE.md`, `.gsd/ROADMAP.md`, `.gsd/TODO.md`, `.gsd/JOURNAL.md`, `.gsd/phases/P0.6/SUMMARY.md`
- **Verification**: Full test suite passes; live browser E2E test runs against Docker Compose stack.

---

## 4. Acceptance Criteria

- [ ] React 18 frontend running at `http://localhost:3000` via Docker Compose.
- [ ] Active model provider badge dynamically displays `🟢 Ollama (llama3.1:8b)` or `🟢 Anthropic (Claude 3.5 Sonnet)` from `/api/v1/health`.
- [ ] Multi-turn conversational Q&A works seamlessly with real-time SSE streaming.
- [ ] GroundingGate tiers (`Strong`, `Limited`, `Conflicting`, `Insufficient`) surfaced accurately.
- [ ] Interactive `SourceDrawer` displays verified guest, episode, and quote excerpt for citations.
- [ ] Insufficient evidence triggers honest refusal with zero source citations.
- [ ] "Create Artifact" workflow generates:
  - `ship30_essay`: ~1,250 words encoding the 7 Ship 30 for 30 principles.
  - `markdown`: Structured notes with source footnotes.
  - `html_card`: Styled HTML card with strict CSP.
- [ ] Safe HTML preview renders in bare sandboxed `<iframe>` (`sandbox=""`) with zero script execution.
- [ ] Bleach sanitization removes malicious scripts, event handlers, and dangerous URIs.
- [ ] Copy to clipboard and download/export (.md / .html) work cleanly.
- [ ] Full automated test suite passes (backend 70+ tests, security tests, frontend tests).
- [ ] Live browser E2E flow verified on Docker stack.
- [ ] Working tree clean with atomic commits per task.
