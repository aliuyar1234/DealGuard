"""Health check endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, literal
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.config import get_settings
from dealguard.infrastructure.database.connection import get_session

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
        redis_client = redis.from_url(str(settings.redis_url))
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        checks["redis"] = False

    # Check S3 storage
    try:
        import boto3
        from botocore.config import Config

        settings = get_settings()
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4"),
        )
        await asyncio.to_thread(
            s3_client.list_objects_v2, Bucket=settings.s3_bucket, MaxKeys=1
        )
        checks["storage"] = True
    except Exception as e:
        logger.warning(f"S3 health check failed: {e}")
        checks["storage"] = False

    all_ready = all(checks.values())

    return ReadyResponse(ready=all_ready, checks=checks)
