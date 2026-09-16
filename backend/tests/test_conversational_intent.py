"""Tests for Conversational Intent Classification and QnA Routing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.intent import (
    IntentCategory,
    classify_conversational_intent,
)
from app.agent.orchestrator import QnAOrchestrator, QnAResult
from app.api.v1.artifacts import create_artifact
from app.artifacts.models import ArtifactCreateRequest
from app.sessions.models import MessageModel, SessionDetailModel


def test_casual_intents_classified_as_conversational():
    """Verify that generic greetings, gratitude, pleasantries, and farewells are conversational."""
    casual_queries = [
        "hi",
        "Hi!",
        "hello",
        "Hello there",
        "hey",
        "hey there",
        "good morning",
        "Good evening!",
        "how are you?",
        "how are you doing",
        "thanks",
        "Thank you so much!",
        "appreciate it",
        "bye",
        "goodbye",
        "see you later",
        "who are you?",
        "what can you do?",
        "cool",
        "okay, got it",
    ]
    for q in casual_queries:
        decision = classify_conversational_intent(q)
        assert decision.is_conversational is True, f"Expected '{q}' to be conversational, got {decision}"
        assert decision.category == IntentCategory.CONVERSATIONAL


def test_substantive_and_knowledge_queries_classified_as_knowledge():
    """Verify that domain questions, entity queries, and out-of-domain topics route to knowledge."""
    knowledge_queries = [
        "What is LNO?",
        "What does PLG mean?",
        "What does PMF mean?",
        "What did Shreyas Doshi say about pre-mortems?",
        "Tell me about pricing strategy",
        "How do companies improve retention?",
        "What is quantum chromodynamics?",
        "Explain growth loops",
        "Who is Elena Verna?",
        "Write a Ship 30 essay about product strategy",
    ]
    for q in knowledge_queries:
        decision = classify_conversational_intent(q)
        assert decision.is_conversational is False, f"Expected '{q}' to be knowledge, got {decision}"
        assert decision.category == IntentCategory.KNOWLEDGE


def test_mixed_greeting_and_knowledge_routes_to_knowledge():
    """Verify that a greeting combined with a substantive question routes to knowledge."""
    mixed_queries = [
        "Hi, what does Shreyas Doshi say about LNO?",
        "Hello! Can you explain the PMF framework?",
        "Hey there, what is Lenny's favorite interview question?",
        "Good morning, tell me about onboarding metrics.",
        "Thanks, now what does PLG mean?",
    ]
    for q in mixed_queries:
        decision = classify_conversational_intent(q)
        assert decision.is_conversational is False, f"Expected mixed '{q}' to be knowledge, got {decision}"
        assert decision.category == IntentCategory.KNOWLEDGE


@pytest.mark.asyncio
async def test_orchestrator_conversational_turn_bypasses_retrieval_and_pi():
    """Verify that a casual message routes to conversational response with zero retrieval and zero Pi calls."""
    mock_pi = MagicMock()
    mock_pi.execute_turn = AsyncMock()
    mock_pi.stream_turn = MagicMock()

    mock_retrieval = MagicMock()
    mock_retrieval.retrieve = AsyncMock()

    mock_gate = MagicMock()
    mock_gate.evaluate = MagicMock()

    mock_rewriter = MagicMock()
    mock_rewriter.rewrite = AsyncMock()

    orchestrator = QnAOrchestrator(
        pi_bridge=mock_pi,
        retrieval_engine=mock_retrieval,
        grounding_gate=mock_gate,
        rewriter=mock_rewriter,
    )

    mock_db = AsyncMock()
    mock_session = MagicMock()
    mock_session.id = "test-session-123"

    mock_asst_msg = MagicMock()
    mock_asst_msg.id = "asst-msg-1"

    with patch("app.agent.orchestrator.SessionStore") as mock_store, \
         patch("app.agent.orchestrator.get_generation_provider") as mock_get_provider:

        mock_store.get_session = AsyncMock(return_value=mock_session)
        mock_store.save_message = AsyncMock(return_value=mock_asst_msg)

        mock_provider = MagicMock()
        mock_provider.model_name = "test-model"
        mock_provider.generate = AsyncMock(return_value="Hello! I am the Lenny Growth Assistant. How can I help you today?")
        mock_get_provider.return_value = mock_provider

        result: QnAResult = await orchestrator.run_turn(
            session_id="test-session-123",
            user_content="Hi",
            db=mock_db,
        )

        # Assertions
        assert result.grounding["tier"] == "Conversational"
        assert result.grounding["can_synthesize"] is True
        assert len(result.sources) == 0
        assert "Hello!" in result.content

        # CRITICAL: Retrieval, Pi, and Rewriter were NEVER called
        mock_pi.execute_turn.assert_not_called()
        mock_retrieval.retrieve.assert_not_called()
        mock_gate.evaluate.assert_not_called()
        mock_rewriter.rewrite.assert_not_called()


@pytest.mark.asyncio
async def test_artifact_compilation_rejected_for_conversational_turn():
    """Verify that compile_artifact rejects a message with Conversational tier and zero sources."""
    mock_db = AsyncMock()
    from uuid import uuid4
    valid_sess_id = str(uuid4())
    valid_msg_id = str(uuid4())

    mock_session = MagicMock(spec=SessionDetailModel)
    mock_session.id = valid_sess_id
    mock_session.title = "Casual Chat"

    conv_msg = MagicMock(spec=MessageModel)
    conv_msg.id = valid_msg_id
    conv_msg.role = "assistant"
    conv_msg.content = "Hello! How can I help you today?"
    conv_msg.evidence_tier = "Conversational"
    conv_msg.sources = []

    mock_session.messages = [conv_msg]

    req = ArtifactCreateRequest(
        session_id=valid_sess_id,
        message_id=valid_msg_id,
        artifact_type="ship30_essay",
    )

    with patch("app.api.v1.artifacts.SessionStore.get_session", AsyncMock(return_value=mock_session)):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await create_artifact(request=req, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "grounded" in exc_info.value.detail.lower()
