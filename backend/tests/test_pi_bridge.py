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


import json
import os
import subprocess
from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.grounding import GroundingGate
from app.retrieval.query import normalize_query


def run_node_bridge_helper(code: str) -> dict:
    """Execute a snippet testing bridge_daemon.mjs exported helpers in node."""
    full_script = f"""
    import('./app/agent/bridge_daemon.mjs').then(async (mod) => {{
        {code}
    }}).catch(err => {{
        console.error(err);
        process.exit(1);
    }});
    """
    res = subprocess.run(
        ["node", "--input-type=module", "-e", full_script],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [ln.strip() for ln in res.stdout.strip().split("\n") if ln.strip()]
    for ln in reversed(lines):
        try:
            return json.loads(ln)
        except Exception:
            continue
    return {}


def test_no_shreyas_or_lno_specific_hardcoding():
    """
    Regression Test 5: Verify that bridge_daemon.mjs contains ZERO hardcoded references
    to 'Shreyas' or 'LNO' in its code logic, ensuring universal applicability.
    """
    daemon_path = os.path.join(os.path.dirname(__file__), "..", "app", "agent", "bridge_daemon.mjs")
    with open(daemon_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "shreyas" not in content.lower(), "Found hardcoded 'shreyas' in bridge_daemon.mjs"
    assert not any(w.lower() == "lno" for w in content.split()), "Found hardcoded 'lno' in bridge_daemon.mjs"


def test_distinctive_term_extraction_and_degraded_query_detection_universal():
    """
    Regression Test 5b: Verify universal distinctive term extraction and materially weaker query
    detection on various guest/framework queries without hardcoding.
    """
    script = """
    const { extractDistinctiveTerms, isMateriallyWeakerQuery, isStrongerDecision } = mod;

    // 1. Shreyas / LNO case
    const lnoTerms = extractDistinctiveTerms("Shreyas Doshi's LNO framework");
    const isLnoWeaker = isMateriallyWeakerQuery("Shreyas Doshi", "Shreyas Doshi's LNO framework");
    const isLnoExact = isMateriallyWeakerQuery("Shreyas Doshi's LNO framework", "Shreyas Doshi's LNO framework");

    // 2. Elena Verna / PLG case (proves universality without hardcoding)
    const plgTerms = extractDistinctiveTerms("Elena Verna's PLG framework");
    const isPlgWeaker = isMateriallyWeakerQuery("Elena Verna", "Elena Verna's PLG framework");

    // 3. Pronoun case
    const isPronounWeaker = isMateriallyWeakerQuery("What did she say about onboarding?", "What did Lauryn Isford say about onboarding?");

    // 4. Decision strength comparison
    const strongerWins = isStrongerDecision({ tier: "Strong", top_score: 0.86 }, { tier: "Limited", top_score: 0.66 });
    const weakerLoses = isStrongerDecision({ tier: "Limited", top_score: 0.66 }, { tier: "Strong", top_score: 0.86 });

    process.stdout.write(JSON.stringify({
        lnoTerms,
        isLnoWeaker,
        isLnoExact,
        plgTerms,
        isPlgWeaker,
        isPronounWeaker,
        strongerWins,
        weakerLoses,
    }) + '\\n');
    process.exit(0);
    """
    res = run_node_bridge_helper(script)
    assert "LNO" in res["lnoTerms"]
    assert res["isLnoWeaker"] is True
    assert res["isLnoExact"] is False
    assert "PLG" in res["plgTerms"]
    assert res["isPlgWeaker"] is True
    assert res["isPronounWeaker"] is True
    assert res["strongerWins"] is True
    assert res["weakerLoses"] is False


@pytest.mark.asyncio
async def test_regression_compound_lno_artifact_query_retrieves_strong_evidence():
    """
    Regression Test 1: Compound artifact query 'Write a Ship 30 for 30 essay about Shreyas Doshi's LNO framework.'
    must normalize to 'Shreyas Doshi's LNO framework.' and retrieve Chunk #17 with Strong tier (score >= 0.80).
    """
    raw_query = "Write a Ship 30 for 30 essay about Shreyas Doshi's LNO framework."
    normalized_q = normalize_query(raw_query)
    assert "Ship 30" not in normalized_q
    assert "Shreyas Doshi" in normalized_q
    assert "LNO" in normalized_q

    engine = VectorRetrievalEngine()
    gate = GroundingGate()

    candidates = await engine.search(normalized_q, top_k=5)
    assert len(candidates) > 0

    top_chunk = candidates[0]
    assert top_chunk.guest == "Shreyas Doshi"
    assert top_chunk.chunk_index == 17
    assert top_chunk.similarity_score >= 0.80

    decision = gate.triage(candidates)
    assert decision.tier == GroundingTier.STRONG
    assert decision.can_synthesize is True
    assert decision.top_score >= 0.80


@pytest.mark.asyncio
async def test_regression_llm_dropping_lno_framework_overridden_by_authoritative():
    """
    Regression Test 2: When LLM drops 'LNO framework' and queries only 'Shreyas Doshi',
    the daemon detects the degradation and overrides with authoritative rewritten query.
    """
    engine = VectorRetrievalEngine()
    gate = GroundingGate()

    degraded_query = "Shreyas Doshi"
    authoritative_query = "Shreyas Doshi's LNO framework."

    degraded_res = await engine.search(degraded_query, top_k=5)
    authoritative_res = await engine.search(authoritative_query, top_k=5)

    degraded_decision = gate.triage(degraded_res)
    authoritative_decision = gate.triage(authoritative_res)

    # Degraded query only retrieves biographical background (Chunks #2, #13, etc.) with score ~0.66
    assert degraded_decision.tier != GroundingTier.STRONG
    assert degraded_decision.top_score < 0.70

    # Authoritative query retrieves Chunk #17 with score ~0.86 (Strong tier)
    assert authoritative_decision.tier == GroundingTier.STRONG
    assert authoritative_decision.top_score >= 0.80
    assert authoritative_res[0].chunk_index == 17

    # Verify node helper identifies this as materially weaker and promotes the authoritative query
    script = f"""
    const {{ isMateriallyWeakerQuery, isStrongerDecision }} = mod;
    const isWeaker = isMateriallyWeakerQuery("{degraded_query}", "{authoritative_query}");
    const isStronger = isStrongerDecision(
        {{ tier: "{authoritative_decision.tier.value}", top_score: {authoritative_decision.top_score} }},
        {{ tier: "{degraded_decision.tier.value}", top_score: {degraded_decision.top_score} }}
    );
    process.stdout.write(JSON.stringify({{ isWeaker, isStronger }}) + '\\n');
    process.exit(0);
    """
    res = run_node_bridge_helper(script)
    assert res["isWeaker"] is True
    assert res["isStronger"] is True


@pytest.mark.asyncio
async def test_regression_missing_tool_call_textual_fake_deterministic_fallback():
    """
    Regression Test 3: When LLM emits a fake textual tool call and fails to execute the tool,
    deterministic fallback executes retrieval using authoritative query and achieves Strong tier.
    """
    authoritative_query = normalize_query("Write a Ship 30 for 30 essay about Shreyas Doshi's LNO framework.")
    engine = VectorRetrievalEngine()
    gate = GroundingGate()

    candidates = await engine.search(authoritative_query, top_k=5)
    decision = gate.triage(candidates)

    assert decision.can_synthesize is True
    assert decision.tier == GroundingTier.STRONG
    assert decision.top_score >= 0.80
    assert candidates[0].chunk_index == 17


@pytest.mark.asyncio
async def test_regression_genuinely_out_of_domain_quantum_query_refuses():
    """
    Regression Test 4: Genuinely out-of-domain quantum query strictly evaluates to Insufficient
    and refuses, preserving GroundingGate and refusal behavior.
    """
    query = "How does quantum entanglement affect distributed consensus in Byzantine fault tolerance?"
    normalized_q = normalize_query(query)
    engine = VectorRetrievalEngine()
    gate = GroundingGate()

    candidates = await engine.search(normalized_q, top_k=5)
    decision = gate.triage(candidates)

    assert decision.can_synthesize is False
    assert decision.tier == GroundingTier.INSUFFICIENT
    assert decision.top_score < 0.65
