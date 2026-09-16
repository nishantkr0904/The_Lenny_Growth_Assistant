"""API endpoints for LLM provider configuration and selection."""

import logging
from typing import Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.providers.manager import ProviderManager

logger = logging.getLogger("lenny_assistant.api.v1.providers")

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderSelectRequest(BaseModel):
    provider: Literal["ollama", "anthropic", "gemini", "openai", "groq"]


class AnthropicKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Anthropic API key")


class GeminiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Google Gemini API key")


class OpenAIKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="OpenAI API key")


class GroqKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Groq API key")


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
    """Switch the active LLM generation provider between local Ollama and cloud providers."""
    manager = ProviderManager.get_instance()
    try:
        manager.set_active_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return ProviderStatusResponse(**manager.get_provider_status())


@router.post("/gemini/key", response_model=ProviderStatusResponse, summary="Configure Google Gemini cloud API key")
async def configure_gemini_key(payload: GeminiKeyRequest) -> ProviderStatusResponse:
    """
    Validate, save, and activate Google Gemini cloud API key in the runtime credential store.
    Validates the key against Google's API before updating active provider.
    Never logs or echoes back the secret key in plaintext.
    """
    key_clean = payload.api_key.strip()
    if not key_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API key cannot be empty or whitespace.",
        )

    manager = ProviderManager.get_instance()
    is_valid, err_msg = await manager.validate_gemini_key(key_clean)
    if not is_valid:
        logger.warning("Gemini API key validation failed: %s", err_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google Gemini API key validation failed: {err_msg}",
        )

    manager.set_gemini_api_key(key_clean)
    manager.set_active_provider("gemini")
    return ProviderStatusResponse(**manager.get_provider_status())


@router.post("/anthropic/key", response_model=ProviderStatusResponse, summary="Configure Anthropic cloud API key")
async def configure_anthropic_key(payload: AnthropicKeyRequest) -> ProviderStatusResponse:
    """
    Validate, save, and activate Anthropic cloud API key in the runtime credential store.
    Validates the key against Anthropic's API before updating active provider.
    Never logs or echoes back the secret key in plaintext.
    """
    key_clean = payload.api_key.strip()
    if not key_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anthropic API key cannot be empty or whitespace.",
        )

    manager = ProviderManager.get_instance()
    is_valid, err_msg = await manager.validate_anthropic_key(key_clean)
    if not is_valid:
        logger.warning("Anthropic API key validation failed: %s", err_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Anthropic API key validation failed: {err_msg}",
        )

    manager.set_anthropic_api_key(key_clean)
    manager.set_active_provider("anthropic")
    return ProviderStatusResponse(**manager.get_provider_status())


@router.post("/openai/key", response_model=ProviderStatusResponse, summary="Configure OpenAI cloud API key")
async def configure_openai_key(payload: OpenAIKeyRequest) -> ProviderStatusResponse:
    """
    Validate, save, and activate OpenAI cloud API key in the runtime credential store.
    Validates the key against OpenAI's API before updating active provider.
    Never logs or echoes back the secret key in plaintext.
    """
    key_clean = payload.api_key.strip()
    if not key_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI API key cannot be empty or whitespace.",
        )

    manager = ProviderManager.get_instance()
    is_valid, err_msg = await manager.validate_openai_key(key_clean)
    if not is_valid:
        logger.warning("OpenAI API key validation failed: %s", err_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OpenAI API key validation failed: {err_msg}",
        )

    manager.set_openai_api_key(key_clean)
    manager.set_active_provider("openai")
    return ProviderStatusResponse(**manager.get_provider_status())


@router.post("/groq/key", response_model=ProviderStatusResponse, summary="Configure Groq cloud API key")
async def configure_groq_key(payload: GroqKeyRequest) -> ProviderStatusResponse:
    """
    Validate, save, and activate Groq cloud API key in the runtime credential store.
    Validates the key against Groq's API before updating active provider.
    Never logs or echoes back the secret key in plaintext.
    """
    key_clean = payload.api_key.strip()
    if not key_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Groq API key cannot be empty or whitespace.",
        )

    manager = ProviderManager.get_instance()
    is_valid, err_msg = await manager.validate_groq_key(key_clean)
    if not is_valid:
        logger.warning("Groq API key validation failed: %s", err_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Groq API key validation failed: {err_msg}",
        )

    manager.set_groq_api_key(key_clean)
    manager.set_active_provider("groq")
    return ProviderStatusResponse(**manager.get_provider_status())
