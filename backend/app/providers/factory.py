"""Factory for resolving and instantiating generation providers."""

import logging
from typing import Optional

from app.core.config import get_settings
from app.providers.anthropic import AnthropicGenerationProvider
from app.providers.base import GenerationProvider, ProviderConfigurationError
from app.providers.ollama import OllamaGenerationProvider

logger = logging.getLogger("lenny_assistant.providers.factory")
settings = get_settings()


def get_generation_provider(provider_name: Optional[str] = None) -> GenerationProvider:
    """
    Resolve and instantiate the configured GenerationProvider.
    Enforces strict configuration validation: never silently falls back to Ollama if a cloud provider fails.
    """
    selected = (provider_name or settings.LLM_PROVIDER).strip().lower()

    if selected == "ollama":
        return OllamaGenerationProvider()

    if selected == "anthropic":
        return AnthropicGenerationProvider()

    if selected == "openai":
        raise ProviderConfigurationError(
            "OpenAI provider adapter is scheduled for Phase P2.1 and is not enabled for P0. "
            "Supported P0 generation providers are 'ollama' (default local) and 'anthropic' (cloud)."
        )

    raise ProviderConfigurationError(
        f"Unsupported LLM_PROVIDER '{selected}'. Supported providers are: 'ollama', 'anthropic'."
    )
