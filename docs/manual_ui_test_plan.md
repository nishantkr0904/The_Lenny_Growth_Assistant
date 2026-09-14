# Manual UI Test Plan — The Lenny Growth Assistant

This document outlines the manual verification protocol and end-to-end evaluator test journeys for **The Lenny Growth Assistant** web application (`http://localhost:3000`).

---

## 1. Test Environment Prerequisites

Before initiating manual testing, ensure all Docker containers are running and healthy:

```bash
docker compose ps
```

Expected container states:
- `lenny_postgres`: Port 5433 -> 5432 (Healthy)
- `lenny_ollama`: Port 11434 (Healthy)
- `lenny_backend`: Port 8000 (Healthy)
- `lenny_frontend`: Port 3000 (Healthy)

Ensure the full podcast corpus has been ingested into PostgreSQL:
```bash
docker compose exec backend python -c "
import asyncio
from app.core.database import get_db_context
from sqlalchemy import text

async def check():
    async with get_db_context() as session:
        res = await session.execute(text('SELECT count(*) FROM transcript_chunks;'))
        print('Total chunks:', res.scalar())
asyncio.run(check())
"
# Expected output: Total chunks: 12014
```

---

## 2. Test Execution Matrix (11 User Journeys)

| # | Journey | Action | Expected UI Behavior | Verification Status |
|---|---------|--------|----------------------|---------------------|
| **1** | **Clean Startup & Empty State** | Navigate to `http://localhost:3000` | Application loads with header, "The Lenny Growth Assistant" branding, empty session list, empty chat state with suggested prompts, and grounding disclaimer badge. | **PASS** |
| **2** | **Out-of-Domain Refusal Flow** | Enter: *"What are the principles of quantum chromodynamics?"* | Backend evaluates Insufficient evidence tier ($S < 0.65$). UI renders deterministic refusal message stating information is not in Lenny's transcripts. Zero citations rendered. | **PASS** |
| **3** | **Real Grounded Q&A Flow** | Enter: *"How does Ada Chen Rekhi evaluate user retention and product-market fit?"* | Live SSE token streaming displays in real-time. Final answer includes source citation badges, Grounding Tier pill (`Strong` or `Limited`), and synthesized text. | **PASS** |
| **4** | **Citation Drawer & Evidence Inspector** | Click on any citation badge in the grounded response | Slide-out citation drawer opens on right. Displays guest name, episode title, transcript chunk ID, exact quote snippet, and similarity score. | **PASS** |
| **5** | **Context-Aware Follow-Up Flow** | In the same session, enter: *"What specific frameworks did she recommend?"* | Query rewriter resolves "she" to Ada Chen Rekhi using bounded session context. Response streams grounded answer referencing Rekhi's frameworks. | **PASS** |
| **6** | **Ship 30 for 30 Essay Artifact** | Click **"Generate Ship 30 Essay"** in artifact action bar | Compiles ~1,250-word structured essay adhering to 7 Ship 30 principles: headline, clear thesis, 1-3-1 cadence, single-sentence paragraphs, bullet transitions. | **PASS** |
| **7** | **Markdown Summary Artifact** | Click **"Generate Markdown Summary"** in action bar | Compiles concise executive brief with bullet points, strategic framework breakdown, and actionable takeaways. | **PASS** |
| **8** | **HTML/CSS Card Sandbox Isolation** | Click **"Generate HTML Card"** | Renders visual card inside isolated `<iframe>`. Inspect element verifies `sandbox` attribute present with no `allow-scripts` or `allow-same-origin`. Script tags stripped. | **PASS** |
| **9** | **Artifact Viewer Tabs & Actions** | Toggle between **Preview** and **Source** tabs, click **Copy** and **Download** | Source tab reveals clean Markdown/HTML with syntax highlighting. Copy button triggers "Copied to clipboard" toast. Download triggers browser file save. | **PASS** |
| **10** | **Multi-Session Isolation** | Click **"New Session"** in sidebar, ask a different question, switch back to previous session | New session starts with clean empty state. Previous session re-loads all previous messages, grounding badges, and citations intact. Zero session cross-contamination. | **PASS** |
| **11** | **Network & Error Resilience** | Disconnect network or trigger invalid session ID in URL | UI displays non-blocking toast warning and graceful fallback message. Application does not crash, freeze, or unmount. User can retry action. | **PASS** |

---

## 3. Detailed Step-by-Step Verification Procedures

### Journey 1: Initial Empty State
1. Open browser to `http://localhost:3000`.
2. Verify sidebar contains "New Chat" button and session history header.
3. Verify main area shows welcoming prompt chips (e.g. *"B2B Growth loops"*, *"Product-Market Fit"*).
4. Verify footer disclaimer: *"Answers are strictly grounded in Lenny's Podcast transcripts."*

### Journey 2: Out-of-Domain Refusal
1. Type: `What are the principles of quantum chromodynamics and gluon binding?`
2. Press Enter or click Send.
3. Verify response appears promptly stating Lenny's transcripts do not contain this topic.
4. Verify Grounding tier indicates `Insufficient`.
5. Verify no hallucinated episode citations or external links are rendered.

### Journey 3: Grounded Q&A with Live Streaming
1. Type: `What advice does Brian Chesky give about founder mode and managing product details?`
2. Observe SSE stream: text tokens appear incrementally without page stutter.
3. Observe citation chips rendered below response: `[1] Brian Chesky: Leading with Founder Mode...`
4. Verify Grounding Gate badge shows `Strong` or `Limited`.

### Journey 4: Citation Inspection
1. Click on citation chip `[1]`.
2. Inspect drawer panel:
   - Episode title
   - Guest name
   - Transcript segment timestamp / chunk ID
   - Exact text quote matching the claim in the answer
3. Click outside or press Esc to close drawer.

### Journey 5: Conversational Follow-Up
1. Type: `How does his perspective compare to Stewart Butterfield?`
2. Verify query rewriter expands context to compare Brian Chesky and Stewart Butterfield.
3. Verify returned answer cites both guests' respective episodes.

### Journey 6-9: Artifact Compilation and Viewer Security
1. Click **"Artifacts"** menu or use prompt: `Generate a Ship 30 for 30 essay on founder mode based on this discussion.`
2. Verify Artifact Viewer splits screen or opens modal.
3. Verify tabs:
   - **Preview Tab**: Formatted rendered markdown.
   - **Source Tab**: Raw markdown source with copy icon.
4. For HTML Card:
   - Open Chrome DevTools (`Inspect Element`).
   - Find `<iframe>` rendering the card.
   - Verify attributes: `sandbox=""` (no `allow-scripts`, no `allow-same-origin`).
   - Verify `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">`.
5. Click **Download**: Verify `.md` or `.html` file is downloaded to local machine.

### Journey 10: Session Persistence
1. Refresh browser (`Cmd+R` / `F5`).
2. Verify active session and all historical turns, citations, and artifacts remain intact.
3. Click **"+ New Chat"**.
4. Send a new query: `What is Shreyas Doshi's LNO framework?`
5. Switch between Session 1 and Session 2 in sidebar.
6. Verify completely independent contexts and clean state restoration.

---

## 4. Acceptance Sign-off
- All 11 browser journeys verified manually and through Playwright browser automation subagent.
- Zero visual regressions, zero unhandled exceptions in browser console.
