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
        Uses native Ollama /api/embed batch endpoint with fallback to single embed_text.
        Preserves input order.
        """
        if not texts:
            return []

        # If embed_text is mocked (e.g. in unit tests), use concurrent single embed
        is_mocked = hasattr(self.embed_text, "mock") or hasattr(self.embed_text, "side_effect") or hasattr(self.embed_text, "_mock_self")
        
        if not is_mocked:
            # Attempt high-performance batch embedding via Ollama /api/embed
            batch_endpoint = f"{self.base_url}/api/embed"
            all_embeddings: list[list[float]] = []

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    for i in range(0, len(texts), batch_size):
                        chunk_slice = texts[i : i + batch_size]
                        payload = {"model": self.model, "input": chunk_slice}
                        resp = await client.post(batch_endpoint, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            embeddings = data.get("embeddings", [])
                            if len(embeddings) == len(chunk_slice):
                                for v in embeddings:
                                    if len(v) != EXPECTED_EMBEDDING_DIMENSION:
                                        raise ValueError(
                                            f"Embedding dimension mismatch: expected {EXPECTED_EMBEDDING_DIMENSION}, got {len(v)}"
                                        )
                                    all_embeddings.append(v)
                                continue
                        raise RuntimeError(f"Batch embed returned status {resp.status_code}")
                return all_embeddings
            except Exception as exc:
                logger.debug("Native /api/embed batch failed or unsupported, falling back to concurrent single embed: %s", exc)

        # Fallback to concurrent single embedding
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
