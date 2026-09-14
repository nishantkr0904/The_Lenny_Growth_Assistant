"""Unit tests for conversation-aware query rewriting."""

from datetime import datetime
from unittest.mock import AsyncMock
import pytest

from app.retrieval.rewriter import ConversationQueryRewriter
from app.sessions.models import MessageModel


def _make_msg(role: str, content: str) -> MessageModel:
    return MessageModel(
        id="msg-1",
        session_id="sess-1",
        role=role,
        content=content,
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_standalone_query_without_history():
    """Verify that turn 1 queries are normalized and unchanged."""
    rewriter = ConversationQueryRewriter()
    query = "  What are the key traits of great product managers?  "
    result = await rewriter.rewrite(query, history=[])
    assert result == "What are the key traits of great product managers?"


@pytest.mark.asyncio
async def test_standalone_query_with_history():
    """Verify that a standalone query with explicit entities is not modified unnecessarily."""
    rewriter = ConversationQueryRewriter()
    history = [
        _make_msg("user", "Tell me about Elena Verna on product-led growth."),
        _make_msg("assistant", "Elena Verna discusses PLG acquisition loops and freemium."),
    ]
    query = "According to Brian Chesky, how should founders manage design reviews?"
    result = await rewriter.rewrite(query, history=history)
    assert "Brian Chesky" in result


@pytest.mark.asyncio
async def test_followup_query_deterministic_rewrite():
    """Verify that pronoun follow-ups are deterministically anchored with prior entities."""
    rewriter = ConversationQueryRewriter()
    history = [
        _make_msg("user", "What does Ada Chen Rekhi say about finding career fulfillment?"),
        _make_msg(
            "assistant",
            "Ada Chen Rekhi explains the concept of explore vs exploit and overcoming the boiling frog syndrome.",
        ),
    ]
    query = "What about when she decided to leave?"
    result = await rewriter.rewrite(query, history=history)
    # Result must resolve the pronoun context with Ada Chen Rekhi
    assert "Ada Chen Rekhi" in result or "Ada" in result
    assert "leave" in result.lower()


@pytest.mark.asyncio
async def test_followup_query_provider_rewrite():
    """Verify that when a provider is available, it is invoked with context and prompt."""
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = "Ada Chen Rekhi decision to leave her job"

    rewriter = ConversationQueryRewriter(provider=mock_provider)
    history = [
        _make_msg("user", "What does Ada Chen Rekhi say about career exploration?"),
        _make_msg("assistant", "Ada emphasizes exploring options before exploiting them."),
    ]
    query = "Why did she make that choice?"
    result = await rewriter.rewrite(query, history=history)

    assert mock_provider.generate.called
    assert result == "Ada Chen Rekhi decision to leave her job"
