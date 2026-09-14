"""Artifact compilation and retrieval endpoints."""

import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.compiler import ArtifactCompiler
from app.artifacts.models import ArtifactCreateRequest, ArtifactListItem, ArtifactResponse, SourceReferenceItem
from app.artifacts.store import ArtifactStore
from app.db.session import get_db
from app.sessions.store import SessionStore

logger = logging.getLogger("lenny_assistant.api.artifacts")

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    request: ArtifactCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """Compile a new research artifact from grounded session messages."""
    session = await SessionStore.get_session(db, str(request.session_id))
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    if not session.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compile artifact from an empty session. Ask a grounded research question first.",
        )

    # Locate target message (either specified or last assistant message)
    target_msg = None
    if request.message_id:
        for m in session.messages:
            if m.id == str(request.message_id):
                target_msg = m
                break
        if not target_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message {request.message_id} not found in session",
            )
    else:
        # Find latest assistant message
        for m in reversed(session.messages):
            if m.role == "assistant":
                target_msg = m
                break

    if not target_msg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No assistant message found to derive artifact from.",
        )

    # Check grounding: refusal or insufficient evidence cannot be transformed into factual artifacts
    if target_msg.evidence_tier == "insufficient":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compile artifact from ungrounded refusal. The topic must have grounded evidence from Lenny's Podcast.",
        )

    # Extract sources dictionary from target message
    sources_data = [
        {
            "chunk_id": s.chunk_id,
            "title": s.title,
            "guest": s.guest,
            "quoted_excerpt": s.quoted_excerpt,
            "similarity_score": s.similarity_score,
        }
        for s in target_msg.sources
    ]

    title = request.title or f"{session.title} — Tactical Playbook"
    topic = session.title

    if request.artifact_type == "ship30_essay":
        raw_md = ArtifactCompiler.compile_ship30_essay(
            title=title,
            topic=topic,
            content=target_msg.content,
            sources=sources_data,
        )
        compiled_html = ArtifactCompiler.compile_html_card(
            title=title,
            raw_markdown=raw_md,
            sources=sources_data,
        )
    elif request.artifact_type == "markdown":
        raw_md = ArtifactCompiler.compile_markdown_brief(
            title=title,
            topic=topic,
            content=target_msg.content,
            sources=sources_data,
        )
        compiled_html = ArtifactCompiler.compile_html_card(
            title=title,
            raw_markdown=raw_md,
            sources=sources_data,
        )
    elif request.artifact_type == "html_card":
        raw_md = ArtifactCompiler.compile_markdown_brief(
            title=title,
            topic=topic,
            content=target_msg.content,
            sources=sources_data,
        )
        compiled_html = ArtifactCompiler.compile_html_card(
            title=title,
            raw_markdown=raw_md,
            sources=sources_data,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported artifact type: {request.artifact_type}",
        )

    sources_items = [
        SourceReferenceItem(
            chunk_id=s.get("chunk_id"),
            title=s.get("title"),
            guest=s.get("guest"),
            quoted_excerpt=s.get("quoted_excerpt"),
            similarity_score=s.get("similarity_score"),
        )
        for s in sources_data
    ]

    artifact = await ArtifactStore.create_artifact(
        db=db,
        session_id=request.session_id,
        message_id=UUID(target_msg.id) if target_msg else None,
        artifact_type=request.artifact_type,
        title=title,
        content_raw=raw_md,
        content_html=compiled_html,
        sources=sources_items,
    )

    return artifact


@router.get("/{id}", response_model=ArtifactResponse)
async def get_artifact(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """Fetch compiled artifact by UUID."""
    artifact = await ArtifactStore.get_artifact(db, id)
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {id} not found",
        )
    return artifact


@router.get("/session/{session_id}", response_model=List[ArtifactListItem])
async def list_session_artifacts(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[ArtifactListItem]:
    """List all artifacts generated for a session."""
    return await ArtifactStore.list_session_artifacts(db, session_id)
