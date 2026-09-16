"""FastAPI routes for session management and grounded conversational Q&A."""

import logging
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import QnAOrchestrator, QnAResult
from app.db.session import get_db
from app.sessions.models import (
    MessageCreate,
    SessionCreate,
    SessionDetailModel,
    SessionModel,
)
from app.sessions.store import SessionStore

logger = logging.getLogger("lenny_assistant.api.v1.sessions")
router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_orchestrator() -> QnAOrchestrator:
    """Dependency injection provider for QnAOrchestrator."""
    return QnAOrchestrator()


@router.post(
    "",
    response_model=SessionModel,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
async def create_session(
    payload: Optional[SessionCreate] = None,
    db: AsyncSession = Depends(get_db),
) -> SessionModel:
    """Create a new conversational research session."""
    title = payload.title if payload and payload.title else "New Research Session"
    return await SessionStore.create_session(db=db, title=title)


@router.get(
    "",
    response_model=list[SessionModel],
    summary="List recent conversation sessions",
)
async def list_sessions(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> list[SessionModel]:
    """Retrieve recent conversation sessions ordered by most recently updated."""
    return await SessionStore.list_sessions(db=db, limit=limit)


@router.get(
    "/{session_id}",
    response_model=SessionDetailModel,
    summary="Get session details and message history",
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailModel:
    """Retrieve full session detail including message turns and attached sources."""
    session = await SessionStore.get_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return session


@router.post(
    "/{session_id}/messages",
    summary="Send a message into a session (supports JSON and SSE streaming)",
)
async def send_message(
    session_id: str,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    orchestrator: QnAOrchestrator = Depends(get_orchestrator),
):
    """
    Submit a user question to the grounded assistant.
    If payload.stream is True, returns text/event-stream (SSE).
    If payload.stream is False, returns structured QnAResult JSON.
    """
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    if payload.stream:
        return StreamingResponse(
            orchestrator.stream_turn(
                session_id=session_id,
                user_content=payload.content.strip(),
                db=db,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming JSON response
    result: QnAResult = await orchestrator.run_turn(
        session_id=session_id,
        user_content=payload.content.strip(),
        db=db,
    )
    return result


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation session and all cascading data",
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete a conversation session, cascading to messages, sources, and artifacts."""
    deleted = await SessionStore.delete_session(db=db, session_id=session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return None
