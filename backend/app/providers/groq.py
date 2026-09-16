"""Groq cloud generation provider implementation."""

from collections.abc import AsyncGenerator
import logging
from typing import Optional
import httpx
from groq import AsyncGroq

from app.core.config import get_settings
from app.providers.base import GenerationProvider, ProviderConfigurationError

logger = logging.getLogger("lenny_assistant.providers.groq")
settings = get_settings()

GROQ_API_BASE = "https://api.groq.com/openai/v1"


class GroqGenerationProvider(GenerationProvider):
    """Cloud generation provider using Groq models (e.g. llama-3.3-70b-versatile)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        key = api_key or settings.GROQ_API_KEY
        if not key or not key.strip():
            raise ProviderConfigurationError(
                "Groq API key is not configured. Set the GROQ_API_KEY environment variable, "
                "configure it in the provider settings UI, or update your .env configuration."
            )
        self.api_key = key.strip()
        self._model = model or settings.GROQ_MODEL
        self._client: Optional[AsyncGroq] = None

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        if hasattr(self, "_resolved_model") and self._resolved_model:
            return self._resolved_model
        return self._model

    def _get_client(self) -> AsyncGroq:
        if self._client is None:
            self._client = AsyncGroq(api_key=self.api_key)
        return self._client

    @staticmethod
    async def validate_api_key(api_key: str, timeout: float = 8.0) -> tuple[bool, str]:
        """
        Validate a Groq API key against the models endpoint.
        Returns (is_valid, message). Fast check with zero token generation.
        """
        clean_key = api_key.strip()
        if not clean_key:
            return False, "API key cannot be empty."

        url = f"{GROQ_API_BASE}/models"
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
            return False, "Validation request timed out connecting to Groq API."
        except Exception as exc:
            return False, f"Network error connecting to Groq API: {exc}"

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

    async def _resolve_fallback_model(self, client: AsyncGroq) -> Optional[str]:
        try:
            models_resp = await client.models.list()
            avail = {m.id for m in models_resp.data}
            preferred = [
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "qwen/qwen3.8-27b",
                "groq/compound",
            ]
            for p in preferred:
                if p in avail:
                    return p
        except Exception as err:
            logger.warning("Failed to query Groq models list for fallback: %s", err)
        return None

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        client = self._get_client()
        formatted_msgs = self._format_messages(messages, system_prompt)
        target_model = self.model_name

        try:
            try:
                response = await client.chat.completions.create(
                    model=target_model,
                    messages=formatted_msgs,  # type: ignore[arg-type]
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception as exc:
                exc_str = str(exc)
                if "404" in exc_str or "model_not_found" in exc_str or "does not exist" in exc_str:
                    fallback = await self._resolve_fallback_model(client)
                    if fallback and fallback != target_model:
                        logger.info(
                            "Groq model '%s' not accessible; falling back to active Groq model '%s'",
                            target_model,
                            fallback,
                        )
                        self._resolved_model = fallback
                        response = await client.chat.completions.create(
                            model=fallback,
                            messages=formatted_msgs,  # type: ignore[arg-type]
                            max_tokens=max_tokens,
                            temperature=temperature,
                        )
                    else:
                        raise
                else:
                    raise

            if response.choices and response.choices[0].message:
                return response.choices[0].message.content or ""
            return ""
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            logger.error("Groq API call failed: %s", exc)
            raise ProviderConfigurationError(f"Groq generation error: {exc}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        formatted_msgs = self._format_messages(messages, system_prompt)
        target_model = self.model_name

        try:
            try:
                response_stream = await client.chat.completions.create(
                    model=target_model,
                    messages=formatted_msgs,  # type: ignore[arg-type]
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )
            except Exception as exc:
                exc_str = str(exc)
                if "404" in exc_str or "model_not_found" in exc_str or "does not exist" in exc_str:
                    fallback = await self._resolve_fallback_model(client)
                    if fallback and fallback != target_model:
                        logger.info(
                            "Groq model '%s' not accessible; falling back to active Groq model '%s'",
                            target_model,
                            fallback,
                        )
                        self._resolved_model = fallback
                        response_stream = await client.chat.completions.create(
                            model=fallback,
                            messages=formatted_msgs,  # type: ignore[arg-type]
                            max_tokens=max_tokens,
                            temperature=temperature,
                            stream=True,
                        )
                    else:
                        raise
                else:
                    raise

            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            logger.error("Groq streaming failed: %s", exc)
            raise ProviderConfigurationError(f"Groq streaming error: {exc}") from exc
