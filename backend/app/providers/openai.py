"""OpenAI cloud generation provider implementation."""

from collections.abc import AsyncGenerator
import logging
from typing import Optional
import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.providers.base import GenerationProvider, ProviderConfigurationError

logger = logging.getLogger("lenny_assistant.providers.openai")
settings = get_settings()

OPENAI_API_BASE = "https://api.openai.com/v1"


class OpenAIGenerationProvider(GenerationProvider):
    """Cloud generation provider using OpenAI models (e.g. gpt-4o)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        key = api_key or settings.OPENAI_API_KEY
        if not key or not key.strip():
            raise ProviderConfigurationError(
                "OpenAI API key is not configured. Set the OPENAI_API_KEY environment variable, "
                "configure it in the provider settings UI, or update your .env configuration."
            )
        self.api_key = key.strip()
        self._model = model or settings.OPENAI_MODEL
        self._client: Optional[AsyncOpenAI] = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    @staticmethod
    async def validate_api_key(api_key: str, timeout: float = 8.0) -> tuple[bool, str]:
        """
        Validate an OpenAI API key against the models endpoint.
        Returns (is_valid, message). Fast check with zero token generation.
        """
        clean_key = api_key.strip()
        if not clean_key:
            return False, "API key cannot be empty."

        url = f"{OPENAI_API_BASE}/models"
        headers = {"Authorization": f"Bearer {clean_key}"}
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
            return False, "Validation request timed out connecting to OpenAI API."
        except Exception as exc:
            return False, f"Network error connecting to OpenAI API: {exc}"

    def _format_messages(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> list[dict[str, str]]:
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            if role not in ("system", "user", "assistant"):
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
        formatted_msgs = self._format_messages(messages, system_prompt)

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=formatted_msgs,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content or ""
            return ""
        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            raise ProviderConfigurationError(f"OpenAI generation error: {exc}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        formatted_msgs = self._format_messages(messages, system_prompt)

        try:
            response_stream = await client.chat.completions.create(
                model=self.model_name,
                messages=formatted_msgs,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            logger.error("OpenAI streaming failed: %s", exc)
            raise ProviderConfigurationError(f"OpenAI streaming error: {exc}") from exc
