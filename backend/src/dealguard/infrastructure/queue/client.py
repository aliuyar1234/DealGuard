"""Queue client for enqueuing background jobs."""

from typing import Any
from uuid import UUID

from arq.connections import ArqRedis, create_pool, RedisSettings

from dealguard.config import get_settings
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)

_pool: ArqRedis | None = None


async def get_queue_pool() -> ArqRedis:
    """Get or create the ARQ Redis connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await create_pool(
            RedisSettings.from_dsn(str(settings.redis_url))
        )
    return _pool


async def close_queue_pool() -> None:
    """Close the queue pool connection."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def enqueue_job(
    job_name: str,
    *args: Any,
    **kwargs: Any,
) -> str | None:
    """Enqueue a background job.

    Args:
        job_name: Name of the job function to execute
        *args: Positional arguments for the job
        **kwargs: Keyword arguments for the job

    Returns:
        Job ID if successfully enqueued, None otherwise
    """
    try:
        pool = await get_queue_pool()
        job = await pool.enqueue_job(job_name, *args, **kwargs)
        if job:
            logger.info(
                "job_enqueued",
                job_name=job_name,
                job_id=job.job_id,
            )
            return job.job_id
        return None
    except Exception as e:
        logger.exception(
            "job_enqueue_failed",
            job_name=job_name,
            error=str(e),
        )
        return None


async def enqueue_contract_analysis(
    contract_id: UUID,
    organization_id: UUID,
    user_id: UUID,
) -> str | None:
    """Enqueue a contract analysis job.

    Args:
        contract_id: UUID of the contract to analyze
        organization_id: Organization ID for tenant context
        user_id: User ID who initiated the analysis

    Returns:
        Job ID if successfully enqueued
    """
    return await enqueue_job(
        "analyze_contract_job",
        contract_id=str(contract_id),
        organization_id=str(organization_id),
        user_id=str(user_id),
    )


async def enqueue_deadline_extraction(
    contract_id: UUID,
    organization_id: UUID,
    user_id: UUID,
) -> str | None:
    """Enqueue a deadline extraction job.

    This should be called after contract analysis completes to extract
    all dates and deadlines from the contract.

    Args:
        contract_id: UUID of the contract to extract deadlines from
        organization_id: Organization ID for tenant context
        user_id: User ID who initiated the extraction

    Returns:
        Job ID if successfully enqueued
    """
    return await enqueue_job(
        "extract_deadlines_job",
        contract_id=str(contract_id),
        organization_id=str(organization_id),
        user_id=str(user_id),
    )
