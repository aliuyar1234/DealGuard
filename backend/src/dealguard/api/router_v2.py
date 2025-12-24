"""API v2 router.

v2 exists for endpoints with breaking contract changes compared to v1.
"""

from fastapi import APIRouter

from dealguard.api.routes import chat_v2

api_v2_router = APIRouter()
api_v2_router.include_router(chat_v2.router)

__all__ = ["api_v2_router"]
