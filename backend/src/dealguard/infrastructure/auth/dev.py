"""Development authentication provider for local testing.

This provider bypasses real authentication and creates a mock user.
NEVER use in production!
"""

from uuid import UUID

from dealguard.infrastructure.auth.provider import AuthProvider, AuthUser
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)

# Fixed UUIDs for development
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
DEV_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")


class DevAuthProvider(AuthProvider):
    """Development auth provider that accepts any token.

    Creates a mock user for local development without needing Supabase.
    """

    async def verify_token(self, token: str) -> AuthUser:
        """Accept any token and return a mock dev user."""
        logger.warning(
            "dev_auth_used",
            message="Using development auth - DO NOT USE IN PRODUCTION",
        )

        return AuthUser(
            id=DEV_USER_ID,
            email="dev@dealguard.local",
            organization_id=DEV_ORG_ID,
            role="owner",
            email_verified=True,
            full_name="Dev User",
        )

    async def get_user(self, user_id: str) -> AuthUser | None:
        """Return mock user for any ID."""
        return AuthUser(
            id=DEV_USER_ID,
            email="dev@dealguard.local",
            organization_id=DEV_ORG_ID,
            role="owner",
            email_verified=True,
            full_name="Dev User",
        )

    async def create_user(
        self,
        email: str,
        password: str,
        organization_id: UUID,
        role: str = "member",
        full_name: str | None = None,
    ) -> AuthUser:
        """Return mock user."""
        return AuthUser(
            id=DEV_USER_ID,
            email=email,
            organization_id=organization_id,
            role=role,
            email_verified=True,
            full_name=full_name,
        )

    async def delete_user(self, user_id: str) -> None:
        """No-op for dev."""
        pass

    async def update_user_metadata(
        self,
        user_id: str,
        organization_id: UUID | None = None,
        role: str | None = None,
        full_name: str | None = None,
    ) -> AuthUser:
        """Return mock user with updated data."""
        return AuthUser(
            id=DEV_USER_ID,
            email="dev@dealguard.local",
            organization_id=organization_id or DEV_ORG_ID,
            role=role or "owner",
            email_verified=True,
            full_name=full_name or "Dev User",
        )

    async def close(self) -> None:
        """No-op for dev."""
        pass
