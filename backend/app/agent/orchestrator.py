"""Production Q&A Orchestrator.

Orchestrates multi-turn conversation context hydration, query rewriting,
vector retrieval, deterministic grounding gate evaluation, cognitive LLM synthesis,
citation validation, and relational persistence.
"""

from collections.abc import AsyncGenerator
from datetime import datetime
import json
import logging
import time
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.citation import CitationValidator
from app.agent.retrieval_tool import format_evidence_for_agent
from app.core.config import get_settings
from app.providers.base import GenerationProvider
from app.providers.factory import get_generation_provider
from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import GroundingTier, RetrievalResponse
from app.retrieval.rewriter import ConversationQueryRewriter
from app.sessions.models import MessageModel, SourceReferenceItem
from app.sessions.store import SessionStore

logger = logging.getLogger("lenny_assistant.agent.orchestrator")
settings = get_settings()

SYSTEM_GROUNDING_PROMPT = (
    "You are The Lenny Growth Assistant, an AI expert grounded strictly in transcripts from Lenny's Podcast.\n"
    "Your mission is to provide accurate, insightful answers based solely on the verified evidence provided.\n\n"
    "STRICT GROUNDING RULES:\n"
    "1. Use ONLY the factual information in the <retrieved_evidence> block below.\n"
    "2. Attribute claims to the specific speaker/guest (e.g., 'Ada Chen Rekhi explains...') and reference the episode title.\n"
    "3. When evidence indicates Conflicting viewpoints across guests, clearly contrast the differing perspectives.\n"
    "4. Do NOT make claims unsupported by the evidence or extrapolate beyond what the guests stated.\n"
    "5. Reference the chunk IDs or citations where appropriate."
)

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
    """Production cognitive orchestrator for grounded conversational Q&A."""

    def __init__(
        self,
        retrieval_engine: Optional[VectorRetrievalEngine] = None,
        grounding_gate: Optional[GroundingGate] = None,
        provider: Optional[GenerationProvider] = None,
        rewriter: Optional[ConversationQueryRewriter] = None,
    ) -> None:
        self.retrieval_engine = retrieval_engine or VectorRetrievalEngine()
        self.grounding_gate = grounding_gate or GroundingGate()
        self.provider = provider or get_generation_provider()
        self.rewriter = rewriter or ConversationQueryRewriter(provider=self.provider)

    async def run_turn(
        self,
        session_id: str,
        user_content: str,
        db: AsyncSession,
    ) -> QnAResult:
        """Execute a complete grounded Q&A turn and return structured response."""
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

        # 5. Semantic vector retrieval over PostgreSQL pgvector
        evidence = await self.retrieval_engine.search(
            query=retrieval_query,
            top_k=settings.RETRIEVAL_TOP_K,
            db=db,
        )

        # 6. Authoritative Grounding Gate triage
        decision = self.grounding_gate.triage(evidence)

        # 7. Check for Insufficient evidence -> Deterministic refusal without LLM synthesis
        if not decision.can_synthesize or decision.tier == GroundingTier.INSUFFICIENT:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            model_ident = f"{self.provider.provider_name}/{self.provider.model_name}"

            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=INSUFFICIENT_REFUSAL_TEXT,
                evidence_tier=decision.tier.value,
                latency_ms=elapsed_ms,
                model_used=model_ident,
            )

            return QnAResult(
                session_id=session_id,
                message_id=asst_msg.id,
                role="assistant",
                content=INSUFFICIENT_REFUSAL_TEXT,
                grounding={
                    "tier": decision.tier.value,
                    "can_synthesize": False,
                    "top_score": decision.top_score,
                    "confidence_score": decision.confidence_score,
                    "reason": decision.reason,
                },
                sources=[],
                latency_ms=elapsed_ms,
                model_used=model_ident,
            )

        # 8. Format structured XML evidence
        retrieval_resp = RetrievalResponse(
            query=user_content,
            normalized_query=retrieval_query,
            decision=decision,
            evidence=evidence,
        )
        xml_evidence = format_evidence_for_agent(retrieval_resp)

        # 9. Build bounded LLM conversation context
        llm_messages = []
        for msg in prior_turns[-4:]:  # Last 2 conversation turns
            llm_messages.append({"role": msg.role, "content": msg.content})

        llm_messages.append(
            {
                "role": "user",
                "content": f"{user_content}\n\n{xml_evidence}",
            }
        )

        # 10. Generate response via configured provider
        response_text = await self.provider.generate(
            messages=llm_messages,
            system_prompt=SYSTEM_GROUNDING_PROMPT,
            max_tokens=384,
        )

        # 11. Validate citations
        cit_result = CitationValidator.validate_and_extract(
            response_text=response_text,
            retrieved_evidence=decision.selected_evidence,
            can_synthesize=True,
            tier=decision.tier,
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        model_ident = f"{self.provider.provider_name}/{self.provider.model_name}"

        # 12. Persist assistant message and source references
        asst_msg = await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=response_text,
            evidence_tier=decision.tier.value,
            latency_ms=elapsed_ms,
            model_used=model_ident,
        )

        if cit_result.validated_sources:
            await SessionStore.save_source_references(db, asst_msg.id, cit_result.validated_sources)

        return QnAResult(
            session_id=session_id,
            message_id=asst_msg.id,
            role="assistant",
            content=response_text,
            grounding={
                "tier": decision.tier.value,
                "can_synthesize": True,
                "top_score": decision.top_score,
                "confidence_score": decision.confidence_score,
                "reason": decision.reason,
            },
            sources=cit_result.validated_sources,
            latency_ms=elapsed_ms,
            model_used=model_ident,
        )

    async def stream_turn(
        self,
        session_id: str,
        user_content: str,
        db: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        """
        Execute grounded Q&A turn yielding Server-Sent Events (SSE) stream chunks:
        event: thinking -> event: evidence -> event: delta -> event: citation -> event: done
        """
        start_time = time.perf_counter()

        # 1. Verify session & persist user message
        session = await SessionStore.get_session(db, session_id)
        if not session:
            await SessionStore.create_session(db, session_id=session_id)

        await SessionStore.save_message(db=db, session_id=session_id, role="user", content=user_content)
        history = await SessionStore.get_recent_messages(db, session_id, limit=6)
        prior_turns = history[:-1]

        # Event: Thinking (Rewriting)
        yield f"event: thinking\ndata: {json.dumps({'step': 'rewriting', 'status': 'in_progress'})}\n\n"
        retrieval_query = await self.rewriter.rewrite(user_content, prior_turns)

        # Event: Thinking (Retrieval)
        yield f"event: thinking\ndata: {json.dumps({'step': 'retrieval', 'query': retrieval_query})}\n\n"
        evidence = await self.retrieval_engine.search(query=retrieval_query, top_k=settings.RETRIEVAL_TOP_K, db=db)
        decision = self.grounding_gate.triage(evidence)

        # Event: Evidence Triage
        evidence_payload = {
            "tier": decision.tier.value,
            "chunk_count": len(decision.selected_evidence),
            "top_score": decision.top_score,
            "can_synthesize": decision.can_synthesize,
        }
        yield f"event: evidence\ndata: {json.dumps(evidence_payload)}\n\n"

        # Check Insufficient
        if not decision.can_synthesize or decision.tier == GroundingTier.INSUFFICIENT:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            model_ident = f"{self.provider.provider_name}/{self.provider.model_name}"

            # Stream refusal delta
            yield f"event: delta\ndata: {json.dumps({'text': INSUFFICIENT_REFUSAL_TEXT})}\n\n"

            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=INSUFFICIENT_REFUSAL_TEXT,
                evidence_tier=decision.tier.value,
                latency_ms=elapsed_ms,
                model_used=model_ident,
            )

            done_payload = {
                "message_id": asst_msg.id,
                "latency_ms": elapsed_ms,
                "tier": decision.tier.value,
                "can_synthesize": False,
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            return

        # Prepare prompt
        retrieval_resp = RetrievalResponse(
            query=user_content,
            normalized_query=retrieval_query,
            decision=decision,
            evidence=evidence,
        )
        xml_evidence = format_evidence_for_agent(retrieval_resp)

        llm_messages = []
        for msg in prior_turns[-4:]:
            llm_messages.append({"role": msg.role, "content": msg.content})
        llm_messages.append({"role": "user", "content": f"{user_content}\n\n{xml_evidence}"})

        # Stream token deltas from provider
        accumulated_text = ""
        async for token in self.provider.stream(
            llm_messages,
            system_prompt=SYSTEM_GROUNDING_PROMPT,
            max_tokens=384,
        ):
            accumulated_text += token
            yield f"event: delta\ndata: {json.dumps({'text': token})}\n\n"

        # Validate citations
        cit_result = CitationValidator.validate_and_extract(
            response_text=accumulated_text,
            retrieved_evidence=decision.selected_evidence,
            can_synthesize=True,
            tier=decision.tier,
        )

        # Emit citation events
        for src in cit_result.validated_sources:
            yield f"event: citation\ndata: {json.dumps(src.model_dump())}\n\n"

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        model_ident = f"{self.provider.provider_name}/{self.provider.model_name}"

        asst_msg = await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=accumulated_text,
            evidence_tier=decision.tier.value,
            latency_ms=elapsed_ms,
            model_used=model_ident,
        )

        if cit_result.validated_sources:
            await SessionStore.save_source_references(db, asst_msg.id, cit_result.validated_sources)

        done_payload = {
            "message_id": asst_msg.id,
            "latency_ms": elapsed_ms,
            "tier": decision.tier.value,
            "can_synthesize": True,
            "sources_count": len(cit_result.validated_sources),
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
