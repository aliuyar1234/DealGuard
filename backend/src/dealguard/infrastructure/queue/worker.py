"""Background worker using ARQ (async Redis queue).

Jobs:
- analyze_contract_job: AI analysis of uploaded contracts
- extract_deadlines_job: Extract deadlines after contract analysis
- check_deadlines_job: Daily check for approaching deadlines (cron)
- create_risk_snapshot_job: Daily risk snapshot creation (cron)
- wake_snoozed_alerts_job: Wake up snoozed alerts (cron)
"""

from uuid import UUID

from arq import cron
from arq.connections import RedisSettings

from dealguard.config import get_settings
from dealguard.infrastructure.ai.cost_tracker import CostTracker
from dealguard.infrastructure.ai.factory import get_ai_client
from dealguard.infrastructure.database.connection import get_session_factory
from dealguard.infrastructure.database.models.organization import Organization
from dealguard.infrastructure.database.repositories.contract import (
    ContractAnalysisRepository,
    ContractRepository,
)
from dealguard.infrastructure.document.extractor import DocumentExtractor
from dealguard.infrastructure.storage.s3 import S3Storage
from dealguard.domain.contracts.services import ContractAnalysisService
from dealguard.domain.proactive.deadline_service import DeadlineService
from dealguard.domain.proactive.alert_service import AlertService
from dealguard.domain.proactive.risk_radar_service import RiskRadarService
from dealguard.shared.context import TenantContext, set_tenant_context
from dealguard.shared.logging import get_logger, setup_logging
from sqlalchemy import select

logger = get_logger(__name__)


# ----- Job Functions -----


async def analyze_contract_job(
    ctx: dict,
    contract_id: str,
    organization_id: str,
    user_id: str,
) -> dict:
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

        # Get service from context
        service: ContractAnalysisService = ctx["contract_service"]

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
    ctx: dict,
    contract_id: str,
    organization_id: str,
    user_id: str,
) -> dict:
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

        session = ctx["session"]
        deadline_service = DeadlineService(session)

        deadlines = await deadline_service.extract_deadlines_from_contract(
            UUID(contract_id)
        )

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


async def check_deadlines_job(ctx: dict) -> dict:
    """Daily cron job to check all organizations for approaching deadlines.

    Generates alerts for deadlines that need attention.
    """
    logger.info("job_started", job="check_deadlines")

    try:
        session_factory = ctx["session_factory"]
        total_alerts = 0
        orgs_processed = 0

        # Get all organizations
        async with session_factory() as session:
            query = select(Organization)
            result = await session.execute(query)
            organizations = result.scalars().all()

        # Process each organization
        for org in organizations:
            try:
                async with session_factory() as session:
                    # Set tenant context
                    set_tenant_context(
                        TenantContext(
                            organization_id=org.id,
                            user_id=org.id,  # Use org ID as system user
                            user_email="system@dealguard.io",
                            user_role="system",
                        )
                    )

                    deadline_service = DeadlineService(session)
                    alerts = await deadline_service.check_and_generate_alerts()
                    await session.commit()

                    total_alerts += len(alerts)
                    orgs_processed += 1

            except Exception as e:
                logger.error(
                    "org_deadline_check_failed",
                    organization_id=str(org.id),
                    error=str(e),
                )

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


async def create_risk_snapshot_job(ctx: dict) -> dict:
    """Daily cron job to create risk snapshots for all organizations."""
    logger.info("job_started", job="create_risk_snapshot")

    try:
        session_factory = ctx["session_factory"]
        orgs_processed = 0

        # Get all organizations
        async with session_factory() as session:
            query = select(Organization)
            result = await session.execute(query)
            organizations = result.scalars().all()

        # Process each organization
        for org in organizations:
            try:
                async with session_factory() as session:
                    set_tenant_context(
                        TenantContext(
                            organization_id=org.id,
                            user_id=org.id,
                            user_email="system@dealguard.io",
                            user_role="system",
                        )
                    )

                    risk_radar_service = RiskRadarService(session)
                    await risk_radar_service.create_daily_snapshot()
                    await session.commit()

                    orgs_processed += 1

            except Exception as e:
                logger.error(
                    "org_snapshot_failed",
                    organization_id=str(org.id),
                    error=str(e),
                )

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


async def wake_snoozed_alerts_job(ctx: dict) -> dict:
    """Hourly cron job to wake up snoozed alerts."""
    logger.info("job_started", job="wake_snoozed_alerts")

    try:
        session_factory = ctx["session_factory"]
        total_awakened = 0

        # Get all organizations
        async with session_factory() as session:
            query = select(Organization)
            result = await session.execute(query)
            organizations = result.scalars().all()

        # Process each organization
        for org in organizations:
            try:
                async with session_factory() as session:
                    set_tenant_context(
                        TenantContext(
                            organization_id=org.id,
                            user_id=org.id,
                            user_email="system@dealguard.io",
                            user_role="system",
                        )
                    )

                    alert_service = AlertService(session)
                    count = await alert_service.wake_snoozed_alerts()
                    await session.commit()

                    total_awakened += count

            except Exception as e:
                logger.error(
                    "org_wake_alerts_failed",
                    organization_id=str(org.id),
                    error=str(e),
                )

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


async def startup(ctx: dict) -> None:
    """Initialize worker resources on startup."""
    setup_logging()
    logger.info("worker_starting")

    # Create shared session factory
    session_factory = get_session_factory()

    # Create shared services
    # Note: Each job will get its own session from the factory
    ctx["session_factory"] = session_factory
    ctx["storage"] = S3Storage()
    ctx["extractor"] = DocumentExtractor()
    ctx["ai_client"] = get_ai_client(CostTracker())

    logger.info("worker_started")


async def shutdown(ctx: dict) -> None:
    """Clean up worker resources on shutdown."""
    logger.info("worker_stopping")
    # Add cleanup if needed
    logger.info("worker_stopped")


async def on_job_start(ctx: dict) -> None:
    """Called before each job starts."""
    # Create a new session for this job
    session_factory = ctx["session_factory"]
    session = session_factory()
    ctx["session"] = session

    # Create service with fresh session
    ctx["contract_service"] = ContractAnalysisService(
        contract_repo=ContractRepository(session),
        analysis_repo=ContractAnalysisRepository(session),
        ai_client=ctx["ai_client"],
        storage=ctx["storage"],
        extractor=ctx["extractor"],
    )


async def on_job_end(ctx: dict) -> None:
    """Called after each job completes."""
    # Commit and close session
    session = ctx.get("session")
    if session:
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
