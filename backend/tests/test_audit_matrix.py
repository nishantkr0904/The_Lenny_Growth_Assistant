"""Automated regression test suite verifying universal production retrieval, grounding, and artifact fixes."""

import pytest
from datetime import date
from uuid import uuid4
from fastapi import HTTPException

from app.artifacts.compiler import ArtifactCompiler
from app.retrieval.engine import (
    VectorRetrievalEngine,
    compute_lexical_boost,
    extract_distinctive_terms,
    extract_potential_guest_mentions,
    extract_substantive_excerpt_terms,
)
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import EvidenceItem, GroundingTier
from app.retrieval.query import (
    collapse_spaced_acronyms,
    normalize_guest_typos,
    normalize_query,
)


def _make_chunk(guest: str, score: float, content: str, title: str = "Test Ep", idx: int = 0) -> EvidenceItem:
    return EvidenceItem(
        chunk_id=f"test-chunk-{idx}",
        episode_id="test-ep-1",
        title=title,
        guest=guest,
        publication_date=date(2024, 1, 1),
        source_path="/test/path.md",
        chunk_index=idx,
        speaker=guest,
        content=content,
        similarity_score=score,
        source_identifier=f"{guest} - {title} [Chunk #{idx}]",
        excerpt=content[:100],
    )


def test_grounding_tier_from_str():
    """Verify canonical case-insensitive parsing of GroundingTier."""
    assert GroundingTier.from_str("Strong") == GroundingTier.STRONG
    assert GroundingTier.from_str("strong") == GroundingTier.STRONG
    assert GroundingTier.from_str("LIMITED") == GroundingTier.LIMITED
    assert GroundingTier.from_str("limited") == GroundingTier.LIMITED
    assert GroundingTier.from_str("Conflicting") == GroundingTier.CONFLICTING
    assert GroundingTier.from_str("conflicting") == GroundingTier.CONFLICTING
    assert GroundingTier.from_str("Insufficient") == GroundingTier.INSUFFICIENT
    assert GroundingTier.from_str("insufficient") == GroundingTier.INSUFFICIENT
    assert GroundingTier.from_str(None) == GroundingTier.INSUFFICIENT
    assert GroundingTier.from_str("unknown_tier") == GroundingTier.INSUFFICIENT


def test_spaced_acronym_collapsing():
    """Verify general spaced and slash-delimited acronym normalization across 2-5 letter acronyms."""
    assert collapse_spaced_acronyms("What does L N O mean?") == "What does LNO mean?"
    assert collapse_spaced_acronyms("What does L / N / O mean?") == "What does LNO mean?"
    assert collapse_spaced_acronyms("How does P M F work?") == "How does PMF work?"
    assert collapse_spaced_acronyms("Explain P L G strategy") == "Explain PLG strategy"
    assert collapse_spaced_acronyms("Setting O K R s for Q3") == "Setting OKRs for Q3"


def test_fuzzy_guest_typo_normalization():
    """Verify fuzzy guest matching with length constraint corrects typos without corrupting English vocabulary."""
    # Corrects genuine guest typos
    assert normalize_guest_typos("What is Shreyash Doshi's framework?") == "What is Shreyas Doshi's framework?"
    assert normalize_guest_typos("What does Brian Cheskey say?") == "What does Brian Chesky say?"
    assert normalize_guest_typos("Advice from Stuart Butterfield") == "Advice from Stewart Butterfield"
    assert normalize_guest_typos("Onboarding with Lauren Isford") == "Onboarding with Lauryn Isford"

    # Preserves normal vocabulary words (no false positives)
    assert normalize_guest_typos("product-market fit") == "product-market fit"
    assert normalize_guest_typos("traits of great product managers") == "traits of great product managers"
    assert normalize_guest_typos("when to leave your job") == "when to leave your job"
    assert normalize_guest_typos("reducing churn rate") == "reducing churn rate"
    assert normalize_guest_typos("quantum chromodynamics") == "quantum chromodynamics"


def test_lexical_boost_uppercase_acronyms():
    """Verify high-specificity uppercase acronyms receive +0.20 boost without boosting unrelated queries."""
    content_with_lno = "Shreyas: The LNO framework divides work into Leverage, Neutral, and Overhead."
    content_without = "Jonny: Nervous system mastery helps with burnout."

    terms_lno = ["LNO"]
    terms_empty = []

    # Query with acronym on chunk with acronym
    boost_lno = compute_lexical_boost(content_with_lno, "Shreyas Doshi", "Art of PM", terms_lno, ["Shreyas Doshi"])
    assert boost_lno >= 0.20

    # Query without acronym or unrelated query
    boost_unrelated = compute_lexical_boost(content_without, "Jonny Miller", "Burnout", terms_empty, [])
    assert boost_unrelated == 0.0


def test_excerpt_selection_centers_on_domain_keywords():
    """Verify evidence excerpt is centered around substantive query terms instead of dialogue preamble."""
    content = (
        "[Episode: Mastering Onboarding]\n\n"
        "Lenny: Welcome back to the podcast. Today I'm joined by Lauryn Isford, head of growth. "
        "We are going to talk about a lot of things. But first, let's thank our sponsors. "
        "Lauryn: When thinking about onboarding, you have to realize that activation is the core milestone. "
        "If users do not experience value in their first 5 minutes, retention drops to zero. "
        "Lenny: That's a profound insight."
    )
    terms = ["onboarding", "activation"]
    excerpt = VectorRetrievalEngine._create_excerpt(content, terms=terms, max_chars=180)

    # Must contain the substantive discussion of onboarding/activation
    assert "onboarding" in excerpt.lower()
    assert "activation" in excerpt.lower()
    # Must NOT start with dialogue preamble about sponsors
    assert "sponsors" not in excerpt
    # Verbatim substring verification (no invented text)
    clean_content = " ".join(content.split())
    # Excerpt without ellipses must exist in content
    inner = excerpt.strip(".").strip()
    assert inner in clean_content


def test_artifact_compiler_zero_hardcoded_substantive_claims():
    """Verify Markdown research brief derives all substantive claims dynamically from content."""
    title = "Customer Discovery Playbook"
    topic = "Discovery"
    content = "Continuous user interviews uncover unarticulated pain points before sprint planning."
    sources = [
        {
            "chunk_id": str(uuid4()),
            "title": "Interviewing Customers",
            "guest": "Teresa Torres",
            "quoted_excerpt": "Do at least one interview every week.",
            "similarity_score": 0.88,
        }
    ]

    brief = ArtifactCompiler.compile_markdown_brief(title, topic, content, sources)

    # Structure & provenance verified
    assert "# Customer Discovery Playbook" in brief
    assert "## Executive Summary" in brief
    assert "## Key Strategic Insights" in brief
    assert "## Source Citations & Provenance" in brief
    assert "Teresa Torres" in brief

    # No hardcoded static boilerplate
    assert "vanity expansion" not in brief
    assert "scaling spend" not in brief
    assert "customer discovery." not in brief  # Old static bullet


def test_ship30_compiler_zero_leaked_framework_concepts():
    """Verify Ship 30 essay takeaways are universal and do not leak LNO or boiling frog concepts."""
    title = "Pricing Strategy Deep Dive"
    topic = "SaaS Pricing"
    content = "Pricing should be aligned with customer value metrics, not competitor benchmarks."
    sources = [
        {
            "chunk_id": str(uuid4()),
            "title": "Pricing Models",
            "guest": "Patrick Campbell",
            "quoted_excerpt": "Value metric is the single most important aspect of monetization.",
            "similarity_score": 0.85,
        }
    ]

    essay = ArtifactCompiler.compile_ship30_essay(title, topic, content, sources)

    assert "Patrick Campbell" in essay
    assert "Value metric" in essay
    # Zero hardcoded LNO / Boiling Frog leakage
    assert "high-leverage efforts belong versus overhead" not in essay
    assert "boiling frog" not in essay.lower()
    assert "exploration vs exploitation" not in essay.lower()


def test_grounding_gate_guest_canonicalization():
    """Verify multi-appearance guests (e.g. 'Shreyas Doshi' and 'Shreyas Doshi Live') do not trigger conflict."""
    gate = GroundingGate()
    evidence = [
        _make_chunk(
            guest="Shreyas Doshi",
            score=0.88,
            title="The Art of PM",
            content="The LNO framework is essential. Instead of treating all tasks equally, categorize them.",
            idx=1,
        ),
        _make_chunk(
            guest="Shreyas Doshi Live",
            score=0.85,
            title="Shreyas Live Q&A",
            content="Rather than spending 10 hours on an O task, do it in 30 minutes.",
            idx=2,
        ),
    ]

    decision = gate.triage(evidence)
    # Must NOT be conflicting (they are the same speaker)
    assert decision.tier != GroundingTier.CONFLICTING
    assert decision.tier in (GroundingTier.STRONG, GroundingTier.LIMITED)
