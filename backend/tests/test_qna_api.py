"""API endpoint tests for sessions and grounded Q&A messaging."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.agent.orchestrator import QnAResult
from app.api.v1.sessions import get_orchestrator
from app.main import app
from app.sessions.models import SourceReferenceItem


@pytest.fixture
def client():
    return TestClient(app)


def test_create_and_get_session(client):
    """Verify creating a session and fetching its details."""
    res = client.post("/api/v1/sessions", json={"title": "Strategic Growth Session"})
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["title"] == "Strategic Growth Session"
    assert data["message_count"] == 0

    session_id = data["id"]
    get_res = client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == session_id
    assert detail["title"] == "Strategic Growth Session"
    assert isinstance(detail["messages"], list)


def test_get_nonexistent_session(client):
    """Verify requesting a missing session returns 404."""
    res = client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_send_empty_message_rejected(client):
    """Verify sending an empty message is rejected with 422."""
    res = client.post(
        "/api/v1/sessions/11111111-1111-1111-1111-111111111111/messages",
        json={"content": "   ", "stream": False},
    )
    assert res.status_code == 422


def test_send_message_json_response(client):
    """Verify sending a message with stream=False returns structured QnAResult."""
    session_res = client.post("/api/v1/sessions", json={"title": "Q&A Test"})
    session_id = session_res.json()["id"]

    mock_orchestrator = MagicMock()
    mock_result = QnAResult(
        session_id=session_id,
        message_id="msg-101",
        role="assistant",
        content="Ada Chen Rekhi emphasizes exploration before exploitation.",
        grounding={
            "tier": "Strong",
            "can_synthesize": True,
            "top_score": 0.85,
            "confidence_score": 0.85,
            "reason": "Strong evidence found.",
        },
        sources=[
            SourceReferenceItem(
                chunk_id="chunk-1",
                episode_id="ep-1",
                title="Career Fulfillment",
                guest="Ada Chen Rekhi",
                similarity_score=0.85,
                quoted_excerpt="Explore or exploit modes.",
            )
        ],
        latency_ms=350,
        model_used="ollama/llama3.1:8b",
    )
    mock_orchestrator.run_turn = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    try:
        res = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "What does Ada say about career exploration?", "stream": False},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == session_id
        assert data["role"] == "assistant"
        assert "Ada Chen Rekhi" in data["content"]
        assert data["grounding"]["tier"] == "Strong"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["guest"] == "Ada Chen Rekhi"
        assert data["latency_ms"] == 350
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)


def test_send_message_sse_streaming(client):
    """Verify sending a message with stream=True returns text/event-stream."""
    session_res = client.post("/api/v1/sessions", json={"title": "Streaming Test"})
    session_id = session_res.json()["id"]

    async def fake_stream(*args, **kwargs):
        yield 'event: thinking\ndata: {"step": "retrieval"}\n\n'
        yield 'event: evidence\ndata: {"tier": "Strong", "can_synthesize": true}\n\n'
        yield 'event: delta\ndata: {"text": "According to Lenny"}\n\n'
        yield 'event: done\ndata: {"message_id": "msg-1", "can_synthesize": true}\n\n'

    mock_orchestrator = MagicMock()
    mock_orchestrator.stream_turn = fake_stream

    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    try:
        res = client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"content": "What is product growth?", "stream": True},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        body = res.text
        assert "event: thinking" in body
        assert "event: evidence" in body
        assert "event: delta" in body
        assert "event: done" in body
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
