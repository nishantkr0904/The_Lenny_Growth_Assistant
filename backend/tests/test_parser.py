"""Unit tests for transcript frontmatter parsing and normalization."""

from datetime import date
from pathlib import Path
import pytest

from app.ingestion.parser import normalize_text, parse_transcript_text


def test_parse_valid_frontmatter():
    sample = """---
guest: Brian Chesky
title: Brian Chesky’s new playbook
youtube_url: https://www.youtube.com/watch?v=4ef0juAMqoE
video_id: 4ef0juAMqoE
publish_date: 2023-11-12
description: 'Brian Chesky is the co-founder and CEO of Airbnb.'
duration_seconds: 4408.0
duration: '1:13:28'
view_count: 381905
channel: Lenny's Podcast
keywords:
- growth
- leadership
---

# Brian Chesky’s new playbook

## Transcript

Brian Chesky (00:00:00):
Way too many founders apologize for how they want to run the company.

Lenny (00:01:01):
Today my guest is Brian Chesky.
"""
    result = parse_transcript_text(sample, "episodes/brian-chesky/transcript.md")
    assert result.metadata.guest == "Brian Chesky"
    assert result.metadata.title == "Brian Chesky’s new playbook"
    assert result.metadata.publish_date == date(2023, 11, 12)
    assert result.metadata.publication_date == date(2023, 11, 12)
    assert result.metadata.youtube_url == "https://www.youtube.com/watch?v=4ef0juAMqoE"
    assert result.metadata.video_id == "4ef0juAMqoE"
    assert result.metadata.duration_seconds == 4408.0
    assert result.metadata.duration == "1:13:28"
    assert result.metadata.view_count == 381905
    assert result.metadata.channel == "Lenny's Podcast"
    assert "leadership" in result.metadata.keywords
    assert result.metadata.source_path == "episodes/brian-chesky/transcript.md"

    # Normalized text checks
    assert not result.content.startswith("# Brian Chesky")
    assert not result.content.startswith("## Transcript")
    assert "Brian Chesky (00:00:00):" in result.content
    assert "Lenny (00:01:01):" in result.content


def test_parse_missing_frontmatter_fallback():
    sample = """Brian Chesky (00:00:00):
This is direct dialogue without any YAML header.
"""
    result = parse_transcript_text(sample, "episodes/brian-chesky/transcript.md")
    assert result.metadata.guest == "Brian Chesky"
    assert "Brian Chesky" in result.metadata.title
    assert result.metadata.publication_date is None
    assert result.metadata.youtube_url is None
    assert result.metadata.source_path == "episodes/brian-chesky/transcript.md"
    assert "This is direct dialogue" in result.content


def test_parse_corrupt_frontmatter_fallback():
    sample = """---
this is invalid yaml: [unclosed list
---

Lenny (00:00:00):
Hello everyone.
"""
    result = parse_transcript_text(sample, "episodes/elena-verna/transcript.md")
    assert result.metadata.guest == "Elena Verna"
    assert result.metadata.publication_date is None
    assert "Hello everyone." in result.content


def test_normalize_unicode_characters():
    dirty = "“Smart quotes” and ‘single quotes’ — with em-dash and\u00a0non-breaking space."
    clean = normalize_text(dirty)
    assert clean == '"Smart quotes" and \'single quotes\' -- with em-dash and non-breaking space.'
