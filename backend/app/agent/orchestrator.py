"""Production Q&A Orchestrator.

Orchestrates multi-turn conversation context hydration, query rewriting,
cognitive execution via Pi Coding Agent 0.85.1, authoritative P0.3
vector retrieval, deterministic GroundingGate evaluation, citation validation,
and relational persistence.
"""

from collections.abc import AsyncGenerator
from datetime import datetime
import json
import logging
import time
from typing import Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.citation import CitationValidator
from app.agent.pi_bridge import PiBridgeClient, PiTurnResult
from app.core.config import get_settings
from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import EvidenceItem, GroundingTier
from app.retrieval.rewriter import ConversationQueryRewriter
from app.sessions.models import MessageModel, SourceReferenceItem
from app.sessions.store import SessionStore

logger = logging.getLogger("lenny_assistant.agent.orchestrator")
settings = get_settings()

INSUFFICIENT_REFUSAL_TEXT = (
    "I could not find guidance on this topic in Lenny's Podcast transcripts. "
    "The transcripts focus on product management, growth, and company building from Lenny's interviews. "
    "Please feel free to ask a question related to Lenny's guests and discussions."
)


class QnAResult(BaseModel):
    """Complete structured response from the Q&A orchestrator."""

    session_id: str
    message_id: str
    role: str = "assistant"
    content: str
    grounding: dict
    sources: list[SourceReferenceItem]
    latency_ms: int
    model_used: str


class QnAOrchestrator:
    """Production cognitive orchestrator routing through Pi Coding Agent."""

    def __init__(
        self,
        pi_bridge: Optional[PiBridgeClient] = None,
        retrieval_engine: Optional[VectorRetrievalEngine] = None,
        grounding_gate: Optional[GroundingGate] = None,
        rewriter: Optional[ConversationQueryRewriter] = None,
    ) -> None:
        self.pi_bridge = pi_bridge or PiBridgeClient.get_instance()
        self.retrieval_engine = retrieval_engine or VectorRetrievalEngine()
        self.grounding_gate = grounding_gate or GroundingGate()
        self.rewriter = rewriter or ConversationQueryRewriter()

    async def run_turn(
        self,
        session_id: str,
        user_content: str,
        db: AsyncSession,
    ) -> QnAResult:
        """Execute a complete grounded Q&A turn via Pi Coding Agent and return structured response."""
        start_time = time.perf_counter()

        # 1. Verify session exists or create it
        session = await SessionStore.get_session(db, session_id)
        if not session:
            await SessionStore.create_session(db, session_id=session_id)

        # 2. Persist user message
        await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="user",
            content=user_content,
        )

        # 3. Fetch bounded working context (last 6 messages)
        history = await SessionStore.get_recent_messages(db, session_id, limit=6)
        prior_turns = history[:-1]  # Exclude current user prompt

        # 4. Conversation-aware query rewriting
        retrieval_query = await self.rewriter.rewrite(user_content, prior_turns)

        # 5. Format prior context for Pi agent session
        formatted_history = [
            {"role": msg.role, "content": msg.content}
            for msg in prior_turns[-4:]
        ]

        # 6. Execute turn through Pi Coding Agent
        logger.info("Dispatching turn to Pi Coding Agent for session %s...", session_id)
        pi_result = await self.pi_bridge.execute_turn(
            user_prompt=user_content,
            rewritten_query=retrieval_query,
            history=formatted_history,
            provider=settings.LLM_PROVIDER,
            model_name=settings.ANTHROPIC_MODEL if settings.LLM_PROVIDER == "anthropic" else settings.OLLAMA_MODEL,
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # 7. Convert retrieved evidence items for citation validation
        evidence_items: list[EvidenceItem] = []
        for raw in pi_result.selected_evidence:
            try:
                evidence_items.append(
                    EvidenceItem(
                        chunk_id=raw["chunk_id"],
                        episode_id=raw["episode_id"],
                        title=raw["title"],
                        guest=raw["guest"],
                        publication_date=raw.get("publication_date") or raw.get("publish_date"),
                        source_path=raw["source_path"],
                        chunk_index=raw["chunk_index"],
                        speaker=raw.get("speaker", raw["guest"]),
                        content=raw["content"],
                        similarity_score=float(raw["similarity_score"]),
                        source_identifier=raw.get("source_identifier", f"{raw['guest']} [Chunk #{raw['chunk_index']}]"),
                        excerpt=raw.get("excerpt", raw["content"][:200]),
                    )
                )
            except Exception as exc:
                logger.warning("Could not parse evidence item from Pi result: %s", exc)

        tier_enum = GroundingTier(pi_result.tier) if pi_result.tier in [t.value for t in GroundingTier] else GroundingTier.INSUFFICIENT

        # 8. Post-generation citation validation
        cit_result = CitationValidator.validate_and_extract(
            response_text=pi_result.content,
            retrieved_evidence=evidence_items,
            can_synthesize=pi_result.can_synthesize,
            tier=tier_enum,
        )

        # 9. Persist assistant message and source references
        asst_msg = await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=pi_result.content,
            evidence_tier=pi_result.tier,
            latency_ms=elapsed_ms,
            model_used=pi_result.model_used,
        )

        if cit_result.validated_sources:
            await SessionStore.save_source_references(db, asst_msg.id, cit_result.validated_sources)

        return QnAResult(
            session_id=session_id,
            message_id=asst_msg.id,
            role="assistant",
            content=pi_result.content,
            grounding={
                "tier": pi_result.tier,
                "can_synthesize": pi_result.can_synthesize,
                "top_score": pi_result.top_score,
                "agent": "pi-coding-agent",
            },
            sources=cit_result.validated_sources,
            latency_ms=elapsed_ms,
            model_used=pi_result.model_used,
        )

    async def stream_turn(
        self,
        session_id: str,
        user_content: str,
        db: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        """Stream a conversational turn through Pi Coding Agent using Server-Sent Events."""
        start_time = time.perf_counter()

        # 1. Verify session
        session = await SessionStore.get_session(db, session_id)
        if not session:
            await SessionStore.create_session(db, session_id=session_id)

        # 2. Persist user message
        await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="user",
            content=user_content,
        )

        # 3. Context & rewriting
        history = await SessionStore.get_recent_messages(db, session_id, limit=6)
        prior_turns = history[:-1]

        retrieval_query = await self.rewriter.rewrite(user_content, prior_turns)

        # Emit thinking event
        thinking_payload = {
            "status": "processing",
            "rewritten_query": retrieval_query,
            "session_id": session_id,
            "agent": "pi-coding-agent",
        }
        yield f"event: thinking\ndata: {json.dumps(thinking_payload)}\n\n"

        formatted_history = [
            {"role": msg.role, "content": msg.content}
            for msg in prior_turns[-4:]
        ]

        # 4. Stream turn via Pi bridge
        accumulated_text = ""
        final_pi_result: Optional[PiTurnResult] = None

        async for item in self.pi_bridge.stream_turn(
            user_prompt=user_content,
            rewritten_query=retrieval_query,
            history=formatted_history,
            provider=settings.LLM_PROVIDER,
            model_name=settings.ANTHROPIC_MODEL if settings.LLM_PROVIDER == "anthropic" else settings.OLLAMA_MODEL,
        ):
            event_type = item["event"]
            data = item["data"]

            if event_type == "tool_call":
                yield f"event: thinking\ndata: {json.dumps({'status': 'retrieving', 'tool': data.get('name'), 'query': data.get('query')})}\n\n"

            elif event_type == "evidence":
                evidence_payload = {
                    "tier": data.get("tier"),
                    "chunk_count": data.get("chunk_count", 0),
                    "top_score": data.get("top_score", 0.0),
                    "can_synthesize": data.get("can_synthesize", False),
                }
                yield f"event: evidence\ndata: {json.dumps(evidence_payload)}\n\n"

            elif event_type == "delta":
                token = data.get("delta", "")
                accumulated_text += token
                yield f"event: delta\ndata: {json.dumps({'text': token})}\n\n"

            elif event_type == "result":
                final_pi_result = data

        if not final_pi_result:
            final_pi_result = PiTurnResult(
                content=accumulated_text or INSUFFICIENT_REFUSAL_TEXT,
                tier="Insufficient",
                top_score=0.0,
                can_synthesize=False,
                model_used=f"{settings.LLM_PROVIDER}/pi",
                selected_evidence=[],
            )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # 5. Parse evidence
        evidence_items: list[EvidenceItem] = []
        for raw in final_pi_result.selected_evidence:
            try:
                evidence_items.append(
                    EvidenceItem(
                        chunk_id=raw["chunk_id"],
                        episode_id=raw["episode_id"],
                        title=raw["title"],
                        guest=raw["guest"],
                        publication_date=raw.get("publication_date") or raw.get("publish_date"),
                        source_path=raw["source_path"],
                        chunk_index=raw["chunk_index"],
                        speaker=raw.get("speaker", raw["guest"]),
                        content=raw["content"],
                        similarity_score=float(raw["similarity_score"]),
                        source_identifier=raw.get("source_identifier", f"{raw['guest']} [Chunk #{raw['chunk_index']}]"),
                        excerpt=raw.get("excerpt", raw["content"][:200]),
                    )
                )
            except Exception as exc:
                logger.warning("Could not parse evidence item: %s", exc)

        tier_enum = GroundingTier(final_pi_result.tier) if final_pi_result.tier in [t.value for t in GroundingTier] else GroundingTier.INSUFFICIENT

        # 6. Validate citations
        cit_result = CitationValidator.validate_and_extract(
            response_text=final_pi_result.content,
            retrieved_evidence=evidence_items,
            can_synthesize=final_pi_result.can_synthesize,
            tier=tier_enum,
        )

        for src in cit_result.validated_sources:
            yield f"event: citation\ndata: {json.dumps(src.model_dump())}\n\n"

        # 7. Persist assistant message
        asst_msg = await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=final_pi_result.content,
            evidence_tier=final_pi_result.tier,
            latency_ms=elapsed_ms,
            model_used=final_pi_result.model_used,
        )

        if cit_result.validated_sources:
            await SessionStore.save_source_references(db, asst_msg.id, cit_result.validated_sources)

        done_payload = {
            "message_id": asst_msg.id,
            "session_id": session_id,
            "latency_ms": elapsed_ms,
            "tier": final_pi_result.tier,
            "can_synthesize": final_pi_result.can_synthesize,
            "sources": [s.model_dump() for s in cit_result.validated_sources],
            "agent": "pi-coding-agent",
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
