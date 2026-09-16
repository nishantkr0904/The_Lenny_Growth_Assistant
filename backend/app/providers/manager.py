"""Runtime Provider Manager.

Manages active LLM generation provider selection and evaluator-configured
cloud API credentials in memory with optional local container persistence.
Strictly decoupled from embedding generation (which remains fixed to nomic-embed-text).
"""

import logging
import os
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger("lenny_assistant.providers.manager")
settings = get_settings()

SECRETS_DIR = Path(os.environ.get("SECRETS_DIR", "/app/.secrets"))
ANTHROPIC_KEY_FILE = SECRETS_DIR / "anthropic_key"
GEMINI_KEY_FILE = SECRETS_DIR / "gemini_key"
OPENAI_KEY_FILE = SECRETS_DIR / "openai_key"
GROQ_KEY_FILE = SECRETS_DIR / "groq_key"


class ProviderManager:
    """Singleton manager controlling active generation provider and credentials."""

    _instance: Optional["ProviderManager"] = None

    def __init__(self) -> None:
        self._active_provider: str = settings.LLM_PROVIDER.lower()
        self._anthropic_api_key: Optional[str] = settings.ANTHROPIC_API_KEY
        self._gemini_api_key: Optional[str] = settings.GEMINI_API_KEY
        self._openai_api_key: Optional[str] = settings.OPENAI_API_KEY
        self._groq_api_key: Optional[str] = settings.GROQ_API_KEY

        # Load persisted Anthropic key from local secrets file if present and not set via env
        if not self._anthropic_api_key and ANTHROPIC_KEY_FILE.exists():
            try:
                saved_key = ANTHROPIC_KEY_FILE.read_text(encoding="utf-8").strip()
                if saved_key:
                    self._anthropic_api_key = saved_key
                    logger.info("Loaded persisted Anthropic API key from secure local store.")
            except Exception as exc:
                logger.warning("Could not read local Anthropic key file: %s", exc)

        # Load persisted Gemini key from local secrets file if present and not set via env
        if not self._gemini_api_key and GEMINI_KEY_FILE.exists():
            try:
                saved_gemini_key = GEMINI_KEY_FILE.read_text(encoding="utf-8").strip()
                if saved_gemini_key:
                    self._gemini_api_key = saved_gemini_key
                    logger.info("Loaded persisted Gemini API key from secure local store.")
            except Exception as exc:
                logger.warning("Could not read local Gemini key file: %s", exc)

        # Load persisted OpenAI key from local secrets file if present and not set via env
        if not self._openai_api_key and OPENAI_KEY_FILE.exists():
            try:
                saved_openai_key = OPENAI_KEY_FILE.read_text(encoding="utf-8").strip()
                if saved_openai_key:
                    self._openai_api_key = saved_openai_key
                    logger.info("Loaded persisted OpenAI API key from secure local store.")
            except Exception as exc:
                logger.warning("Could not read local OpenAI key file: %s", exc)

        # Load persisted Groq key from local secrets file if present and not set via env
        if not self._groq_api_key and GROQ_KEY_FILE.exists():
            try:
                saved_groq_key = GROQ_KEY_FILE.read_text(encoding="utf-8").strip()
                if saved_groq_key:
                    self._groq_api_key = saved_groq_key
                    logger.info("Loaded persisted Groq API key from secure local store.")
            except Exception as exc:
                logger.warning("Could not read local Groq key file: %s", exc)

    @classmethod
    def get_instance(cls) -> "ProviderManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_active_provider(self) -> str:
        return self._active_provider

    def set_active_provider(self, provider: str) -> None:
        cleaned = provider.strip().lower()
        if cleaned not in ("ollama", "anthropic", "gemini", "openai", "groq"):
            raise ValueError(
                f"Unsupported provider '{provider}'. Must be 'ollama', 'anthropic', 'gemini', 'openai', or 'groq'."
            )

        if cleaned == "anthropic" and not self.is_anthropic_configured():
            raise ValueError("Anthropic API key is not configured. Please configure an API key first.")

        if cleaned == "gemini" and not self.is_gemini_configured():
            raise ValueError("Gemini API key is not configured. Please configure an API key first.")

        if cleaned == "openai" and not self.is_openai_configured():
            raise ValueError("OpenAI API key is not configured. Please configure an API key first.")

        if cleaned == "groq" and not self.is_groq_configured():
            raise ValueError("Groq API key is not configured. Please configure an API key first.")

        self._active_provider = cleaned
        logger.info("Switched active generation provider to '%s'", cleaned)

    def get_anthropic_api_key(self) -> Optional[str]:
        return self._anthropic_api_key

    def set_anthropic_api_key(self, api_key: str) -> None:
        cleaned = api_key.strip()
        if not cleaned:
            raise ValueError("API key cannot be empty.")
        self._anthropic_api_key = cleaned
        logger.info("Updated Anthropic cloud API key in runtime credential store.")

        # Persist to local container file if possible
        try:
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            ANTHROPIC_KEY_FILE.write_text(cleaned, encoding="utf-8")
            os.chmod(ANTHROPIC_KEY_FILE, 0o600)
        except Exception as exc:
            logger.warning("Could not persist Anthropic key to local disk: %s", exc)

    def is_anthropic_configured(self) -> bool:
        return bool(self._anthropic_api_key and self._anthropic_api_key.strip())

    def get_gemini_api_key(self) -> Optional[str]:
        return self._gemini_api_key

    def set_gemini_api_key(self, api_key: str) -> None:
        cleaned = api_key.strip()
        if not cleaned:
            raise ValueError("API key cannot be empty.")
        self._gemini_api_key = cleaned
        logger.info("Updated Google Gemini cloud API key in runtime credential store.")

        # Persist to local container file if possible
        try:
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            GEMINI_KEY_FILE.write_text(cleaned, encoding="utf-8")
            os.chmod(GEMINI_KEY_FILE, 0o600)
        except Exception as exc:
            logger.warning("Could not persist Gemini key to local disk: %s", exc)

    def is_gemini_configured(self) -> bool:
        return bool(self._gemini_api_key and self._gemini_api_key.strip())

    def get_openai_api_key(self) -> Optional[str]:
        return self._openai_api_key

    def set_openai_api_key(self, api_key: str) -> None:
        cleaned = api_key.strip()
        if not cleaned:
            raise ValueError("API key cannot be empty.")
        self._openai_api_key = cleaned
        logger.info("Updated OpenAI cloud API key in runtime credential store.")

        # Persist to local container file if possible
        try:
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            OPENAI_KEY_FILE.write_text(cleaned, encoding="utf-8")
            os.chmod(OPENAI_KEY_FILE, 0o600)
        except Exception as exc:
            logger.warning("Could not persist OpenAI key to local disk: %s", exc)

    def is_openai_configured(self) -> bool:
        return bool(self._openai_api_key and self._openai_api_key.strip())

    def get_groq_api_key(self) -> Optional[str]:
        return self._groq_api_key

    def set_groq_api_key(self, api_key: str) -> None:
        cleaned = api_key.strip()
        if not cleaned:
            raise ValueError("API key cannot be empty.")
        self._groq_api_key = cleaned
        logger.info("Updated Groq cloud API key in runtime credential store.")

        # Persist to local container file if possible
        try:
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            GROQ_KEY_FILE.write_text(cleaned, encoding="utf-8")
            os.chmod(GROQ_KEY_FILE, 0o600)
        except Exception as exc:
            logger.warning("Could not persist Groq key to local disk: %s", exc)

    def is_groq_configured(self) -> bool:
        return bool(self._groq_api_key and self._groq_api_key.strip())

    async def validate_gemini_key(self, api_key: str) -> tuple[bool, str]:
        from app.providers.gemini import GeminiGenerationProvider
        return await GeminiGenerationProvider.validate_api_key(api_key)

    async def validate_anthropic_key(self, api_key: str) -> tuple[bool, str]:
        from app.providers.anthropic import AnthropicGenerationProvider
        return await AnthropicGenerationProvider.validate_api_key(api_key)

    async def validate_openai_key(self, api_key: str) -> tuple[bool, str]:
        from app.providers.openai import OpenAIGenerationProvider
        return await OpenAIGenerationProvider.validate_api_key(api_key)

    async def validate_groq_key(self, api_key: str) -> tuple[bool, str]:
        from app.providers.groq import GroqGenerationProvider
        return await GroqGenerationProvider.validate_api_key(api_key)

    def get_provider_status(self) -> dict:
        """Return safe public provider metadata without ever exposing secret keys."""
        return {
            "active_provider": self._active_provider,
            "providers": [
                {
                    "id": "ollama",
                    "name": "Ollama",
                    "type": "local",
                    "model": settings.OLLAMA_MODEL,
                    "configured": True,
                },
                {
                    "id": "gemini",
                    "name": "Google Gemini",
                    "type": "cloud",
                    "model": settings.GEMINI_MODEL,
                    "configured": self.is_gemini_configured(),
                },
                {
                    "id": "anthropic",
                    "name": "Anthropic",
                    "type": "cloud",
                    "model": settings.ANTHROPIC_MODEL,
                    "configured": self.is_anthropic_configured(),
                },
                {
                    "id": "openai",
                    "name": "OpenAI",
                    "type": "cloud",
                    "model": settings.OPENAI_MODEL,
                    "configured": self.is_openai_configured(),
                },
                {
                    "id": "groq",
                    "name": "Groq",
                    "type": "cloud",
                    "model": settings.GROQ_MODEL,
                    "configured": self.is_groq_configured(),
                },
            ],
        }
