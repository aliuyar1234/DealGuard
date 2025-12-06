"""Main API router aggregating all routes."""

from fastapi import APIRouter

from dealguard.api.routes import contracts, health, partners, legal_chat, company_profile, proactive, chat_v2, settings

# Create main router
api_router = APIRouter()

# Include route modules
api_router.include_router(health.router)
api_router.include_router(contracts.router)
api_router.include_router(partners.router)
api_router.include_router(legal_chat.router)
api_router.include_router(company_profile.router)
api_router.include_router(proactive.router)
api_router.include_router(chat_v2.router)  # DealGuard 2.0 Chat with Tool-Calling
api_router.include_router(settings.router)  # User settings and API keys
