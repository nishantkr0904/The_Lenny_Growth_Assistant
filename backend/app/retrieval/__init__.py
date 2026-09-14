"""Vector retrieval and deterministic grounding package."""

from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.models import (
    EvidenceItem,
    GroundingDecision,
    GroundingTier,
    RetrievalRequest,
    RetrievalResponse,
    SourceDiversity,
)
from app.retrieval.query import normalize_query

__all__ = [
    "EvidenceItem",
    "GroundingDecision",
    "GroundingTier",
    "RetrievalRequest",
    "RetrievalResponse",
    "SourceDiversity",
    "VectorRetrievalEngine",
    "normalize_query",
]
