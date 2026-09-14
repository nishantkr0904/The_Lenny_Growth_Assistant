"""Vector retrieval engine executing semantic cosine similarity search over pgvector."""

import logging
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine
from app.ingestion.embeddings import OllamaEmbeddingProvider
from app.retrieval.models import EvidenceItem
from app.retrieval.query import normalize_query

logger = logging.getLogger("lenny_assistant.retrieval.engine")


class VectorRetrievalEngine:
    """
    Executes semantic search over transcript_chunks table using pgvector HNSW index.
    Embeds queries using nomic-embed-text (768 dimensions).
    """

    def __init__(
        self,
        embedding_provider: Optional[OllamaEmbeddingProvider] = None,
    ) -> None:
        self.embedding_provider = embedding_provider or OllamaEmbeddingProvider()

    @staticmethod
    def _create_excerpt(content: str, max_chars: int = 240) -> str:
        """Create a clean substantive excerpt from chunk content, skipping the preamble."""
        lines = content.split("\n\n")
        # If the first line is the [Episode: ...] preamble, start from second line
        dialogue = "\n\n".join(lines[1:]) if len(lines) > 1 and lines[0].startswith("[Episode:") else content
        clean = " ".join(dialogue.split())
        if len(clean) <= max_chars:
            return clean
        # Trim at word boundary
        trimmed = clean[:max_chars].rsplit(" ", 1)[0]
        return f"{trimmed}..."

    async def search(
        self,
        query: str,
        top_k: int = 15,
        db: Optional[AsyncSession] = None,
    ) -> list[EvidenceItem]:
        """
        Embed query, execute cosine similarity search against pgvector,
        and return ordered EvidenceItems with metadata.
        """
        normalized_q = normalize_query(query)
        logger.debug("Executing vector retrieval for query: %s (top_k=%d)", normalized_q, top_k)

        # Generate 768-dim query embedding
        query_vector = await self.embedding_provider.embed_text(normalized_q)
        vector_str = f"[{','.join(str(v) for v in query_vector)}]"

        sql = text(
            """
            SELECT
                c.id AS chunk_id,
                c.episode_id,
                e.title,
                e.guest,
                e.publication_date,
                e.source_path,
                c.chunk_index,
                c.speaker,
                c.content,
                1 - (c.embedding <=> :query_vector) AS similarity_score
            FROM transcript_chunks c
            JOIN episodes e ON c.episode_id = e.id
            WHERE c.embedding IS NOT NULL
            ORDER BY c.embedding <=> :query_vector ASC
            LIMIT :top_k;
            """
        )

        async def _execute(session_or_conn):
            result = await session_or_conn.execute(sql, {"query_vector": vector_str, "top_k": top_k})
            return result.fetchall()

        if db is not None:
            rows = await _execute(db)
        else:
            async with engine.connect() as conn:
                rows = await _execute(conn)

        evidence_items: list[EvidenceItem] = []
        for row in rows:
            chunk_id = str(row[0])
            episode_id = str(row[1])
            title = str(row[2])
            guest = str(row[3])
            pub_date = row[4]
            source_path = str(row[5])
            chunk_index = int(row[6])
            speaker = str(row[7]) if row[7] else guest
            content = str(row[8])
            raw_score = float(row[9])
            # Clamp similarity score to [0.0, 1.0] for safety
            similarity = max(0.0, min(1.0, round(raw_score, 4)))

            source_id = f"{guest} - {title} [Chunk #{chunk_index}]"
            excerpt = self._create_excerpt(content)

            evidence_items.append(
                EvidenceItem(
                    chunk_id=chunk_id,
                    episode_id=episode_id,
                    title=title,
                    guest=guest,
                    publication_date=pub_date,
                    source_path=source_path,
                    chunk_index=chunk_index,
                    speaker=speaker,
                    content=content,
                    similarity_score=similarity,
                    source_identifier=source_id,
                    excerpt=excerpt,
                )
            )

        logger.info(
            "Retrieved %d chunks for query (top_score=%.4f)",
            len(evidence_items),
            evidence_items[0].similarity_score if evidence_items else 0.0,
        )
        return evidence_items
