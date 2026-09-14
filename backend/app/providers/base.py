"""Base abstractions for generation providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Optional


class ProviderConfigurationError(Exception):
    """Raised when a generation provider is misconfigured or lacks mandatory credentials."""
    pass


class GenerationProvider(ABC):
    """Abstract base class for LLM generation providers (Ollama, Anthropic)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the generation provider (e.g. 'ollama', 'anthropic')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model being invoked (e.g. 'llama3.1:8b', 'claude-3-5-sonnet-20241022')."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        """Generate a complete text response asynchronously."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """Stream token deltas asynchronously."""
        pass
