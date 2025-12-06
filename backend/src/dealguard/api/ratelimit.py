"""Rate limiting configuration for API endpoints.

Uses slowapi with Redis backend for distributed rate limiting.
Falls back to in-memory storage for development.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from dealguard.config import get_settings

logger = logging.getLogger(__name__)


def _get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on user or IP.

    For authenticated requests, use user_id.
    For unauthenticated requests, use IP address.
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address
    return get_remote_address(request)


def _create_limiter(storage_uri: str = "memory://") -> Limiter:
    """Create rate limiter with appropriate storage backend."""
    return Limiter(
        key_func=_get_rate_limit_key,
        storage_uri=storage_uri,
        strategy="fixed-window",
    )


def get_limiter() -> Limiter:
    """Get or create the rate limiter with appropriate storage backend.

    Uses lazy initialization to avoid settings loading at import time.
    """
    global _limiter
    if _limiter is None:
        try:
            settings = get_settings()
            # Use Redis for production, in-memory for development
            if settings.is_production:
                storage_uri = str(settings.redis_url)
                logger.info("Rate limiter using Redis backend")
            else:
                storage_uri = "memory://"
                logger.info("Rate limiter using in-memory backend (dev mode)")
        except Exception:
            # Fallback for testing or when settings not available
            storage_uri = "memory://"
            logger.info("Rate limiter using in-memory backend (fallback)")

        _limiter = _create_limiter(storage_uri)
    return _limiter


# Global limiter instance (lazy initialization)
_limiter: Limiter | None = None

# For backwards compatibility - creates default in-memory limiter
limiter = _create_limiter("memory://")


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        method=request.method,
        key=_get_rate_limit_key(request),
        limit=str(exc.detail),
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "too_many_requests",
            "message": "Zu viele Anfragen. Bitte warten Sie einen Moment.",
            "detail": str(exc.detail),
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": str(exc.detail).split("/")[0] if "/" in str(exc.detail) else "unknown",
        },
    )


# ----- Rate Limit Decorators -----
# Usage: @limiter.limit("10/minute")

# Standard API limits
RATE_LIMIT_DEFAULT = "100/minute"        # General API calls
RATE_LIMIT_AUTH = "5/minute"             # Login/Register attempts
RATE_LIMIT_UPLOAD = "10/minute"          # File uploads
RATE_LIMIT_AI = "20/minute"              # AI-powered endpoints (expensive)
RATE_LIMIT_SEARCH = "30/minute"          # Search endpoints
RATE_LIMIT_HEALTH = "60/minute"          # Health checks


def get_rate_limit_decorator(limit: str) -> Callable:
    """Get a rate limit decorator with the specified limit.

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")

    Returns:
        Decorator function
    """
    return limiter.limit(limit)
