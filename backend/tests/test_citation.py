"""Unit tests for post-generation citation validation."""

from datetime import date
import pytest

from app.agent.citation import CitationValidator
from app.retrieval.models import EvidenceItem, GroundingTier


def _make_evidence(
    chunk_id: str = "d3d0b6c8-4d68-4b9a-a21e-ec6ed2cd5c7c",
    guest: str = "Ada Chen Rekhi",
    title: str = "Finding Career Fulfillment",
    excerpt: str = "Explore or exploit are two modes of operating.",
    score: float = 0.82,
) -> EvidenceItem:
    return EvidenceItem(
        chunk_id=chunk_id,
        episode_id="ep-101",
        title=title,
        guest=guest,
        publication_date=date(2024, 2, 1),
        source_path="data/transcripts/ada_chen_rekhi/transcript.md",
        chunk_index=0,
        speaker=guest,
        content="Full transcript chunk text.",
        similarity_score=score,
        source_identifier=f"[{guest} - {title} #0]",
        excerpt=excerpt,
    )


def test_citation_validation_with_exact_uuid():
    """Verify response mentioning chunk UUID is validated and mapped."""
    chunk_id = "d3d0b6c8-4d68-4b9a-a21e-ec6ed2cd5c7c"
    item = _make_evidence(chunk_id=chunk_id)

    response_text = (
        f"In chunk {chunk_id}, Ada Chen Rekhi explains that founders must balance explore and exploit modes."
    )
    result = CitationValidator.validate_and_extract(
        response_text=response_text,
        retrieved_evidence=[item],
        can_synthesize=True,
        tier=GroundingTier.STRONG,
    )

    assert result.is_valid is True
    assert len(result.validated_sources) == 1
    assert result.validated_sources[0].chunk_id == chunk_id
    assert result.validated_sources[0].guest == "Ada Chen Rekhi"


def test_citation_validation_with_guest_name():
    """Verify response mentioning guest name without explicit UUID still links evidence."""
    item = _make_evidence()
    response_text = "According to Ada Chen Rekhi, you should evaluate if you feel like a boiling frog."

    result = CitationValidator.validate_and_extract(
        response_text=response_text,
        retrieved_evidence=[item],
        can_synthesize=True,
        tier=GroundingTier.LIMITED,
    )

    assert result.is_valid is True
    assert len(result.validated_sources) == 1
    assert result.validated_sources[0].guest == "Ada Chen Rekhi"


def test_citation_validation_detects_fabricated_uuid():
    """Verify response citing unknown/hallucinated chunk UUID is flagged."""
    item = _make_evidence(chunk_id="11111111-1111-1111-1111-111111111111")
    response_text = "According to chunk 99999999-9999-9999-9999-999999999999, growth is easy."

    result = CitationValidator.validate_and_extract(
        response_text=response_text,
        retrieved_evidence=[item],
        can_synthesize=True,
        tier=GroundingTier.STRONG,
    )

    assert result.is_valid is False
    assert len(result.warnings) > 0
    assert "fabricated" in result.warnings[0].lower() or "unknown" in result.warnings[0].lower()


def test_citation_validation_insufficient_refusal():
    """Verify refusal response on Insufficient tier has zero source references."""
    response_text = "I cannot find guidance on this topic in Lenny's Podcast transcripts."

    result = CitationValidator.validate_and_extract(
        response_text=response_text,
        retrieved_evidence=[],
        can_synthesize=False,
        tier=GroundingTier.INSUFFICIENT,
    )

    assert result.is_valid is True
    assert len(result.validated_sources) == 0
    assert len(result.warnings) == 0


def test_citation_validation_refusal_with_candidate_chunks_returns_zero_sources():
    """
    Regression Test (Issue 1):
    Verify that an out-of-domain refusal like quantum chromodynamics returns exactly ZERO sources,
    even if low-similarity candidate chunks are passed in retrieved_evidence.
    """
    unrelated_chunks = [
        _make_evidence(
            chunk_id="11111111-2222-3333-4444-555555555555",
            guest="Chandra Janakiraman",
            title="An operator's guide to product strategy",
            excerpt="Product strategy requires identifying the core lever.",
            score=0.7045,
        ),
        _make_evidence(
            chunk_id="22222222-3333-4444-5555-666666666666",
            guest="Jonny Miller",
            title="Managing nerves, anxiety, and burnout",
            excerpt="Nervous system mastery helps with burnout.",
            score=0.7014,
        ),
    ]

    refusal_text = "There is no information about quantum chromodynamics in Lenny's Podcast."

    # Test under both Insufficient tier and refusal text
    result_insufficient = CitationValidator.validate_and_extract(
        response_text=refusal_text,
        retrieved_evidence=unrelated_chunks,
        can_synthesize=False,
        tier=GroundingTier.INSUFFICIENT,
    )
    assert result_insufficient.is_valid is True
    assert len(result_insufficient.validated_sources) == 0
    assert len(result_insufficient.cited_chunk_ids) == 0

    # Test where response text is a refusal even if tier was Limited
    result_refusal_text = CitationValidator.validate_and_extract(
        response_text=refusal_text,
        retrieved_evidence=unrelated_chunks,
        can_synthesize=True,
        tier=GroundingTier.LIMITED,
    )
    assert result_refusal_text.is_valid is True
    assert len(result_refusal_text.validated_sources) == 0
    assert len(result_refusal_text.cited_chunk_ids) == 0


def test_citation_validation_unrelated_chunk_overlap_prevention():
    """
    Regression Test (Issue 3):
    Verify that candidate chunks without substantive vocabulary overlap or guest mention
    are not blindly attached as evidence.
    """
    chunk = _make_evidence(
        chunk_id="33333333-4444-5555-6666-777777777777",
        guest="Brian Balfour",
        title="Four Growth Loops",
        excerpt="Retention is the output of product market fit and acquisition loops.",
        score=0.72,
    )
    # Generic response that does not mention Balfour or any Balfour concepts
    unrelated_text = "The organization should consider various unrelated factors."

    result = CitationValidator.validate_and_extract(
        response_text=unrelated_text,
        retrieved_evidence=[chunk],
        can_synthesize=True,
        tier=GroundingTier.LIMITED,
    )
    assert len(result.validated_sources) == 0

