"""Ollama local generation provider implementation."""

from collections.abc import AsyncGenerator
import json
import logging
from typing import Optional
import httpx

from app.core.config import get_settings
from app.providers.base import GenerationProvider, ProviderConfigurationError

logger = logging.getLogger("lenny_assistant.providers.ollama")
settings = get_settings()


class OllamaGenerationProvider(GenerationProvider):
    """Local generation provider running containerized Ollama models (e.g. llama3.1:8b)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def _format_messages(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> list[dict[str, str]]:
        formatted: list[dict[str, str]] = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        formatted.extend(messages)
        return formatted

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": self._format_messages(messages, system_prompt),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            http_timeout = httpx.Timeout(connect=15.0, read=self.timeout, write=15.0, pool=15.0)
            async with httpx.AsyncClient(timeout=http_timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    raise ProviderConfigurationError(
                        f"Ollama generation error ({response.status_code}): {response.text}"
                    )
                data = response.json()
                return data.get("message", {}).get("content", "")
        except httpx.TimeoutException as exc:
            raise ProviderConfigurationError(
                f"Ollama generation timed out after {self.timeout}s at {self.base_url}: {exc}"
            ) from exc
        except httpx.ConnectError as exc:
            raise ProviderConfigurationError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure container is running: {exc}"
            ) from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": self._format_messages(messages, system_prompt),
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        raise ProviderConfigurationError(
                            f"Ollama stream error ({response.status_code}): {err_text.decode('utf-8', errors='replace')}"
                        )
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            delta = chunk.get("message", {}).get("content", "")
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError as exc:
            raise ProviderConfigurationError(
                f"Cannot connect to Ollama stream at {self.base_url}: {exc}"
            ) from exc
