"""Unit tests for Google Gemini cloud generation provider."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.providers.base import ProviderConfigurationError
from app.providers.factory import get_generation_provider
from app.providers.gemini import GeminiGenerationProvider
from app.providers.manager import ProviderManager


def test_gemini_missing_key_raises_error():
    """Verify Gemini provider fails immediately when API key is missing."""
    with patch("app.providers.gemini.settings.GEMINI_API_KEY", None):
        with pytest.raises(ProviderConfigurationError) as exc_info:
            GeminiGenerationProvider(api_key=None)
        assert "Gemini API key is not configured" in str(exc_info.value)


def test_gemini_provider_with_key():
    """Verify Gemini provider initializes cleanly when API key is provided."""
    provider = GeminiGenerationProvider(api_key="AIzaSyTestKey12345", model="gemini-2.5-flash")
    assert provider.provider_name == "gemini"
    assert provider.model_name == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_gemini_generate_mock():
    """Verify Gemini generate constructs proper payload and returns content."""
    provider = GeminiGenerationProvider(api_key="AIzaSyTestKey12345", model="gemini-2.5-flash")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Gemini synthesis response for growth strategy."}],
                    "role": "model",
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        output = await provider.generate(
            messages=[{"role": "user", "content": "How to achieve PMF?"}],
            system_prompt="Be concise and helpful.",
        )
        assert output == "Gemini synthesis response for growth strategy."
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "gemini-2.5-flash:generateContent" in call_kwargs[0][0]
        assert call_kwargs[1]["json"]["systemInstruction"]["parts"][0]["text"] == "Be concise and helpful."


@pytest.mark.asyncio
async def test_gemini_stream_mock():
    """Verify Gemini streaming parses SSE lines and yields chunks."""
    provider = GeminiGenerationProvider(api_key="AIzaSyTestKey12345", model="gemini-2.5-flash")

    sse_lines = [
        'data: {"candidates": [{"content": {"parts": [{"text": "Hello "}]}}]}',
        'data: {"candidates": [{"content": {"parts": [{"text": "world!"}]}}]}',
        "",
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines

    class MockStreamContext:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient.stream", return_value=MockStreamContext()):
        collected = []
        async for chunk in provider.stream(messages=[{"role": "user", "content": "Hi"}]):
            collected.append(chunk)

        assert "".join(collected) == "Hello world!"


@pytest.mark.asyncio
async def test_gemini_validate_api_key_valid():
    """Verify validate_api_key returns True when Google returns 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        is_valid, msg = await GeminiGenerationProvider.validate_api_key("AIzaSyValidKey")
        assert is_valid is True
        assert "valid" in msg.lower()


@pytest.mark.asyncio
async def test_gemini_validate_api_key_invalid():
    """Verify validate_api_key returns False when Google returns 400 error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": {
            "code": 400,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "INVALID_ARGUMENT",
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        is_valid, msg = await GeminiGenerationProvider.validate_api_key("bad_key_123")
        assert is_valid is False
        assert "API key not valid" in msg


@pytest.mark.asyncio
async def test_gemini_validate_api_key_timeout():
    """Verify validate_api_key handles timeouts cleanly."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        is_valid, msg = await GeminiGenerationProvider.validate_api_key("some_key")
        assert is_valid is False
        assert "timed out" in msg.lower()


def test_gemini_factory_resolution():
    """Verify get_generation_provider resolves Gemini when configured and raises when not."""
    # When key is present
    with patch.object(ProviderManager.get_instance(), "get_gemini_api_key", return_value="AIzaSyTestKey"):
        prov = get_generation_provider("gemini")
        assert isinstance(prov, GeminiGenerationProvider)
        assert prov.api_key == "AIzaSyTestKey"

    # When key is absent
    with patch.object(ProviderManager.get_instance(), "get_gemini_api_key", return_value=None):
        with patch("app.providers.gemini.settings.GEMINI_API_KEY", None):
            with pytest.raises(ProviderConfigurationError):
                get_generation_provider("gemini")
