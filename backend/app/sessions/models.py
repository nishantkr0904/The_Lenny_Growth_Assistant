"""Data models and Pydantic schemas for sessions and messages."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class SourceReferenceItem(BaseModel):
    """Structured evidence source reference attached to a synthesized message."""

    id: Optional[str] = None
    chunk_id: str
    episode_id: Optional[str] = None
    title: Optional[str] = None
    guest: Optional[str] = None
    similarity_score: float
    quoted_excerpt: str
    source_identifier: Optional[str] = None


class MessageModel(BaseModel):
    """Model representing an individual conversational message turn."""

    id: str
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    evidence_tier: Optional[str] = None  # 'Strong', 'Limited', 'Conflicting', 'Insufficient'
    latency_ms: Optional[int] = None
    model_used: Optional[str] = None
    created_at: datetime
    sources: list[SourceReferenceItem] = Field(default_factory=list)


class SessionModel(BaseModel):
    """Summary representation of a conversation session."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SessionDetailModel(SessionModel):
    """Full representation of a session including its message history."""

    messages: list[MessageModel] = Field(default_factory=list)


class SessionCreate(BaseModel):
    """Request payload for creating a new session."""

    title: Optional[str] = "New Research Session"


class MessageCreate(BaseModel):
    """Request payload for sending a user message into a session."""

    content: str
    stream: bool = False
