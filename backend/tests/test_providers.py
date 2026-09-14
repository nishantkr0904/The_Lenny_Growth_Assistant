"""Unit tests for generation provider abstraction and provider switching."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.providers.anthropic import AnthropicGenerationProvider
from app.providers.base import ProviderConfigurationError
from app.providers.factory import get_generation_provider
from app.providers.ollama import OllamaGenerationProvider


def test_ollama_provider_initialization():
    """Verify Ollama provider default configuration."""
    provider = OllamaGenerationProvider(base_url="http://localhost:11434", model="llama3.1:8b")
    assert provider.provider_name == "ollama"
    assert provider.model_name == "llama3.1:8b"


@pytest.mark.asyncio
async def test_ollama_generate_mock():
    """Verify Ollama generate parses response payload."""
    provider = OllamaGenerationProvider(base_url="http://test-ollama:11434")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message": {"content": "This is grounded Lenny advice."}}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        output = await provider.generate(
            messages=[{"role": "user", "content": "How to scale?"}],
            system_prompt="Be concise.",
        )
        assert output == "This is grounded Lenny advice."
        mock_post.assert_called_once()


def test_anthropic_missing_key_raises_error():
    """Verify Anthropic provider fails immediately when API key is missing."""
    with patch("app.providers.anthropic.settings.ANTHROPIC_API_KEY", None):
        with pytest.raises(ProviderConfigurationError) as exc_info:
            AnthropicGenerationProvider(api_key=None)
        assert "Anthropic API key is not configured" in str(exc_info.value)


def test_anthropic_provider_with_key():
    """Verify Anthropic provider initializes cleanly when API key is provided."""
    provider = AnthropicGenerationProvider(api_key="sk-ant-test-key-12345", model="claude-3-5-sonnet-20241022")
    assert provider.provider_name == "anthropic"
    assert provider.model_name == "claude-3-5-sonnet-20241022"


@pytest.mark.asyncio
async def test_anthropic_generate_mock():
    """Verify Anthropic provider invokes messages.create and extracts text."""
    provider = AnthropicGenerationProvider(api_key="sk-ant-test-key-12345")

    mock_content_block = MagicMock()
    mock_content_block.text = "Synthesized Claude response."
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = mock_response
    provider._client = mock_client

    output = await provider.generate(
        messages=[{"role": "user", "content": "Tell me about product strategy."}],
        system_prompt="Be factual.",
    )
    assert output == "Synthesized Claude response."
    mock_client.messages.create.assert_called_once()


def test_provider_factory_resolution():
    """Verify provider factory correctly resolves providers and enforces configuration errors."""
    # Ollama
    ollama_prov = get_generation_provider("ollama")
    assert isinstance(ollama_prov, OllamaGenerationProvider)

    # Anthropic without key
    with patch("app.providers.anthropic.settings.ANTHROPIC_API_KEY", None):
        with pytest.raises(ProviderConfigurationError):
            get_generation_provider("anthropic")

    # OpenAI (deferred to P2)
    with pytest.raises(ProviderConfigurationError) as exc_p2:
        get_generation_provider("openai")
    assert "Phase P2.1" in str(exc_p2.value)

    # Invalid provider
    with pytest.raises(ProviderConfigurationError) as exc_inv:
        get_generation_provider("unknown-provider")
    assert "Unsupported LLM_PROVIDER" in str(exc_inv.value)
