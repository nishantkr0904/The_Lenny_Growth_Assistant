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

    @staticmethod
    async def validate_api_key(api_key: str, timeout: float = 8.0) -> tuple[bool, str]:
        """
        Validate an Anthropic API key against the models endpoint.
        Returns (is_valid, message). Fast check with zero token generation.
        """
        clean_key = api_key.strip()
        if not clean_key:
            return False, "API key cannot be empty."

        import httpx
        url = "https://api.anthropic.com/v1/models"
        headers = {
            "x-api-key": clean_key,
            "anthropic-version": "2023-06-01",
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return True, "API key is valid."

                try:
                    err_json = resp.json()
                    err_msg = (
                        err_json.get("error", {}).get("message")
                        or f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                except Exception:
                    err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"

                return False, err_msg
        except httpx.TimeoutException:
            return False, "Validation request timed out connecting to Anthropic API."
        except Exception as exc:
            return False, f"Network error connecting to Anthropic API: {exc}"

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
