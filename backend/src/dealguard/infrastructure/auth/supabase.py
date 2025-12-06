"""Supabase authentication provider implementation."""

from uuid import UUID

import httpx
from jose import JWTError, jwt

from dealguard.config import get_settings
from dealguard.infrastructure.auth.provider import AuthProvider, AuthUser
from dealguard.shared.exceptions import (
    AuthenticationError,
    ConflictError,
    TokenExpiredError,
    TokenInvalidError,
)
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


class SupabaseAuthProvider(AuthProvider):
    """Supabase Auth implementation.

    Uses Supabase's JWT tokens and Admin API for user management.
    User metadata stores organization_id and role.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.supabase_url = settings.supabase_url
        self.jwt_secret = settings.supabase_jwt_secret
        self.service_role_key = settings.supabase_service_role_key
        self._client: httpx.AsyncClient | None = None

    @property
    def admin_client(self) -> httpx.AsyncClient:
        """Get or create admin HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.supabase_url}/auth/v1",
                headers={
                    "apikey": self.service_role_key,
                    "Authorization": f"Bearer {self.service_role_key}",
                },
                timeout=30.0,
            )
        return self._client

    async def verify_token(self, token: str) -> AuthUser:
        """Verify Supabase JWT and extract user info."""
        try:
            # Decode JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

            # Extract user info from claims
            user_id = payload.get("sub")
            email = payload.get("email")
            user_metadata = payload.get("user_metadata", {})

            if not user_id or not email:
                raise TokenInvalidError("Token enthält keine Benutzer-ID oder E-Mail")

            # Get organization info from metadata
            organization_id = user_metadata.get("organization_id")
            role = user_metadata.get("role", "member")

            if not organization_id:
                raise TokenInvalidError(
                    "Benutzer ist keiner Organisation zugeordnet"
                )

            return AuthUser(
                id=user_id,
                email=email,
                organization_id=UUID(organization_id),
                role=role,
                email_verified=payload.get("email_confirmed_at") is not None,
                full_name=user_metadata.get("full_name"),
            )

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token ist abgelaufen")
        except JWTError as e:
            logger.warning("jwt_decode_failed", error=str(e))
            raise TokenInvalidError("Token ist ungültig")

    async def get_user(self, user_id: str) -> AuthUser | None:
        """Get user by ID from Supabase."""
        try:
            response = await self.admin_client.get(f"/admin/users/{user_id}")

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            user_metadata = data.get("user_metadata", {})
            organization_id = user_metadata.get("organization_id")

            if not organization_id:
                return None

            return AuthUser(
                id=data["id"],
                email=data["email"],
                organization_id=UUID(organization_id),
                role=user_metadata.get("role", "member"),
                email_verified=data.get("email_confirmed_at") is not None,
                full_name=user_metadata.get("full_name"),
            )

        except httpx.HTTPError as e:
            logger.error("supabase_get_user_failed", user_id=user_id, error=str(e))
            return None

    async def create_user(
        self,
        email: str,
        password: str,
        organization_id: UUID,
        role: str = "member",
        full_name: str | None = None,
    ) -> AuthUser:
        """Create a new user in Supabase."""
        try:
            response = await self.admin_client.post(
                "/admin/users",
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,  # Auto-confirm for now
                    "user_metadata": {
                        "organization_id": str(organization_id),
                        "role": role,
                        "full_name": full_name,
                    },
                },
            )

            if response.status_code == 422:
                error_data = response.json()
                if "already registered" in str(error_data).lower():
                    raise ConflictError("E-Mail-Adresse ist bereits registriert")

            response.raise_for_status()
            data = response.json()

            logger.info(
                "user_created",
                user_id=data["id"],
                email=email,
                organization_id=str(organization_id),
            )

            return AuthUser(
                id=data["id"],
                email=data["email"],
                organization_id=organization_id,
                role=role,
                email_verified=True,
                full_name=full_name,
            )

        except httpx.HTTPError as e:
            logger.error("supabase_create_user_failed", email=email, error=str(e))
            raise AuthenticationError(f"Benutzer konnte nicht erstellt werden: {e}")

    async def delete_user(self, user_id: str) -> None:
        """Delete a user from Supabase."""
        try:
            response = await self.admin_client.delete(f"/admin/users/{user_id}")
            response.raise_for_status()
            logger.info("user_deleted", user_id=user_id)
        except httpx.HTTPError as e:
            logger.error("supabase_delete_user_failed", user_id=user_id, error=str(e))
            raise AuthenticationError(f"Benutzer konnte nicht gelöscht werden: {e}")

    async def update_user_metadata(
        self,
        user_id: str,
        organization_id: UUID | None = None,
        role: str | None = None,
        full_name: str | None = None,
    ) -> AuthUser:
        """Update user metadata in Supabase."""
        # First get current metadata
        current_user = await self.get_user(user_id)
        if not current_user:
            raise AuthenticationError("Benutzer nicht gefunden")

        # Build updated metadata
        metadata = {
            "organization_id": str(organization_id or current_user.organization_id),
            "role": role or current_user.role,
            "full_name": full_name or current_user.full_name,
        }

        try:
            response = await self.admin_client.put(
                f"/admin/users/{user_id}",
                json={"user_metadata": metadata},
            )
            response.raise_for_status()
            data = response.json()

            return AuthUser(
                id=data["id"],
                email=data["email"],
                organization_id=UUID(metadata["organization_id"]),
                role=metadata["role"],
                email_verified=data.get("email_confirmed_at") is not None,
                full_name=metadata.get("full_name"),
            )

        except httpx.HTTPError as e:
            logger.error(
                "supabase_update_user_failed", user_id=user_id, error=str(e)
            )
            raise AuthenticationError(f"Benutzer konnte nicht aktualisiert werden: {e}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
