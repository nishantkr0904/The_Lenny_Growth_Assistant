"""Google Gemini cloud generation provider implementation."""

from collections.abc import AsyncGenerator
import json
import logging
from typing import Optional
import httpx

from app.core.config import get_settings
from app.providers.base import GenerationProvider, ProviderConfigurationError

logger = logging.getLogger("lenny_assistant.providers.gemini")
settings = get_settings()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiGenerationProvider(GenerationProvider):
    """Cloud generation provider using Google Gemini models (e.g. gemini-2.5-flash)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        key = api_key or settings.GEMINI_API_KEY
        if not key or not key.strip():
            raise ProviderConfigurationError(
                "Gemini API key is not configured. Set the GEMINI_API_KEY environment variable, "
                "configure it in the provider settings UI, or update your .env configuration."
            )
        self.api_key = key.strip()
        self._model = model or settings.GEMINI_MODEL

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @staticmethod
    async def validate_api_key(api_key: str, timeout: float = 8.0) -> tuple[bool, str]:
        """
        Validate a Gemini API key against Google's models endpoint.
        Returns (is_valid, message). Fast check with zero token generation.
        """
        clean_key = api_key.strip()
        if not clean_key:
            return False, "API key cannot be empty."

        url = f"{GEMINI_API_BASE}/models?key={clean_key}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
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
            return False, "Validation request timed out connecting to Google Gemini API."
        except Exception as exc:
            return False, f"Network error connecting to Google Gemini API: {exc}"

    def _format_contents(
        self,
        messages: list[dict[str, str]],
    ) -> list[dict]:
        """Format standard message list into Gemini API contents structure."""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            gemini_role = "model" if role == "assistant" else "user"
            text_content = msg.get("content", "")
            if text_content:
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": text_content}],
                })
        return contents

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        contents = self._format_contents(messages)
        url = f"{GEMINI_API_BASE}/models/{self.model_name}:generateContent?key={self.api_key}"

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise ProviderConfigurationError(
                        f"Google Gemini generation failed ({resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return ""
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(part.get("text", "") for part in parts)
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            raise ProviderConfigurationError(f"Gemini generation error: {exc}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        contents = self._format_contents(messages)
        url = f"{GEMINI_API_BASE}/models/{self.model_name}:streamGenerateContent?alt=sse&key={self.api_key}"

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        raise ProviderConfigurationError(
                            f"Google Gemini stream failed ({response.status_code}): {err_body.decode('utf-8', errors='replace')}"
                        )
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        raw_data = line[len("data: "):].strip()
                        if not raw_data:
                            continue
                        try:
                            parsed = json.loads(raw_data)
                            candidates = parsed.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            continue
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            logger.error("Gemini streaming failed: %s", exc)
            raise ProviderConfigurationError(f"Gemini streaming error: {exc}") from exc
