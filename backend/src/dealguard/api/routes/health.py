"""Health check endpoints."""

import logging
from typing import Any, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.config import get_settings
from dealguard.infrastructure.database.connection import get_session
from dealguard.infrastructure.storage.s3 import S3Storage
from dealguard.shared.concurrency import to_thread_limited

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str
    redis: str


class ReadyResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check - always returns OK if service is running."""
    from dealguard import __version__

    return HealthResponse(
        status="healthy",
        version=__version__,
        database="not_checked",
        redis="not_checked",
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReadyResponse:
    """Readiness check - verifies all dependencies are available."""
    checks: dict[str, bool] = {}

    # Check database using ORM (no raw SQL)
    try:
        await session.execute(select(literal(1)))
        checks["database"] = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        checks["database"] = False

    # Check Redis
    try:
        import redis.asyncio as redis

        settings = get_settings()
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client is None:
            redis_client = cast(Any, redis.from_url)(str(settings.redis_url))
            request.app.state.redis_client = redis_client
        await redis_client.ping()
        checks["redis"] = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        checks["redis"] = False

    # Check S3 storage
    try:
        settings = get_settings()
        storage = getattr(request.app.state, "s3_storage", None)
        if storage is None:
            storage = S3Storage()
            request.app.state.s3_storage = storage

        await to_thread_limited(
            storage.client.list_objects_v2,
            Bucket=settings.s3_bucket,
            MaxKeys=1,
        )
        checks["storage"] = True
    except Exception as e:
        logger.warning(f"S3 health check failed: {e}")
        checks["storage"] = False

    all_ready = all(checks.values())

    return ReadyResponse(ready=all_ready, checks=checks)
