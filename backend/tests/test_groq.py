"""Unit tests for Groq cloud generation provider."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.providers.base import ProviderConfigurationError
from app.providers.factory import get_generation_provider
from app.providers.groq import GroqGenerationProvider
from app.providers.manager import ProviderManager


def test_groq_missing_key_raises_error():
    """Verify Groq provider fails immediately when API key is missing."""
    with patch("app.providers.groq.settings.GROQ_API_KEY", None):
        with pytest.raises(ProviderConfigurationError) as exc_info:
            GroqGenerationProvider(api_key=None)
        assert "Groq API key is not configured" in str(exc_info.value)


def test_groq_provider_with_key():
    """Verify Groq provider initializes cleanly when API key is provided."""
    provider = GroqGenerationProvider(api_key="gsk_test_valid_key_12345", model="llama-3.3-70b-versatile")
    assert provider.provider_name == "groq"
    assert provider.model_name == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_groq_generate_mock():
    """Verify Groq generate constructs proper client call and returns content."""
    provider = GroqGenerationProvider(api_key="gsk_test_valid_key_12345", model="llama-3.3-70b-versatile")

    mock_choice = MagicMock()
    mock_choice.message.content = "Groq lightning-fast strategy response."
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_resp
    provider._client = mock_client

    output = await provider.generate(
        messages=[{"role": "user", "content": "Explain product led growth."}],
        system_prompt="Be concise and helpful.",
    )
    assert output == "Groq lightning-fast strategy response."
    mock_client.chat.completions.create.assert_called_once()
    kwargs = mock_client.chat.completions.create.call_args[1]
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][0]["content"] == "Be concise and helpful."
    assert kwargs["messages"][1]["role"] == "user"
    assert kwargs["messages"][1]["content"] == "Explain product led growth."


@pytest.mark.asyncio
async def test_groq_stream_mock():
    """Verify Groq streaming yields delta tokens cleanly."""
    provider = GroqGenerationProvider(api_key="gsk_test_valid_key_12345", model="llama-3.3-70b-versatile")

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
async def test_groq_validate_api_key_valid():
    """Verify validate_api_key returns True when Groq returns 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        is_valid, msg = await GroqGenerationProvider.validate_api_key("gsk_valid_test_key")
        assert is_valid is True
        assert "valid" in msg.lower()


@pytest.mark.asyncio
async def test_groq_validate_api_key_invalid():
    """Verify validate_api_key returns False when Groq returns 401 error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {
        "error": {
            "message": "Invalid API Key",
            "type": "invalid_request_error",
            "code": "invalid_api_key",
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        is_valid, msg = await GroqGenerationProvider.validate_api_key("gsk_bad_key")
        assert is_valid is False
        assert "Invalid API Key" in msg


@pytest.mark.asyncio
async def test_groq_validate_api_key_timeout():
    """Verify validate_api_key handles timeouts cleanly."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        is_valid, msg = await GroqGenerationProvider.validate_api_key("gsk_some_key")
        assert is_valid is False
        assert "timed out" in msg.lower()


def test_groq_factory_resolution():
    """Verify get_generation_provider resolves Groq when configured and raises when not."""
    # When key is present
    with patch.object(ProviderManager.get_instance(), "get_groq_api_key", return_value="gsk_test_key"):
        prov = get_generation_provider("groq")
        assert isinstance(prov, GroqGenerationProvider)
        assert prov.api_key == "gsk_test_key"

    # When key is absent
    with patch.object(ProviderManager.get_instance(), "get_groq_api_key", return_value=None):
        with patch("app.providers.groq.settings.GROQ_API_KEY", None):
            with pytest.raises(ProviderConfigurationError):
                get_generation_provider("groq")


@pytest.mark.asyncio
async def test_groq_stream_openai_compatible_chunk_formats():
    """Verify Groq stream correctly handles empty, None, and valid delta chunks."""
    provider = GroqGenerationProvider(api_key="gsk_test_valid_key_12345", model="llama-3.3-70b-versatile")

    # Various chunk formats (empty delta, delta with None content, delta with text, empty choices)
    chunk_empty_choices = MagicMock(choices=[])
    chunk_none_delta = MagicMock(choices=[MagicMock(delta=None)])
    chunk_none_content = MagicMock(choices=[MagicMock(delta=MagicMock(content=None))])
    chunk_valid_1 = MagicMock(choices=[MagicMock(delta=MagicMock(content="First "))])
    chunk_empty_str = MagicMock(choices=[MagicMock(delta=MagicMock(content=""))])
    chunk_valid_2 = MagicMock(choices=[MagicMock(delta=MagicMock(content="Second"))])

    async def mock_stream_iter():
        for ch in [chunk_empty_choices, chunk_none_delta, chunk_valid_1, chunk_none_content, chunk_empty_str, chunk_valid_2]:
            yield ch

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_stream_iter()
    provider._client = mock_client

    chunks = []
    async for chunk in provider.stream(messages=[{"role": "user", "content": "Hi"}]):
        chunks.append(chunk)

    assert chunks == ["First ", "Second"]
    assert "".join(chunks) == "First Second"


@pytest.mark.asyncio
async def test_groq_auth_failure_surfaced_correctly():
    """Verify Groq 401 authentication failure raises ProviderConfigurationError."""
    provider = GroqGenerationProvider(api_key="gsk_invalid_key")
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("401: Invalid API Key")
    provider._client = mock_client

    with pytest.raises(ProviderConfigurationError) as exc_info:
        await provider.generate(messages=[{"role": "user", "content": "Hello"}])
    assert "Groq generation error" in str(exc_info.value)

    with pytest.raises(ProviderConfigurationError) as exc_info:
        async for _ in provider.stream(messages=[{"role": "user", "content": "Hello"}]):
            pass
    assert "Groq streaming error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_groq_timeout_surfaced_correctly():
    """Verify Groq timeout surfaces as ProviderConfigurationError."""
    provider = GroqGenerationProvider(api_key="gsk_valid_key")
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = httpx.TimeoutException("Read timeout after 10s")
    provider._client = mock_client

    with pytest.raises(ProviderConfigurationError) as exc_info:
        await provider.generate(messages=[{"role": "user", "content": "Hello"}])
    assert "Groq generation error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_groq_model_fallback_on_404():
    """Verify Groq falls back to available model when requested model returns 404."""
    provider = GroqGenerationProvider(api_key="gsk_valid_key", model="llama-3.3-70b-versatile")
    mock_client = AsyncMock()

    # First call with llama-3.3-70b-versatile throws 404
    mock_404 = Exception("404: The model `llama-3.3-70b-versatile` does not exist")
    mock_success = MagicMock(choices=[MagicMock(message=MagicMock(content="Fallback response"))])

    mock_client.chat.completions.create.side_effect = [mock_404, mock_success]
    mock_client.models.list.return_value = MagicMock(data=[MagicMock(id="openai/gpt-oss-120b")])
    provider._client = mock_client

    res = await provider.generate(messages=[{"role": "user", "content": "Test"}])
    assert res == "Fallback response"
    assert mock_client.chat.completions.create.call_count == 2
    assert mock_client.chat.completions.create.call_args_list[1][1]["model"] == "openai/gpt-oss-120b"


def test_provider_selection_guard_for_unconfigured_groq():
    """Verify provider selection does not activate Groq without a valid configured key."""
    mgr = ProviderManager.get_instance()
    mgr.set_active_provider("ollama")

    with patch.object(mgr, "is_groq_configured", return_value=False):
        with pytest.raises(ValueError) as exc_info:
            mgr.set_active_provider("groq")
        assert "not configured" in str(exc_info.value).lower()
        assert mgr.get_active_provider() == "ollama"


@pytest.mark.asyncio
async def test_groq_generation_failure_does_not_appear_as_successful_answer():
    """Verify failed generation is flagged as failure and does not produce empty successful answers."""
    from app.agent.orchestrator import QnAOrchestrator
    from app.agent.pi_bridge import PiTurnResult

    orch = QnAOrchestrator()
    mock_bridge = MagicMock()

    # Simulate Pi bridge returning an empty content result (generation failed)
    async def mock_stream(*args, **kwargs):
        yield {"event": "evidence", "data": {"tier": "Strong", "chunk_count": 3, "top_score": 0.85, "can_synthesize": True}}
        yield {
            "event": "result",
            "data": PiTurnResult(
                content="",
                tier="Strong",
                top_score=0.85,
                can_synthesize=True,
                model_used="groq/llama-3.3-70b-versatile",
                generation_failed=True,
                selected_evidence=[
                    {
                        "chunk_id": "c-1",
                        "episode_id": "ep-1",
                        "title": "Title",
                        "guest": "Guest",
                        "source_path": "/path",
                        "chunk_index": 1,
                        "content": "Evidence content",
                        "similarity_score": 0.85,
                    }
                ],
            ),
        }

    mock_bridge.stream_turn = mock_stream
    orch.pi_bridge = mock_bridge

    mock_db = AsyncMock()
    with patch("app.agent.orchestrator.SessionStore.get_session", return_value=MagicMock()), \
         patch("app.agent.orchestrator.SessionStore.save_message", return_value=MagicMock(id="msg-1")), \
         patch("app.agent.orchestrator.SessionStore.get_recent_messages", return_value=[]), \
         patch.object(ProviderManager.get_instance(), "get_active_provider", return_value="groq"), \
         patch.object(ProviderManager.get_instance(), "get_groq_api_key", return_value="gsk_key"):

        events = []
        async for sse_chunk in orch.stream_turn("sess-1", "What is LNO?", mock_db):
            events.append(sse_chunk)

        full_stream = "".join(events)
        assert "event: delta" in full_stream
        assert "Generation failed with Groq" in full_stream
        assert '"generation_status": "failed"' in full_stream
        assert '"sources": []' in full_stream

