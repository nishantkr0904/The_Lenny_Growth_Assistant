import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.artifacts.compiler import ArtifactCompiler
from app.artifacts.store import ArtifactStore
from app.db.session import get_db
from app.main import app
from app.sessions.store import SessionStore


@pytest.fixture
def client():
    return TestClient(app)


def test_compile_ship30_essay_structure():
    title = "Why Growth Leaders Stop Growing"
    topic = "Boiling Frog Syndrome"
    content = "Ada Chen Rekhi explains that teams often normalize gradual stagnation."
    sources = [
        {
            "chunk_id": str(uuid4()),
            "title": "Feeling stuck? Here's how to know when it's time to leave your job",
            "guest": "Ada Chen Rekhi",
            "quoted_excerpt": "You have to know which mode you are in.",
            "similarity_score": 0.81,
        }
    ]

    essay = ArtifactCompiler.compile_ship30_essay(title, topic, content, sources)

    # Verify 7 encoded Ship 30 for 30 principles
    assert "# Why Growth Leaders Stop Growing" in essay
    assert "Ship 30 for 30 Atomic Essay" in essay
    assert "The Hook" in essay  # Principle 1: Strong Hook
    assert "Core Insights & Evidence" in essay  # Principle 2: Clear Progression
    assert "Ada Chen Rekhi" in essay  # Principle 6: Grounded Claims
    assert "Tactical Playbook" in essay  # Principle 3: Skimmable formatting
    assert "Actionable Takeaway: What to Do on Monday Morning" in essay  # Principle 5: Useful takeaway
    assert "Sources & Attribution" in essay  # Principle 7: Curating the experts
    assert "You have to know which mode you are in." in essay  # Quoted evidence
    assert len(essay.split()) > 100  # Substantial structured document


def test_compile_markdown_brief():
    title = "Product-Led Growth Playbook"
    topic = "PLG vs Sales"
    content = "Elena Verna discusses acquisition loops."
    sources = [
        {
            "chunk_id": str(uuid4()),
            "title": "Elena Verna on PLG",
            "guest": "Elena Verna",
            "quoted_excerpt": "PLG is an acquisition model, not just a product feature.",
            "similarity_score": 0.85,
        }
    ]

    brief = ArtifactCompiler.compile_markdown_brief(title, topic, content, sources)

    assert "# Product-Led Growth Playbook" in brief
    assert "Research Brief" in brief
    assert "Executive Summary" in brief
    assert "Key Strategic Insights" in brief
    assert "Elena Verna" in brief


@pytest.mark.asyncio
async def test_artifacts_api_flow(client: TestClient):
    # 1. Create a session
    sess_res = client.post("/api/v1/sessions", json={"title": "Career Strategy with Ada"})
    assert sess_res.status_code == 201
    session_data = sess_res.json()
    session_id = session_data["id"]

    # 2. Add a grounded message turn to the session
    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        # Add user message
        await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="user",
            content="What does Ada Chen Rekhi say about boiling frogs?",
        )
        # Add assistant message with strong tier and source reference
        asst_msg = await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content="According to Ada Chen Rekhi, boiling frog syndrome is when you normalize stagnation.",
            evidence_tier="strong",
            latency_ms=1200,
            model_used="pi-coding-agent",
        )
        from app.sessions.models import SourceReferenceItem
        from sqlalchemy import text
        chunk_row = (await db.execute(text("SELECT id FROM transcript_chunks LIMIT 1;"))).fetchone()
        chunk_id = str(chunk_row.id) if chunk_row else str(uuid4())

        # Add a source reference
        await SessionStore.save_source_references(
            db=db,
            message_id=asst_msg.id,
            references=[
                SourceReferenceItem(
                    chunk_id=chunk_id,
                    similarity_score=0.82,
                    quoted_excerpt="You have to know which mode you are in.",
                )
            ],
        )

    # 3. Compile Ship 30 essay via API
    art_res = client.post(
        "/api/v1/artifacts",
        json={
            "session_id": session_id,
            "artifact_type": "ship30_essay",
            "title": "Escaping the Boiling Frog Trap",
        },
    )
    assert art_res.status_code == 201
    art_data = art_res.json()
    assert art_data["title"] == "Escaping the Boiling Frog Trap"
    assert art_data["artifact_type"] == "ship30_essay"
    assert "Ship 30 for 30" in art_data["content_raw"]
    assert "<!DOCTYPE html>" in art_data["content_html"]
    assert "Content-Security-Policy" in art_data["content_html"]
    artifact_id = art_data["id"]

    # 4. Fetch artifact by ID
    get_res = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == artifact_id

    # 5. List session artifacts
    list_res = client.get(f"/api/v1/artifacts/session/{session_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert list_res.json()[0]["id"] == artifact_id


@pytest.mark.asyncio
async def test_artifacts_api_rejects_ungrounded_refusal(client: TestClient):
    # 1. Create a session with refusal
    sess_res = client.post("/api/v1/sessions", json={"title": "Quantum Physics"})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="user",
            content="What is quantum chromodynamics?",
        )
        await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content="I could not find guidance on this topic in Lenny's Podcast transcripts.",
            evidence_tier="insufficient",
            latency_ms=250,
            model_used="pi-coding-agent",
        )

    # 2. Attempt to compile artifact from refusal
    art_res = client.post(
        "/api/v1/artifacts",
        json={
            "session_id": session_id,
            "artifact_type": "ship30_essay",
        },
    )
    assert art_res.status_code == 400
    assert "ungrounded refusal" in art_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_artifacts_api_rejects_capitalized_insufficient_refusal(client: TestClient):
    """Verify refusal is blocked when evidence_tier is 'Insufficient' (canonical capitalized enum)."""
    sess_res = client.post("/api/v1/sessions", json={"title": "String Theory"})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="user",
            content="What does Lenny say about string theory?",
        )
        await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content="I could not find guidance on this topic in Lenny's Podcast transcripts.",
            evidence_tier="Insufficient",  # Canonical GroundingTier.INSUFFICIENT.value
            latency_ms=250,
            model_used="pi-coding-agent",
        )

    art_res = client.post(
        "/api/v1/artifacts",
        json={
            "session_id": session_id,
            "artifact_type": "ship30_essay",
        },
    )
    assert art_res.status_code == 400
    assert "ungrounded refusal" in art_res.json()["detail"].lower()
