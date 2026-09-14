"""CLI Entrypoint for Lenny's Podcast transcript ingestion pipeline."""

import argparse
import asyncio
import logging
from pathlib import Path
import sys

from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db
from app.ingestion.pipeline import IngestionPipeline

setup_logging()
logger = get_logger("lenny_assistant.scripts.ingest")


def find_default_data_dir() -> Path:
    """Detect default transcript directory across container and host execution contexts."""
    candidates = [
        Path("/app/data/transcripts"),
        Path("data/transcripts"),
        Path("../data/transcripts"),
        Path(__file__).resolve().parent.parent.parent / "data" / "transcripts",
    ]
    for c in candidates:
        if c.exists() and (c / "episodes").exists():
            return c
    # Fallback to first existing candidate or default
    for c in candidates:
        if c.exists():
            return c
    return Path("data/transcripts")


async def main_async(args: argparse.Namespace) -> int:
    """Execute ingestion with configured CLI options."""
    data_dir = Path(args.data_dir) if args.data_dir else find_default_data_dir()

    print("==================================================")
    print("  Lenny Growth Assistant - Transcript Ingestion   ")
    print("==================================================")
    print(f"Corpus Directory:   {data_dir}")
    print(f"Episode Limit:      {args.limit if args.limit else 'All'}")
    print(f"Chunk Size:         {args.chunk_size} tokens")
    print(f"Chunk Overlap:      {args.chunk_overlap} tokens")
    print(f"Dry Run:            {args.dry_run}")
    print(f"Force Re-embed:     {args.force}")
    print("==================================================")

    if not data_dir.exists():
        print(f"\n[ERROR] Transcripts directory not found: {data_dir}", file=sys.stderr)
        print("Please clone or specify the path using --data-dir <path>", file=sys.stderr)
        return 1

    # Ensure database schema is initialized
    if not args.dry_run:
        print("\nEnsuring database schema is up-to-date...")
        try:
            await init_db()
        except Exception as e:
            print(f"[ERROR] Failed to initialize database: {e}", file=sys.stderr)
            return 1

    pipeline = IngestionPipeline(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    print("\nStarting ingestion...")
    stats = await pipeline.run(
        data_dir=data_dir,
        limit=args.limit,
        dry_run=args.dry_run,
        force_reembed=args.force,
    )

    print("\n==================================================")
    print("               INGESTION REPORT                   ")
    print("==================================================")
    print(f"Files Discovered:     {stats.files_discovered}")
    print(f"Episodes Parsed:      {stats.episodes_parsed}")
    print(f"Episodes Upserted:    {stats.episodes_upserted}")
    print(f"Chunks Created:       {stats.chunks_created}")
    print(f"Chunks Skipped:       {stats.chunks_skipped} (deduplicated)")
    print(f"Embeddings Generated: {stats.embeddings_generated}")
    print(f"Failures:             {len(stats.failures)}")
    print(f"Elapsed Time:         {stats.elapsed_seconds:.2f}s")
    print("==================================================")

    if stats.failures:
        print("\nFailures encountered:")
        for f in stats.failures[:10]:
            print(f" - {f['file']}: {f['error']}")
        if len(stats.failures) > 10:
            print(f" ... and {len(stats.failures) - 10} more.")
        return 1

    print("\n[SUCCESS] Ingestion completed successfully.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest Lenny's Podcast transcripts into PostgreSQL + pgvector."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to transcript directory containing 'episodes/'",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of episode transcripts to ingest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk transcripts without database writes or embeddings",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-embedding of existing chunks instead of skipping",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=600,
        help="Target chunk size in tokens (default: 600)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=100,
        help="Sliding token overlap across chunks (default: 100)",
    )

    args = parser.parse_args()
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
