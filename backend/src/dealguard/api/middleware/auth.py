"""Authentication middleware for FastAPI."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dealguard.config import Settings, get_settings
from dealguard.infrastructure.auth.provider import AuthProvider, AuthUser
from dealguard.shared.context import set_tenant_context
from dealguard.shared.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
)
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer scheme
security = HTTPBearer(auto_error=False)


def build_auth_provider(settings: Settings) -> AuthProvider:
    """Build the configured auth provider.

    Set AUTH_PROVIDER env var to "dev" for local testing without Supabase.
    To switch to Clerk later, just change this function.
    """
    if settings.auth_provider == "dev":
        from dealguard.infrastructure.auth.dev import DevAuthProvider

        return DevAuthProvider()

    from dealguard.infrastructure.auth.supabase import SupabaseAuthProvider

    return SupabaseAuthProvider()


def get_auth_provider(request: Request) -> AuthProvider:
    """Get a cached auth provider instance (per FastAPI app)."""
    provider = getattr(request.app.state, "auth_provider", None)
    if provider is None:
        provider = build_auth_provider(get_settings())
        request.app.state.auth_provider = provider
    return provider


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_provider: Annotated[AuthProvider, Depends(get_auth_provider)],
) -> AuthUser:
    """Dependency to get the current authenticated user.

    Usage:
        @router.get("/me")
        async def get_me(user: AuthUser = Depends(get_current_user)):
            return {"email": user.email}
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentifizierung erforderlich",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await auth_provider.verify_token(credentials.credentials)

        # Set tenant context for this request
        set_tenant_context(user.to_tenant_context())

        # Make the authenticated user available to utilities (e.g., rate limiter keying)
        request.state.user = user

        logger.debug(
            "user_authenticated",
            user_id=user.id,
            email=user.email,
            organization_id=str(user.organization_id),
        )

        return user

    except TokenExpiredError:
        raise HTTPException(
            status_code=401,
            detail="Token abgelaufen. Bitte erneut anmelden.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenInvalidError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e.message),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError as e:
        logger.warning("auth_failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Authentifizierung fehlgeschlagen",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_provider: Annotated[AuthProvider, Depends(get_auth_provider)],
) -> AuthUser | None:
    """Dependency to get the current user if authenticated, None otherwise.

    Useful for endpoints that work both with and without authentication.
    """
    if credentials is None:
        return None

    try:
        user = await auth_provider.verify_token(credentials.credentials)
        set_tenant_context(user.to_tenant_context())
        request.state.user = user
        return user
    except (TokenExpiredError, TokenInvalidError, AuthenticationError):
        return None


def require_role(*roles: str) -> Callable[[AuthUser], Awaitable[AuthUser]]:
    """Dependency factory to require specific roles.

    Usage:
        @router.delete("/org")
        async def delete_org(
            user: AuthUser = Depends(require_role("owner"))
        ):
            ...
    """

    async def check_role(
        user: Annotated[AuthUser, Depends(get_current_user)],
    ) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Diese Aktion erfordert eine der Rollen: {', '.join(roles)}",
            )
        return user

    return check_role


# Common role dependencies
RequireOwner = Annotated[AuthUser, Depends(require_role("owner"))]
RequireAdmin = Annotated[AuthUser, Depends(require_role("owner", "admin"))]
RequireMember = Annotated[AuthUser, Depends(require_role("owner", "admin", "member"))]

# Type alias for authenticated user
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
OptionalUser = Annotated[AuthUser | None, Depends(get_optional_user)]
