"""Health and service readiness endpoints."""

import httpx
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.session import get_db

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Service health check")
async def health_check(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Verify service readiness: PostgreSQL connectivity and Ollama server reachability.

    P0.1 Constraint: Verifies service reachability only, not model readiness/download status.
    """
    db_status = "disconnected"
    ollama_status = "unreachable"

    # 1. Verify PostgreSQL connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "connected"
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        db_status = "disconnected"

    # 2. Verify Ollama reachability (HTTP GET /api/tags)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            if response.status_code == 200:
                ollama_status = "reachable"
            else:
                logger.warning(
                    "Ollama health check returned non-200 status: %s",
                    response.status_code,
                )
    except Exception as exc:
        logger.warning("Ollama service unreachable at %s: %s", settings.OLLAMA_BASE_URL, exc)
        ollama_status = "unreachable"

    overall_status = "ok" if (db_status == "connected" and ollama_status == "reachable") else "degraded"
    http_status_code = status.HTTP_200_OK

    # If database is down, service is unavailable
    if db_status == "disconnected":
        overall_status = "unhealthy"
        http_status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    payload = {
        "status": overall_status,
        "database": db_status,
        "ollama": ollama_status,
        "provider": settings.LLM_PROVIDER,
        "version": "0.1.0",
    }

    return JSONResponse(status_code=http_status_code, content=payload)
