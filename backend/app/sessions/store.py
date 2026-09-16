"""Session and message persistence store using PostgreSQL."""

from datetime import datetime
import logging
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.sessions.models import MessageModel, SessionDetailModel, SessionModel, SourceReferenceItem

logger = logging.getLogger("lenny_assistant.sessions.store")


class SessionStore:
    """PostgreSQL-backed store for conversation sessions, messages, and source references."""

    @staticmethod
    async def create_session(
        db: AsyncSession,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> SessionModel:
        """Create a new conversational research session."""
        sid = session_id or str(uuid4())
        session_title = title or "New Research Session"
        now = datetime.utcnow()

        sql = text(
            """
            INSERT INTO sessions (id, title, created_at, updated_at)
            VALUES (:id, :title, :created_at, :updated_at)
            RETURNING id, title, created_at, updated_at;
            """
        )
        result = await db.execute(
            sql,
            {
                "id": sid,
                "title": session_title,
                "created_at": now,
                "updated_at": now,
            },
        )
        row = result.fetchone()
        await db.commit()

        logger.info("Created new session %s ('%s')", sid, session_title)
        return SessionModel(
            id=str(row.id),
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
            message_count=0,
        )

    @staticmethod
    async def get_session(db: AsyncSession, session_id: str) -> Optional[SessionDetailModel]:
        """Fetch a session and its full message history with attached sources."""
        # 1. Fetch session row
        s_sql = text("SELECT id, title, created_at, updated_at FROM sessions WHERE id = :id;")
        s_result = await db.execute(s_sql, {"id": session_id})
        s_row = s_result.fetchone()
        if not s_row:
            return None

        # 2. Fetch messages ordered chronologically
        m_sql = text(
            """
            SELECT id, session_id, role, content, evidence_tier, latency_ms, model_used, created_at
            FROM messages
            WHERE session_id = :session_id
            ORDER BY created_at ASC;
            """
        )
        m_result = await db.execute(m_sql, {"session_id": session_id})
        m_rows = m_result.fetchall()

        if not m_rows:
            return SessionDetailModel(
                id=str(s_row.id),
                title=s_row.title,
                created_at=s_row.created_at,
                updated_at=s_row.updated_at,
                message_count=0,
                messages=[],
            )

        message_ids = [str(r.id) for r in m_rows]

        # 3. Fetch source references for these messages
        sources_by_message: dict[str, list[SourceReferenceItem]] = {mid: [] for mid in message_ids}
        ref_sql = text(
            """
            SELECT
                sr.id,
                sr.message_id,
                sr.chunk_id,
                sr.similarity_score,
                sr.quoted_excerpt,
                c.episode_id,
                e.title,
                e.guest,
                c.chunk_index
            FROM source_references sr
            JOIN transcript_chunks c ON sr.chunk_id = c.id
            JOIN episodes e ON c.episode_id = e.id
            WHERE sr.message_id = ANY(:message_ids);
            """
        )
        ref_result = await db.execute(ref_sql, {"message_ids": message_ids})
        for ref in ref_result.fetchall():
            mid = str(ref.message_id)
            if mid in sources_by_message:
                source_ident = f"[{ref.guest} - {ref.title} #{ref.chunk_index}]"
                sources_by_message[mid].append(
                    SourceReferenceItem(
                        id=str(ref.id),
                        chunk_id=str(ref.chunk_id),
                        episode_id=str(ref.episode_id),
                        title=ref.title,
                        guest=ref.guest,
                        similarity_score=ref.similarity_score,
                        quoted_excerpt=ref.quoted_excerpt,
                        source_identifier=source_ident,
                    )
                )

        messages = [
            MessageModel(
                id=str(r.id),
                session_id=str(r.session_id),
                role=r.role,
                content=r.content,
                evidence_tier=r.evidence_tier,
                latency_ms=r.latency_ms,
                model_used=r.model_used,
                created_at=r.created_at,
                sources=sources_by_message.get(str(r.id), []),
            )
            for r in m_rows
        ]

        return SessionDetailModel(
            id=str(s_row.id),
            title=s_row.title,
            created_at=s_row.created_at,
            updated_at=s_row.updated_at,
            message_count=len(messages),
            messages=messages,
        )

    @staticmethod
    async def list_sessions(db: AsyncSession, limit: int = 20) -> list[SessionModel]:
        """List recent conversation sessions ordered by most recently updated."""
        sql = text(
            """
            SELECT
                s.id,
                s.title,
                s.created_at,
                s.updated_at,
                COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id, s.title, s.created_at, s.updated_at
            ORDER BY s.updated_at DESC
            LIMIT :limit;
            """
        )
        result = await db.execute(sql, {"limit": limit})
        return [
            SessionModel(
                id=str(row.id),
                title=row.title,
                created_at=row.created_at,
                updated_at=row.updated_at,
                message_count=int(row.message_count),
            )
            for row in result.fetchall()
        ]

    @staticmethod
    async def save_message(
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        evidence_tier: Optional[str] = None,
        latency_ms: Optional[int] = None,
        model_used: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> MessageModel:
        """Persist a user or assistant message and update session updated_at timestamp."""
        mid = message_id or str(uuid4())
        now = datetime.utcnow()

        sql = text(
            """
            INSERT INTO messages (id, session_id, role, content, evidence_tier, latency_ms, model_used, created_at)
            VALUES (:id, :session_id, :role, :content, :evidence_tier, :latency_ms, :model_used, :created_at)
            RETURNING id, session_id, role, content, evidence_tier, latency_ms, model_used, created_at;
            """
        )
        result = await db.execute(
            sql,
            {
                "id": mid,
                "session_id": session_id,
                "role": role,
                "content": content,
                "evidence_tier": evidence_tier,
                "latency_ms": latency_ms,
                "model_used": model_used,
                "created_at": now,
            },
        )
        row = result.fetchone()

        # Update session touch timestamp
        upd_sql = text("UPDATE sessions SET updated_at = :updated_at WHERE id = :id;")
        await db.execute(upd_sql, {"id": session_id, "updated_at": now})
        await db.commit()

        return MessageModel(
            id=str(row.id),
            session_id=str(row.session_id),
            role=row.role,
            content=row.content,
            evidence_tier=row.evidence_tier,
            latency_ms=row.latency_ms,
            model_used=row.model_used,
            created_at=row.created_at,
            sources=[],
        )

    @staticmethod
    async def save_source_references(
        db: AsyncSession,
        message_id: str,
        references: list[SourceReferenceItem],
    ) -> None:
        """Persist verified source references linking an assistant message to transcript chunks."""
        if not references:
            return

        sql = text(
            """
            INSERT INTO source_references (id, message_id, chunk_id, similarity_score, quoted_excerpt, created_at)
            VALUES (:id, :message_id, :chunk_id, :similarity_score, :quoted_excerpt, :created_at);
            """
        )
        now = datetime.utcnow()
        for ref in references:
            rid = ref.id or str(uuid4())
            await db.execute(
                sql,
                {
                    "id": rid,
                    "message_id": message_id,
                    "chunk_id": ref.chunk_id,
                    "similarity_score": ref.similarity_score,
                    "quoted_excerpt": ref.quoted_excerpt,
                    "created_at": now,
                },
            )
        await db.commit()

    @staticmethod
    async def get_recent_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 6,
    ) -> list[MessageModel]:
        """
        Fetch the last `limit` messages in chronological order (bounded working context for agent).
        Default limit=6 corresponds to 3 user/assistant turns.
        """
        sql = text(
            """
            SELECT id, session_id, role, content, evidence_tier, latency_ms, model_used, created_at
            FROM (
                SELECT id, session_id, role, content, evidence_tier, latency_ms, model_used, created_at
                FROM messages
                WHERE session_id = :session_id
                ORDER BY created_at DESC
                LIMIT :limit
            ) sub
            ORDER BY created_at ASC;
            """
        )
        result = await db.execute(sql, {"session_id": session_id, "limit": limit})
        rows = result.fetchall()
        return [
            MessageModel(
                id=str(r.id),
                session_id=str(r.session_id),
                role=r.role,
                content=r.content,
                evidence_tier=r.evidence_tier,
                latency_ms=r.latency_ms,
                model_used=r.model_used,
                created_at=r.created_at,
                sources=[],
            )
            for r in rows
        ]

    @staticmethod
    async def update_session_title(db: AsyncSession, session_id: str, title: str) -> None:
        """Update the title of an existing session."""
        sql = text("UPDATE sessions SET title = :title, updated_at = NOW() WHERE id = :id;")
        await db.execute(sql, {"id": session_id, "title": title})
        await db.commit()

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: str) -> bool:
        """Permanently delete a session. Cascades to messages, sources, and artifacts via DB foreign keys."""
        check_sql = text("SELECT id FROM sessions WHERE id = :id;")
        result = await db.execute(check_sql, {"id": session_id})
        if not result.fetchone():
            return False

        del_sql = text("DELETE FROM sessions WHERE id = :id;")
        await db.execute(del_sql, {"id": session_id})
        await db.commit()
        return True
