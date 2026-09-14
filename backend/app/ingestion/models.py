"""Data models for the transcript ingestion pipeline."""

from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, Field


class EpisodeMetadata(BaseModel):
    """Metadata extracted from transcript frontmatter or path fallback."""

    title: str = Field(..., description="Episode title")
    guest: str = Field(..., description="Featured guest name")
    publication_date: Optional[date] = Field(None, description="Episode release date")
    source_path: str = Field(..., description="Relative canonical path to transcript file")
    episode_url: Optional[str] = Field(None, description="Podcast web page URL")
    youtube_url: Optional[str] = Field(None, description="YouTube recording URL")
    description: Optional[str] = Field(None, description="Episode synopsis/description")
    video_id: Optional[str] = Field(None, description="YouTube video ID")
    duration_seconds: Optional[float] = Field(None, description="Duration in seconds")
    duration: Optional[str] = Field(None, description="Human-readable duration (HH:MM:SS)")
    view_count: Optional[int] = Field(None, description="YouTube view count at capture time")
    channel: Optional[str] = Field(None, description="Channel/podcast name")
    keywords: list[str] = Field(default_factory=list, description="Categorization keywords/tags")

    @property
    def publish_date(self) -> Optional[date]:
        """Convenience alias for publication_date matching frontmatter field name."""
        return self.publication_date


class RawTranscript(BaseModel):
    """Parsed transcript containing structured metadata and normalized dialogue text."""

    metadata: EpisodeMetadata
    content: str = Field(..., description="Cleaned, normalized dialogue content")


class ProcessedChunk(BaseModel):
    """A semantic chunk ready for embedding and persistence."""

    chunk_index: int = Field(..., description="0-indexed position within the episode")
    speaker: Optional[str] = Field(None, description="Primary speaker or speaker turn label")
    content: str = Field(..., description="Chunk content with metadata preamble")
    content_hash: str = Field(..., description="Deterministic SHA-256 content hash")
    embedding: Optional[list[float]] = Field(None, description="768-dim vector embedding")
    token_count: int = Field(0, description="Estimated token count")


class IngestionStats(BaseModel):
    """Summary metrics recorded during an ingestion run."""

    files_discovered: int = 0
    episodes_parsed: int = 0
    episodes_upserted: int = 0
    chunks_created: int = 0
    chunks_skipped: int = 0
    embeddings_generated: int = 0
    failures: list[dict[str, Any]] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
