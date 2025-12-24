"""Partner check service - orchestrates external data checks."""

from uuid import UUID

from dealguard.infrastructure.database.models.partner import (
    CheckStatus,
    CheckType,
    PartnerCheck,
)
from dealguard.infrastructure.database.repositories.partner import (
    PartnerCheckRepository,
    PartnerRepository,
)
from dealguard.infrastructure.external.base import (
    CompanyDataProvider,
    CreditProvider,
    InsolvencyProvider,
    SanctionProvider,
)
from dealguard.shared.exceptions import NotFoundError
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


class PartnerCheckService:
    """Service for running external checks on partners.

    This service orchestrates calls to external APIs and stores results.
    """

    def __init__(
        self,
        partner_repo: PartnerRepository,
        check_repo: PartnerCheckRepository,
        company_provider: CompanyDataProvider | None = None,
        credit_provider: CreditProvider | None = None,
        sanction_provider: SanctionProvider | None = None,
        insolvency_provider: InsolvencyProvider | None = None,
    ) -> None:
        self.partner_repo = partner_repo
        self.check_repo = check_repo
        self.company_provider = company_provider
        self.credit_provider = credit_provider
        self.sanction_provider = sanction_provider
        self.insolvency_provider = insolvency_provider

    async def run_handelsregister_check(
        self,
        partner_id: UUID,
    ) -> PartnerCheck:
        """Run Handelsregister check to fetch/update company data."""
        if not self.company_provider:
            raise ValueError("No company provider configured")

        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        # Create check record
        check = PartnerCheck(
            partner_id=partner_id,
            check_type=CheckType.HANDELSREGISTER,
            status=CheckStatus.IN_PROGRESS,
            provider=self.company_provider.provider_name,
        )
        check = await self.check_repo.create(check)

        try:
            # Try to get company data
            company_data = None
            if partner.handelsregister_id:
                company_data = await self.company_provider.get_company_by_register_id(
                    partner.handelsregister_id
                )
            else:
                # Search by name
                results = await self.company_provider.search_companies(partner.name)
                if results:
                    company_data = await self.company_provider.get_company_data(
                        results[0].provider_id
                    )

            if company_data:
                # Update partner with fetched data
                if company_data.handelsregister_id:
                    partner.handelsregister_id = company_data.handelsregister_id
                if company_data.street:
                    partner.street = company_data.street
                if company_data.city:
                    partner.city = company_data.city
                if company_data.postal_code:
                    partner.postal_code = company_data.postal_code

                # Store external data
                partner.external_data = {
                    **partner.external_data,
                    "handelsregister": company_data.raw_data or {},
                    "managing_directors": company_data.managing_directors,
                    "share_capital": company_data.share_capital,
                    "business_purpose": company_data.business_purpose,
                }
                await self.partner_repo.update(partner)

                # Calculate a score (lower = better for operational stability)
                # Factors: company age, capital, active status
                score = 30  # Base score
                if company_data.status != "active":
                    score += 40
                if company_data.share_capital and company_data.share_capital < 25000:
                    score += 15

                check.status = CheckStatus.COMPLETED
                check.score = score
                check.result_summary = (
                    f"Firma gefunden: {company_data.name}. "
                    f"Status: {company_data.status or 'unbekannt'}. "
                    f"Stammkapital: {company_data.share_capital or 'unbekannt'} EUR."
                )
                check.raw_response = company_data.raw_data or {}
            else:
                check.status = CheckStatus.COMPLETED
                check.score = 50  # Neutral - no data found
                check.result_summary = "Keine Handelsregisterdaten gefunden."
                check.raw_response = {}

            check = await self.check_repo.update(check)

            logger.info(
                "handelsregister_check_completed",
                partner_id=str(partner_id),
                score=check.score,
            )

            return check

        except Exception as e:
            check.status = CheckStatus.FAILED
            check.error_message = str(e)
            check = await self.check_repo.update(check)

            logger.exception(
                "handelsregister_check_failed",
                partner_id=str(partner_id),
                error=str(e),
            )
            return check

    async def run_credit_check(
        self,
        partner_id: UUID,
    ) -> PartnerCheck:
        """Run credit/bonität check."""
        if not self.credit_provider:
            raise ValueError("No credit provider configured")

        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        # Create check record
        check = PartnerCheck(
            partner_id=partner_id,
            check_type=CheckType.CREDIT_CHECK,
            status=CheckStatus.IN_PROGRESS,
            provider=self.credit_provider.provider_name,
        )
        check = await self.check_repo.create(check)

        try:
            result = await self.credit_provider.check_credit(
                company_name=partner.name,
                handelsregister_id=partner.handelsregister_id,
                address=f"{partner.street}, {partner.postal_code} {partner.city}"
                if partner.street
                else None,
            )

            check.status = CheckStatus.COMPLETED
            check.score = result.score
            check.result_summary = result.summary
            check.raw_response = result.raw_data or {}
            check = await self.check_repo.update(check)

            # Store in partner external data
            partner.external_data = {
                **partner.external_data,
                "credit": {
                    "score": result.score,
                    "rating": result.rating,
                    "credit_limit_eur": result.credit_limit_eur,
                    "checked_at": check.created_at.isoformat(),
                },
            }
            await self.partner_repo.update(partner)

            logger.info(
                "credit_check_completed",
                partner_id=str(partner_id),
                score=result.score,
            )

            return check

        except Exception as e:
            check.status = CheckStatus.FAILED
            check.error_message = str(e)
            check = await self.check_repo.update(check)

            logger.exception(
                "credit_check_failed",
                partner_id=str(partner_id),
                error=str(e),
            )
            return check

    async def run_sanction_check(
        self,
        partner_id: UUID,
    ) -> PartnerCheck:
        """Run sanctions list check."""
        if not self.sanction_provider:
            raise ValueError("No sanction provider configured")

        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        # Create check record
        check = PartnerCheck(
            partner_id=partner_id,
            check_type=CheckType.SANCTIONS,
            status=CheckStatus.IN_PROGRESS,
            provider=self.sanction_provider.provider_name,
        )
        check = await self.check_repo.create(check)

        try:
            result = await self.sanction_provider.check_sanctions(
                company_name=partner.name,
                country=partner.country,
            )

            check.status = CheckStatus.COMPLETED
            check.score = result.score
            check.result_summary = result.summary
            check.raw_response = result.raw_data or {}
            check = await self.check_repo.update(check)

            logger.info(
                "sanction_check_completed",
                partner_id=str(partner_id),
                is_sanctioned=result.is_sanctioned,
            )

            return check

        except Exception as e:
            check.status = CheckStatus.FAILED
            check.error_message = str(e)
            check = await self.check_repo.update(check)

            logger.exception(
                "sanction_check_failed",
                partner_id=str(partner_id),
                error=str(e),
            )
            return check

    async def run_insolvency_check(
        self,
        partner_id: UUID,
    ) -> PartnerCheck:
        """Run insolvency check."""
        if not self.insolvency_provider:
            raise ValueError("No insolvency provider configured")

        partner = await self.partner_repo.get_by_id(partner_id)
        if not partner:
            raise NotFoundError("Partner", str(partner_id))

        # Create check record
        check = PartnerCheck(
            partner_id=partner_id,
            check_type=CheckType.INSOLVENCY,
            status=CheckStatus.IN_PROGRESS,
            provider=self.insolvency_provider.provider_name,
        )
        check = await self.check_repo.create(check)

        try:
            result = await self.insolvency_provider.check_insolvency(
                company_name=partner.name,
                handelsregister_id=partner.handelsregister_id,
            )

            check.status = CheckStatus.COMPLETED
            check.score = result.score
            check.result_summary = result.summary
            check.raw_response = result.raw_data or {}
            check = await self.check_repo.update(check)

            logger.info(
                "insolvency_check_completed",
                partner_id=str(partner_id),
                has_proceedings=result.has_proceedings,
            )

            return check

        except Exception as e:
            check.status = CheckStatus.FAILED
            check.error_message = str(e)
            check = await self.check_repo.update(check)

            logger.exception(
                "insolvency_check_failed",
                partner_id=str(partner_id),
                error=str(e),
            )
            return check

    async def run_all_checks(
        self,
        partner_id: UUID,
    ) -> list[PartnerCheck]:
        """Run all available checks for a partner."""
        checks = []

        if self.company_provider:
            check = await self.run_handelsregister_check(partner_id)
            checks.append(check)

        if self.credit_provider:
            check = await self.run_credit_check(partner_id)
            checks.append(check)

        if self.sanction_provider:
            check = await self.run_sanction_check(partner_id)
            checks.append(check)

        if self.insolvency_provider:
            check = await self.run_insolvency_check(partner_id)
            checks.append(check)

        logger.info(
            "all_checks_completed",
            partner_id=str(partner_id),
            checks_run=len(checks),
        )

        return checks
