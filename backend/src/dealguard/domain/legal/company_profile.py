"""Company profile service for legal context.

Stores legal context about the company in Organization.settings.
This context is used by the AI to provide better answers.
"""

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.infrastructure.database.models.organization import Organization
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CompanyProfile:
    """Legal context about the company.

    Stored in Organization.settings["legal_profile"].
    """

    # Basic info
    company_name: str | None = None
    industry: str | None = None  # e.g., "E-Commerce", "SaaS", "Manufacturing"
    company_size: str | None = None  # "1-10", "11-50", "51-250", "250+"

    # Legal jurisdiction
    jurisdiction: str = "AT"  # AT, DE, CH

    # Risk preferences
    risk_tolerance: str = "moderate"  # "conservative", "moderate", "aggressive"

    # Key business activities (helps AI understand context)
    business_activities: list[str] = field(default_factory=list)

    # Typical contract types the company deals with
    typical_contract_types: list[str] = field(default_factory=list)

    # Custom legal guidelines/concerns
    custom_guidelines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyProfile":
        """Create from dictionary."""
        if not data:
            return cls()

        return cls(
            company_name=data.get("company_name"),
            industry=data.get("industry"),
            company_size=data.get("company_size"),
            jurisdiction=data.get("jurisdiction", "AT"),
            risk_tolerance=data.get("risk_tolerance", "moderate"),
            business_activities=data.get("business_activities", []),
            typical_contract_types=data.get("typical_contract_types", []),
            custom_guidelines=data.get("custom_guidelines", []),
        )


class CompanyProfileService:
    """Service for managing company legal profile.

    The profile is stored in Organization.settings["legal_profile"].
    This allows extending the profile without database migrations.
    """

    SETTINGS_KEY = "legal_profile"

    def __init__(self, session: AsyncSession, *, organization_id: UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    def _get_organization_id(self) -> UUID:
        """Get current tenant's organization ID."""
        return self.organization_id

    async def get_profile(self) -> CompanyProfile:
        """Get the company's legal profile.

        Returns empty profile if not set.
        """
        org_id = self._get_organization_id()

        query = select(Organization).where(Organization.id == org_id)
        result = await self.session.execute(query)
        org = result.scalar_one_or_none()

        if not org:
            logger.warning("organization_not_found", org_id=str(org_id))
            return CompanyProfile()

        # Extract legal_profile from settings
        profile_data = org.settings.get(self.SETTINGS_KEY, {})
        profile = CompanyProfile.from_dict(profile_data)

        # Use org name as fallback
        if not profile.company_name:
            profile.company_name = org.name

        return profile

    async def update_profile(self, profile: CompanyProfile) -> CompanyProfile:
        """Update the company's legal profile.

        Merges with existing settings to preserve other settings.
        """
        org_id = self._get_organization_id()

        # Get current organization
        query = select(Organization).where(Organization.id == org_id)
        result = await self.session.execute(query)
        org = result.scalar_one_or_none()

        if not org:
            raise ValueError(f"Organization not found: {org_id}")

        # Merge with existing settings
        new_settings = dict(org.settings)  # Copy
        new_settings[self.SETTINGS_KEY] = profile.to_dict()

        # Update
        org.settings = new_settings
        await self.session.flush()

        logger.info(
            "company_profile_updated",
            organization_id=str(org_id),
            jurisdiction=profile.jurisdiction,
            industry=profile.industry,
        )

        return profile

    async def get_organization_name(self) -> str:
        """Get the organization's name."""
        org_id = self._get_organization_id()

        query = select(Organization.name).where(Organization.id == org_id)
        result = await self.session.execute(query)
        name = result.scalar_one_or_none()

        return name or "Unbekanntes Unternehmen"
