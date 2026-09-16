"""Integration tests for session and message persistence layer."""

import pytest
from sqlalchemy import text
from app.db.session import async_session_factory
from app.sessions.models import SourceReferenceItem
from app.sessions.store import SessionStore


@pytest.mark.asyncio
async def test_session_creation_and_retrieval():
    """Verify session creation, fetching by ID, and listing."""
    async with async_session_factory() as session:
        # Create
        created = await SessionStore.create_session(session, title="Test Exploration Session")
        assert created.id is not None
        assert created.title == "Test Exploration Session"
        assert created.message_count == 0

        # Retrieve
        fetched = await SessionStore.get_session(session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Test Exploration Session"
        assert len(fetched.messages) == 0

        # List
        sessions_list = await SessionStore.list_sessions(session, limit=10)
        assert any(s.id == created.id for s in sessions_list)


@pytest.mark.asyncio
async def test_message_persistence_and_bounded_context():
    """Verify persisting messages and retrieving bounded working context."""
    async with async_session_factory() as session:
        created_session = await SessionStore.create_session(session, title="Multi-Turn Session")
        sid = created_session.id

        # Insert 8 messages (4 user, 4 assistant)
        for i in range(1, 9):
            role = "user" if i % 2 != 0 else "assistant"
            content = f"Turn {i} message content"
            await SessionStore.save_message(
                db=session,
                session_id=sid,
                role=role,
                content=content,
                evidence_tier="Limited" if role == "assistant" else None,
                latency_ms=100 * i if role == "assistant" else None,
                model_used="ollama/llama3.1:8b" if role == "assistant" else None,
            )

        # Full session retrieval should have 8 messages
        detail = await SessionStore.get_session(session, sid)
        assert detail is not None
        assert len(detail.messages) == 8
        assert detail.messages[0].content == "Turn 1 message content"
        assert detail.messages[7].content == "Turn 8 message content"

        # Bounded working context: limit=6 should return the most recent 6 in chronological order
        recent = await SessionStore.get_recent_messages(session, sid, limit=6)
        assert len(recent) == 6
        assert recent[0].content == "Turn 3 message content"
        assert recent[-1].content == "Turn 8 message content"


@pytest.mark.asyncio
async def test_source_references_persistence():
    """Verify source references are linked to messages and reconstructed correctly."""
    async with async_session_factory() as session:
        created_session = await SessionStore.create_session(session, title="Source Reference Session")
        sid = created_session.id

        # Get an existing chunk from DB
        chunk_res = await session.execute(text("SELECT id FROM transcript_chunks LIMIT 1;"))
        chunk_row = chunk_res.fetchone()
        if not chunk_row:
            pytest.skip("No transcript chunks in DB to link source reference")

        chunk_id = str(chunk_row.id)

        # Save assistant message
        msg = await SessionStore.save_message(
            db=session,
            session_id=sid,
            role="assistant",
            content="According to Lenny, onboarding is crucial.",
            evidence_tier="Strong",
            latency_ms=350,
            model_used="ollama/llama3.1:8b",
        )

        # Save source reference
        ref = SourceReferenceItem(
            chunk_id=chunk_id,
            similarity_score=0.88,
            quoted_excerpt="Onboarding is the most critical lever.",
        )
        await SessionStore.save_source_references(session, msg.id, [ref])

        # Fetch session detail
        detail = await SessionStore.get_session(session, sid)
        assert detail is not None
        assert len(detail.messages) == 1
        assert len(detail.messages[0].sources) == 1
        assert detail.messages[0].sources[0].chunk_id == chunk_id
        assert detail.messages[0].sources[0].similarity_score == 0.88
        assert detail.messages[0].sources[0].quoted_excerpt == "Onboarding is the most critical lever."


@pytest.mark.asyncio
async def test_session_deletion_cascade():
    """Verify deleting a session cascades to messages and sources."""
    async with async_session_factory() as session:
        created = await SessionStore.create_session(session, title="Session to Delete")
        sid = created.id

        msg = await SessionStore.save_message(
            db=session,
            session_id=sid,
            role="user",
            content="Temporary message",
        )

        # Confirm message exists
        check_msg = await session.execute(text("SELECT id FROM messages WHERE session_id = :sid;"), {"sid": sid})
        assert check_msg.fetchone() is not None

        # Delete session
        deleted = await SessionStore.delete_session(session, sid)
        assert deleted is True

        # Verify session is gone
        fetched = await SessionStore.get_session(session, sid)
        assert fetched is None

        # Verify messages cascaded
        check_msg_after = await session.execute(text("SELECT id FROM messages WHERE session_id = :sid;"), {"sid": sid})
        assert check_msg_after.fetchone() is None

        # Deleting again returns False
        deleted_again = await SessionStore.delete_session(session, sid)
        assert deleted_again is False


def test_session_delete_api():
    """Verify DELETE /api/v1/sessions/{session_id} returns 204 then 404."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Create a session
    create_resp = client.post("/api/v1/sessions", json={"title": "API Delete Test"})
    assert create_resp.status_code == 201
    sid = create_resp.json()["id"]

    # 2. Delete it
    del_resp = client.delete(f"/api/v1/sessions/{sid}")
    assert del_resp.status_code == 204

    # 3. Verify 404 on GET
    get_resp = client.get(f"/api/v1/sessions/{sid}")
    assert get_resp.status_code == 404

    # 4. Verify 404 on subsequent DELETE
    del_resp_again = client.delete(f"/api/v1/sessions/{sid}")
    assert del_resp_again.status_code == 404
