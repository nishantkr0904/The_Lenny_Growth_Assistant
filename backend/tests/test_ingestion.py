"""Integration tests for the ingestion pipeline, persistence, and idempotency."""

from pathlib import Path
import tempfile
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import engine
from app.ingestion.embeddings import OllamaEmbeddingProvider
from app.ingestion.pipeline import IngestionPipeline
from app.main import app


class FakeEmbeddingProvider(OllamaEmbeddingProvider):
    """Deterministic mock embedding provider producing 768-dim vectors without Ollama."""

    async def embed_text(self, text: str) -> list[float]:
        return [0.01] * 768

    async def embed_batch(self, texts: list[str], batch_size: int = 32, concurrency: int = 4) -> list[list[float]]:
        return [[0.01] * 768 for _ in texts]


@pytest.fixture
def sample_transcript_dir(tmp_path: Path) -> Path:
    """Create a temporary directory structure with a sample episode."""
    ep_dir = tmp_path / "episodes" / "test-founder"
    ep_dir.mkdir(parents=True, exist_ok=True)
    transcript_file = ep_dir / "transcript.md"

    content = """---
guest: Test Founder
title: Building Great Products
youtube_url: https://www.youtube.com/watch?v=sample123
video_id: sample123
publish_date: 2024-02-15
description: Test episode description for automated testing.
duration_seconds: 1800.0
duration: '30:00'
view_count: 5000
channel: Lenny's Podcast
keywords:
- growth
- testing
---

# Building Great Products

## Transcript

Test Founder (00:00:00):
The most important metric for an early stage startup is retention. If retention is flat, you have a leaky bucket.

Lenny (00:01:00):
How do you define retention when you are just getting started?

Test Founder (00:01:15):
You look at cohort retention curves over 30, 60, and 90 days.
"""
    transcript_file.write_text(content, encoding="utf-8")
    return tmp_path


@pytest.mark.asyncio
async def test_pipeline_discovery(sample_transcript_dir: Path):
    pipeline = IngestionPipeline(embedding_provider=FakeEmbeddingProvider())
    files = pipeline.discover_transcript_files(sample_transcript_dir)
    assert len(files) == 1
    assert files[0].name == "transcript.md"


@pytest.mark.asyncio
async def test_pipeline_dry_run(sample_transcript_dir: Path):
    pipeline = IngestionPipeline(embedding_provider=FakeEmbeddingProvider())
    stats = await pipeline.run(sample_transcript_dir, dry_run=True)
    assert stats.files_discovered == 1
    assert stats.episodes_parsed == 1
    assert stats.episodes_upserted == 0
    assert stats.chunks_created > 0
    assert stats.embeddings_generated == 0
    assert len(stats.failures) == 0


@pytest.mark.asyncio
async def test_pipeline_idempotency_and_persistence(sample_transcript_dir: Path):
    pipeline = IngestionPipeline(
        embedding_provider=FakeEmbeddingProvider(),
        chunk_size=300,
        chunk_overlap=50,
    )

    # Clean up any leftover test data
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM episodes WHERE source_path LIKE '%test-founder%';"))

    try:
        # First ingestion run
        stats1 = await pipeline.run(sample_transcript_dir, dry_run=False)
        assert stats1.episodes_upserted == 1
        assert stats1.chunks_created > 0
        assert stats1.chunks_skipped == 0
        assert stats1.embeddings_generated == stats1.chunks_created
        initial_chunks = stats1.chunks_created

        # Verify data in PostgreSQL
        async with engine.connect() as conn:
            ep_res = await conn.execute(
                text("SELECT guest, title, duration_seconds FROM episodes WHERE source_path LIKE '%test-founder%';")
            )
            ep_row = ep_res.fetchone()
            assert ep_row is not None
            assert ep_row[0] == "Test Founder"
            assert ep_row[1] == "Building Great Products"
            assert float(ep_row[2]) == 1800.0

            chunk_res = await conn.execute(
                text(
                    """
                    SELECT COUNT(*), COUNT(embedding) 
                    FROM transcript_chunks tc
                    JOIN episodes e ON tc.episode_id = e.id
                    WHERE e.source_path LIKE '%test-founder%';
                    """
                )
            )
            chunk_count, embed_count = chunk_res.fetchone()
            assert chunk_count == initial_chunks
            assert embed_count == initial_chunks

        # Second ingestion run (idempotency verification)
        stats2 = await pipeline.run(sample_transcript_dir, dry_run=False)
        assert stats2.episodes_upserted == 1
        assert stats2.chunks_created == 0
        assert stats2.chunks_skipped == initial_chunks
        assert stats2.embeddings_generated == 0

        # Ensure chunk count in DB has not doubled
        async with engine.connect() as conn:
            count_res = await conn.execute(
                text(
                    """
                    SELECT COUNT(*) 
                    FROM transcript_chunks tc
                    JOIN episodes e ON tc.episode_id = e.id
                    WHERE e.source_path LIKE '%test-founder%';
                    """
                )
            )
            assert count_res.scalar() == initial_chunks
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM episodes WHERE source_path LIKE '%test-founder%';"))


def test_ingest_status_endpoint():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get("/api/v1/ingest/status")
    assert response.status_code == 200
    data = response.json()
    assert "total_episodes" in data
    assert "total_chunks" in data
    assert "chunks_with_embeddings" in data
    assert "hnsw_index_ready" in data
    assert data["hnsw_index_ready"] is True
