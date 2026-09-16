"""Deterministic Grounding Gate enforcing the 4 canonical evidence tiers."""

import logging
import re
from typing import Optional

from app.core.config import settings
from app.retrieval.models import (
    EvidenceItem,
    GroundingDecision,
    GroundingTier,
    SourceDiversity,
)

logger = logging.getLogger("lenny_assistant.retrieval.grounding")

# Contrastive and oppositional lexical signals for heuristic conflict triage
CONTRAST_PATTERNS = [
    re.compile(r"\b(disagree|contrary|opposite|on the other hand|in contrast|opposing|counter-argument)\b", re.IGNORECASE),
    re.compile(r"\b(never (?:work|do)|waste of time|anti-pattern|huge misconception|bad advice)\b", re.IGNORECASE),
    re.compile(r"\b(instead of|rather than|stop doing|failure mode)\b", re.IGNORECASE),
]


class GroundingGate:
    """
    Deterministic triage gate evaluating retrieved evidence before model synthesis.
    Enforces the 4 canonical tiers: Strong, Limited, Conflicting, Insufficient.
    """

    def __init__(
        self,
        strong_threshold: Optional[float] = None,
        limited_threshold: Optional[float] = None,
        max_synthesis_evidence: int = 5,
    ) -> None:
        self.strong_threshold = strong_threshold if strong_threshold is not None else settings.GROUNDING_STRONG_THRESHOLD
        self.limited_threshold = limited_threshold if limited_threshold is not None else settings.GROUNDING_LIMITED_THRESHOLD
        self.max_synthesis_evidence = max_synthesis_evidence

    def _compute_source_diversity(self, evidence: list[EvidenceItem]) -> SourceDiversity:
        """Calculate distribution of evidence across episodes and guests."""
        unique_guests = list(dict.fromkeys(e.guest for e in evidence if e.guest))
        unique_episodes = list(dict.fromkeys(e.title for e in evidence if e.title))
        return SourceDiversity(
            episode_count=len(unique_episodes),
            guest_count=len(unique_guests),
            guests=unique_guests,
            episodes=unique_episodes,
        )

    def _detect_conflicting_perspectives(self, qualifying_chunks: list[EvidenceItem]) -> tuple[bool, str]:
        """
        Evaluate whether high-relevance evidence contains materially divergent perspectives.
        Requires >= 2 distinct guests and explicit contrasting/oppositional signals.
        """
        if len(qualifying_chunks) < 2:
            return False, ""

        def canonical_guest(name: str) -> str:
            cleaned = re.sub(r"\s+(?:Live|\d+\.\d+|\d+)$", "", name, flags=re.IGNORECASE).strip()
            return cleaned


        distinct_guests = list(
            dict.fromkeys(
                canonical_guest(c.guest)
                for c in qualifying_chunks
                if c.guest and "lenny" not in c.guest.lower() and "various" not in c.guest.lower()
            )
        )

        if len(distinct_guests) < 2:
            return False, ""

        # Check if chunks from different guests display contrastive lexical signals
        guest_has_contrast: dict[str, bool] = {}
        for c in qualifying_chunks:
            cg = canonical_guest(c.guest)
            has_signal = any(p.search(c.content) for p in CONTRAST_PATTERNS)
            if has_signal:
                guest_has_contrast[cg] = True

        # If contrast markers exist across chunks from differing guests
        if len(guest_has_contrast) >= 2 or (len(guest_has_contrast) >= 1 and len(distinct_guests) >= 2):
            guest_list_str = " and ".join(distinct_guests[:2])
            return True, f"Divergent perspectives identified between {guest_list_str}"


        return False, ""

    def triage(self, evidence: list[EvidenceItem]) -> GroundingDecision:
        """
        Evaluate retrieved evidence against empirical cosine thresholds.
        Returns a deterministic GroundingDecision.
        """
        if not evidence:
            return GroundingDecision(
                tier=GroundingTier.INSUFFICIENT,
                can_synthesize=False,
                top_score=0.0,
                confidence_score=0.0,
                selected_evidence=[],
                source_diversity=SourceDiversity(),
                reason="No relevant evidence found in Lenny's Podcast transcripts. Refusing query.",
            )

        top_score = max(e.similarity_score for e in evidence)
        diversity = self._compute_source_diversity(evidence)

        # Tier 3: Insufficient Evidence ($S < LIMITED_THRESHOLD)
        if top_score < self.limited_threshold:
            logger.info("GroundingGate: Insufficient tier (top_score=%.4f < %.4f)", top_score, self.limited_threshold)
            return GroundingDecision(
                tier=GroundingTier.INSUFFICIENT,
                can_synthesize=False,
                top_score=top_score,
                confidence_score=top_score,
                selected_evidence=[],  # Refusal prevents hallucination
                source_diversity=diversity,
                reason=(
                    f"Top similarity score ({top_score:.4f}) falls below minimum required threshold "
                    f"({self.limited_threshold:.2f}). Evidence is insufficient to answer reliably."
                ),
            )

        # Filter qualifying evidence items meeting minimum threshold
        qualifying = [e for e in evidence if e.similarity_score >= self.limited_threshold]
        selected = qualifying[: self.max_synthesis_evidence]

        # Tier 2a: Limited Evidence ($LIMITED_THRESHOLD <= S < STRONG_THRESHOLD)
        if top_score < self.strong_threshold:
            logger.info(
                "GroundingGate: Limited tier (%.4f <= top_score=%.4f < %.4f)",
                self.limited_threshold,
                top_score,
                self.strong_threshold,
            )
            return GroundingDecision(
                tier=GroundingTier.LIMITED,
                can_synthesize=True,
                top_score=top_score,
                confidence_score=round(top_score * 0.9, 4),
                selected_evidence=selected,
                source_diversity=self._compute_source_diversity(selected),
                reason=(
                    f"Evidence retrieved with moderate relevance ({top_score:.4f} in [{self.limited_threshold:.2f}, "
                    f"{self.strong_threshold:.2f})). Answer synthesis must note evidence limitations."
                ),
            )

        # Tier 1 or Tier 2b (top_score >= STRONG_THRESHOLD)
        # Check for conflicting perspectives across qualifying chunks meeting strong relevance
        strong_qualifying = [c for c in qualifying if c.similarity_score >= max(self.strong_threshold, top_score - 0.08)]
        is_conflicting, conflict_detail = self._detect_conflicting_perspectives(strong_qualifying)

        if is_conflicting:
            logger.info("GroundingGate: Conflicting tier detected (%s)", conflict_detail)
            return GroundingDecision(
                tier=GroundingTier.CONFLICTING,
                can_synthesize=True,
                top_score=top_score,
                confidence_score=round(top_score, 4),
                selected_evidence=selected,
                source_diversity=self._compute_source_diversity(selected),
                reason=(
                    f"Strong evidence retrieved ({top_score:.4f} >= {self.strong_threshold:.2f}), but multiple "
                    f"distinct viewpoints were detected: {conflict_detail}. Synthesis must present both sides."
                ),
            )

        # Tier 1: Strong Evidence ($S >= STRONG_THRESHOLD)
        logger.info("GroundingGate: Strong tier (top_score=%.4f >= %.4f)", top_score, self.strong_threshold)
        return GroundingDecision(
            tier=GroundingTier.STRONG,
            can_synthesize=True,
            top_score=top_score,
            confidence_score=round(top_score, 4),
            selected_evidence=selected,
            source_diversity=self._compute_source_diversity(selected),
            reason=(
                f"High-relevance evidence retrieved ({top_score:.4f} >= {self.strong_threshold:.2f}) directly "
                f"supporting grounded synthesis."
            ),
        )
