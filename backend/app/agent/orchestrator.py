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
from app.agent.intent import classify_conversational_intent
from app.agent.pi_bridge import PiBridgeClient, PiTurnResult
from app.core.config import get_settings
from app.providers.base import ProviderConfigurationError
from app.providers.factory import get_generation_provider
from app.providers.manager import ProviderManager
from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import EvidenceItem, GroundingTier
from app.retrieval.rewriter import ConversationQueryRewriter
from app.sessions.models import MessageModel, SourceReferenceItem
from app.sessions.store import SessionStore

logger = logging.getLogger("lenny_assistant.agent.orchestrator")
settings = get_settings()

CONVERSATIONAL_SYSTEM_PROMPT = (
    "You are the Lenny Growth Assistant, a helpful AI companion focused on product management, "
    "growth, and company-building wisdom from Lenny's Podcast transcripts. "
    "The user is engaging in casual conversation (e.g., greeting, thanking, acknowledging, or saying goodbye). "
    "Respond in a friendly, natural, and concise manner (1-2 sentences). "
    "Acknowledge them warmly and invite them to ask questions about product strategy, growth frameworks, "
    "metrics, or lessons from Lenny's guests. "
    "Do not cite podcast transcripts, invent evidence, or create citations."
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

        # 3. Check provider configuration and handle missing cloud API key
        manager = ProviderManager.get_instance()
        active_provider = manager.get_active_provider()
        active_key = (
            manager.get_anthropic_api_key() if active_provider == "anthropic"
            else manager.get_gemini_api_key() if active_provider == "gemini"
            else None
        )

        if active_provider == "anthropic" and not active_key:
            err_msg = (
                "Anthropic API key is required when Anthropic provider is selected. "
                "Please configure an API key in the provider settings or switch to Ollama."
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=err_msg,
                evidence_tier="Insufficient",
                latency_ms=elapsed_ms,
                model_used="anthropic/unconfigured",
            )
            return QnAResult(
                session_id=session_id,
                message_id=asst_msg.id,
                role="assistant",
                content=err_msg,
                grounding={
                    "tier": "Insufficient",
                    "can_synthesize": False,
                    "top_score": 0.0,
                    "agent": "provider-gate",
                },
                sources=[],
                latency_ms=elapsed_ms,
                model_used="anthropic/unconfigured",
            )
        elif active_provider == "gemini" and not active_key:
            err_msg = (
                "Google Gemini API key is required when Gemini provider is selected. "
                "Please configure an API key in the provider settings or switch to Ollama."
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=err_msg,
                evidence_tier="Insufficient",
                latency_ms=elapsed_ms,
                model_used="gemini/unconfigured",
            )
            return QnAResult(
                session_id=session_id,
                message_id=asst_msg.id,
                role="assistant",
                content=err_msg,
                grounding={
                    "tier": "Insufficient",
                    "can_synthesize": False,
                    "top_score": 0.0,
                    "agent": "provider-gate",
                },
                sources=[],
                latency_ms=elapsed_ms,
                model_used="gemini/unconfigured",
            )

        # 4. Check conversational intent before retrieval / rewriting
        intent_decision = classify_conversational_intent(user_content)
        if intent_decision.is_conversational:
            logger.info("Routing user message as conversational intent (%s)", intent_decision.sub_intent)
            try:
                provider = get_generation_provider(active_provider)
                conv_content = await provider.generate(
                    messages=[{"role": "user", "content": user_content}],
                    system_prompt=CONVERSATIONAL_SYSTEM_PROMPT,
                    max_tokens=150,
                    temperature=0.3,
                )
                conv_content = conv_content.strip()
            except Exception as exc:
                logger.warning("GenerationProvider failed for conversational turn: %s. Using fallback.", exc)
                conv_content = (
                    "Hello! I'm the Lenny Growth Assistant, here to help you explore insights, frameworks, "
                    "and tactical wisdom from Lenny's Podcast. What product or growth challenge are you working through today?"
                )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=conv_content,
                evidence_tier="Conversational",
                latency_ms=elapsed_ms,
                model_used=f"{active_provider}/conversational",
            )

            return QnAResult(
                session_id=session_id,
                message_id=asst_msg.id,
                role="assistant",
                content=conv_content,
                grounding={
                    "tier": "Conversational",
                    "can_synthesize": True,
                    "top_score": 0.0,
                    "agent": "conversational-router",
                },
                sources=[],
                latency_ms=elapsed_ms,
                model_used=f"{active_provider}/conversational",
            )

        # 5. Fetch bounded working context (last 6 messages)
        history = await SessionStore.get_recent_messages(db, session_id, limit=6)
        prior_turns = history[:-1]  # Exclude current user prompt

        # 6. Conversation-aware query rewriting
        retrieval_query = await self.rewriter.rewrite(user_content, prior_turns)

        # 7. Format prior context for Pi agent session
        formatted_history = [
            {"role": msg.role, "content": msg.content}
            for msg in prior_turns[-4:]
        ]

        # 8. Execute turn through Pi Coding Agent
        logger.info("Dispatching turn to Pi Coding Agent for session %s (provider=%s)...", session_id, active_provider)
        target_model = (
            settings.ANTHROPIC_MODEL if active_provider == "anthropic"
            else settings.GEMINI_MODEL if active_provider == "gemini"
            else settings.OLLAMA_MODEL
        )
        pi_result = await self.pi_bridge.execute_turn(
            user_prompt=user_content,
            rewritten_query=retrieval_query,
            history=formatted_history,
            provider=active_provider,
            model_name=target_model,
            api_key=active_key,
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

        tier_enum = GroundingTier.from_str(pi_result.tier)

        # 8. Post-generation citation validation
        cit_result = CitationValidator.validate_and_extract(
            response_text=pi_result.content,
            retrieved_evidence=evidence_items,
            can_synthesize=pi_result.can_synthesize,
            tier=tier_enum,
        )

        # Refusal turns or insufficient evidence must strictly be Insufficient tier with zero sources
        is_refusal = len(cit_result.validated_sources) == 0 and (
            tier_enum == GroundingTier.INSUFFICIENT
            or not pi_result.can_synthesize
            or any(w in pi_result.content.lower() for w in ["no information", "not discussed", "not covered", "could not find"])
        )
        effective_tier = "Insufficient" if is_refusal else pi_result.tier
        effective_can_synthesize = False if is_refusal else pi_result.can_synthesize

        # 9. Persist assistant message and source references
        asst_msg = await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=pi_result.content,
            evidence_tier=effective_tier,
            latency_ms=elapsed_ms,
            model_used=pi_result.model_used,
        )

        if cit_result.validated_sources and not is_refusal:
            await SessionStore.save_source_references(db, asst_msg.id, cit_result.validated_sources)

        return QnAResult(
            session_id=session_id,
            message_id=asst_msg.id,
            role="assistant",
            content=pi_result.content,
            grounding={
                "tier": effective_tier,
                "can_synthesize": effective_can_synthesize,
                "top_score": pi_result.top_score if not is_refusal else 0.0,
                "agent": "pi-coding-agent",
            },
            sources=[] if is_refusal else cit_result.validated_sources,
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

        # 3. Check provider configuration and handle missing cloud API key
        manager = ProviderManager.get_instance()
        active_provider = manager.get_active_provider()
        active_key = (
            manager.get_anthropic_api_key() if active_provider == "anthropic"
            else manager.get_gemini_api_key() if active_provider == "gemini"
            else None
        )

        if active_provider == "anthropic" and not active_key:
            err_msg = (
                "Anthropic API key is required when Anthropic provider is selected. "
                "Please configure an API key in the provider settings or switch to Ollama."
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            yield f"event: delta\ndata: {json.dumps({'text': err_msg})}\n\n"
            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=err_msg,
                evidence_tier="Insufficient",
                latency_ms=elapsed_ms,
                model_used="anthropic/unconfigured",
            )
            done_payload = {
                "message_id": asst_msg.id,
                "session_id": session_id,
                "latency_ms": elapsed_ms,
                "tier": "Insufficient",
                "can_synthesize": False,
                "sources": [],
                "agent": "provider-gate",
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            return
        elif active_provider == "gemini" and not active_key:
            err_msg = (
                "Google Gemini API key is required when Gemini provider is selected. "
                "Please configure an API key in the provider settings or switch to Ollama."
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            yield f"event: delta\ndata: {json.dumps({'text': err_msg})}\n\n"
            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=err_msg,
                evidence_tier="Insufficient",
                latency_ms=elapsed_ms,
                model_used="gemini/unconfigured",
            )
            done_payload = {
                "message_id": asst_msg.id,
                "session_id": session_id,
                "latency_ms": elapsed_ms,
                "tier": "Insufficient",
                "can_synthesize": False,
                "sources": [],
                "agent": "provider-gate",
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            return

        # 4. Check conversational intent before retrieval / rewriting
        intent_decision = classify_conversational_intent(user_content)
        if intent_decision.is_conversational:
            logger.info("Routing stream turn as conversational intent (%s)", intent_decision.sub_intent)
            thinking_payload = {
                "status": "processing",
                "session_id": session_id,
                "agent": "conversational-router",
            }
            yield f"event: thinking\ndata: {json.dumps(thinking_payload)}\n\n"

            accumulated_text = ""
            try:
                provider = get_generation_provider(active_provider)
                async for token in provider.stream(
                    messages=[{"role": "user", "content": user_content}],
                    system_prompt=CONVERSATIONAL_SYSTEM_PROMPT,
                    max_tokens=150,
                    temperature=0.3,
                ):
                    accumulated_text += token
                    yield f"event: delta\ndata: {json.dumps({'text': token})}\n\n"
            except Exception as exc:
                logger.warning("Streaming failed for conversational turn: %s. Emitting fallback.", exc)
                fallback = (
                    "Hello! I'm the Lenny Growth Assistant, here to help you explore insights, frameworks, "
                    "and tactical wisdom from Lenny's Podcast. What product or growth challenge are you working through today?"
                )
                accumulated_text = fallback
                yield f"event: delta\ndata: {json.dumps({'text': fallback})}\n\n"

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            asst_msg = await SessionStore.save_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=accumulated_text.strip(),
                evidence_tier="Conversational",
                latency_ms=elapsed_ms,
                model_used=f"{active_provider}/conversational",
            )

            done_payload = {
                "message_id": asst_msg.id,
                "session_id": session_id,
                "latency_ms": elapsed_ms,
                "tier": "Conversational",
                "can_synthesize": True,
                "sources": [],
                "agent": "conversational-router",
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            return

        # 5. Context & rewriting
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

        # 6. Stream turn via Pi bridge
        accumulated_text = ""
        final_pi_result: Optional[PiTurnResult] = None

        async for item in self.pi_bridge.stream_turn(
            user_prompt=user_content,
            rewritten_query=retrieval_query,
            history=formatted_history,
            provider=active_provider,
            model_name=(
                settings.ANTHROPIC_MODEL if active_provider == "anthropic"
                else settings.GEMINI_MODEL if active_provider == "gemini"
                else settings.OLLAMA_MODEL
            ),
            api_key=active_key,
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
                model_used=f"{active_provider}/pi",
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

        tier_enum = GroundingTier.from_str(final_pi_result.tier)

        # 6. Validate citations
        cit_result = CitationValidator.validate_and_extract(
            response_text=final_pi_result.content,
            retrieved_evidence=evidence_items,
            can_synthesize=final_pi_result.can_synthesize,
            tier=tier_enum,
        )

        # Refusal turns or insufficient evidence must strictly be Insufficient tier with zero sources
        is_refusal = len(cit_result.validated_sources) == 0 and (
            tier_enum == GroundingTier.INSUFFICIENT
            or not final_pi_result.can_synthesize
            or any(w in final_pi_result.content.lower() for w in ["no information", "not discussed", "not covered", "could not find"])
        )
        effective_tier = "Insufficient" if is_refusal else final_pi_result.tier
        effective_can_synthesize = False if is_refusal else final_pi_result.can_synthesize

        if not is_refusal:
            for src in cit_result.validated_sources:
                yield f"event: citation\ndata: {json.dumps(src.model_dump())}\n\n"

        # 7. Persist assistant message
        asst_msg = await SessionStore.save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=final_pi_result.content,
            evidence_tier=effective_tier,
            latency_ms=elapsed_ms,
            model_used=final_pi_result.model_used,
        )

        if cit_result.validated_sources and not is_refusal:
            await SessionStore.save_source_references(db, asst_msg.id, cit_result.validated_sources)

        done_payload = {
            "message_id": asst_msg.id,
            "session_id": session_id,
            "latency_ms": elapsed_ms,
            "tier": effective_tier,
            "can_synthesize": effective_can_synthesize,
            "sources": [] if is_refusal else [s.model_dump() for s in cit_result.validated_sources],
            "agent": "pi-coding-agent",
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

