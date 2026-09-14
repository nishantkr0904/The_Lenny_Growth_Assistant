"""Retrieval tool adapter binding Pi Coding Agent to the P0.3 Vector Retrieval and Grounding Gate."""

import html
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import engine as db_engine
from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import EvidenceItem, GroundingDecision, GroundingTier, RetrievalResponse
from app.retrieval.query import normalize_query

logger = get_logger(__name__)


def format_evidence_for_agent(response: RetrievalResponse) -> str:
    """
    Format a RetrievalResponse into a structured XML evidence block for Pi.
    Enforces deterministic grounding rules:
    - If can_synthesize is False (Insufficient), injects explicit refusal directives.
    - If can_synthesize is True, injects verified chunk excerpts with citation metadata.
    """
    decision: GroundingDecision = response.decision

    if not decision.can_synthesize or decision.tier == GroundingTier.INSUFFICIENT:
        return (
            f'<retrieved_evidence status="INSUFFICIENT" tier="{decision.tier.value}" can_synthesize="false" top_score="{decision.top_score:.4f}">\n'
            f"  <grounding_decision>\n"
            f"    {html.escape(decision.reason)}\n"
            f"  </grounding_decision>\n"
            f"  <system_directive>\n"
            f"    NO_GROUNDED_EVIDENCE: The retrieved evidence does not meet the minimum relevance threshold for factual synthesis.\n"
            f"    You are strictly FORBIDDEN from answering this question using general training knowledge or fabricating quotes.\n"
            f"    You MUST explicitly inform the user that this topic is not discussed in Lenny's Podcast transcripts.\n"
            f"  </system_directive>\n"
            f"</retrieved_evidence>"
        )

    evidence_items = decision.selected_evidence or response.evidence
    xml_chunks: list[str] = []

    for item in evidence_items:
        escaped_title = html.escape(item.title)
        escaped_guest = html.escape(item.guest)
        escaped_speaker = html.escape(item.speaker or item.guest)
        escaped_citation = html.escape(item.source_identifier)
        escaped_content = html.escape(item.content.strip())
        date_str = item.publication_date.isoformat() if item.publication_date else "Unknown"

        xml_chunks.append(
            f'  <chunk id="{item.chunk_id}" guest="{escaped_guest}" episode="{escaped_title}" '
            f'date="{date_str}" chunk_index="{item.chunk_index}" score="{item.similarity_score:.4f}" '
            f'citation="{escaped_citation}">\n'
            f"    <speaker>{escaped_speaker}</speaker>\n"
            f"    <content>\n{escaped_content}\n    </content>\n"
            f"  </chunk>"
        )

    chunks_str = "\n".join(xml_chunks)
    conflict_note = ""
    if decision.tier == GroundingTier.CONFLICTING:
        conflict_note = (
            f"  <conflict_directive>\n"
            f"    NOTE: Multiple divergent viewpoints exist across distinct guests. Synthesis must present both sides.\n"
            f"  </conflict_directive>\n"
        )

    return (
        f'<retrieved_evidence status="VALID" tier="{decision.tier.value}" can_synthesize="true" top_score="{decision.top_score:.4f}">\n'
        f"  <grounding_decision>\n"
        f"    {html.escape(decision.reason)}\n"
        f"  </grounding_decision>\n"
        f"{conflict_note}"
        f"  <system_directive>\n"
        f"    Use ONLY the factual information contained in the chunks below.\n"
        f"    Attribute factual claims to the speaker/guest and reference the episode title.\n"
        f"  </system_directive>\n"
        f"{chunks_str}\n"
        f"</retrieved_evidence>"
    )


async def execute_transcript_retrieval(
    query: str,
    top_k: int = 5,
    db: Optional[AsyncSession] = None,
    engine: Optional[VectorRetrievalEngine] = None,
    gate: Optional[GroundingGate] = None,
) -> dict:
    """
    Execute semantic retrieval against the P0.3 retrieval layer and return a structured
    evidence package containing both typed data and formatted XML for the agent.
    """
    normalized_q = normalize_query(query)
    retrieval_engine = engine or VectorRetrievalEngine()
    grounding_gate = gate or GroundingGate()

    if db is not None:
        evidence = await retrieval_engine.search(query=normalized_q, top_k=top_k, db=db)
    else:
        async with db_engine.connect() as conn:
            evidence = await retrieval_engine.search(query=normalized_q, top_k=top_k, db=conn)

    decision = grounding_gate.triage(evidence)

    response = RetrievalResponse(
        query=query,
        normalized_query=normalized_q,
        decision=decision,
        evidence=evidence,
    )

    formatted_xml = format_evidence_for_agent(response)

    return {
        "status": "success",
        "query": query,
        "normalized_query": normalized_q,
        "tier": decision.tier.value,
        "can_synthesize": decision.can_synthesize,
        "top_score": decision.top_score,
        "confidence_score": decision.confidence_score,
        "reason": decision.reason,
        "chunk_count": len(decision.selected_evidence),
        "source_diversity": decision.source_diversity.model_dump(),
        "xml_content": formatted_xml,
    }
