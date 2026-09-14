"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration specification for The Lenny Growth Assistant."""

    # Runtime
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@postgres:5432/lenny_growth"
    )

    # Host Port Mappings (optional host-side overrides; does not alter internal DATABASE_URL)
    HOST_PORT_POSTGRES: int = 5432
    HOST_PORT_BACKEND: int = 8000
    HOST_PORT_FRONTEND: int = 3000
    HOST_PORT_OLLAMA: int = 11434

    # Active LLM Provider (P0: 'ollama' default local, 'anthropic' selected cloud)
    LLM_PROVIDER: Literal["ollama", "anthropic", "openai"] = "ollama"

    # Ollama Configuration (Local Demo Default — Generation)
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_TIMEOUT_SECONDS: float = 180.0

    # Corpus Embedding (Fixed — always via Ollama nomic-embed-text at 768 dimensions)
    EMBED_MODEL: str = "nomic-embed-text"
    EMBED_DIMENSIONS: int = 768

    # Cloud Providers (Optional / Generation Only)
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"

    # Retrieval & Grounding Thresholds (Canonical: Strong, Limited, Conflicting, Insufficient)
    RETRIEVAL_TOP_K: int = 15
    GROUNDING_STRONG_THRESHOLD: float = 0.78
    GROUNDING_LIMITED_THRESHOLD: float = 0.65

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


settings = get_settings()
