"""Knowledge ingestion pipeline orchestrating parsing, chunking, embedding, and idempotent storage."""

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import time
from typing import Optional
from sqlalchemy import text

from app.db.session import engine
from app.ingestion.chunker import chunk_transcript
from app.ingestion.embeddings import OllamaEmbeddingProvider
from app.ingestion.models import IngestionStats, ProcessedChunk, RawTranscript
from app.ingestion.parser import parse_transcript_file

logger = logging.getLogger("lenny_assistant.ingestion.pipeline")


class IngestionPipeline:
    """
    Coordinates end-to-end ingestion of Lenny's Podcast transcripts into PostgreSQL + pgvector.
    Guarantees idempotency via source_path and SHA-256 chunk content hashes.
    """

    def __init__(
        self,
        embedding_provider: Optional[OllamaEmbeddingProvider] = None,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
    ) -> None:
        self.embedding_provider = embedding_provider or OllamaEmbeddingProvider()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def discover_transcript_files(self, data_dir: Path) -> list[Path]:
        """
        Discover all transcript markdown files under the specified directory.
        Handles both episodes/{guest}/transcript.md and direct markdown directories.
        """
        if not data_dir.exists():
            logger.error("Data directory does not exist: %s", data_dir)
            return []

        # Find all transcript.md files first, or any .md files under episodes
        files = list(data_dir.glob("episodes/**/transcript.md"))
        if not files:
            # Fallback to any markdown files under episodes
            files = list(data_dir.glob("episodes/**/*.md"))
        if not files:
            # Fallback to any markdown files in root
            files = [f for f in data_dir.glob("**/*.md") if not f.name.startswith(".")]

        # Filter out non-transcript files (README, CLAUDE, etc.)
        ignored_names = {"readme.md", "claude.md", "contributing.md", "license.md"}
        valid_files = [f for f in files if f.name.lower() not in ignored_names]

        # Sort deterministically
        valid_files.sort(key=lambda p: str(p))
        return valid_files

    async def ingest_single_transcript(
        self,
        file_path: Path,
        base_dir: Optional[Path] = None,
        dry_run: bool = False,
        force_reembed: bool = False,
    ) -> tuple[int, int, int]:
        """
        Ingest a single transcript file.
        Returns: (chunks_created, chunks_skipped, embeddings_generated)
        """
        raw = parse_transcript_file(file_path, base_dir=base_dir)
        meta = raw.metadata
        chunks = chunk_transcript(
            raw,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        if dry_run:
            logger.info("[Dry Run] Parsed %s: %d chunks generated", meta.source_path, len(chunks))
            return len(chunks), 0, 0

        # Persist episode metadata
        async with engine.begin() as conn:
            upsert_episode_sql = text(
                """
                INSERT INTO episodes (
                    title, guest, publication_date, source_path,
                    episode_url, youtube_url, description, video_id,
                    duration_seconds, duration, view_count, channel
                ) VALUES (
                    :title, :guest, :publication_date, :source_path,
                    :episode_url, :youtube_url, :description, :video_id,
                    :duration_seconds, :duration, :view_count, :channel
                )
                ON CONFLICT (source_path) DO UPDATE SET
                    title = EXCLUDED.title,
                    guest = EXCLUDED.guest,
                    publication_date = EXCLUDED.publication_date,
                    episode_url = EXCLUDED.episode_url,
                    youtube_url = EXCLUDED.youtube_url,
                    description = EXCLUDED.description,
                    video_id = EXCLUDED.video_id,
                    duration_seconds = EXCLUDED.duration_seconds,
                    duration = EXCLUDED.duration,
                    view_count = EXCLUDED.view_count,
                    channel = EXCLUDED.channel
                RETURNING id;
                """
            )
            res = await conn.execute(
                upsert_episode_sql,
                {
                    "title": meta.title,
                    "guest": meta.guest,
                    "publication_date": meta.publication_date,
                    "source_path": meta.source_path,
                    "episode_url": meta.episode_url,
                    "youtube_url": meta.youtube_url,
                    "description": meta.description,
                    "video_id": meta.video_id,
                    "duration_seconds": meta.duration_seconds,
                    "duration": meta.duration,
                    "view_count": meta.view_count,
                    "channel": meta.channel,
                },
            )
            episode_id = res.scalar_one()

            # Query existing chunk hashes for this episode to check for idempotency
            existing_hashes_res = await conn.execute(
                text("SELECT content_hash FROM transcript_chunks WHERE episode_id = :episode_id"),
                {"episode_id": episode_id},
            )
            existing_hashes = {row[0].strip() for row in existing_hashes_res.fetchall()}

        # Identify chunks requiring embedding
        chunks_to_embed: list[ProcessedChunk] = []
        chunks_skipped = 0

        for chunk in chunks:
            if not force_reembed and chunk.content_hash in existing_hashes:
                chunks_skipped += 1
            else:
                chunks_to_embed.append(chunk)

        embeddings_generated = 0
        chunks_created = 0

        if chunks_to_embed:
            # Generate embeddings via Ollama in batch
            texts = [c.content for c in chunks_to_embed]
            embeddings = await self.embedding_provider.embed_batch(texts, batch_size=32)
            embeddings_generated = len(embeddings)

            # Insert chunks with embeddings
            async with engine.begin() as conn:
                insert_chunk_sql = text(
                    """
                    INSERT INTO transcript_chunks (
                        episode_id, chunk_index, speaker, content, embedding, content_hash
                    ) VALUES (
                        :episode_id, :chunk_index, :speaker, :content, :embedding, :content_hash
                    )
                    ON CONFLICT (content_hash) DO UPDATE SET
                        speaker = EXCLUDED.speaker,
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding;
                    """
                )
                for chunk, vector in zip(chunks_to_embed, embeddings):
                    # Format vector as pgvector-compatible bracketed string or list
                    vector_str = f"[{','.join(str(v) for v in vector)}]"
                    await conn.execute(
                        insert_chunk_sql,
                        {
                            "episode_id": episode_id,
                            "chunk_index": chunk.chunk_index,
                            "speaker": chunk.speaker,
                            "content": chunk.content,
                            "embedding": vector_str,
                            "content_hash": chunk.content_hash,
                        },
                    )
                    chunks_created += 1

        return chunks_created, chunks_skipped, embeddings_generated

    async def run(
        self,
        data_dir: Path,
        limit: Optional[int] = None,
        dry_run: bool = False,
        force_reembed: bool = False,
    ) -> IngestionStats:
        """
        Execute full ingestion pipeline across discovered transcript files.
        """
        start_time = time.perf_counter()
        stats = IngestionStats()

        files = self.discover_transcript_files(data_dir)
        stats.files_discovered = len(files)
        logger.info("Discovered %d transcript files in %s", len(files), data_dir)

        if not files:
            stats.elapsed_seconds = round(time.perf_counter() - start_time, 2)
            return stats

        target_files = files[:limit] if limit else files
        logger.info("Processing %d files (limit=%s, dry_run=%s)", len(target_files), limit, dry_run)

        for idx, file_path in enumerate(target_files, start=1):
            try:
                c_created, c_skipped, e_gen = await self.ingest_single_transcript(
                    file_path=file_path,
                    base_dir=data_dir,
                    dry_run=dry_run,
                    force_reembed=force_reembed,
                )
                stats.episodes_parsed += 1
                if not dry_run:
                    stats.episodes_upserted += 1
                stats.chunks_created += c_created
                stats.chunks_skipped += c_skipped
                stats.embeddings_generated += e_gen

                if idx % 10 == 0 or idx == len(target_files):
                    logger.info(
                        "[%d/%d] Ingested: %s (new_chunks=%d, skipped=%d)",
                        idx,
                        len(target_files),
                        file_path.parent.name,
                        c_created,
                        c_skipped,
                    )
            except Exception as e:
                logger.error("Failed to ingest %s: %s", file_path, e, exc_info=True)
                stats.failures.append({"file": str(file_path), "error": str(e)})

        stats.elapsed_seconds = round(time.perf_counter() - start_time, 2)
        logger.info(
            "Ingestion complete in %.2fs: %d episodes, %d chunks created, %d chunks skipped, %d embeddings, %d failures",
            stats.elapsed_seconds,
            stats.episodes_upserted,
            stats.chunks_created,
            stats.chunks_skipped,
            stats.embeddings_generated,
            len(stats.failures),
        )
        return stats
