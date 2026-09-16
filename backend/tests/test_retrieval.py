"""Unit and integration tests for vector retrieval, query normalization, and GroundingGate triage."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app
from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import EvidenceItem, GroundingTier, RetrievalResponse
from app.retrieval.query import normalize_query


# ============================================================================
# Fixtures & Test Helpers
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    session.execute.return_value = mock_result
    return session


def _make_evidence(
    guest: str = "Test Guest",
    score: float = 0.85,
    title: str = "Test Episode",
    content: str = "Test transcript chunk content.",
    idx: int = 0,
) -> EvidenceItem:
    """Helper to generate deterministic EvidenceItem fixtures."""
    return EvidenceItem(
        chunk_id=f"chunk-{100 + idx}",
        episode_id="ep-1",
        title=title,
        guest=guest,
        publication_date=date(2024, 1, 1),
        source_path=f"data/transcripts/{guest.lower().replace(' ', '_')}/transcript.md",
        chunk_index=idx,
        speaker=guest,
        content=content,
        similarity_score=score,
        source_identifier=f"[{guest} - {title} #{idx}]",
        excerpt=content[:80],
    )


# ============================================================================
# 1. Query Normalization Tests
# ============================================================================

def test_query_normalization_strips_whitespace():
    """Verify extraneous whitespace, newlines, and tabs are collapsed."""
    raw = "  how   to calculate \n\t  retention?   "
    normalized = normalize_query(raw)
    assert normalized == "how to calculate retention?"


def test_query_normalization_normalizes_quotes_and_unicode():
    """Verify smart quotes and special unicode spaces are normalized."""
    raw = "“What is ‘product-market fit’?”"
    normalized = normalize_query(raw)
    assert normalized == '"What is \'product-market fit\'?"'


def test_query_normalization_rejects_empty():
    """Verify empty or whitespace-only queries raise ValueError."""
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        normalize_query("")

    with pytest.raises(ValueError, match="Search query cannot be empty"):
        normalize_query("   \t \n  ")


# ============================================================================
# 2. GroundingGate Deterministic Triage Tests
# ============================================================================

def test_grounding_gate_empty_evidence():
    """Verify empty evidence list triggers Insufficient tier with can_synthesize=False."""
    gate = GroundingGate()
    decision = gate.triage([])

    assert decision.tier == GroundingTier.INSUFFICIENT
    assert decision.can_synthesize is False
    assert decision.confidence_score == 0.0
    assert decision.selected_evidence == []
    assert "No relevant evidence found" in decision.reason
    assert decision.source_diversity.episode_count == 0


def test_grounding_gate_insufficient_tier_low_score():
    """Verify top score below 0.65 triggers Insufficient tier with selected_evidence cleared."""
    gate = GroundingGate()
    evidence = [
        _make_evidence(score=0.55, content="Irrelevant discussion about cooking recipes."),
        _make_evidence(score=0.42, content="Random noise."),
    ]
    decision = gate.triage(evidence)

    assert decision.tier == GroundingTier.INSUFFICIENT
    assert decision.can_synthesize is False
    assert decision.confidence_score == 0.55
    assert decision.selected_evidence == []
    assert "below minimum required threshold" in decision.reason


def test_grounding_gate_limited_tier():
    """Verify score between 0.65 and 0.78 triggers Limited tier."""
    gate = GroundingGate()
    evidence = [
        _make_evidence(score=0.72, content="Moderate discussion on user feedback loops."),
        _make_evidence(score=0.67, content="Brief mention of surveys."),
    ]
    decision = gate.triage(evidence)

    assert decision.tier == GroundingTier.LIMITED
    assert decision.can_synthesize is True
    assert decision.confidence_score == 0.648  # 0.72 * 0.9 = 0.648
    assert len(decision.selected_evidence) == 2
    assert "moderate relevance" in decision.reason


def test_grounding_gate_strong_tier():
    """Verify score >= 0.78 triggers Strong tier."""
    gate = GroundingGate()
    evidence = [
        _make_evidence(score=0.88, content="Direct answer on cohort retention analysis."),
        _make_evidence(score=0.81, content="Deep dive on churn rates."),
    ]
    decision = gate.triage(evidence)

    assert decision.tier == GroundingTier.STRONG
    assert decision.can_synthesize is True
    assert decision.confidence_score == 0.88
    assert len(decision.selected_evidence) == 2
    assert "High-relevance evidence" in decision.reason


def test_grounding_gate_single_episode_can_be_strong():
    """
    CRITICAL INVARIANT: Episode count is a source-diversity signal,
    NOT a mandatory condition for Strong tier.
    """
    gate = GroundingGate()
    evidence = [
        _make_evidence(guest="Elena Verna", title="B2B Growth", score=0.85, idx=0),
        _make_evidence(guest="Elena Verna", title="B2B Growth", score=0.82, idx=1),
    ]
    decision = gate.triage(evidence)

    assert decision.tier == GroundingTier.STRONG
    assert decision.can_synthesize is True
    assert decision.source_diversity.episode_count == 1
    assert decision.source_diversity.guests == ["Elena Verna"]


def test_grounding_gate_conflicting_tier():
    """
    Verify that when evidence score >= 0.78 spans distinct guests with
    explicit opposing/divergent perspectives, Conflicting tier is assigned.
    """
    gate = GroundingGate()
    evidence = [
        _make_evidence(
            guest="Guest A",
            score=0.85,
            title="PLG is King",
            content="Product-led growth is the only sustainable strategy. However, sales-led is dead.",
            idx=0,
        ),
        _make_evidence(
            guest="Guest B",
            score=0.82,
            title="Enterprise Sales Wins",
            content="On the contrary, PLG fails in enterprise. Sales-led growth is fundamentally superior.",
            idx=1,
        ),
    ]
    decision = gate.triage(evidence)

    assert decision.tier == GroundingTier.CONFLICTING
    assert decision.can_synthesize is True
    assert len(decision.selected_evidence) == 2
    assert "multiple distinct viewpoints were detected" in decision.reason
    assert "Guest A" in decision.reason
    assert "Guest B" in decision.reason


# ============================================================================
# 3. Vector Retrieval Engine Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vector_retrieval_engine_search_mapping():
    """Verify VectorRetrievalEngine executes pgvector query and maps columns to EvidenceItem."""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()

    # Mock row returned from pgvector <=> query
    mock_row = (
        "chunk-uuid-42",  # chunk_id
        "episode-uuid-1",  # episode_id
        "Building Products",  # title
        "Shreyas Doshi",  # guest
        date(2023, 5, 10),  # publication_date
        "data/transcripts/shreyas_doshi/transcript.md",  # source_path
        3,  # chunk_index
        "Shreyas Doshi",  # speaker
        "High impact vs high effort matrix analysis.",  # content
        0.8654,  # similarity_score
    )
    mock_result.fetchall.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    engine = VectorRetrievalEngine()
    with patch.object(engine.embedding_provider, "embed_text", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.05] * 768

        evidence = await engine.search("how to prioritize features", top_k=5, db=mock_db)

        assert len(evidence) == 1
        item = evidence[0]
        assert item.chunk_id == "chunk-uuid-42"
        assert item.episode_id == "episode-uuid-1"
        assert item.title == "Building Products"
        assert item.guest == "Shreyas Doshi"
        assert item.chunk_index == 3
        assert item.similarity_score == 0.8654
        assert "High impact" in item.content

        # Verify embed_text was invoked
        mock_embed.assert_awaited_once_with("how to prioritize features")

        # Verify DB execute called
        assert mock_db.execute.called
        sql_call = mock_db.execute.call_args[0][0]
        sql_text = str(sql_call)
        assert "<=>" in sql_text
        assert "ORDER BY c.embedding <=> :query_vector ASC" in sql_text


# ============================================================================
# 4. API Route Tests (/api/v1/retrieval/search and /preview)
# ============================================================================

def test_retrieval_search_empty_query_rejected():
    """Verify 422 error on empty query."""
    client = TestClient(app)
    response = client.post("/api/v1/retrieval/search", json={"query": "   \t  "})
    assert response.status_code == 422
    assert "Search query cannot be empty" in response.json()["detail"]


def test_retrieval_search_with_mocked_engine(mock_db):
    """Verify 200 OK and response contract for /api/v1/retrieval/search."""
    app.dependency_overrides[get_db] = lambda: mock_db

    sample_evidence = [
        _make_evidence(score=0.84, content="Retention is king.")
    ]

    with patch.object(VectorRetrievalEngine, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_evidence

        client = TestClient(app)
        response = client.post(
            "/api/v1/retrieval/search",
            json={"query": "retention metrics", "top_k": 3},
        )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "retention metrics"
        assert data["normalized_query"] == "retention metrics"
        assert data["decision"]["tier"] == "Strong"
        assert data["decision"]["can_synthesize"] is True
        assert data["decision"]["confidence_score"] == 0.84
        assert len(data["evidence"]) == 1
        assert data["evidence"][0]["similarity_score"] == 0.84


def test_retrieval_preview_endpoint_alias(mock_db):
    """Verify /preview alias behaves identically to /search."""
    app.dependency_overrides[get_db] = lambda: mock_db

    sample_evidence = [
        _make_evidence(score=0.70, content="Customer interviews are important.")
    ]

    with patch.object(VectorRetrievalEngine, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_evidence

        client = TestClient(app)
        response = client.post(
            "/api/v1/retrieval/preview",
            json={"query": "customer interview advice", "top_k": 2},
        )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["decision"]["tier"] == "Limited"
        assert data["decision"]["can_synthesize"] is True
        assert data["decision"]["confidence_score"] == 0.63


# ============================================================================
# 5. Live End-to-End Integration Verification against Ingested Transcripts
# ============================================================================

@pytest.mark.asyncio
async def test_live_retrieval_supported_query():
    """
    Live query against PostgreSQL and Ollama with real ingested transcripts.
    Verifies that real queries return ranked chunks with similarity scores.
    """
    from app.db.session import engine as db_engine

    retrieval_engine = VectorRetrievalEngine()
    gate = GroundingGate()

    async with db_engine.connect() as conn:
        evidence = await retrieval_engine.search(
            query="Feeling stuck? Here's how to know when it's time to leave your job | Ada Chen Rekhi",
            top_k=3,
            db=conn,
        )

    assert len(evidence) <= 3
    assert len(evidence) > 0

    # Scores must be valid cosine similarities in [0, 1] and strictly descending
    scores = [item.similarity_score for item in evidence]
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores == sorted(scores, reverse=True)

    # Chunks have required metadata
    first = evidence[0]
    assert first.title is not None
    assert first.guest is not None
    assert len(first.content) > 0

    # Grounding triage works on live result
    decision = gate.triage(evidence)
    assert decision.tier == GroundingTier.STRONG
    assert decision.can_synthesize is True
    assert decision.confidence_score == first.similarity_score
    assert len(decision.selected_evidence) > 0


@pytest.mark.asyncio
async def test_live_retrieval_insufficient_query():
    """
    Live query with an obviously unsupported out-of-domain topic.
    Verifies that Insufficient tier is triggered and synthesis is disallowed.
    """
    from app.db.session import engine as db_engine

    retrieval_engine = VectorRetrievalEngine()
    gate = GroundingGate()

    # Query far outside Lenny's podcast domain
    async with db_engine.connect() as conn:
        evidence = await retrieval_engine.search(
            query="quantum chromodynamics gluon plasma hadronization in lattice gauge theory",
            top_k=3,
            db=conn,
        )

    # Even if pgvector returns nearest chunks, their similarity must be evaluated by the gate
    decision = gate.triage(evidence)
    # The score for this topic should fall below the limited threshold (0.65)
    assert decision.tier == GroundingTier.INSUFFICIENT
    assert decision.can_synthesize is False
    assert decision.selected_evidence == []


# ============================================================================
# 6. Targeted Regression Tests for Phonetic Normalization & Domain Term Retrieval
# ============================================================================

def test_query_normalization_artifact_meta_patterns():
    """Verify artifact generation prompt prefixes are stripped to avoid vector dilution."""
    assert normalize_query("Write a Ship 30 for 30 essay about Shreyash Doshi's LNO framework.") == "Shreyas Doshi's LNO framework."
    assert normalize_query("Draft an executive summary on product led growth") == "product led growth"
    assert normalize_query("Create an interactive HTML card covering churn metrics") == "churn metrics"


def test_query_normalization_guest_phonetics():
    """Verify guest name phonetic spelling variations are normalized across corpus."""
    assert normalize_query("What does Shreyash Doshi say about task triage?") == "What does Shreyas Doshi say about task triage?"
    assert normalize_query("How did Brian Cheskey build culture?") == "How did Brian Chesky build culture?"
    assert normalize_query("Stewart Butterfield advice") == "Stewart Butterfield advice"


def test_distinctive_term_extraction():
    """Verify generic acronym and framework extractor identifies key terms without stopwords."""
    from app.retrieval.engine import extract_distinctive_terms, extract_potential_guest_mentions

    terms_lno = extract_distinctive_terms("What is Shreyash Doshi's LNO framework?")
    assert "LNO" in terms_lno

    terms_essay = extract_distinctive_terms("Write a Ship 30 for 30 essay about Shreyash Doshi's LNO framework.")
    assert "LNO" in terms_essay

    terms_b2b = extract_distinctive_terms("What does Elena Verna say about B2B product-led growth?")
    assert "B2B" in terms_b2b

    terms_quantum = extract_distinctive_terms("What does Lenny's Podcast say about quantum chromodynamics?")
    assert terms_quantum == []

    guests_lno = extract_potential_guest_mentions("What is Shreyas Doshi's LNO framework?")
    assert "Shreyas Doshi" in guests_lno


@pytest.mark.asyncio
async def test_live_retrieval_lno_framework_queries():
    """
    Live query verification for Shreyash Doshi LNO framework questions.
    Guarantees both direct and artifact-generation prompts meet the synthesis threshold.
    """
    from app.db.session import engine as db_engine

    retrieval_engine = VectorRetrievalEngine()
    gate = GroundingGate()

    queries = [
        "What is Shreyash Doshi's LNO framework?",
        "Write a Ship 30 for 30 essay about Shreyash Doshi's LNO framework.",
    ]

    async with db_engine.connect() as conn:
        for q in queries:
            evidence = await retrieval_engine.search(query=q, top_k=5, db=conn)
            assert len(evidence) > 0

            top = evidence[0]
            assert "Shreyas Doshi" in top.guest
            assert "LNO" in top.content
            assert top.similarity_score >= 0.65

            decision = gate.triage(evidence)
            assert decision.can_synthesize is True
            assert decision.tier in (GroundingTier.LIMITED, GroundingTier.STRONG)
            assert len(decision.selected_evidence) >= 1
            assert decision.selected_evidence[0].guest == "Shreyas Doshi"


@pytest.mark.asyncio
async def test_live_retrieval_quantum_refusal_zero_citations():
    """
    Live query verification that out-of-domain quantum query produces Insufficient tier
    with exactly zero selected citations.
    """
    from app.db.session import engine as db_engine

    retrieval_engine = VectorRetrievalEngine()
    gate = GroundingGate()

    async with db_engine.connect() as conn:
        evidence = await retrieval_engine.search(
            query="What does Lenny's Podcast say about quantum chromodynamics?",
            top_k=5,
            db=conn,
        )

    decision = gate.triage(evidence)
    assert decision.tier == GroundingTier.INSUFFICIENT
    assert decision.can_synthesize is False
    assert decision.selected_evidence == []
    assert decision.top_score < 0.65


@pytest.mark.asyncio
async def test_live_retrieval_lno_standalone_and_spaced_acronyms():
    """
    Verify standalone 'LNO framework' and spaced 'L N O framework'
    pull Chunk #17 into the candidate pool and rank it at the top.
    """
    from app.db.session import engine as db_engine

    retrieval_engine = VectorRetrievalEngine()

    async with db_engine.connect() as conn:
        for q in ["LNO framework", "L N O framework"]:
            evidence = await retrieval_engine.search(query=q, top_k=3, db=conn)
            assert len(evidence) > 0
            top = evidence[0]
            assert "Shreyas Doshi" in top.guest
            assert top.chunk_index == 17
            assert "LNO" in top.content


@pytest.mark.asyncio
async def test_live_retrieval_smart_excerpt_contains_lno_context():
    """
    Verify smart excerpt generation centers on the LNO framework occurrence
    rather than dialogue preamble about sleep or stress.
    """
    from app.db.session import engine as db_engine

    retrieval_engine = VectorRetrievalEngine()

    async with db_engine.connect() as conn:
        evidence = await retrieval_engine.search(
            query="What is Shreyash Doshi's LNO framework?",
            top_k=1,
            db=conn,
        )
        assert len(evidence) > 0
        top = evidence[0]
        # Excerpt must contain the LNO definition or mention, not personal sleep preamble
        assert "LNO" in top.excerpt
        assert "talk to my wife" not in top.excerpt


@pytest.mark.asyncio
async def test_normal_shreyas_queries_continue_working():
    """Verify general Shreyas Doshi queries continue returning relevant Shreyas episodes."""
    from app.db.session import engine as db_engine

    retrieval_engine = VectorRetrievalEngine()
    gate = GroundingGate()

    async with db_engine.connect() as conn:
        evidence = await retrieval_engine.search(
            query="What does Shreyas Doshi say about product management?",
            top_k=5,
            db=conn,
        )
        assert len(evidence) > 0
        assert "Shreyas Doshi" in evidence[0].guest
        assert evidence[0].similarity_score >= 0.70

        decision = gate.triage(evidence)
        assert decision.can_synthesize is True
        assert decision.tier in (GroundingTier.LIMITED, GroundingTier.STRONG, GroundingTier.CONFLICTING)
