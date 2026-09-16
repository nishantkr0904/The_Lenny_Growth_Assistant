"""Unit tests for generation provider abstraction and provider switching."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.providers.anthropic import AnthropicGenerationProvider
from app.providers.base import ProviderConfigurationError
from app.providers.factory import get_generation_provider
from app.providers.manager import ProviderManager
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
    with patch.object(ProviderManager.get_instance(), "get_anthropic_api_key", return_value=None):
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


def test_provider_manager_and_api(tmp_path):
    """Verify ProviderManager methods and providers API endpoints."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.providers.manager import ProviderManager

    manager = ProviderManager.get_instance()
    # Reset to known state
    manager._active_provider = "ollama"
    manager._anthropic_api_key = None
    manager._gemini_api_key = None

    client = TestClient(app)

    # 1. GET /api/v1/providers
    resp = client.get("/api/v1/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_provider"] == "ollama"
    assert len(data["providers"]) == 3
    ollama_info = next(p for p in data["providers"] if p["id"] == "ollama")
    assert ollama_info["configured"] is True
    gemini_info = next(p for p in data["providers"] if p["id"] == "gemini")
    assert gemini_info["configured"] is False
    anthropic_info = next(p for p in data["providers"] if p["id"] == "anthropic")
    assert anthropic_info["configured"] is False

    # 2. POST /api/v1/providers/select unconfigured fails (active provider remains ollama)
    unconf_gemini = client.post("/api/v1/providers/select", json={"provider": "gemini"})
    assert unconf_gemini.status_code == 400
    assert "Gemini API key is not configured" in unconf_gemini.json()["detail"]
    assert manager.get_active_provider() == "ollama"

    unconf_ant = client.post("/api/v1/providers/select", json={"provider": "anthropic"})
    assert unconf_ant.status_code == 400
    assert "Anthropic API key is not configured" in unconf_ant.json()["detail"]
    assert manager.get_active_provider() == "ollama"

    # Reject invalid provider selection
    bad_select = client.post("/api/v1/providers/select", json={"provider": "invalid-llm"})
    assert bad_select.status_code == 422

    # 3. POST /api/v1/providers/gemini/key with live validation
    with patch("app.providers.manager.SECRETS_DIR", tmp_path), \
         patch("app.providers.manager.GEMINI_KEY_FILE", tmp_path / "gemini_key"):

        # 3a. Invalid key fails, active remains ollama
        with patch.object(manager, "validate_gemini_key", new_callable=AsyncMock) as mock_val_gem:
            mock_val_gem.return_value = (False, "API key not valid")
            bad_key_resp = client.post("/api/v1/providers/gemini/key", json={"api_key": "bad-key"})
            assert bad_key_resp.status_code == 400
            assert "API key not valid" in bad_key_resp.json()["detail"]
            assert manager.get_active_provider() == "ollama"
            assert manager.get_gemini_api_key() is None

        # 3b. Empty key fails
        empty_key = client.post("/api/v1/providers/gemini/key", json={"api_key": "   "})
        assert empty_key.status_code == 400

        # 3c. Valid key succeeds and activates Gemini
        with patch.object(manager, "validate_gemini_key", new_callable=AsyncMock) as mock_val_gem:
            mock_val_gem.return_value = (True, "API key is valid.")
            key_resp = client.post("/api/v1/providers/gemini/key", json={"api_key": "AIzaSyTestValidRuntimeKey"})
            assert key_resp.status_code == 200
            assert key_resp.json()["active_provider"] == "gemini"
            assert manager.get_active_provider() == "gemini"
            gem_p = next(p for p in key_resp.json()["providers"] if p["id"] == "gemini")
            assert gem_p["configured"] is True
            assert manager.get_gemini_api_key() == "AIzaSyTestValidRuntimeKey"

    # 4. POST /api/v1/providers/anthropic/key with live validation
    with patch("app.providers.manager.SECRETS_DIR", tmp_path), \
         patch("app.providers.manager.ANTHROPIC_KEY_FILE", tmp_path / "anthropic_key"):

        # 4a. Invalid key fails, active remains gemini
        with patch.object(manager, "validate_anthropic_key", new_callable=AsyncMock) as mock_val_ant:
            mock_val_ant.return_value = (False, "Invalid x-api-key")
            bad_ant_resp = client.post("/api/v1/providers/anthropic/key", json={"api_key": "bad-ant-key"})
            assert bad_ant_resp.status_code == 400
            assert "Invalid x-api-key" in bad_ant_resp.json()["detail"]
            assert manager.get_active_provider() == "gemini"

        # 4b. Valid key succeeds and activates Anthropic
        with patch.object(manager, "validate_anthropic_key", new_callable=AsyncMock) as mock_val_ant:
            mock_val_ant.return_value = (True, "API key is valid.")
            ant_resp = client.post("/api/v1/providers/anthropic/key", json={"api_key": "sk-ant-test-runtime-key"})
            assert ant_resp.status_code == 200
            assert ant_resp.json()["active_provider"] == "anthropic"
            assert manager.get_active_provider() == "anthropic"
            ant_info = next(p for p in ant_resp.json()["providers"] if p["id"] == "anthropic")
            assert ant_info["configured"] is True

    # 5. Now that both are configured, switching via select works cleanly
    sel_gemini = client.post("/api/v1/providers/select", json={"provider": "gemini"})
    assert sel_gemini.status_code == 200
    assert sel_gemini.json()["active_provider"] == "gemini"
    assert manager.get_active_provider() == "gemini"

    sel_ollama = client.post("/api/v1/providers/select", json={"provider": "ollama"})
    assert sel_ollama.status_code == 200
    assert sel_ollama.json()["active_provider"] == "ollama"
    assert manager.get_active_provider() == "ollama"

    # Reset test state
    manager._anthropic_api_key = None
    manager._gemini_api_key = None
    manager._active_provider = "ollama"
