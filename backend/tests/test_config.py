"""Tests for application configuration and settings."""

import pytest
from app.core.config import Settings


def test_field_schema_defaults():
    """Verify class-level schema defaults match architecture specifications."""
    # Test Pydantic model field defaults
    fields = Settings.model_fields

    assert fields["GROUNDING_LIMITED_THRESHOLD"].default == 0.65
    assert fields["GROUNDING_STRONG_THRESHOLD"].default == 0.78
    assert fields["RETRIEVAL_TOP_K"].default == 15

    # Verification: Ensure no legacy 'weak' attribute exists in fields
    assert "GROUNDING_WEAK_THRESHOLD" not in fields

    # Embedding provider invariants
    assert fields["EMBED_MODEL"].default == "nomic-embed-text"
    assert fields["EMBED_DIMENSIONS"].default == 768

    # Default LLM provider
    assert fields["LLM_PROVIDER"].default == "ollama"
    assert fields["OLLAMA_MODEL"].default == "llama3.1:8b"
    assert fields["OLLAMA_BASE_URL"].default == "http://ollama:11434"

    # PostgreSQL internal port & default host port mapping
    assert fields["HOST_PORT_POSTGRES"].default == 5432
    assert "postgres:5432" in fields["DATABASE_URL"].default
    assert "lenny_growth" in fields["DATABASE_URL"].default


def test_instantiated_settings():
    """Verify settings loaded in active environment."""
    settings = Settings()

    # Grounding thresholds
    assert settings.GROUNDING_LIMITED_THRESHOLD == 0.65
    assert settings.GROUNDING_STRONG_THRESHOLD == 0.78

    # Ensure internal DATABASE_URL is strictly on container port 5432
    assert "postgres:5432" in settings.DATABASE_URL
    assert "lenny_growth" in settings.DATABASE_URL


def test_custom_environment_settings(monkeypatch):
    """Verify settings overrides from environment variables."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-12345")
    monkeypatch.setenv("GROUNDING_LIMITED_THRESHOLD", "0.70")
    monkeypatch.setenv("HOST_PORT_POSTGRES", "5435")

    settings = Settings()
    assert settings.LLM_PROVIDER == "anthropic"
    assert settings.ANTHROPIC_API_KEY == "sk-ant-test-key-12345"
    assert settings.GROUNDING_LIMITED_THRESHOLD == 0.70
    assert settings.HOST_PORT_POSTGRES == 5435
    # Invariant: Host port override must NOT alter internal DATABASE_URL
    assert "postgres:5432" in settings.DATABASE_URL
