"""Conversation-aware query rewriting module.

Transforms follow-up questions into self-contained, retrieval-ready queries
using bounded conversation history, resolving pronouns and implicit references
without generating answers or hallucinations.
"""

import logging
import re
from typing import Optional

from app.core.logging import get_logger
from app.retrieval.query import normalize_query
from app.sessions.models import MessageModel

logger = get_logger(__name__)

# Common pronouns and conversational follow-up triggers indicating context dependency
FOLLOWUP_TRIGGERS = {
    "she", "he", "they", "it", "his", "her", "their", "its",
    "that", "this", "these", "those",
    "what about", "how about", "tell me more", "why", "and what",
    "what else", "also", "and", "why so", "how so", "more details",
    "did she", "did he", "does she", "does he", "what did she", "what did he",
}

REWRITER_SYSTEM_PROMPT = (
    "You are a search query rewriter for Lenny's Podcast transcripts. "
    "Given the recent conversation history and a follow-up user question, rewrite the question into "
    "a single, self-contained semantic search query that resolves pronouns (e.g., 'she', 'he', 'that') "
    "and carries forward the specific person, product, or topic being discussed.\n\n"
    "CRITICAL CONSTRAINTS:\n"
    "1. Output ONLY the rewritten search query string.\n"
    "2. Do NOT answer the question or provide explanations.\n"
    "3. Do NOT invent new entities or facts not present in the conversation history.\n"
    "4. If the query is already self-contained, output it unchanged."
)


class ConversationQueryRewriter:
    """
    Transforms multi-turn conversational queries into standalone retrieval queries.
    Uses LLM when available, falling back to deterministic entity-linking heuristic.
    """

    def __init__(self, provider: Optional[any] = None) -> None:
        self.provider = provider

    @staticmethod
    def is_followup_query(query: str, history: list[MessageModel]) -> bool:
        """Determine if a query is likely dependent on previous conversation context."""
        if not history:
            return False

        q_lower = query.lower().strip()
        words = set(re.findall(r"\b[a-z]+\b", q_lower))

        # Check for pronoun or continuation triggers
        for trigger in FOLLOWUP_TRIGGERS:
            if trigger in words or q_lower.startswith(trigger):
                return True

        # Extremely short queries with prior history are almost always follow-ups
        if len(words) <= 3:
            return True

        return False

    @staticmethod
    def deterministic_rewrite(query: str, history: list[MessageModel]) -> str:
        """
        Deterministic fallback rewriter that extracts salient entities and topics
        from recent user/assistant turns to anchor the follow-up query.
        """
        if not history:
            return normalize_query(query)

        # Look at the most recent user question and assistant answer
        recent_contexts = []
        for msg in reversed(history[-4:]):
            content_snippet = msg.content[:300]
            # Extract proper nouns or capitalized word sequences (potential guests/topics)
            proper_nouns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content_snippet)
            # Filter common sentence starters
            salient = [
                pn for pn in proper_nouns
                if pn.lower() not in {"the", "according", "when", "what", "how", "this", "that", "in", "for", "to"}
            ]
            if salient:
                recent_contexts.extend(salient)

        # Deduplicate while preserving order
        seen = set()
        deduped_entities = []
        for ent in recent_contexts:
            if ent.lower() not in seen:
                seen.add(ent.lower())
                deduped_entities.append(ent)

        if deduped_entities:
            # Combine top 2 entities with the query
            anchors = " ".join(deduped_entities[:2])
            combined = f"{anchors} {query}"
            return normalize_query(combined)

        return normalize_query(query)

    async def rewrite(self, query: str, history: list[MessageModel]) -> str:
        """
        Rewrite a query into a standalone retrieval query using conversation context.
        Returns the normalized query.
        """
        normalized_q = normalize_query(query)

        if not history or not self.is_followup_query(normalized_q, history):
            return normalized_q

        # Format bounded history for rewriter
        formatted_history = []
        for msg in history[-6:]:
            formatted_history.append(f"{msg.role.capitalize()}: {msg.content[:400]}")
        history_text = "\n".join(formatted_history)

        if self.provider is not None:
            try:
                user_instruction = (
                    f"Conversation History:\n{history_text}\n\n"
                    f"Follow-up Question: {normalized_q}\n\n"
                    f"Rewritten Standalone Search Query:"
                )
                response = await self.provider.generate(
                    messages=[{"role": "user", "content": user_instruction}],
                    system_prompt=REWRITER_SYSTEM_PROMPT,
                    max_tokens=60,
                )
                candidate = response.strip().strip('"').strip("'")
                # Ensure the rewriter did not output an empty string or verbose explanation
                if candidate and len(candidate.split("\n")) == 1 and len(candidate) < 200:
                    rewritten = normalize_query(candidate)
                    logger.info("Rewrote query '%s' -> '%s'", normalized_q, rewritten)
                    return rewritten
            except Exception as exc:
                logger.warning("LLM query rewrite failed (%s), using deterministic fallback", exc)

        # Fallback to deterministic rewrite
        rewritten = self.deterministic_rewrite(normalized_q, history)
        logger.info("Deterministically rewrote query '%s' -> '%s'", normalized_q, rewritten)
        return rewritten
