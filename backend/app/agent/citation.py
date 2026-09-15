"""Post-generation citation validation boundary.

Validates that model-generated responses cite only genuine, retrieved evidence chunks
and constructs structured SourceReferenceItem records for persistence and provenance.
"""

import logging
import re
from typing import Optional
from pydantic import BaseModel

from app.retrieval.models import EvidenceItem, GroundingTier
from app.sessions.models import SourceReferenceItem

logger = logging.getLogger("lenny_assistant.agent.citation")

UUID_REGEX = re.compile(r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b", re.IGNORECASE)


REFUSAL_PATTERNS = [
    re.compile(r"\bno\s+(?:relevant\s+)?information\b", re.IGNORECASE),
    re.compile(r"\bnot\s+(?:covered|discussed|mentioned|found)\b", re.IGNORECASE),
    re.compile(r"\bcould\s+not\s+find\b", re.IGNORECASE),
    re.compile(r"\bunable\s+to\s+find\b", re.IGNORECASE),
    re.compile(r"\bnot\s+contain\s+(?:any\s+)?information\b", re.IGNORECASE),
    re.compile(r"\btranscripts?\s+(?:do\s+not|does\s+not)\s+(?:contain|mention|discuss)\b", re.IGNORECASE),
    re.compile(r"\bthere\s+is\s+no\s+(?:record|mention|information)\b", re.IGNORECASE),
    re.compile(r"\bdoes\s+not\s+(?:discuss|mention|cover)\b", re.IGNORECASE),
]


class CitationValidationResult(BaseModel):
    """Result payload from citation validation."""

    is_valid: bool
    validated_sources: list[SourceReferenceItem]
    cited_chunk_ids: list[str]
    warnings: list[str] = []


class CitationValidator:
    """
    Deterministic validator verifying that response citations are structurally grounded
    in the evidence actually supplied to the agent.
    """

    @staticmethod
    def validate_and_extract(
        response_text: str,
        retrieved_evidence: list[EvidenceItem],
        can_synthesize: bool = True,
        tier: GroundingTier = GroundingTier.STRONG,
    ) -> CitationValidationResult:
        """
        Validate cited sources in response text against the retrieved evidence set.
        Guarantees zero sources are returned if the tier is Insufficient, synthesis is disallowed,
        or the response text expresses an explicit refusal.
        """
        is_refusal_text = any(p.search(response_text) for p in REFUSAL_PATTERNS)

        # Case 1: Insufficient grounding tier, synthesis disallowed, or refusal response
        if not can_synthesize or tier == GroundingTier.INSUFFICIENT or is_refusal_text:
            # Check if model fabricated UUIDs/citations despite refusal
            fabricated_uuids = UUID_REGEX.findall(response_text)
            if fabricated_uuids:
                logger.warning(
                    "Model response contains chunk IDs during refusal/Insufficient tier: %s",
                    fabricated_uuids,
                )
                return CitationValidationResult(
                    is_valid=False,
                    validated_sources=[],
                    cited_chunk_ids=fabricated_uuids,
                    warnings=["Model fabricated source IDs on an Insufficient/refusal evidence turn."],
                )
            return CitationValidationResult(
                is_valid=True,
                validated_sources=[],
                cited_chunk_ids=[],
                warnings=[],
            )


        # Case 2: Synthesized response with candidate evidence
        valid_chunk_map = {str(item.chunk_id).lower(): item for item in retrieved_evidence}
        valid_guest_names = {item.guest.lower(): item for item in retrieved_evidence if item.guest}

        # Check for UUID citations in text
        text_uuids = [u.lower() for u in UUID_REGEX.findall(response_text)]
        invalid_uuids = [u for u in text_uuids if u not in valid_chunk_map]

        warnings = []
        if invalid_uuids:
            warning_msg = f"Response referenced unknown/fabricated chunk IDs: {invalid_uuids}"
            logger.warning(warning_msg)
            warnings.append(warning_msg)
            # If all cited UUIDs are fabricated, fail validation
            if len(invalid_uuids) == len(text_uuids) and len(text_uuids) > 0:
                return CitationValidationResult(
                    is_valid=False,
                    validated_sources=[],
                    cited_chunk_ids=text_uuids,
                    warnings=warnings,
                )

        # Identify which evidence chunks were explicitly or contextually referenced
        matched_chunks: dict[str, EvidenceItem] = {}

        # 1. Direct UUID matches
        for uid in text_uuids:
            if uid in valid_chunk_map:
                matched_chunks[uid] = valid_chunk_map[uid]

        # 2. Source identifier or guest name matches in text
        lower_response = response_text.lower()
        for item in retrieved_evidence:
            chunk_key = str(item.chunk_id).lower()
            if chunk_key in matched_chunks:
                continue

            # Check verbatim source identifier [Guest - Title #Idx]
            if item.source_identifier and item.source_identifier.lower() in lower_response:
                matched_chunks[chunk_key] = item
                continue

            # Check guest mention
            if item.guest and item.guest.lower() in lower_response:
                matched_chunks[chunk_key] = item
                continue

        # If model did not explicitly tag chunks, attach top qualifying chunks
        # that formed the factual basis for synthesis (verifying substantive topical overlap)
        if not matched_chunks:
            words_in_response = set(re.findall(r"\b[a-z]{4,}\b", lower_response))
            for item in retrieved_evidence[:3]:
                chunk_words = set(re.findall(r"\b[a-z]{4,}\b", (item.excerpt or item.content or "").lower()))
                substantive_overlap = (words_in_response & chunk_words) - {
                    "this", "that", "with", "from", "have", "more", "what", "when", "about",
                    "your", "they", "will", "would", "there", "their", "which", "could", "also",
                    "podcast", "lenny", "episode", "transcript", "think", "said", "says"
                }
                if substantive_overlap or (item.guest and item.guest.lower() in lower_response):
                    matched_chunks[str(item.chunk_id).lower()] = item


        # Build verified SourceReferenceItems
        validated_sources = [
            SourceReferenceItem(
                chunk_id=str(item.chunk_id),
                episode_id=str(item.episode_id) if item.episode_id else None,
                title=item.title,
                guest=item.guest,
                similarity_score=item.similarity_score,
                quoted_excerpt=item.excerpt,
                source_identifier=item.source_identifier,
            )
            for item in matched_chunks.values()
        ]

        return CitationValidationResult(
            is_valid=True,
            validated_sources=validated_sources,
            cited_chunk_ids=list(matched_chunks.keys()),
            warnings=warnings,
        )
