"""Unit and integration tests for Pi agent retrieval tool adapter."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.agent.retrieval_tool import execute_transcript_retrieval, format_evidence_for_agent
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import (
    EvidenceItem,
    GroundingDecision,
    GroundingTier,
    RetrievalResponse,
    SourceDiversity,
)


def _make_evidence(
    guest: str = "Ada Chen Rekhi",
    score: float = 0.85,
    title: str = "Finding Career Fulfillment",
    content: str = "When you feel like a boiling frog, it is time to explore.",
    idx: int = 0,
) -> EvidenceItem:
    """Helper to generate deterministic EvidenceItem fixtures."""
    return EvidenceItem(
        chunk_id=f"chunk-{100 + idx}",
        episode_id="ep-ada-1",
        title=title,
        guest=guest,
        publication_date=date(2024, 2, 1),
        source_path="data/transcripts/ada_chen_rekhi/transcript.md",
        chunk_index=idx,
        speaker=guest,
        content=content,
        similarity_score=score,
        source_identifier=f"[{guest} - {title} #{idx}]",
        excerpt=content[:60],
    )


# ============================================================================
# 1. format_evidence_for_agent Tests
# ============================================================================

def test_format_evidence_insufficient_refusal():
    """Verify that Insufficient grounding generates an explicit refusal XML block."""
    decision = GroundingDecision(
        tier=GroundingTier.INSUFFICIENT,
        can_synthesize=False,
        top_score=0.42,
        confidence_score=0.35,
        reason="Top similarity score 0.4200 is below limited threshold 0.6500",
        source_diversity=SourceDiversity(unique_episodes=0, unique_guests=0, episodes=[], guests=[]),
        selected_evidence=[],
    )
    response = RetrievalResponse(
        query="What is quantum chromodynamics?",
        normalized_query="what is quantum chromodynamics",
        decision=decision,
        evidence=[],
    )

    xml = format_evidence_for_agent(response)
    assert '<retrieved_evidence status="INSUFFICIENT"' in xml
    assert 'can_synthesize="false"' in xml
    assert 'tier="Insufficient"' in xml
    assert "NO_GROUNDED_EVIDENCE" in xml
    assert "strictly FORBIDDEN from answering this question using general training knowledge" in xml
    assert "explicitly inform the user that this topic is not discussed" in xml


def test_format_evidence_strong():
    """Verify that Strong evidence generates chunk blocks with citation metadata."""
    item = _make_evidence(score=0.86)
    decision = GroundingDecision(
        tier=GroundingTier.STRONG,
        can_synthesize=True,
        top_score=0.86,
        confidence_score=0.86,
        reason="Evidence qualifies for Strong grounding tier",
        source_diversity=SourceDiversity(
            unique_episodes=1, unique_guests=1, episodes=["Finding Career Fulfillment"], guests=["Ada Chen Rekhi"]
        ),
        selected_evidence=[item],
    )
    response = RetrievalResponse(
        query="When is it time to leave your job?",
        normalized_query="when is it time to leave your job",
        decision=decision,
        evidence=[item],
    )

    xml = format_evidence_for_agent(response)
    assert '<retrieved_evidence status="VALID"' in xml
    assert 'can_synthesize="true"' in xml
    assert 'tier="Strong"' in xml
    assert '<chunk id="chunk-100"' in xml
    assert 'guest="Ada Chen Rekhi"' in xml
    assert 'episode="Finding Career Fulfillment"' in xml
    assert 'citation="[Ada Chen Rekhi - Finding Career Fulfillment #0]"' in xml
    assert "boiling frog" in xml
    assert "<system_directive>" in xml
    assert "Attribute factual claims to the speaker/guest" in xml


def test_format_evidence_conflicting():
    """Verify that Conflicting evidence includes the conflict directive block."""
    item1 = _make_evidence(guest="Guest A", score=0.82, idx=0)
    item2 = _make_evidence(guest="Guest B", score=0.80, idx=1)
    decision = GroundingDecision(
        tier=GroundingTier.CONFLICTING,
        can_synthesize=True,
        top_score=0.82,
        confidence_score=0.75,
        reason="Strong evidence with deterministic conflicting viewpoints",
        source_diversity=SourceDiversity(
            unique_episodes=2, unique_guests=2, episodes=["Ep A", "Ep B"], guests=["Guest A", "Guest B"]
        ),
        selected_evidence=[item1, item2],
    )
    response = RetrievalResponse(
        query="Should you hire specialists or generalists?",
        normalized_query="should you hire specialists or generalists",
        decision=decision,
        evidence=[item1, item2],
    )

    xml = format_evidence_for_agent(response)
    assert '<retrieved_evidence status="VALID"' in xml
    assert 'tier="Conflicting"' in xml
    assert "<conflict_directive>" in xml
    assert "Multiple divergent viewpoints exist across distinct guests" in xml


# ============================================================================
# 2. execute_transcript_retrieval Tests
# ============================================================================

@pytest.mark.asyncio
async def test_execute_transcript_retrieval_integration():
    """Verify execute_transcript_retrieval coordinates engine, gate, and formatting."""
    mock_engine = AsyncMock()
    mock_db = AsyncMock()
    evidence_item = _make_evidence(score=0.85)
    mock_engine.search.return_value = [evidence_item]

    result = await execute_transcript_retrieval(
        query="  when to leave   your job?  ",
        top_k=3,
        db=mock_db,
        engine=mock_engine,
        gate=GroundingGate(),
    )

    # Engine called with normalized query and top_k
    mock_engine.search.assert_called_once_with(
        query="when to leave your job?",
        top_k=3,
        db=mock_db,
    )

    assert result["status"] == "success"
    assert result["tier"] == "Strong"
    assert result["can_synthesize"] is True
    assert result["top_score"] == 0.85
    assert result["chunk_count"] == 1
    assert "xml_content" in result
    assert '<retrieved_evidence status="VALID"' in result["xml_content"]
    assert "Ada Chen Rekhi" in result["xml_content"]


@pytest.mark.asyncio
async def test_execute_transcript_retrieval_insufficient():
    """Verify execute_transcript_retrieval handles empty or low-scoring evidence."""
    mock_engine = AsyncMock()
    mock_db = AsyncMock()
    mock_engine.search.return_value = []

    result = await execute_transcript_retrieval(
        query="quantum string theory",
        top_k=5,
        db=mock_db,
        engine=mock_engine,
        gate=GroundingGate(),
    )

    assert result["status"] == "success"
    assert result["tier"] == "Insufficient"
    assert result["can_synthesize"] is False
    assert result["top_score"] == 0.0
    assert result["chunk_count"] == 0
    assert "NO_GROUNDED_EVIDENCE" in result["xml_content"]
