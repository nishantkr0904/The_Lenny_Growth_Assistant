"""Speaker-aware semantic chunker with context injection and deterministic SHA-256 hashing."""

from dataclasses import dataclass
import hashlib
import logging
import re
from typing import Optional

from app.ingestion.models import ProcessedChunk, RawTranscript

logger = logging.getLogger("lenny_assistant.ingestion.chunker")

# Regex to identify speaker turn header: e.g., "Lenny (00:01:01):", "Brian Chesky:", "(00:02:17):"
SPEAKER_TURN_PATTERN = re.compile(
    r"^(?:([A-Za-z0-9 .\'-]+?)\s*(?:\(([0-9:]+)\))?|\(([0-9:]+)\)):\s*(.*)$"
)


@dataclass
class SpeakerTurn:
    """A single continuous turn of dialogue by a speaker."""
    speaker: Optional[str]
    timestamp: Optional[str]
    text: str

    @property
    def token_estimate(self) -> int:
        """Estimate token count based on word count (~1.33 tokens per word)."""
        words = len(self.text.split())
        return max(1, int(words * 1.33))


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string using standard ~1.33 tokens/word."""
    words = len(text.split())
    return max(1, int(words * 1.33))


def parse_speaker_turns(transcript_text: str, default_speaker: str = "Unknown") -> list[SpeakerTurn]:
    """
    Split normalized transcript text into sequential SpeakerTurn objects.
    Preserves speaker identity, timestamps, and multi-line turn text.
    """
    lines = transcript_text.splitlines()
    turns: list[SpeakerTurn] = []
    current_speaker: Optional[str] = None
    current_timestamp: Optional[str] = None
    current_text_lines: list[str] = []

    def flush_current():
        nonlocal current_speaker, current_timestamp, current_text_lines
        body = " ".join(line.strip() for line in current_text_lines if line.strip())
        if body:
            turns.append(
                SpeakerTurn(
                    speaker=current_speaker or default_speaker,
                    timestamp=current_timestamp,
                    text=body,
                )
            )
        current_text_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        match = SPEAKER_TURN_PATTERN.match(stripped)
        if match:
            # New speaker turn encountered
            flush_current()
            named_speaker = match.group(1)
            speaker_ts = match.group(2)
            anonymous_ts = match.group(3)
            turn_content = match.group(4)

            if named_speaker:
                current_speaker = named_speaker.strip()
                current_timestamp = speaker_ts.strip() if speaker_ts else None
            elif anonymous_ts:
                # Same speaker continuing with new timestamp
                current_timestamp = anonymous_ts.strip()
                # keep current_speaker as is

            if turn_content.strip():
                current_text_lines.append(turn_content.strip())
        else:
            # Continuation of existing turn
            current_text_lines.append(stripped)

    flush_current()
    return turns


def chunk_transcript(
    raw: RawTranscript,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
    min_chunk_size: int = 100,
) -> list[ProcessedChunk]:
    """
    Segment transcript into speaker-aware semantic chunks.
    
    Strategy:
    1. Parse transcript into structured SpeakerTurns.
    2. Group consecutive speaker turns until reaching ~chunk_size tokens.
    3. Retain ~chunk_overlap tokens from prior turns at chunk boundary for context.
    4. Inject metadata preamble at the beginning of each chunk.
    5. Compute deterministic SHA-256 content hash.
    """
    meta = raw.metadata
    date_str = meta.publication_date.isoformat() if meta.publication_date else "Unknown"
    preamble = f"[Episode: {meta.title} | Guest: {meta.guest} | Date: {date_str}]\n\n"
    preamble_tokens = estimate_tokens(preamble)

    turns = parse_speaker_turns(raw.content, default_speaker=meta.guest)
    if not turns:
        logger.warning("No speaker turns found in %s; using full text as single chunk", meta.source_path)
        content_with_preamble = preamble + raw.content
        chash = hashlib.sha256(f"{meta.source_path}:0:{content_with_preamble}".encode("utf-8")).hexdigest()
        return [
            ProcessedChunk(
                chunk_index=0,
                speaker=meta.guest,
                content=content_with_preamble,
                content_hash=chash,
                token_count=estimate_tokens(content_with_preamble),
            )
        ]

    effective_target_tokens = max(50, chunk_size - preamble_tokens)
    chunks: list[ProcessedChunk] = []
    
    current_turns: list[SpeakerTurn] = []
    current_tokens = 0
    chunk_idx = 0
    turn_idx = 0

    while turn_idx < len(turns):
        turn = turns[turn_idx]
        current_turns.append(turn)
        current_tokens += turn.token_estimate

        # Check if we've accumulated enough tokens for a full chunk
        if current_tokens >= effective_target_tokens or turn_idx == len(turns) - 1:
            # If this is the final turn and it's tiny, but we already have chunks,
            # consider whether to merge into the last chunk or emit.
            if turn_idx == len(turns) - 1 and current_tokens < min_chunk_size and chunks:
                # Merge into previous chunk
                prev = chunks[-1]
                additional_text = "\n\n" + "\n\n".join(
                    f"{t.speaker}: {t.text}" if t.speaker else t.text for t in current_turns
                )
                updated_content = prev.content + additional_text
                new_hash = hashlib.sha256(
                    f"{meta.source_path}:{prev.chunk_index}:{updated_content}".encode("utf-8")
                ).hexdigest()
                chunks[-1] = ProcessedChunk(
                    chunk_index=prev.chunk_index,
                    speaker=prev.speaker,
                    content=updated_content,
                    content_hash=new_hash,
                    token_count=estimate_tokens(updated_content),
                )
                break

            # Format the accumulated turns into chunk body
            body_parts = []
            speaker_weights: dict[str, int] = {}
            for t in current_turns:
                spk = t.speaker or meta.guest
                body_parts.append(f"{spk}: {t.text}")
                speaker_weights[spk] = speaker_weights.get(spk, 0) + t.token_estimate

            body = "\n\n".join(body_parts)
            full_chunk_text = preamble + body
            full_tokens = estimate_tokens(full_chunk_text)

            # Determine primary/dominant speaker for chunk
            dominant_speaker = max(speaker_weights.items(), key=lambda x: x[1])[0] if speaker_weights else meta.guest

            # Compute deterministic SHA-256 content hash
            chash = hashlib.sha256(
                f"{meta.source_path}:{chunk_idx}:{full_chunk_text}".encode("utf-8")
            ).hexdigest()

            chunks.append(
                ProcessedChunk(
                    chunk_index=chunk_idx,
                    speaker=dominant_speaker,
                    content=full_chunk_text,
                    content_hash=chash,
                    token_count=full_tokens,
                )
            )
            chunk_idx += 1

            if turn_idx == len(turns) - 1:
                break

            # Compute overlap: take turns from the tail of current_turns up to ~chunk_overlap tokens
            overlap_turns: list[SpeakerTurn] = []
            overlap_accum = 0
            for t in reversed(current_turns):
                if overlap_accum + t.token_estimate <= chunk_overlap or not overlap_turns:
                    overlap_turns.insert(0, t)
                    overlap_accum += t.token_estimate
                else:
                    break

            # Avoid infinite loop if single turn exceeds target: ensure progress
            if overlap_turns and len(overlap_turns) == len(current_turns):
                # Overlap would include all turns; drop at least the first turn to make forward progress
                overlap_turns = overlap_turns[1:]

            current_turns = list(overlap_turns)
            current_tokens = sum(t.token_estimate for t in current_turns)

        turn_idx += 1

    return chunks
