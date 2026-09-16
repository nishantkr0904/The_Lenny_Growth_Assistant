"""Unit tests for OpenAI cloud generation provider."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.providers.base import ProviderConfigurationError
from app.providers.factory import get_generation_provider
from app.providers.manager import ProviderManager
from app.providers.openai import OpenAIGenerationProvider


def test_openai_missing_key_raises_error():
    """Verify OpenAI provider fails immediately when API key is missing."""
    with patch("app.providers.openai.settings.OPENAI_API_KEY", None):
        with pytest.raises(ProviderConfigurationError) as exc_info:
            OpenAIGenerationProvider(api_key=None)
        assert "OpenAI API key is not configured" in str(exc_info.value)


def test_openai_provider_with_key():
    """Verify OpenAI provider initializes cleanly when API key is provided."""
    provider = OpenAIGenerationProvider(api_key="sk-test-valid-key-12345", model="gpt-4o")
    assert provider.provider_name == "openai"
    assert provider.model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_openai_generate_mock():
    """Verify OpenAI generate constructs proper client call and returns content."""
    provider = OpenAIGenerationProvider(api_key="sk-test-valid-key-12345", model="gpt-4o")

    mock_choice = MagicMock()
    mock_choice.message.content = "OpenAI synthesized strategy advice."
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_resp
    provider._client = mock_client

    output = await provider.generate(
        messages=[{"role": "user", "content": "How to scale B2B SaaS?"}],
        system_prompt="Be concise and helpful.",
    )
    assert output == "OpenAI synthesized strategy advice."
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args[1]
    assert kwargs["model"] == "gpt-4o"
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][0]["content"] == "Be concise and helpful."
    assert kwargs["messages"][1]["role"] == "user"
    assert kwargs["messages"][1]["content"] == "How to scale B2B SaaS?"


@pytest.mark.asyncio
async def test_openai_stream_mock():
    """Verify OpenAI streaming yields delta tokens cleanly."""
    provider = OpenAIGenerationProvider(api_key="sk-test-valid-key-12345", model="gpt-4o")

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hello "))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content="world!"))]

    async def mock_stream_iter():
        yield chunk1
        yield chunk2

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_stream_iter()
    provider._client = mock_client

    chunks = []
    async for chunk in provider.stream(messages=[{"role": "user", "content": "Hi"}]):
        chunks.append(chunk)

    assert "".join(chunks) == "Hello world!"


@pytest.mark.asyncio
async def test_openai_validate_api_key_valid():
    """Verify validate_api_key returns True when OpenAI returns 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        is_valid, msg = await OpenAIGenerationProvider.validate_api_key("sk-valid-test-key")
        assert is_valid is True
        assert "valid" in msg.lower()


@pytest.mark.asyncio
async def test_openai_validate_api_key_invalid():
    """Verify validate_api_key returns False when OpenAI returns 401 error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {
        "error": {
            "message": "Incorrect API key provided: sk-invalid. You can find your API key at https://platform.openai.com/account/api-keys.",
            "type": "invalid_request_error",
            "param": None,
            "code": "invalid_api_key",
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        is_valid, msg = await OpenAIGenerationProvider.validate_api_key("sk-bad-key")
        assert is_valid is False
        assert "Incorrect API key provided" in msg


@pytest.mark.asyncio
async def test_openai_validate_api_key_timeout():
    """Verify validate_api_key handles timeouts cleanly."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        is_valid, msg = await OpenAIGenerationProvider.validate_api_key("sk-some-key")
        assert is_valid is False
        assert "timed out" in msg.lower()


def test_openai_factory_resolution():
    """Verify get_generation_provider resolves OpenAI when configured and raises when not."""
    # When key is present
    with patch.object(ProviderManager.get_instance(), "get_openai_api_key", return_value="sk-test-key"):
        prov = get_generation_provider("openai")
        assert isinstance(prov, OpenAIGenerationProvider)
        assert prov.api_key == "sk-test-key"

    # When key is absent
    with patch.object(ProviderManager.get_instance(), "get_openai_api_key", return_value=None):
        with patch("app.providers.openai.settings.OPENAI_API_KEY", None):
            with pytest.raises(ProviderConfigurationError):
                get_generation_provider("openai")
