"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from dealguard import __version__
from dealguard.api.ratelimit import limiter, rate_limit_exceeded_handler
from dealguard.api.router import api_router
from dealguard.api.router_v2 import api_v2_router
from dealguard.config import get_settings
from dealguard.infrastructure.ai.factory import close_ai_client
from dealguard.infrastructure.document.extractor import DocumentExtractor
from dealguard.infrastructure.external.factory import build_partner_providers, close_providers
from dealguard.infrastructure.queue.client import close_queue_pool
from dealguard.infrastructure.storage.s3 import S3Storage
from dealguard.observability.metrics import setup_metrics
from dealguard.shared.exceptions import (
    AuthenticationError,
    DealGuardError,
    NotFoundError,
    QuotaExceededError,
    UnauthorizedError,
    ValidationError,
)
from dealguard.shared.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - startup and shutdown events."""
    # Startup
    setup_logging()
    logger.info("dealguard_starting", version=__version__)

    # Shared resources (avoid per-request client creation)
    settings = get_settings()
    app.state.auth_provider = getattr(app.state, "auth_provider", None) or None
    if app.state.auth_provider is None:
        from dealguard.api.middleware.auth import build_auth_provider

        app.state.auth_provider = build_auth_provider(settings)

    app.state.partner_providers = getattr(
        app.state, "partner_providers", None
    ) or build_partner_providers(settings)
    app.state.s3_storage = getattr(app.state, "s3_storage", None) or S3Storage()
    app.state.document_extractor = (
        getattr(app.state, "document_extractor", None) or DocumentExtractor()
    )

    yield

    # Shutdown
    logger.info("dealguard_stopping")
    await close_providers(getattr(app.state, "partner_providers", None))

    auth_provider = getattr(app.state, "auth_provider", None)
    if auth_provider is not None:
        close = getattr(auth_provider, "close", None)
        if close is not None:
            await close()

    redis_client = getattr(app.state, "redis_client", None)
    if redis_client is not None:
        close = getattr(redis_client, "close", None)
        if close is not None:
            await close()

    await close_ai_client()
    await close_queue_pool()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="DealGuard API",
        description="AI-powered contract analysis and partner intelligence",
        version=__version__,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # CORS middleware
    # In production, be more restrictive; in development, allow all for convenience
    if settings.is_production:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(api_v2_router, prefix="/api/v2")

    # Observability
    setup_metrics(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()},
            },
        )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=401,
            content={
                "error": "authentication_error",
                "message": exc.message,
            },
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=403,
            content={
                "error": "unauthorized",
                "message": exc.message,
            },
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(QuotaExceededError)
    async def quota_exceeded_handler(request: Request, exc: QuotaExceededError) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=429,
            content={
                "error": "quota_exceeded",
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(DealGuardError)
    async def dealguard_error_handler(request: Request, exc: DealGuardError) -> JSONResponse:
        _ = request
        logger.error("unhandled_error", error=exc.message, details=exc.details)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Ein interner Fehler ist aufgetreten",
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        _ = request
        logger.exception("unexpected_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Ein unerwarteter Fehler ist aufgetreten",
            },
        )


# Create app instance
app = create_app()
