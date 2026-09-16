"""Main FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.providers import router as providers_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    setup_logging(settings.LOG_LEVEL)
    logger.info(
        "Starting The Lenny Growth Assistant API (env=%s, provider=%s)",
        settings.ENVIRONMENT,
        settings.LLM_PROVIDER,
    )

    # Initialize database schema idempotently
    try:
        await init_db()
    except Exception as exc:
        logger.error("Failed to initialize database schema on startup: %s", exc)
        # In development/startup, log error and allow health endpoint to report status
    
    yield

    logger.info("Shutting down The Lenny Growth Assistant API")
    try:
        from app.agent.pi_bridge import PiBridgeClient
        await PiBridgeClient.get_instance().close()
    except Exception as exc:
        logger.warning("Error closing PiBridgeClient on shutdown: %s", exc)


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="The Lenny Growth Assistant API",
        description="Grounded conversational assistant over Lenny's Podcast transcripts",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Routers
    app.include_router(health_router, prefix="/api/v1")
    # Convenience alias for top-level /health
    app.include_router(health_router)
    app.include_router(ingest_router, prefix="/api/v1")
    app.include_router(retrieval_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(artifacts_router, prefix="/api/v1")
    app.include_router(providers_router, prefix="/api/v1")

    @app.get("/", summary="Root index")
    async def root_index() -> dict[str, str]:
        return {
            "name": "The Lenny Growth Assistant API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", exc)
        # RFC 7807 Problem Details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "type": "https://errors.lennygrowth.com/internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred. Please consult server logs.",
                "instance": str(request.url),
            },
        )

    return app


app = create_app()
