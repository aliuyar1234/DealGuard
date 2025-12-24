"""Main API router aggregating all v1 routes."""

from fastapi import APIRouter

from dealguard.api.routes import (
    company_profile,
    contracts,
    health,
    legal_chat,
    partners,
    proactive,
    settings,
)

# Create main router
api_router = APIRouter()

# Include route modules
api_router.include_router(health.router)
api_router.include_router(contracts.router)
api_router.include_router(partners.router)
api_router.include_router(legal_chat.router)
api_router.include_router(company_profile.router)
api_router.include_router(proactive.router)
api_router.include_router(settings.router)  # User settings and API keys
