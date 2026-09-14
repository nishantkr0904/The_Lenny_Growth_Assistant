"""Tests for the production Pi Coding Agent bridge client and orchestrator routing."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agent.citation import CitationValidationResult
from app.agent.orchestrator import QnAOrchestrator, QnAResult
from app.agent.pi_bridge import PiBridgeClient, PiTurnResult
from app.retrieval.models import GroundingTier


@pytest.mark.asyncio
async def test_pi_bridge_ping():
    """Verify Pi bridge client pings the daemon process successfully."""
    client = PiBridgeClient.get_instance()
    # Ping should start daemon if not running and return status
    res = await client.ping()
    assert res.get("status") == "ok"
    assert res.get("agent") == "pi-coding-agent"
    assert res.get("version") == "0.85.1"


@pytest.mark.asyncio
async def test_orchestrator_routes_through_pi_bridge():
    """Verify QnAOrchestrator delegates turn execution to PiBridgeClient."""
    mock_bridge = MagicMock(spec=PiBridgeClient)
    mock_bridge.execute_turn = AsyncMock(
        return_value=PiTurnResult(
            content="Ada Chen Rekhi explains explore vs exploit modes.",
            tier="Strong",
            top_score=0.82,
            can_synthesize=True,
            model_used="ollama/llama3.1:8b",
            selected_evidence=[
                {
                    "chunk_id": "c1111111-1111-1111-1111-111111111111",
                    "episode_id": "e1111111-1111-1111-1111-111111111111",
                    "title": "Finding Career Fulfillment",
                    "guest": "Ada Chen Rekhi",
                    "publication_date": "2023-04-21",
                    "source_path": "episodes/ada-chen-rekhi/transcript.md",
                    "chunk_index": 14,
                    "speaker": "Ada Chen Rekhi",
                    "content": "Explore or exploit are two modes of operating in your career.",
                    "similarity_score": 0.82,
                }
            ],
            duration_ms=450,
        )
    )

    mock_db = AsyncMock()
    # Mock session and message storage
    with patch("app.sessions.store.SessionStore.get_session", AsyncMock(return_value=MagicMock(id="s1"))), \
         patch("app.sessions.store.SessionStore.save_message", AsyncMock(return_value=MagicMock(id="m1"))), \
         patch("app.sessions.store.SessionStore.get_recent_messages", AsyncMock(return_value=[MagicMock(role="user", content="What did Ada say?")])), \
         patch("app.sessions.store.SessionStore.save_source_references", AsyncMock()):

        orchestrator = QnAOrchestrator(pi_bridge=mock_bridge)
        result = await orchestrator.run_turn(
            session_id="s1",
            user_content="What did Ada say about career modes?",
            db=mock_db,
        )

        # 1. Assert PiBridge was invoked
        mock_bridge.execute_turn.assert_called_once()
        call_kwargs = mock_bridge.execute_turn.call_args.kwargs
        assert call_kwargs["user_prompt"] == "What did Ada say about career modes?"

        # 2. Assert QnAResult contains Pi content and metadata
        assert "Ada Chen Rekhi" in result.content
        assert result.grounding["tier"] == "Strong"
        assert result.grounding["agent"] == "pi-coding-agent"
        assert result.model_used == "ollama/llama3.1:8b"


@pytest.mark.asyncio
async def test_orchestrator_insufficient_refusal_via_pi():
    """Verify that Insufficient grounding through Pi produces honest refusal and 0 sources."""
    mock_bridge = MagicMock(spec=PiBridgeClient)
    mock_bridge.execute_turn = AsyncMock(
        return_value=PiTurnResult(
            content="I could not find guidance on this topic in Lenny's Podcast transcripts.",
            tier="Insufficient",
            top_score=0.45,
            can_synthesize=False,
            model_used="ollama/llama3.1:8b",
            selected_evidence=[],
            duration_ms=200,
        )
    )

    mock_db = AsyncMock()
    with patch("app.sessions.store.SessionStore.get_session", AsyncMock(return_value=MagicMock(id="s2"))), \
         patch("app.sessions.store.SessionStore.save_message", AsyncMock(return_value=MagicMock(id="m2"))), \
         patch("app.sessions.store.SessionStore.get_recent_messages", AsyncMock(return_value=[MagicMock(role="user", content="quantum physics")])), \
         patch("app.sessions.store.SessionStore.save_source_references", AsyncMock()) as mock_save_sources:

        orchestrator = QnAOrchestrator(pi_bridge=mock_bridge)
        result = await orchestrator.run_turn(
            session_id="s2",
            user_content="Explain quantum gravity in lattice gauge theory",
            db=mock_db,
        )

        assert result.grounding["tier"] == "Insufficient"
        assert result.grounding["can_synthesize"] is False
        assert len(result.sources) == 0
        mock_save_sources.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_streaming_via_pi_bridge():
    """Verify QnAOrchestrator.stream_turn yields thinking, evidence, delta, and done events from Pi."""
    async def mock_stream_turn(**kwargs):
        yield {"event": "tool_call", "data": {"name": "transcript_retrieval", "query": "Ada Chen Rekhi"}}
        yield {"event": "evidence", "data": {"tier": "Strong", "top_score": 0.81, "chunk_count": 3, "can_synthesize": True}}
        yield {"event": "delta", "data": {"delta": "Ada "}}
        yield {"event": "delta", "data": {"delta": "recommends "}}
        yield {"event": "delta", "data": {"delta": "explore mode."}}
        yield {
            "event": "result",
            "data": PiTurnResult(
                content="Ada recommends explore mode.",
                tier="Strong",
                top_score=0.81,
                can_synthesize=True,
                model_used="ollama/llama3.1:8b",
                selected_evidence=[],
            ),
        }

    mock_bridge = MagicMock(spec=PiBridgeClient)
    mock_bridge.stream_turn = mock_stream_turn

    mock_db = AsyncMock()
    with patch("app.sessions.store.SessionStore.get_session", AsyncMock(return_value=MagicMock(id="s3"))), \
         patch("app.sessions.store.SessionStore.save_message", AsyncMock(return_value=MagicMock(id="m3"))), \
         patch("app.sessions.store.SessionStore.get_recent_messages", AsyncMock(return_value=[])), \
         patch("app.sessions.store.SessionStore.save_source_references", AsyncMock()):

        orchestrator = QnAOrchestrator(pi_bridge=mock_bridge)
        events = []
        async for chunk in orchestrator.stream_turn("s3", "What did Ada say?", mock_db):
            events.append(chunk)

        body = "".join(events)
        assert "event: thinking" in body
        assert "event: evidence" in body
        assert "event: delta" in body
        assert "event: done" in body
