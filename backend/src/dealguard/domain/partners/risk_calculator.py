"""Partner risk score calculator."""

from typing import Sequence

from dealguard.infrastructure.database.models.partner import (
    PartnerCheck,
    PartnerRiskLevel,
    CheckType,
    CheckStatus,
)


class PartnerRiskCalculator:
    """Calculate partner risk score from check results.

    Score components and weights:
    - Financial Stability (30%): Credit/Bonität check
    - Legal Compliance (25%): Sanctions, insolvency checks
    - Reputation (20%): News sentiment
    - Operative Stability (15%): Handelsregister data
    - ESG (10%): ESG check

    Score range: 0-100 (0 = low risk, 100 = critical risk)
    """

    WEIGHTS = {
        CheckType.CREDIT_CHECK: 0.30,
        CheckType.SANCTIONS: 0.15,
        CheckType.INSOLVENCY: 0.10,
        CheckType.NEWS: 0.20,
        CheckType.HANDELSREGISTER: 0.15,
        CheckType.ESG: 0.10,
    }

    def calculate(
        self,
        checks: Sequence[PartnerCheck],
    ) -> tuple[int, PartnerRiskLevel]:
        """Calculate overall risk score from completed checks.

        Args:
            checks: List of completed partner checks

        Returns:
            Tuple of (risk_score, risk_level)
        """
        if not checks:
            return 0, PartnerRiskLevel.UNKNOWN

        # Filter to completed checks with scores
        scored_checks = [
            c for c in checks
            if c.status == CheckStatus.COMPLETED and c.score is not None
        ]

        if not scored_checks:
            return 0, PartnerRiskLevel.UNKNOWN

        # Calculate weighted average
        total_weight = 0.0
        weighted_sum = 0.0

        for check in scored_checks:
            weight = self.WEIGHTS.get(check.check_type, 0.1)
            weighted_sum += check.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0, PartnerRiskLevel.UNKNOWN

        # Normalize to 100
        risk_score = int(weighted_sum / total_weight)

        # Clamp to 0-100
        risk_score = max(0, min(100, risk_score))

        # Determine risk level
        risk_level = self._score_to_level(risk_score)

        return risk_score, risk_level

    def _score_to_level(self, score: int) -> PartnerRiskLevel:
        """Convert numeric score to risk level."""
        if score <= 30:
            return PartnerRiskLevel.LOW
        elif score <= 60:
            return PartnerRiskLevel.MEDIUM
        elif score <= 80:
            return PartnerRiskLevel.HIGH
        else:
            return PartnerRiskLevel.CRITICAL

    def calculate_component_scores(
        self,
        checks: Sequence[PartnerCheck],
    ) -> dict[str, int | None]:
        """Get individual component scores for display.

        Returns:
            Dict mapping component names to scores (or None if not available)
        """
        component_scores = {
            "financial_stability": None,
            "legal_compliance": None,
            "reputation": None,
            "operative_stability": None,
            "esg": None,
        }

        # Map check types to component names
        type_to_component = {
            CheckType.CREDIT_CHECK: "financial_stability",
            CheckType.SANCTIONS: "legal_compliance",
            CheckType.INSOLVENCY: "legal_compliance",
            CheckType.NEWS: "reputation",
            CheckType.HANDELSREGISTER: "operative_stability",
            CheckType.ESG: "esg",
        }

        # Get most recent score for each component
        for check in sorted(checks, key=lambda c: c.created_at, reverse=True):
            if check.status != CheckStatus.COMPLETED or check.score is None:
                continue

            component = type_to_component.get(check.check_type)
            if component and component_scores[component] is None:
                component_scores[component] = check.score

        return component_scores
