"""Company Profile API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from dealguard.api.middleware.auth import CurrentUser, RequireMember
from dealguard.domain.legal.company_profile import (
    CompanyProfile,
    CompanyProfileService,
)
from dealguard.infrastructure.database.connection import SessionDep
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/company", tags=["Company Profile"])


# ─────────────────────────────────────────────────────────────
#                     SCHEMAS
# ─────────────────────────────────────────────────────────────


class CompanyProfileResponse(BaseModel):
    """Company legal profile response."""

    company_name: str | None = None
    industry: str | None = None
    company_size: str | None = None
    jurisdiction: str = "AT"
    risk_tolerance: str = "moderate"
    business_activities: list[str] = []
    typical_contract_types: list[str] = []
    custom_guidelines: list[str] = []


class UpdateCompanyProfileRequest(BaseModel):
    """Request to update company profile."""

    company_name: str | None = Field(None, max_length=255)
    industry: str | None = Field(None, max_length=100)
    company_size: str | None = Field(None, pattern="^(1-10|11-50|51-250|250\\+)$")
    jurisdiction: str = Field("AT", pattern="^(AT|DE|CH)$")
    risk_tolerance: str = Field(
        "moderate",
        pattern="^(conservative|moderate|aggressive)$",
    )
    business_activities: list[str] = Field(default_factory=list, max_length=10)
    typical_contract_types: list[str] = Field(default_factory=list, max_length=10)
    custom_guidelines: list[str] = Field(default_factory=list, max_length=20)


# ─────────────────────────────────────────────────────────────
#                   DEPENDENCIES
# ─────────────────────────────────────────────────────────────


async def get_profile_service(
    session: SessionDep,
    user: CurrentUser,
) -> CompanyProfileService:
    """Get company profile service."""
    return CompanyProfileService(session, organization_id=user.organization_id)


ProfileServiceDep = Annotated[CompanyProfileService, Depends(get_profile_service)]


# ─────────────────────────────────────────────────────────────
#                      ROUTES
# ─────────────────────────────────────────────────────────────


@router.get("/profile", response_model=CompanyProfileResponse)
async def get_profile(
    user: CurrentUser,
    service: ProfileServiceDep,
) -> CompanyProfileResponse:
    """Get the company's legal profile.

    The profile includes:
    - Company info (name, industry, size)
    - Legal jurisdiction (AT, DE, CH)
    - Risk tolerance (conservative, moderate, aggressive)
    - Business activities
    - Typical contract types
    - Custom legal guidelines

    This information helps the AI-Jurist provide better answers.
    """
    profile = await service.get_profile()

    return CompanyProfileResponse(
        company_name=profile.company_name,
        industry=profile.industry,
        company_size=profile.company_size,
        jurisdiction=profile.jurisdiction,
        risk_tolerance=profile.risk_tolerance,
        business_activities=profile.business_activities,
        typical_contract_types=profile.typical_contract_types,
        custom_guidelines=profile.custom_guidelines,
    )


@router.put("/profile", response_model=CompanyProfileResponse)
async def update_profile(
    request: UpdateCompanyProfileRequest,
    user: RequireMember,
    service: ProfileServiceDep,
) -> CompanyProfileResponse:
    """Update the company's legal profile.

    Setting up your company profile helps the AI-Jurist:
    - Understand your business context
    - Apply the correct legal jurisdiction (AT/DE/CH)
    - Adjust analysis based on your risk tolerance
    - Focus on your typical contract types
    """
    profile = CompanyProfile(
        company_name=request.company_name,
        industry=request.industry,
        company_size=request.company_size,
        jurisdiction=request.jurisdiction,
        risk_tolerance=request.risk_tolerance,
        business_activities=request.business_activities,
        typical_contract_types=request.typical_contract_types,
        custom_guidelines=request.custom_guidelines,
    )

    updated = await service.update_profile(profile)

    logger.info(
        "company_profile_updated_via_api",
        jurisdiction=updated.jurisdiction,
        industry=updated.industry,
    )

    return CompanyProfileResponse(
        company_name=updated.company_name,
        industry=updated.industry,
        company_size=updated.company_size,
        jurisdiction=updated.jurisdiction,
        risk_tolerance=updated.risk_tolerance,
        business_activities=updated.business_activities,
        typical_contract_types=updated.typical_contract_types,
        custom_guidelines=updated.custom_guidelines,
    )
