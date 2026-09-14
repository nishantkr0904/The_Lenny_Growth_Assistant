"""API endpoints for vector retrieval and Grounding Gate triage."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.retrieval.engine import VectorRetrievalEngine
from app.retrieval.grounding import GroundingGate
from app.retrieval.models import RetrievalRequest, RetrievalResponse
from app.retrieval.query import normalize_query

logger = get_logger(__name__)

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])

# Singletons for retrieval engine and grounding gate
engine_instance = VectorRetrievalEngine()
gate_instance = GroundingGate()


@router.post("/search", response_model=RetrievalResponse, summary="Vector retrieval with Grounding Gate triage")
@router.post("/preview", response_model=RetrievalResponse, summary="Retrieval preview endpoint alias")
async def search_transcripts(
    request: RetrievalRequest,
    db: AsyncSession = Depends(get_db),
) -> RetrievalResponse:
    """
    Execute semantic cosine similarity search over transcript chunks and
    triage evidence through the deterministic Grounding Gate.
    """
    try:
        normalized_q = normalize_query(request.query)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    try:
        # 1. Retrieve candidates via pgvector
        evidence = await engine_instance.search(
            query=normalized_q,
            top_k=request.top_k,
            db=db,
        )

        # 2. Triage evidence through deterministic Grounding Gate
        decision = gate_instance.triage(evidence)

        return RetrievalResponse(
            query=request.query,
            normalized_query=normalized_q,
            decision=decision,
            evidence=evidence,
        )
    except ConnectionError as e:
        logger.error("Embedding provider connection failure: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service is currently unavailable. Please verify Ollama is running.",
        ) from e
    except Exception as e:
        logger.exception("Retrieval error for query %r: %s", request.query, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during vector retrieval: {str(e)}",
        ) from e
