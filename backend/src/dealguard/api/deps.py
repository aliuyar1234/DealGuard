"""FastAPI dependencies for API routes.

This module re-exports commonly used dependencies for convenience.
"""

import logging
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.api.middleware.auth import get_current_user
from dealguard.infrastructure.database.connection import SessionDep, get_session
from dealguard.infrastructure.database.models.user import User
from dealguard.shared.crypto import decrypt_secret, is_encrypted

logger = logging.getLogger(__name__)

# Re-export get_session as get_db for compatibility
get_db = get_session


async def get_user_settings(
    db: AsyncSession,
    user_id: str,
    decrypt_keys: bool = True,
) -> dict[str, Any]:
    """Get user settings from database.

    Args:
        db: Database session
        user_id: User ID
        decrypt_keys: If True, decrypt API keys before returning

    Returns:
        User settings dict with optionally decrypted API keys
    """
    result = await db.execute(select(User.settings).where(User.id == UUID(user_id)))
    row = result.scalar_one_or_none()
    if not row:
        return {}

    settings = cast(dict[str, Any], dict(row))

    # Decrypt API keys if requested
    if decrypt_keys:
        for key_name in ["anthropic_api_key", "deepseek_api_key"]:
            if key_name in settings and settings[key_name]:
                stored_value = settings[key_name]
                # Only decrypt if it looks encrypted (backward compatibility)
                if isinstance(stored_value, str) and is_encrypted(stored_value):
                    try:
                        settings[key_name] = decrypt_secret(stored_value)
                    except ValueError:
                        logger.warning(f"Failed to decrypt {key_name} for user {user_id}")
                        settings[key_name] = None

    return settings


__all__ = [
    "get_current_user",
    "get_db",
    "get_session",
    "get_user_settings",
    "SessionDep",
]
