"""Unit tests for speaker-aware semantic chunking and content hashing."""

import hashlib
import pytest

from app.ingestion.chunker import chunk_transcript, parse_speaker_turns
from app.ingestion.parser import parse_transcript_text


def test_parse_speaker_turns():
    sample = """
Brian Chesky (00:00:00):
Way too many founders apologize for how they want to run the company.
They find some midpoint between how they want to run a company.

Lenny (00:01:01):
Today my guest is Brian Chesky.

(00:01:27):
In our conversation, Brian shares an in-depth explanation.
"""
    turns = parse_speaker_turns(sample, default_speaker="Brian Chesky")
    assert len(turns) == 3
    assert turns[0].speaker == "Brian Chesky"
    assert turns[0].timestamp == "00:00:00"
    assert "founders apologize" in turns[0].text

    assert turns[1].speaker == "Lenny"
    assert turns[1].timestamp == "00:01:01"
    assert "guest is Brian Chesky" in turns[1].text

    # Anonymous timestamp continues previous speaker (Lenny)
    assert turns[2].speaker == "Lenny"
    assert turns[2].timestamp == "00:01:27"
    assert "shares an in-depth explanation" in turns[2].text


def test_chunk_transcript_context_preamble():
    raw_text = """---
guest: Elena Verna
title: 10 growth tactics
publish_date: 2025-01-19
---
Elena Verna (00:00:00):
Growth is a fairly new field with lots of experimentation.
Lenny (00:00:21):
What is number one on the list?
"""
    raw = parse_transcript_text(raw_text, "episodes/elena-verna/transcript.md")
    chunks = chunk_transcript(raw, chunk_size=300, chunk_overlap=50)
    assert len(chunks) >= 1
    first = chunks[0]
    expected_preamble = "[Episode: 10 growth tactics | Guest: Elena Verna | Date: 2025-01-19]"
    assert expected_preamble in first.content
    assert first.chunk_index == 0


def test_chunking_determinism_and_hash():
    raw_text = """---
guest: Brian Chesky
title: New Playbook
publish_date: 2023-11-12
---
Brian Chesky (00:00:00):
Founders must be in the details of the product every day.
Lenny (00:01:01):
How do you balance that with empowerment?
"""
    raw1 = parse_transcript_text(raw_text, "episodes/brian-chesky/transcript.md")
    chunks1 = chunk_transcript(raw1, chunk_size=200, chunk_overlap=40)

    raw2 = parse_transcript_text(raw_text, "episodes/brian-chesky/transcript.md")
    chunks2 = chunk_transcript(raw2, chunk_size=200, chunk_overlap=40)

    assert len(chunks1) == len(chunks2)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.chunk_index == c2.chunk_index
        assert c1.content_hash == c2.content_hash
        assert c1.content == c2.content
        # Verify manual hash matches
        expected_hash = hashlib.sha256(
            f"episodes/brian-chesky/transcript.md:{c1.chunk_index}:{c1.content}".encode("utf-8")
        ).hexdigest()
        assert c1.content_hash == expected_hash


def test_chunk_ordering_preserved():
    turns = [
        f"Speaker {i%2} (00:0{i}:00):\n" + ("Content turn with sufficient text to fill tokens. " * 8)
        for i in range(10)
    ]
    body = "\n\n".join(turns)
    raw_text = f"""---
guest: Test Guest
title: Ordering Test
publish_date: 2024-01-01
---

{body}
"""
    raw = parse_transcript_text(raw_text, "episodes/test-guest/transcript.md")
    chunks = chunk_transcript(raw, chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
