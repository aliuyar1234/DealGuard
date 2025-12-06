"""User Settings API.

This module provides endpoints for managing user settings,
particularly API keys for external services.

In single-tenant mode (self-hosted), users manage their own API keys.
API keys are encrypted using Fernet symmetric encryption.
"""

import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from dealguard.api.deps import get_current_user, get_db
from dealguard.config import get_settings, DEFAULT_ORGANIZATION_ID
from dealguard.infrastructure.auth.provider import AuthUser
from dealguard.infrastructure.database.models.user import User
from dealguard.shared.crypto import encrypt_secret, decrypt_secret, is_encrypted

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


# ----- Request/Response Models -----


class APIKeysResponse(BaseModel):
    """Response with API key status (not the actual keys)."""

    anthropic_configured: bool = Field(description="Is Anthropic API key configured?")
    deepseek_configured: bool = Field(description="Is DeepSeek API key configured?")
    ai_provider: Literal["anthropic", "deepseek"] = Field(description="Current AI provider")


class UpdateAPIKeysRequest(BaseModel):
    """Request to update API keys."""

    anthropic_api_key: str | None = Field(
        None,
        description="Anthropic API key (starts with sk-ant-)",
        min_length=10,
    )
    deepseek_api_key: str | None = Field(
        None,
        description="DeepSeek API key",
        min_length=10,
    )
    ai_provider: Literal["anthropic", "deepseek"] | None = Field(
        None,
        description="Which AI provider to use",
    )


class SettingsResponse(BaseModel):
    """Full settings response."""

    api_keys: APIKeysResponse
    single_tenant_mode: bool
    app_version: str = "2.0.0"


# ----- Helper Functions -----


async def get_user_settings(db: AsyncSession, user_id: str, decrypt_keys: bool = True) -> dict:
    """Get user settings from database using ORM.

    Args:
        db: Database session
        user_id: User ID
        decrypt_keys: If True, decrypt API keys before returning

    Returns:
        User settings dict with optionally decrypted API keys
    """
    from uuid import UUID

    result = await db.execute(
        select(User.settings).where(User.id == UUID(user_id))
    )
    row = result.scalar_one_or_none()
    if not row:
        return {}

    settings = dict(row)

    # Decrypt API keys if requested
    if decrypt_keys:
        for key_name in ["anthropic_api_key", "deepseek_api_key"]:
            if key_name in settings and settings[key_name]:
                stored_value = settings[key_name]
                # Only decrypt if it looks encrypted (backward compatibility)
                if is_encrypted(stored_value):
                    try:
                        settings[key_name] = decrypt_secret(stored_value)
                    except ValueError:
                        logger.warning(f"Failed to decrypt {key_name} for user {user_id}")
                        settings[key_name] = None

    return settings


async def update_user_settings(db: AsyncSession, user_id: str, updates: dict) -> None:
    """Update user settings in database using ORM."""
    from uuid import UUID
    from sqlalchemy import func

    # Merge new settings with existing ones using PostgreSQL jsonb concatenation
    await db.execute(
        update(User)
        .where(User.id == UUID(user_id))
        .values(
            settings=func.coalesce(User.settings, {}) + updates
        )
    )
    await db.commit()


# ----- API Endpoints -----


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Get current settings.

    Returns the status of configured API keys (not the keys themselves)
    and other settings.
    """
    settings = get_settings()

    # Check if keys are configured (either from env or user settings)
    user_settings = await get_user_settings(db, current_user.id)

    anthropic_key = user_settings.get("anthropic_api_key") or settings.anthropic_api_key
    deepseek_key = user_settings.get("deepseek_api_key") or settings.deepseek_api_key
    ai_provider = user_settings.get("ai_provider") or settings.ai_provider

    return SettingsResponse(
        api_keys=APIKeysResponse(
            anthropic_configured=bool(anthropic_key),
            deepseek_configured=bool(deepseek_key),
            ai_provider=ai_provider,
        ),
        single_tenant_mode=settings.single_tenant_mode,
    )


@router.put("/api-keys", response_model=APIKeysResponse)
async def update_api_keys(
    request: UpdateAPIKeysRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIKeysResponse:
    """Update API keys.

    API keys are stored encrypted in the user's settings.
    Only the user can access their own keys.
    """
    settings = get_settings()
    user_id = current_user.id

    # Validate Anthropic key format
    if request.anthropic_api_key:
        if not request.anthropic_api_key.startswith("sk-ant-"):
            raise HTTPException(
                status_code=400,
                detail="Anthropic API Key muss mit 'sk-ant-' beginnen",
            )

    # Build settings update
    updates = {}
    if request.anthropic_api_key is not None:
        updates["anthropic_api_key"] = request.anthropic_api_key
    if request.deepseek_api_key is not None:
        updates["deepseek_api_key"] = request.deepseek_api_key
    if request.ai_provider is not None:
        updates["ai_provider"] = request.ai_provider

    if updates:
        # Encrypt API keys before storing
        encrypted_updates = {}
        for key, value in updates.items():
            if key in ["anthropic_api_key", "deepseek_api_key"] and value:
                encrypted_updates[key] = encrypt_secret(value)
            else:
                encrypted_updates[key] = value

        await update_user_settings(db, user_id, encrypted_updates)
        logger.info(f"API keys updated for user {user_id}")

    # Get updated status
    user_settings = await get_user_settings(db, user_id)

    anthropic_key = user_settings.get("anthropic_api_key") or settings.anthropic_api_key
    deepseek_key = user_settings.get("deepseek_api_key") or settings.deepseek_api_key
    ai_provider = user_settings.get("ai_provider") or settings.ai_provider

    return APIKeysResponse(
        anthropic_configured=bool(anthropic_key),
        deepseek_configured=bool(deepseek_key),
        ai_provider=ai_provider,
    )


@router.delete("/api-keys/{key_type}")
async def delete_api_key(
    key_type: Literal["anthropic", "deepseek"],
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a specific API key."""
    from uuid import UUID
    from sqlalchemy import func

    user_id = current_user.id
    key_name = f"{key_type}_api_key"

    # Remove key from JSONB settings using PostgreSQL - operator
    await db.execute(
        update(User)
        .where(User.id == UUID(user_id))
        .values(settings=User.settings - key_name)
    )
    await db.commit()

    return {"message": f"{key_type.title()} API Key gelöscht"}


@router.get("/check-ai")
async def check_ai_connection(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Test the AI connection with current settings."""
    settings = get_settings()
    user_id = current_user.id
    user_settings = await get_user_settings(db, user_id)

    ai_provider = user_settings.get("ai_provider") or settings.ai_provider

    if ai_provider == "anthropic":
        api_key = user_settings.get("anthropic_api_key") or settings.anthropic_api_key
        if not api_key:
            return {"status": "error", "message": "Anthropic API Key nicht konfiguriert"}

        try:
            import anthropic
            # Use async client to avoid blocking the event loop
            client = anthropic.AsyncAnthropic(api_key=api_key)
            # Simple test - just check if key is valid
            response = await client.messages.create(
                model="claude-3-haiku-20240307",  # Cheapest model for testing
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return {"status": "ok", "message": "Anthropic Verbindung erfolgreich", "model": settings.anthropic_model}
        except Exception as e:
            return {"status": "error", "message": f"Anthropic Fehler: {str(e)}"}

    elif ai_provider == "deepseek":
        api_key = user_settings.get("deepseek_api_key") or settings.deepseek_api_key
        if not api_key:
            return {"status": "error", "message": "DeepSeek API Key nicht konfiguriert"}

        try:
            import httpx
            # Use async client to avoid blocking the event loop
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.deepseek_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": settings.deepseek_model,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 10,
                    },
                    timeout=10,
                )
            if response.status_code == 200:
                return {"status": "ok", "message": "DeepSeek Verbindung erfolgreich", "model": settings.deepseek_model}
            else:
                return {"status": "error", "message": f"DeepSeek Fehler: {response.text}"}
        except Exception as e:
            return {"status": "error", "message": f"DeepSeek Fehler: {str(e)}"}

    return {"status": "error", "message": f"Unbekannter AI Provider: {ai_provider}"}
