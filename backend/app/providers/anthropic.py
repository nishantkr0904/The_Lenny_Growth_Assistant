"""Anthropic Claude cloud generation provider implementation."""

from collections.abc import AsyncGenerator
import logging
from typing import Optional
from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.providers.base import GenerationProvider, ProviderConfigurationError

logger = logging.getLogger("lenny_assistant.providers.anthropic")
settings = get_settings()


class AnthropicGenerationProvider(GenerationProvider):
    """Cloud generation provider using Anthropic Claude models (e.g. claude-3-5-sonnet-20241022)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        key = api_key or settings.ANTHROPIC_API_KEY
        if not key or not key.strip():
            raise ProviderConfigurationError(
                "Anthropic API key is not configured. Set the ANTHROPIC_API_KEY environment variable "
                "or update your .env configuration when using LLM_PROVIDER=anthropic."
            )
        self.api_key = key.strip()
        self._model = model or settings.ANTHROPIC_MODEL
        self._client: Optional[AsyncAnthropic] = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    def _format_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Filter and format messages for Anthropic messages API (must be user/assistant roles)."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            # Anthropic API allows only 'user' and 'assistant' roles in messages array
            if role not in ("user", "assistant"):
                role = "user"
            formatted.append({"role": role, "content": msg.get("content", "")})
        return formatted

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        client = self._get_client()
        formatted_msgs = self._format_messages(messages)

        kwargs: dict = {
            "model": self.model_name,
            "messages": formatted_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = await client.messages.create(**kwargs)
            text_parts = [block.text for block in response.content if hasattr(block, "text")]
            return "".join(text_parts)
        except Exception as exc:
            logger.error("Anthropic API call failed: %s", exc)
            raise ProviderConfigurationError(f"Anthropic generation error: {exc}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        formatted_msgs = self._format_messages(messages)

        kwargs: dict = {
            "model": self.model_name,
            "messages": formatted_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            async with client.messages.stream(**kwargs) as stream_ctx:
                async for text in stream_ctx.text_stream:
                    yield text
        except Exception as exc:
            logger.error("Anthropic stream failed: %s", exc)
            raise ProviderConfigurationError(f"Anthropic streaming error: {exc}") from exc
