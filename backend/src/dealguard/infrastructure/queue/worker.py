"""Background worker using ARQ (async Redis queue).

Jobs:
- analyze_contract_job: AI analysis of uploaded contracts
- extract_deadlines_job: Extract deadlines after contract analysis
- check_deadlines_job: Daily check for approaching deadlines (cron)
- create_risk_snapshot_job: Daily risk snapshot creation (cron)
- wake_snoozed_alerts_job: Wake up snoozed alerts (cron)
"""

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.config import get_settings
from dealguard.domain.contracts.services import ContractAnalysisService
from dealguard.domain.proactive.alert_service import AlertService
from dealguard.domain.proactive.deadline_service import (
    DeadlineExtractionService,
    DeadlineMonitoringService,
)
from dealguard.domain.proactive.risk_radar_service import RiskRadarService
from dealguard.infrastructure.ai.factory import AIClient, get_ai_client
from dealguard.infrastructure.ai.prompts.deadline_extraction_v1 import (
    DeadlineExtractionPromptV1,
)
from dealguard.infrastructure.database.connection import get_session_factory
from dealguard.infrastructure.database.models.organization import Organization
from dealguard.infrastructure.database.repositories.contract import (
    ContractAnalysisRepository,
    ContractRepository,
)
from dealguard.infrastructure.document.extractor import DocumentExtractor
from dealguard.infrastructure.storage.s3 import S3Storage
from dealguard.shared.context import TenantContext, clear_tenant_context, set_tenant_context
from dealguard.shared.logging import get_logger, setup_logging

logger = get_logger(__name__)


@dataclass
class JobContext:
    session_factory: Callable[[], AsyncSession]
    storage: S3Storage
    extractor: DocumentExtractor
    ai_client: AIClient


@dataclass
class JobState:
    session: AsyncSession
    contract_service: ContractAnalysisService


# ----- Job Functions -----


async def analyze_contract_job(
    ctx: dict[str, object],
    contract_id: str,
    organization_id: str,
    user_id: str,
) -> dict[str, object]:
    """Background job to analyze a contract.

    Args:
        ctx: ARQ context with shared resources
        contract_id: UUID of contract to analyze
        organization_id: Organization ID for tenant context
        user_id: User ID who initiated the analysis

    Returns:
        Result dict with status and details
    """
    logger.info(
        "job_started",
        job="analyze_contract",
        contract_id=contract_id,
    )

    try:
        # Set tenant context for this job
        set_tenant_context(
            TenantContext(
                organization_id=UUID(organization_id),
                user_id=UUID(user_id),
                user_email="worker@internal",
                user_role="system",
            )
        )

        job_state = cast(JobState, ctx["job_state"])
        service = job_state.contract_service

        # Perform analysis
        analysis = await service.perform_analysis(UUID(contract_id))

        logger.info(
            "job_completed",
            job="analyze_contract",
            contract_id=contract_id,
            risk_score=analysis.risk_score,
        )

        return {
            "status": "completed",
            "contract_id": contract_id,
            "risk_score": analysis.risk_score,
        }

    except Exception as e:
        logger.exception(
            "job_failed",
            job="analyze_contract",
            contract_id=contract_id,
            error=str(e),
        )
        return {
            "status": "failed",
            "contract_id": contract_id,
            "error": str(e),
        }


async def extract_deadlines_job(
    ctx: dict[str, object],
    contract_id: str,
    organization_id: str,
    user_id: str,
) -> dict[str, object]:
    """Background job to extract deadlines from a contract.

    This should be called after contract analysis completes.
    """
    logger.info(
        "job_started",
        job="extract_deadlines",
        contract_id=contract_id,
    )

    try:
        # Set tenant context
        set_tenant_context(
            TenantContext(
                organization_id=UUID(organization_id),
                user_id=UUID(user_id),
                user_email="worker@internal",
                user_role="system",
            )
        )

        job_state = cast(JobState, ctx["job_state"])
        job_ctx = cast(JobContext, ctx["job_context"])
        deadline_service = DeadlineExtractionService(
            session=job_state.session,
            ai_client=job_ctx.ai_client,
            prompt=DeadlineExtractionPromptV1(),
            organization_id=UUID(organization_id),
        )

        deadlines = await deadline_service.extract_deadlines_from_contract(UUID(contract_id))

        logger.info(
            "job_completed",
            job="extract_deadlines",
            contract_id=contract_id,
            deadline_count=len(deadlines),
        )

        return {
            "status": "completed",
            "contract_id": contract_id,
            "deadline_count": len(deadlines),
        }

    except Exception as e:
        logger.exception(
            "job_failed",
            job="extract_deadlines",
            contract_id=contract_id,
            error=str(e),
        )
        return {
            "status": "failed",
            "contract_id": contract_id,
            "error": str(e),
        }


async def check_deadlines_job(ctx: dict[str, object]) -> dict[str, object]:
    """Daily cron job to check all organizations for approaching deadlines.

    Generates alerts for deadlines that need attention.
    """
    logger.info("job_started", job="check_deadlines")

    try:
        job_ctx = cast(JobContext, ctx["job_context"])
        session_factory = job_ctx.session_factory
        total_alerts = 0
        orgs_processed = 0

        max_org_concurrency = int(os.getenv("DEALGUARD_ORG_JOB_CONCURRENCY", "5"))
        max_org_concurrency = max(1, min(32, max_org_concurrency))
        batch_size = int(os.getenv("DEALGUARD_ORG_JOB_BATCH_SIZE", "200"))
        batch_size = max(1, min(2000, batch_size))

        semaphore = asyncio.Semaphore(max_org_concurrency)

        async def _process_org(org_id: UUID) -> tuple[bool, int]:
            await semaphore.acquire()
            try:
                async with session_factory() as session:
                    set_tenant_context(
                        TenantContext(
                            organization_id=org_id,
                            user_id=org_id,  # System user
                            user_email="system@dealguard.io",
                            user_role="system",
                        )
                    )

                    deadline_service = DeadlineMonitoringService(
                        session,
                        organization_id=org_id,
                        user_id=org_id,
                    )
                    alerts = await deadline_service.check_and_generate_alerts()
                    await session.commit()

                    return True, len(alerts)
            except Exception as e:
                logger.error(
                    "org_deadline_check_failed",
                    organization_id=str(org_id),
                    error=str(e),
                )
                return False, 0
            finally:
                clear_tenant_context()
                semaphore.release()

        last_org_id: UUID | None = None
        while True:
            async with session_factory() as session:
                query = select(Organization.id).order_by(Organization.id).limit(batch_size)
                if last_org_id is not None:
                    query = query.where(Organization.id > last_org_id)
                result = await session.execute(query)
                org_ids = list(result.scalars().all())

            if not org_ids:
                break

            last_org_id = org_ids[-1]

            results = await asyncio.gather(*(_process_org(org_id) for org_id in org_ids))
            for ok, alerts_count in results:
                if ok:
                    orgs_processed += 1
                total_alerts += alerts_count

        logger.info(
            "job_completed",
            job="check_deadlines",
            orgs_processed=orgs_processed,
            total_alerts=total_alerts,
        )

        return {
            "status": "completed",
            "orgs_processed": orgs_processed,
            "alerts_generated": total_alerts,
        }

    except Exception as e:
        logger.exception(
            "job_failed",
            job="check_deadlines",
            error=str(e),
        )
        return {"status": "failed", "error": str(e)}


async def create_risk_snapshot_job(ctx: dict[str, object]) -> dict[str, object]:
    """Daily cron job to create risk snapshots for all organizations."""
    logger.info("job_started", job="create_risk_snapshot")

    try:
        job_ctx = cast(JobContext, ctx["job_context"])
        session_factory = job_ctx.session_factory
        orgs_processed = 0

        max_org_concurrency = int(os.getenv("DEALGUARD_ORG_JOB_CONCURRENCY", "5"))
        max_org_concurrency = max(1, min(32, max_org_concurrency))
        batch_size = int(os.getenv("DEALGUARD_ORG_JOB_BATCH_SIZE", "200"))
        batch_size = max(1, min(2000, batch_size))

        semaphore = asyncio.Semaphore(max_org_concurrency)

        async def _process_org(org_id: UUID) -> bool:
            await semaphore.acquire()
            try:
                async with session_factory() as session:
                    set_tenant_context(
                        TenantContext(
                            organization_id=org_id,
                            user_id=org_id,
                            user_email="system@dealguard.io",
                            user_role="system",
                        )
                    )

                    risk_radar_service = RiskRadarService(
                        session,
                        organization_id=org_id,
                    )
                    await risk_radar_service.create_daily_snapshot()
                    await session.commit()
                    return True
            except Exception as e:
                logger.error(
                    "org_snapshot_failed",
                    organization_id=str(org_id),
                    error=str(e),
                )
                return False
            finally:
                clear_tenant_context()
                semaphore.release()

        last_org_id: UUID | None = None
        while True:
            async with session_factory() as session:
                query = select(Organization.id).order_by(Organization.id).limit(batch_size)
                if last_org_id is not None:
                    query = query.where(Organization.id > last_org_id)
                result = await session.execute(query)
                org_ids = list(result.scalars().all())

            if not org_ids:
                break

            last_org_id = org_ids[-1]

            results = await asyncio.gather(*(_process_org(org_id) for org_id in org_ids))
            orgs_processed += sum(1 for ok in results if ok)

        logger.info(
            "job_completed",
            job="create_risk_snapshot",
            orgs_processed=orgs_processed,
        )

        return {
            "status": "completed",
            "orgs_processed": orgs_processed,
        }

    except Exception as e:
        logger.exception(
            "job_failed",
            job="create_risk_snapshot",
            error=str(e),
        )
        return {"status": "failed", "error": str(e)}


async def wake_snoozed_alerts_job(ctx: dict[str, object]) -> dict[str, object]:
    """Hourly cron job to wake up snoozed alerts."""
    logger.info("job_started", job="wake_snoozed_alerts")

    try:
        job_ctx = cast(JobContext, ctx["job_context"])
        session_factory = job_ctx.session_factory
        total_awakened = 0

        max_org_concurrency = int(os.getenv("DEALGUARD_ORG_JOB_CONCURRENCY", "5"))
        max_org_concurrency = max(1, min(32, max_org_concurrency))
        batch_size = int(os.getenv("DEALGUARD_ORG_JOB_BATCH_SIZE", "200"))
        batch_size = max(1, min(2000, batch_size))

        semaphore = asyncio.Semaphore(max_org_concurrency)

        async def _process_org(org_id: UUID) -> tuple[bool, int]:
            await semaphore.acquire()
            try:
                async with session_factory() as session:
                    set_tenant_context(
                        TenantContext(
                            organization_id=org_id,
                            user_id=org_id,
                            user_email="system@dealguard.io",
                            user_role="system",
                        )
                    )

                    alert_service = AlertService(
                        session,
                        organization_id=org_id,
                        user_id=org_id,
                    )
                    count = await alert_service.wake_snoozed_alerts()
                    await session.commit()
                    return True, count
            except Exception as e:
                logger.error(
                    "org_wake_alerts_failed",
                    organization_id=str(org_id),
                    error=str(e),
                )
                return False, 0
            finally:
                clear_tenant_context()
                semaphore.release()

        last_org_id: UUID | None = None
        while True:
            async with session_factory() as session:
                query = select(Organization.id).order_by(Organization.id).limit(batch_size)
                if last_org_id is not None:
                    query = query.where(Organization.id > last_org_id)
                result = await session.execute(query)
                org_ids = list(result.scalars().all())

            if not org_ids:
                break

            last_org_id = org_ids[-1]

            results = await asyncio.gather(*(_process_org(org_id) for org_id in org_ids))
            for _ok, awakened in results:
                total_awakened += awakened

        logger.info(
            "job_completed",
            job="wake_snoozed_alerts",
            total_awakened=total_awakened,
        )

        return {
            "status": "completed",
            "alerts_awakened": total_awakened,
        }

    except Exception as e:
        logger.exception(
            "job_failed",
            job="wake_snoozed_alerts",
            error=str(e),
        )
        return {"status": "failed", "error": str(e)}


# ----- Worker Settings -----


async def startup(ctx: dict[str, object]) -> None:
    """Initialize worker resources on startup."""
    setup_logging()
    logger.info("worker_starting")

    # Create shared session factory
    session_factory = get_session_factory()

    # Create shared services
    # Note: Each job will get its own session from the factory
    ctx["job_context"] = JobContext(
        session_factory=session_factory,
        storage=S3Storage(),
        extractor=DocumentExtractor(),
        ai_client=get_ai_client(),
    )

    logger.info("worker_started")


async def shutdown(ctx: dict[str, object]) -> None:
    """Clean up worker resources on shutdown."""
    _ = ctx
    logger.info("worker_stopping")
    from dealguard.infrastructure.ai.factory import close_ai_client

    await close_ai_client()
    logger.info("worker_stopped")


async def on_job_start(ctx: dict[str, object]) -> None:
    """Called before each job starts."""
    job_ctx = cast(JobContext, ctx["job_context"])
    session = job_ctx.session_factory()
    ctx["job_state"] = JobState(
        session=session,
        contract_service=ContractAnalysisService(
            contract_repo=ContractRepository(session),
            analysis_repo=ContractAnalysisRepository(session),
            ai_client=job_ctx.ai_client,
            storage=job_ctx.storage,
            extractor=job_ctx.extractor,
            transaction=session,
        ),
    )


async def on_job_end(ctx: dict[str, object]) -> None:
    """Called after each job completes."""
    # Commit and close session
    job_state_value = ctx.get("job_state")
    job_state = job_state_value if isinstance(job_state_value, JobState) else None
    if job_state is not None:
        try:
            await job_state.session.commit()
        except Exception:
            await job_state.session.rollback()
            raise
        finally:
            await job_state.session.close()


def get_redis_settings() -> RedisSettings:
    """Get Redis settings from app config."""
    settings = get_settings()
    return RedisSettings.from_dsn(str(settings.redis_url))


class WorkerSettings:
    """ARQ worker settings."""

    # Job functions (on-demand jobs)
    functions = [
        analyze_contract_job,
        extract_deadlines_job,
    ]

    # Redis connection - must be a RedisSettings instance, not a method
    redis_settings = get_redis_settings()

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end

    # Worker config
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    keep_result = 3600  # Keep results for 1 hour
    retry_jobs = True
    max_tries = 3

    # Cron jobs (scheduled tasks)
    cron_jobs = [
        # Daily at 6:00 AM - Check deadlines and generate alerts
        cron(check_deadlines_job, hour=6, minute=0),
        # Daily at 6:30 AM - Create risk snapshots for trending
        cron(create_risk_snapshot_job, hour=6, minute=30),
        # Every hour - Wake up snoozed alerts
        cron(wake_snoozed_alerts_job, minute=0),
    ]
