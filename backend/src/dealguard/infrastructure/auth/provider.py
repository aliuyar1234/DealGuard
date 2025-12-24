"""Abstract authentication provider interface.

This abstraction allows switching between auth providers (Supabase → Clerk)
without changing the rest of the application.

To switch to Clerk later:
1. Create ClerkAuthProvider implementing AuthProvider
2. Update dependencies.py to use ClerkAuthProvider
3. That's it!
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from dealguard.shared.context import TenantContext


@dataclass(frozen=True)
class AuthUser:
    """Authenticated user data from auth provider.

    This is the unified user representation across all auth providers.
    """

    id: str  # Provider's user ID (e.g., Supabase UUID or Clerk user_id)
    email: str
    organization_id: UUID  # Our internal organization ID
    role: str  # User role within organization
    email_verified: bool = False
    full_name: str | None = None

    def to_tenant_context(self) -> "TenantContext":
        """Convert to TenantContext for request processing."""
        from dealguard.shared.context import TenantContext

        return TenantContext(
            organization_id=self.organization_id,
            user_id=UUID(self.id) if self._is_uuid(self.id) else UUID(int=0),
            user_email=self.email,
            user_role=self.role,
        )

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            UUID(value)
            return True
        except ValueError:
            return False


class AuthProvider(ABC):
    """Abstract authentication provider.

    Implementations:
    - SupabaseAuthProvider: Current implementation using Supabase Auth
    - ClerkAuthProvider: Future implementation for Clerk
    """

    @abstractmethod
    async def verify_token(self, token: str) -> AuthUser:
        """Verify a JWT token and return the authenticated user.

        Args:
            token: JWT access token from Authorization header

        Returns:
            AuthUser with user details and organization info

        Raises:
            TokenExpiredError: If the token has expired
            TokenInvalidError: If the token is invalid
            AuthenticationError: For other auth failures
        """
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> AuthUser | None:
        """Get user by ID.

        Args:
            user_id: The provider's user ID

        Returns:
            AuthUser if found, None otherwise
        """
        pass

    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str,
        organization_id: UUID,
        role: str = "member",
        full_name: str | None = None,
    ) -> AuthUser:
        """Create a new user.

        Args:
            email: User's email address
            password: Password (will be hashed by provider)
            organization_id: Organization to add user to
            role: User's role within organization
            full_name: Optional full name

        Returns:
            Created AuthUser

        Raises:
            ConflictError: If email already exists
        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Delete a user.

        Args:
            user_id: The provider's user ID
        """
        pass
