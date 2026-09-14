"""Embedding provider client for Ollama nomic-embed-text (768 dimensions)."""

import asyncio
import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("lenny_assistant.ingestion.embeddings")

EXPECTED_EMBEDDING_DIMENSION = 768


class OllamaEmbeddingProvider:
    """
    Client for generating fixed 768-dimensional embeddings via Ollama.
    Strictly decoupled from generation providers (LLM_PROVIDER).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or str(settings.OLLAMA_BASE_URL)).rstrip("/")
        self.model = model or settings.EMBED_MODEL
        self.timeout = timeout
        self.endpoint = f"{self.base_url}/api/embeddings"

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single text string."""
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        payload = {
            "model": self.model,
            "prompt": text,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
            except httpx.ConnectError as e:
                logger.error("Failed to connect to Ollama embedding service at %s: %s", self.endpoint, e)
                raise ConnectionError(f"Cannot connect to Ollama embedding service at {self.endpoint}") from e
            except httpx.HTTPStatusError as e:
                logger.error("Ollama embedding service error (%s): %s", e.response.status_code, e.response.text)
                raise RuntimeError(f"Ollama embedding error: {e.response.text}") from e

        data = response.json()
        vector = data.get("embedding")
        if not vector or not isinstance(vector, list):
            raise ValueError(f"Ollama returned invalid embedding payload: {data}")

        if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIMENSION}, got {len(vector)}"
            )

        return vector

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        concurrency: int = 4,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts in controlled concurrent batches.
        Preserves input order.
        """
        if not texts:
            return []

        semaphore = asyncio.Semaphore(concurrency)

        async def _embed_with_semaphore(idx: int, t: str) -> tuple[int, list[float]]:
            async with semaphore:
                vec = await self.embed_text(t)
                return idx, vec

        tasks = [_embed_with_semaphore(i, t) for i, t in enumerate(texts)]
        results = await asyncio.gather(*tasks)

        # Sort by original index to ensure deterministic ordering
        results.sort(key=lambda x: x[0])
        return [vec for _, vec in results]
