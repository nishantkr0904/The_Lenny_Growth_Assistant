from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

ArtifactType = Literal["ship30_essay", "markdown", "html_card"]


class ArtifactCreateRequest(BaseModel):
    session_id: UUID = Field(..., description="ID of the research session")
    message_id: Optional[UUID] = Field(None, description="Optional specific message turn ID to derive artifact from")
    artifact_type: ArtifactType = Field("ship30_essay", description="Type of artifact to compile")
    title: Optional[str] = Field(None, description="Optional custom title for the artifact")
    custom_instructions: Optional[str] = Field(None, description="Optional styling or focus instructions")


class SourceReferenceItem(BaseModel):
    chunk_id: Optional[str] = None
    episode_id: Optional[str] = None
    title: Optional[str] = None
    guest: Optional[str] = None
    similarity_score: Optional[float] = None
    quoted_excerpt: Optional[str] = None


class ArtifactResponse(BaseModel):
    id: UUID
    session_id: UUID
    message_id: Optional[UUID] = None
    artifact_type: str
    title: str
    content_raw: str
    content_html: Optional[str] = None
    created_at: datetime
    sources: List[SourceReferenceItem] = Field(default_factory=list)


class ArtifactListItem(BaseModel):
    id: UUID
    session_id: UUID
    artifact_type: str
    title: str
    created_at: datetime
