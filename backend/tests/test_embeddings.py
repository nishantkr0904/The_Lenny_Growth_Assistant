"""Unit and integration tests for OllamaEmbeddingProvider."""

import asyncio
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.ingestion.embeddings import EXPECTED_EMBEDDING_DIMENSION, OllamaEmbeddingProvider


def test_embedding_provider_initialization():
    provider = OllamaEmbeddingProvider(
        base_url="http://localhost:11434/",
        model="nomic-embed-text",
        timeout=30.0,
    )
    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "nomic-embed-text"
    assert provider.endpoint == "http://localhost:11434/api/embeddings"
    assert provider.timeout == 30.0


@pytest.mark.asyncio
async def test_embed_empty_text_raises_error():
    provider = OllamaEmbeddingProvider()
    with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
        await provider.embed_text("   ")


@pytest.mark.asyncio
async def test_embed_dimension_mismatch_raises_error():
    provider = OllamaEmbeddingProvider()
    fake_vector = [0.1] * 512  # Wrong dimension (expected 768)

    mock_response = httpx.Response(
        status_code=200,
        json={"embedding": fake_vector},
        request=httpx.Request("POST", provider.endpoint),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(ValueError, match="Embedding dimension mismatch: expected 768, got 512"):
            await provider.embed_text("Test prompt")


@pytest.mark.asyncio
async def test_embed_batch_preserves_order():
    provider = OllamaEmbeddingProvider()
    vec1 = [0.1] * 768
    vec2 = [0.2] * 768

    async def fake_embed_text(text: str):
        if text == "first":
            await asyncio.sleep(0.02)
            return vec1
        return vec2

    with patch.object(provider, "embed_text", side_effect=fake_embed_text):
        results = await provider.embed_batch(["first", "second"])
        assert len(results) == 2
        assert results[0] == vec1
        assert results[1] == vec2


@pytest.mark.asyncio
async def test_live_embedding_generation():
    """Live integration test against Ollama nomic-embed-text."""
    provider = OllamaEmbeddingProvider()
    try:
        vec = await provider.embed_text("Lenny's Podcast product strategy")
        assert len(vec) == EXPECTED_EMBEDDING_DIMENSION
        assert all(isinstance(v, float) for v in vec)
    except ConnectionError:
        pytest.skip("Ollama service not reachable for live test")
