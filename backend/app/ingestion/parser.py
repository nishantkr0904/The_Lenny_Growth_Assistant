"""Transcript parser with YAML frontmatter extraction and text normalization."""

from datetime import date, datetime
import logging
from pathlib import Path
import re
from typing import Any, Optional
import yaml

from app.ingestion.models import EpisodeMetadata, RawTranscript

logger = logging.getLogger("lenny_assistant.ingestion.parser")

# Regex to isolate YAML frontmatter at start of file
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Patterns for normalizing Unicode quotes, dashes, and whitespace
UNICODE_REPLACEMENTS = [
    ("\u2018", "'"),  # Left single quote
    ("\u2019", "'"),  # Right single quote
    ("\u201c", '"'),  # Left double quote
    ("\u201d", '"'),  # Right double quote
    ("\u2013", "-"),  # En dash
    ("\u2014", "--"),  # Em dash
    ("\u00a0", " "),  # Non-breaking space
    ("\u2026", "..."),  # Horizontal ellipsis
]

# Patterns to strip markdown heading noise at transcript start
HEADING_PREFIX_PATTERN = re.compile(
    r"^(?:#\s+[^\n]+\n+)*(?:##\s+Transcript\s*\n+)?",
    re.IGNORECASE,
)


def _format_guest_from_path(folder_name: str) -> str:
    """Format a slugified guest directory name (e.g. 'brian-chesky') into Title Case."""
    parts = folder_name.replace("_", "-").split("-")
    return " ".join(part.capitalize() for part in parts if part)


def _parse_date(val: Any) -> Optional[date]:
    """Safely parse a date value from frontmatter."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val = val.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def normalize_text(text: str) -> str:
    """
    Normalize transcript text for deterministic chunking while strictly
    preserving verbatim textual dialogue and speaker turns.
    """
    if not text:
        return ""

    # Replace irregular Unicode characters
    for old, new in UNICODE_REPLACEMENTS:
        text = text.replace(old, new)

    # Normalize carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip initial markdown title/transcript headers
    text = HEADING_PREFIX_PATTERN.sub("", text)

    # Normalize excessive blank lines (more than 2 consecutive newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def parse_transcript_text(raw_text: str, source_path: str) -> RawTranscript:
    """
    Parse transcript raw text into EpisodeMetadata and normalized body content.
    If frontmatter is missing or corrupt, falls back to path-based inference.
    """
    match = FRONTMATTER_PATTERN.match(raw_text)
    frontmatter_data: dict[str, Any] = {}
    body_content = raw_text

    if match:
        frontmatter_str = match.group(1)
        body_content = raw_text[match.end():]
        try:
            parsed = yaml.safe_load(frontmatter_str)
            if isinstance(parsed, dict):
                frontmatter_data = parsed
            else:
                logger.warning("Frontmatter in %s is not a dictionary; falling back to path inference", source_path)
        except Exception as e:
            logger.warning("Failed to parse YAML frontmatter in %s (%s); falling back to path inference", source_path, e)
    else:
        logger.warning("No YAML frontmatter found in %s; falling back to path inference", source_path)

    # Derive fallback values from path
    path_obj = Path(source_path)
    # Expecting episodes/{guest-name}/transcript.md or similar
    parent_name = path_obj.parent.name if path_obj.parent else path_obj.stem
    fallback_guest = _format_guest_from_path(parent_name) if parent_name else "Unknown Guest"
    fallback_title = f"Lenny's Podcast: {fallback_guest}"

    # Extract metadata fields
    guest = str(frontmatter_data.get("guest") or fallback_guest).strip()
    title = str(frontmatter_data.get("title") or fallback_title).strip()
    pub_date = _parse_date(frontmatter_data.get("publish_date") or frontmatter_data.get("date"))

    episode_url = frontmatter_data.get("episode_url") or frontmatter_data.get("url")
    youtube_url = frontmatter_data.get("youtube_url") or frontmatter_data.get("youtube")
    video_id = frontmatter_data.get("video_id")
    description = frontmatter_data.get("description")
    
    # Handle duration_seconds (float or int)
    raw_duration_sec = frontmatter_data.get("duration_seconds")
    duration_seconds: Optional[float] = None
    if raw_duration_sec is not None:
        try:
            duration_seconds = float(raw_duration_sec)
        except (ValueError, TypeError):
            pass

    duration = str(frontmatter_data.get("duration")).strip() if frontmatter_data.get("duration") else None

    # Handle view_count
    raw_views = frontmatter_data.get("view_count")
    view_count: Optional[int] = None
    if raw_views is not None:
        try:
            view_count = int(raw_views)
        except (ValueError, TypeError):
            pass

    channel = frontmatter_data.get("channel")
    keywords = frontmatter_data.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = [str(keywords)]

    metadata = EpisodeMetadata(
        title=title,
        guest=guest,
        publication_date=pub_date,
        source_path=source_path,
        episode_url=str(episode_url).strip() if episode_url else None,
        youtube_url=str(youtube_url).strip() if youtube_url else None,
        description=str(description).strip() if description else None,
        video_id=str(video_id).strip() if video_id else None,
        duration_seconds=duration_seconds,
        duration=duration,
        view_count=view_count,
        channel=str(channel).strip() if channel else None,
        keywords=[str(k).strip() for k in keywords if k],
    )

    normalized_content = normalize_text(body_content)
    return RawTranscript(metadata=metadata, content=normalized_content)


def parse_transcript_file(file_path: Path, base_dir: Optional[Path] = None) -> RawTranscript:
    """
    Read and parse a transcript markdown file from the filesystem.
    Computes a clean, relative canonical source_path.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Transcript file not found: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")

    if base_dir and file_path.is_relative_to(base_dir):
        rel_path = file_path.relative_to(base_dir).as_posix()
    else:
        # Normalize relative to episodes/ if present
        parts = file_path.parts
        if "episodes" in parts:
            idx = parts.index("episodes")
            rel_path = Path(*parts[idx:]).as_posix()
        else:
            rel_path = file_path.as_posix()

    return parse_transcript_text(raw_text, source_path=rel_path)
