"""Artifact persistence store using PostgreSQL."""

from datetime import datetime
import logging
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import ArtifactListItem, ArtifactResponse, SourceReferenceItem

logger = logging.getLogger("lenny_assistant.artifacts.store")


class ArtifactStore:
    """PostgreSQL-backed store for research artifacts."""

    @staticmethod
    async def create_artifact(
        db: AsyncSession,
        session_id: UUID,
        message_id: Optional[UUID],
        artifact_type: str,
        title: str,
        content_raw: str,
        content_html: Optional[str] = None,
        sources: Optional[List[SourceReferenceItem]] = None,
    ) -> ArtifactResponse:
        """Persist a new artifact to the database."""
        artifact_id = uuid4()
        now = datetime.utcnow()

        sql = text(
            """
            INSERT INTO artifacts (id, session_id, message_id, artifact_type, title, content_raw, content_html, created_at)
            VALUES (:id, :session_id, :message_id, :artifact_type, :title, :content_raw, :content_html, :created_at)
            RETURNING id, session_id, message_id, artifact_type, title, content_raw, content_html, created_at;
            """
        )

        result = await db.execute(
            sql,
            {
                "id": str(artifact_id),
                "session_id": str(session_id),
                "message_id": str(message_id) if message_id else None,
                "artifact_type": artifact_type,
                "title": title,
                "content_raw": content_raw,
                "content_html": content_html,
                "created_at": now,
            },
        )
        row = result.fetchone()
        await db.commit()

        logger.info("Persisted artifact %s of type '%s' for session %s", str(artifact_id), artifact_type, str(session_id))

        return ArtifactResponse(
            id=row.id,
            session_id=row.session_id,
            message_id=row.message_id,
            artifact_type=row.artifact_type,
            title=row.title,
            content_raw=row.content_raw,
            content_html=row.content_html,
            created_at=row.created_at,
            sources=sources or [],
        )

    @staticmethod
    async def get_artifact(db: AsyncSession, artifact_id: UUID) -> Optional[ArtifactResponse]:
        """Fetch an artifact by its UUID, including attached sources if derived from a message."""
        sql = text(
            """
            SELECT id, session_id, message_id, artifact_type, title, content_raw, content_html, created_at
            FROM artifacts
            WHERE id = :id;
            """
        )
        result = await db.execute(sql, {"id": str(artifact_id)})
        row = result.fetchone()
        if not row:
            return None

        # Fetch sources if derived from a message
        sources: List[SourceReferenceItem] = []
        if row.message_id:
            src_sql = text(
                """
                SELECT sr.chunk_id, sr.similarity_score, sr.quoted_excerpt,
                       e.id as episode_id, e.title as episode_title, e.guest
                FROM source_references sr
                JOIN transcript_chunks tc ON sr.chunk_id = tc.id
                JOIN episodes e ON tc.episode_id = e.id
                WHERE sr.message_id = :message_id
                ORDER BY sr.similarity_score DESC;
                """
            )
            src_res = await db.execute(src_sql, {"message_id": str(row.message_id)})
            for s in src_res.fetchall():
                sources.append(
                    SourceReferenceItem(
                        chunk_id=str(s.chunk_id),
                        episode_id=str(s.episode_id),
                        title=s.episode_title,
                        guest=s.guest,
                        similarity_score=s.similarity_score,
                        quoted_excerpt=s.quoted_excerpt,
                    )
                )

        return ArtifactResponse(
            id=row.id,
            session_id=row.session_id,
            message_id=row.message_id,
            artifact_type=row.artifact_type,
            title=row.title,
            content_raw=row.content_raw,
            content_html=row.content_html,
            created_at=row.created_at,
            sources=sources,
        )

    @staticmethod
    async def list_session_artifacts(db: AsyncSession, session_id: UUID) -> List[ArtifactListItem]:
        """List all artifacts generated for a session in reverse chronological order."""
        sql = text(
            """
            SELECT id, session_id, artifact_type, title, created_at
            FROM artifacts
            WHERE session_id = :session_id
            ORDER BY created_at DESC;
            """
        )
        result = await db.execute(sql, {"session_id": str(session_id)})
        rows = result.fetchall()
        return [
            ArtifactListItem(
                id=r.id,
                session_id=r.session_id,
                artifact_type=r.artifact_type,
                title=r.title,
                created_at=r.created_at,
            )
            for r in rows
        ]
