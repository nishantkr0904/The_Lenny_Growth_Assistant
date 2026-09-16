"""API endpoints for LLM provider configuration and selection."""

import logging
from typing import Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.providers.manager import ProviderManager

logger = logging.getLogger("lenny_assistant.api.v1.providers")

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderSelectRequest(BaseModel):
    provider: Literal["ollama", "anthropic"]


class AnthropicKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Anthropic API key")


class ProviderStatusItem(BaseModel):
    id: str
    name: str
    type: str  # 'local' or 'cloud'
    model: str
    configured: bool


class ProviderStatusResponse(BaseModel):
    active_provider: str
    providers: list[ProviderStatusItem]


@router.get("", response_model=ProviderStatusResponse, summary="Get active and available LLM providers")
async def get_providers() -> ProviderStatusResponse:
    """Retrieve active LLM generation provider and configuration status for each supported provider."""
    manager = ProviderManager.get_instance()
    return ProviderStatusResponse(**manager.get_provider_status())


@router.post("/select", response_model=ProviderStatusResponse, summary="Select active LLM generation provider")
async def select_provider(payload: ProviderSelectRequest) -> ProviderStatusResponse:
    """Switch the active LLM generation provider between local Ollama and cloud Anthropic."""
    manager = ProviderManager.get_instance()
    try:
        manager.set_active_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return ProviderStatusResponse(**manager.get_provider_status())


@router.post("/anthropic/key", response_model=ProviderStatusResponse, summary="Configure Anthropic cloud API key")
async def configure_anthropic_key(payload: AnthropicKeyRequest) -> ProviderStatusResponse:
    """
    Save or update the Anthropic cloud API key in the runtime credential store.
    Never logs or echoes back the secret key in plaintext.
    """
    key_clean = payload.api_key.strip()
    if not key_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anthropic API key cannot be empty or whitespace.",
        )

    manager = ProviderManager.get_instance()
    manager.set_anthropic_api_key(key_clean)
    manager.set_active_provider("anthropic")
    return ProviderStatusResponse(**manager.get_provider_status())
