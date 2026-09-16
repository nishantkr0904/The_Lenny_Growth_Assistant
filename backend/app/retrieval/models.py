"""Data models for retrieval, evidence items, and grounding decisions."""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GroundingTier(str, Enum):
    """Canonical 4-tier grounding taxonomy."""
    STRONG = "Strong"
    LIMITED = "Limited"
    CONFLICTING = "Conflicting"
    INSUFFICIENT = "Insufficient"

    @classmethod
    def from_str(cls, val: object) -> "GroundingTier":
        """Safely parse a string or enum into canonical GroundingTier."""
        if isinstance(val, cls):
            return val
        if not val or not isinstance(val, str):
            return cls.INSUFFICIENT
        val_clean = val.strip().lower()
        mapping = {
            "strong": cls.STRONG,
            "limited": cls.LIMITED,
            "conflicting": cls.CONFLICTING,
            "insufficient": cls.INSUFFICIENT,
        }
        return mapping.get(val_clean, cls.INSUFFICIENT)



class EvidenceItem(BaseModel):
    """A single retrieved transcript chunk with source attribution and similarity score."""

    chunk_id: str = Field(..., description="UUID of the transcript chunk")
    episode_id: str = Field(..., description="UUID of the parent episode")
    title: str = Field(..., description="Episode title")
    guest: str = Field(..., description="Featured guest name")
    publication_date: Optional[date] = Field(None, description="Publication date")
    source_path: str = Field(..., description="Canonical source file path")
    chunk_index: int = Field(..., description="Chunk position within the episode")
    speaker: Optional[str] = Field(None, description="Speaker attribution")
    content: str = Field(..., description="Substantive transcript chunk content")
    similarity_score: float = Field(..., description="Cosine similarity score [0.0 - 1.0]")
    source_identifier: str = Field(..., description="Human-readable citation identifier")
    excerpt: str = Field(..., description="Short substantive excerpt of the chunk")


class SourceDiversity(BaseModel):
    """Metadata regarding the distribution of retrieved evidence across episodes and guests."""

    episode_count: int = Field(0, description="Number of distinct episodes represented")
    guest_count: int = Field(0, description="Number of distinct guests represented")
    guests: list[str] = Field(default_factory=list, description="Unique guest names")
    episodes: list[str] = Field(default_factory=list, description="Unique episode titles")


class GroundingDecision(BaseModel):
    """Deterministic triage decision produced by GroundingGate."""

    tier: GroundingTier = Field(..., description="Assigned grounding tier")
    can_synthesize: bool = Field(..., description="Whether evidence permits answer synthesis")
    top_score: float = Field(0.0, description="Maximum similarity score among retrieved chunks")
    confidence_score: float = Field(0.0, description="Overall confidence assessment [0.0 - 1.0]")
    selected_evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Curated evidence items passed to future synthesis",
    )
    source_diversity: SourceDiversity = Field(
        default_factory=SourceDiversity,
        description="Source distribution statistics",
    )
    reason: str = Field(..., description="Human-readable rationale for the decision")


class RetrievalRequest(BaseModel):
    """Request contract for semantic retrieval."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(15, ge=1, le=50, description="Number of top candidates to retrieve")


class RetrievalResponse(BaseModel):
    """Response contract containing query, decision, and evidence items."""

    query: str = Field(..., description="Original user query")
    normalized_query: str = Field(..., description="Normalized search query used for retrieval")
    decision: GroundingDecision = Field(..., description="Grounding Gate decision")
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="All retrieved candidate chunks prior to gate filtering",
    )
