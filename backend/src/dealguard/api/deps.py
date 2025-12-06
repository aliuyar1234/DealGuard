"""FastAPI dependencies for API routes.

This module re-exports commonly used dependencies for convenience.
"""

from dealguard.api.middleware.auth import get_current_user
from dealguard.infrastructure.database.connection import get_session, SessionDep

# Re-export get_session as get_db for compatibility
get_db = get_session

__all__ = [
    "get_current_user",
    "get_db",
    "get_session",
    "SessionDep",
]
