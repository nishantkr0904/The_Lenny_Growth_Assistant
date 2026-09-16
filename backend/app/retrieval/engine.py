"""Vector retrieval engine executing semantic cosine similarity search over pgvector with hybrid lexical boosting."""

import logging
import re
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine
from app.ingestion.embeddings import OllamaEmbeddingProvider
from app.retrieval.models import EvidenceItem
from app.retrieval.query import normalize_query

logger = logging.getLogger("lenny_assistant.retrieval.engine")

COMMON_QUERY_WORDS = {
    "what", "when", "where", "which", "while", "who", "whom", "whose", "why", "how",
    "the", "and", "for", "are", "about", "with", "this", "that", "from", "they",
    "will", "would", "could", "should", "have", "more", "some", "such", "than",
    "them", "then", "their", "there", "these", "those", "does", "been", "also",
    "best", "good", "make", "take", "give", "like", "into", "time", "just", "know",
    "think", "people", "podcast", "episode", "advice", "talk", "says", "said",
}


def extract_distinctive_terms(query: str) -> list[str]:
    """
    Extract distinctive domain acronyms and framework identifiers from query.
    E.g.: 'LNO', 'PLG', 'PMF', 'OKRs', 'CAC', 'LTV', 'SaaS', or 'XYZ framework'.
    """
    terms: list[str] = []
    acronyms = re.findall(r"\b(?:[A-Z0-9]{2,6}|[A-Z][a-z]{1,2}[A-Z]{1,2}|[A-Z]{2,4}s)\b", query)
    for a in acronyms:
        if a.lower() not in COMMON_QUERY_WORDS and a not in terms and not a.isdigit():
            terms.append(a)

    fw_matches = re.findall(
        r"\b([A-Za-z0-9_-]{2,15})\s+(?:framework|model|matrix|method|rule|principle|formula|playbook)\b",
        query,
        re.IGNORECASE,
    )
    for m in fw_matches:
        if m.lower() not in COMMON_QUERY_WORDS and m not in terms:
            terms.append(m)

    return terms


def extract_potential_guest_mentions(query: str) -> list[str]:
    """
    Extract capitalized multi-word proper nouns that could represent guest names.
    E.g. 'Shreyas Doshi', 'Elena Verna', 'Brian Chesky'.
    """
    names: list[str] = []
    matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", query)
    for m in matches:
        words = m.split()
        if any(w.lower() in {"what", "how", "why", "when", "where", "lenny", "podcast"} for w in words):
            continue
        names.append(m)
    return names


def extract_substantive_excerpt_terms(
    query: str,
    distinctive_terms: list[str],
    guest_mentions: list[str],
) -> list[str]:
    """
    Extract substantive target keywords to anchor excerpt window around the most
    information-dense discussion in the retrieved chunk.
    Prioritizes distinctive acronyms and domain terms, then topic terms, then guest names.
    """
    terms: list[str] = []
    # 1. Distinctive domain acronyms/frameworks (highest specificity)
    for dt in distinctive_terms:
        if dt not in terms:
            terms.append(dt)

    # 2. Substantive content keywords from query (length >= 4, non-stopwords)
    query_words = re.findall(r"\b[A-Za-z0-9_-]{3,}\b", query)
    for qw in query_words:
        qw_lower = qw.lower()
        if qw_lower not in COMMON_QUERY_WORDS and qw not in terms and qw_lower not in [t.lower() for t in terms]:
            terms.append(qw)

    # 3. Guest names/surnames
    for gm in guest_mentions:
        for w in reversed(gm.split()):
            if len(w) >= 3 and w not in terms and w.lower() not in [t.lower() for t in terms]:
                terms.append(w)

    return terms


def compute_lexical_boost(
    content: str,
    guest: str,
    title: str,
    distinctive_terms: list[str],
    guest_mentions: list[str],
) -> float:
    """
    Compute a bounded, conservative lexical boost (+0.00 to +0.22) when an exact
    distinctive domain term (acronym, framework) or guest name appears verbatim in the chunk.
    Never boosts out-of-domain terms (since boost is 0.0 when terms are absent).
    """
    boost = 0.0
    text_lower = f"{guest} {title} {content}".lower()

    for term in distinctive_terms:
        # High-specificity uppercase acronym (e.g. LNO, PLG, PMF, ARR, CAC)
        if term.isupper() and 2 <= len(term) <= 6:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, content) or re.search(pattern, title):
                boost += 0.20
                break
        else:
            pattern = rf"\b{re.escape(term.lower())}\b"
            if re.search(pattern, text_lower):
                boost += 0.08
                break

    for g in guest_mentions:
        if g.lower() in guest.lower() or g.lower() in text_lower:
            boost += 0.04
            break

    return min(boost, 0.22)



class VectorRetrievalEngine:
    """
    Executes semantic search over transcript_chunks table using pgvector HNSW index,
    augmented with candidate pool expansion and bounded lexical boosting for exact terms.
    Embeds queries using nomic-embed-text (768 dimensions).
    """

    def __init__(
        self,
        embedding_provider: Optional[OllamaEmbeddingProvider] = None,
    ) -> None:
        self.embedding_provider = embedding_provider or OllamaEmbeddingProvider()

    @staticmethod
    def _create_excerpt(
        content: str,
        terms: Optional[list[str]] = None,
        max_chars: int = 240,
    ) -> str:
        """
        Create a clean substantive excerpt from chunk content.
        If distinctive terms appear in the content, centers the excerpt around
        the primary occurrence to avoid cutting off substantive framework definitions
        in favor of conversational dialogue preamble.
        """
        lines = content.split("\n\n")
        dialogue = "\n\n".join(lines[1:]) if len(lines) > 1 and lines[0].startswith("[Episode:") else content
        clean = " ".join(dialogue.split())

        if terms:
            for t in terms:
                if len(t) < 2:
                    continue
                pattern = rf"\b{re.escape(t)}\b"
                match = re.search(pattern, clean, re.IGNORECASE)
                if match:
                    idx = match.start()

                    # Sentence or speaker turn-aligned start
                    sent_start = clean.rfind(". ", max(0, idx - 100), idx)
                    if sent_start != -1:
                        start = sent_start + 2
                    else:
                        speaker_start = clean.rfind(": ", max(0, idx - 80), idx)
                        if speaker_start != -1:
                            start = speaker_start + 2
                        else:
                            start = max(0, idx - 20)
                            if start > 0:
                                sp = clean.find(" ", start)
                                if sp != -1 and sp < idx:
                                    start = sp + 1
                    end = min(len(clean), start + max_chars)

                    if end < len(clean):
                        last_space = clean.rfind(" ", start, end)
                        if last_space != -1 and last_space > start:
                            end = last_space
                    prefix = "..." if start > 0 else ""
                    suffix = "..." if end < len(clean) else ""
                    return f"{prefix}{clean[start:end]}{suffix}"

        if len(clean) <= max_chars:
            return clean
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
        apply bounded lexical boosting for exact acronyms/frameworks/guests,
        and return ordered EvidenceItems with metadata.
        """
        normalized_q = normalize_query(query)
        logger.debug("Executing vector retrieval for query: %s (top_k=%d)", normalized_q, top_k)

        # Extract domain signals from both raw and normalized queries
        raw_terms = extract_distinctive_terms(query) + extract_distinctive_terms(normalized_q)
        distinctive_terms = list(dict.fromkeys(raw_terms))
        raw_guests = extract_potential_guest_mentions(query) + extract_potential_guest_mentions(normalized_q)
        guest_mentions = list(dict.fromkeys(raw_guests))

        # Generate 768-dim query embedding
        query_vector = await self.embedding_provider.embed_text(normalized_q)
        vector_str = f"[{','.join(str(v) for v in query_vector)}]"

        # Retrieve an expanded candidate pool (at least 25) to prevent acronym vector dropouts
        candidate_limit = max(top_k * 2, 25)

        if distinctive_terms:
            patterns = [f"%{t}%" for t in distinctive_terms]
            sql = text(
                """
                WITH vector_candidates AS (
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
                    LIMIT :candidate_limit
                ),
                keyword_candidates AS (
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
                      AND (c.content ILIKE ANY(:patterns))
                    LIMIT 25
                )
                SELECT * FROM vector_candidates
                UNION
                SELECT * FROM keyword_candidates;
                """
            )
            params = {"query_vector": vector_str, "candidate_limit": candidate_limit, "patterns": patterns}
        else:
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
                LIMIT :candidate_limit;
                """
            )
            params = {"query_vector": vector_str, "candidate_limit": candidate_limit}

        async def _execute(session_or_conn):
            result = await session_or_conn.execute(sql, params)
            return result.fetchall()

        if db is not None:
            rows = await _execute(db)
        else:
            async with engine.connect() as conn:
                rows = await _execute(conn)

        excerpt_terms = extract_substantive_excerpt_terms(normalized_q, distinctive_terms, guest_mentions)
        scored_candidates: list[tuple[float, EvidenceItem]] = []
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

            # Apply conservative bounded lexical boost if exact distinctive term or guest matches
            boost = compute_lexical_boost(content, guest, title, distinctive_terms, guest_mentions)
            final_score = max(0.0, min(1.0, round(raw_score + boost, 4)))

            source_id = f"{guest} - {title} [Chunk #{chunk_index}]"
            excerpt = self._create_excerpt(content, terms=excerpt_terms)


            item = EvidenceItem(
                chunk_id=chunk_id,
                episode_id=episode_id,
                title=title,
                guest=guest,
                publication_date=pub_date,
                source_path=source_path,
                chunk_index=chunk_index,
                speaker=speaker,
                content=content,
                similarity_score=final_score,
                source_identifier=source_id,
                excerpt=excerpt,
            )
            scored_candidates.append((final_score, item))

        # Re-sort candidates by final bounded score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        evidence_items = [item for _, item in scored_candidates[:top_k]]

        logger.info(
            "Retrieved %d chunks for query (top_score=%.4f, raw_candidates=%d)",
            len(evidence_items),
            evidence_items[0].similarity_score if evidence_items else 0.0,
            len(rows),
        )
        return evidence_items
