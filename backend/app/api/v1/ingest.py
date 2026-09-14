"""Ingestion status and corpus statistics endpoint."""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.core.logging import get_logger
from app.db.session import engine

router = APIRouter(prefix="/ingest", tags=["Ingestion"])
logger = get_logger(__name__)


class IngestStatusResponse(BaseModel):
    """Corpus ingestion statistics and vector index status."""
    total_episodes: int
    total_chunks: int
    chunks_with_embeddings: int
    unique_guests: int
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None
    hnsw_index_ready: bool
    status: str


@router.get("/status", response_model=IngestStatusResponse)
async def get_ingest_status() -> dict[str, Any]:
    """
    Return current corpus statistics from PostgreSQL and pgvector.
    Reports total episodes, chunk counts, embedded vector count, and HNSW index status.
    """
    try:
        async with engine.connect() as conn:
            # Episode stats
            ep_res = await conn.execute(
                text(
                    """
                    SELECT 
                        COUNT(*), 
                        COUNT(DISTINCT guest),
                        MIN(publication_date),
                        MAX(publication_date)
                    FROM episodes;
                    """
                )
            )
            ep_row = ep_res.fetchone()
            total_episodes = ep_row[0] if ep_row else 0
            unique_guests = ep_row[1] if ep_row else 0
            earliest_date = str(ep_row[2]) if ep_row and ep_row[2] else None
            latest_date = str(ep_row[3]) if ep_row and ep_row[3] else None

            # Chunk stats
            chunk_res = await conn.execute(
                text(
                    """
                    SELECT 
                        COUNT(*),
                        COUNT(embedding)
                    FROM transcript_chunks;
                    """
                )
            )
            chunk_row = chunk_res.fetchone()
            total_chunks = chunk_row[0] if chunk_row else 0
            chunks_with_embeddings = chunk_row[1] if chunk_row else 0

            # Check HNSW index status
            idx_res = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM pg_indexes
                    WHERE tablename = 'transcript_chunks' 
                      AND indexname = 'idx_chunks_embedding_hnsw';
                    """
                )
            )
            idx_count = idx_res.scalar() or 0
            hnsw_index_ready = idx_count > 0

        return {
            "total_episodes": total_episodes,
            "total_chunks": total_chunks,
            "chunks_with_embeddings": chunks_with_embeddings,
            "unique_guests": unique_guests,
            "earliest_date": earliest_date,
            "latest_date": latest_date,
            "hnsw_index_ready": hnsw_index_ready,
            "status": "ready" if total_chunks > 0 else "empty",
        }
    except Exception as e:
        logger.error("Failed to query ingest status: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query database ingestion status: {str(e)}",
        ) from e
