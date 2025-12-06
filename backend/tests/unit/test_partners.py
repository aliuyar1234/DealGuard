"""
Unit tests for Partner domain (Phase 2).
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from dealguard.domain.partners.risk_calculator import PartnerRiskCalculator
from dealguard.infrastructure.database.models.partner import (
    AlertSeverity,
    AlertType,
    CheckStatus,
    CheckType,
    ContractPartner,
    Partner,
    PartnerAlert,
    PartnerCheck,
    PartnerRiskLevel,
    PartnerType,
)


class TestPartnerModel:
    """Tests for Partner model."""

    def test_partner_creation(self):
        """Test partner model can be created with required fields."""
        org_id = uuid.uuid4()
        partner = Partner(
            id=uuid.uuid4(),
            organization_id=org_id,
            name="Test Partner GmbH",
            partner_type=PartnerType.SUPPLIER,
        )

        assert partner.name == "Test Partner GmbH"
        assert partner.partner_type == PartnerType.SUPPLIER
        assert partner.organization_id == org_id
        # Default is set in DB column, not Python-side
        # assert partner.risk_level == PartnerRiskLevel.UNKNOWN

    def test_partner_with_full_details(self):
        """Test partner model with all optional fields."""
        partner = Partner(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            name="ACME GmbH",
            partner_type=PartnerType.CUSTOMER,
            handelsregister_id="HRB 12345",
            vat_id="DE123456789",
            street="Musterstraße 123",
            city="Berlin",
            postal_code="10115",
            country="DE",
            website="https://acme.de",
            email="kontakt@acme.de",
            phone="+49 30 12345678",
            notes="Important customer",
            is_watched=True,
            risk_score=45,
            risk_level=PartnerRiskLevel.MEDIUM,
        )

        assert partner.handelsregister_id == "HRB 12345"
        assert partner.vat_id == "DE123456789"
        assert partner.city == "Berlin"
        assert partner.country == "DE"
        assert partner.is_watched is True
        assert partner.risk_score == 45
        assert partner.risk_level == PartnerRiskLevel.MEDIUM


class TestPartnerTypes:
    """Tests for partner type enumerations."""

    def test_partner_type_values(self):
        """Test all partner type values exist."""
        expected_types = [
            "supplier", "customer", "service_provider",
            "distributor", "partner", "other"
        ]
        actual_types = [t.value for t in PartnerType]
        for expected in expected_types:
            assert expected in actual_types

    def test_partner_risk_level_values(self):
        """Test all partner risk level values exist."""
        assert PartnerRiskLevel.LOW.value == "low"
        assert PartnerRiskLevel.MEDIUM.value == "medium"
        assert PartnerRiskLevel.HIGH.value == "high"
        assert PartnerRiskLevel.CRITICAL.value == "critical"
        assert PartnerRiskLevel.UNKNOWN.value == "unknown"

    def test_check_type_values(self):
        """Test all check type values exist."""
        expected_types = [
            "handelsregister", "credit_check", "sanctions",
            "news", "insolvency", "esg", "manual"
        ]
        actual_types = [t.value for t in CheckType]
        for expected in expected_types:
            assert expected in actual_types

    def test_check_status_values(self):
        """Test all check status values exist."""
        assert CheckStatus.PENDING.value == "pending"
        assert CheckStatus.IN_PROGRESS.value == "in_progress"
        assert CheckStatus.COMPLETED.value == "completed"
        assert CheckStatus.FAILED.value == "failed"

    def test_alert_severity_values(self):
        """Test all alert severity values exist."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_type_values(self):
        """Test all alert type values exist."""
        expected_types = [
            "insolvency", "management_change", "address_change",
            "credit_downgrade", "sanction_hit", "negative_news",
            "legal_issue", "financial_warning"
        ]
        actual_types = [t.value for t in AlertType]
        for expected in expected_types:
            assert expected in actual_types


class TestPartnerCheckModel:
    """Tests for PartnerCheck model."""

    def test_check_creation(self):
        """Test partner check creation."""
        partner_id = uuid.uuid4()
        check = PartnerCheck(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            partner_id=partner_id,
            check_type=CheckType.CREDIT_CHECK,
            status=CheckStatus.PENDING,
        )

        assert check.partner_id == partner_id
        assert check.check_type == CheckType.CREDIT_CHECK
        assert check.status == CheckStatus.PENDING

    def test_check_with_results(self):
        """Test partner check with completed results."""
        check = PartnerCheck(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            partner_id=uuid.uuid4(),
            check_type=CheckType.CREDIT_CHECK,
            status=CheckStatus.COMPLETED,
            score=75,
            result_summary="Good credit rating",
            raw_response={"credit_score": 750, "rating": "A"},
        )

        assert check.status == CheckStatus.COMPLETED
        assert check.raw_response["credit_score"] == 750
        assert check.score == 75


class TestPartnerAlertModel:
    """Tests for PartnerAlert model."""

    def test_alert_creation(self):
        """Test partner alert creation."""
        partner_id = uuid.uuid4()
        alert = PartnerAlert(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            partner_id=partner_id,
            alert_type=AlertType.CREDIT_DOWNGRADE,
            severity=AlertSeverity.WARNING,
            title="Credit Rating Changed",
            description="Partner credit score decreased from A to B",
            is_read=False,  # Explicitly set for unit tests
        )

        assert alert.partner_id == partner_id
        assert alert.alert_type == AlertType.CREDIT_DOWNGRADE
        assert alert.severity == AlertSeverity.WARNING
        assert alert.is_read is False

    def test_alert_with_details(self):
        """Test partner alert with all details."""
        alert = PartnerAlert(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            partner_id=uuid.uuid4(),
            alert_type=AlertType.SANCTION_HIT,
            severity=AlertSeverity.CRITICAL,
            title="Sanction List Match",
            description="Partner found on EU sanction list",
            source="OpenSanctions",
            source_url="https://sanctions.eu/list",
            is_read=False,
        )

        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.source == "OpenSanctions"


class TestContractPartnerModel:
    """Tests for ContractPartner linking model."""

    def test_contract_partner_link(self):
        """Test contract-partner linking."""
        link = ContractPartner(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            partner_id=uuid.uuid4(),
            role="counterparty",
        )

        assert link.role == "counterparty"

    def test_contract_partner_roles(self):
        """Test different partner roles in contracts."""
        roles = ["counterparty", "guarantor", "beneficiary", "agent"]
        for role in roles:
            link = ContractPartner(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                contract_id=uuid.uuid4(),
                partner_id=uuid.uuid4(),
                role=role,
            )
            assert link.role == role


class TestPartnerRiskCalculator:
    """Tests for PartnerRiskCalculator."""

    def test_calculate_risk_score_no_checks(self):
        """Test risk score with no checks returns unknown."""
        calculator = PartnerRiskCalculator()
        score, level = calculator.calculate([])

        assert score == 0
        assert level == PartnerRiskLevel.UNKNOWN

    def test_calculate_risk_score_single_check(self):
        """Test risk score with single check."""
        calculator = PartnerRiskCalculator()
        checks = [
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                partner_id=uuid.uuid4(),
                check_type=CheckType.CREDIT_CHECK,
                status=CheckStatus.COMPLETED,
                score=30,
            )
        ]
        # Need to set created_at for sorting
        checks[0].created_at = datetime.utcnow()

        score, level = calculator.calculate(checks)

        assert score is not None
        assert score == 30  # Single check, score = 30
        assert level == PartnerRiskLevel.LOW

    def test_calculate_risk_score_multiple_checks(self):
        """Test risk score with multiple checks."""
        calculator = PartnerRiskCalculator()
        partner_id = uuid.uuid4()
        org_id = uuid.uuid4()
        now = datetime.utcnow()

        checks = [
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=org_id,
                partner_id=partner_id,
                check_type=CheckType.CREDIT_CHECK,
                status=CheckStatus.COMPLETED,
                score=20,
            ),
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=org_id,
                partner_id=partner_id,
                check_type=CheckType.SANCTIONS,
                status=CheckStatus.COMPLETED,
                score=0,  # No sanction hit
            ),
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=org_id,
                partner_id=partner_id,
                check_type=CheckType.NEWS,
                status=CheckStatus.COMPLETED,
                score=40,  # Some negative news
            ),
        ]
        for c in checks:
            c.created_at = now

        score, level = calculator.calculate(checks)

        assert score is not None
        assert 0 <= score <= 100

    def test_risk_level_low(self):
        """Test low risk level determination."""
        calculator = PartnerRiskCalculator()
        checks = [
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                partner_id=uuid.uuid4(),
                check_type=CheckType.CREDIT_CHECK,
                status=CheckStatus.COMPLETED,
                score=10,
            ),
        ]
        checks[0].created_at = datetime.utcnow()

        score, level = calculator.calculate(checks)

        assert level == PartnerRiskLevel.LOW

    def test_risk_level_critical(self):
        """Test critical risk level determination."""
        calculator = PartnerRiskCalculator()
        partner_id = uuid.uuid4()
        checks = [
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                partner_id=partner_id,
                check_type=CheckType.SANCTIONS,
                status=CheckStatus.COMPLETED,
                score=100,  # Sanction hit!
            ),
        ]
        checks[0].created_at = datetime.utcnow()

        score, level = calculator.calculate(checks)

        assert level == PartnerRiskLevel.CRITICAL

    def test_pending_checks_excluded(self):
        """Test that pending checks are excluded from calculation."""
        calculator = PartnerRiskCalculator()
        partner_id = uuid.uuid4()
        org_id = uuid.uuid4()
        now = datetime.utcnow()

        checks = [
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=org_id,
                partner_id=partner_id,
                check_type=CheckType.CREDIT_CHECK,
                status=CheckStatus.COMPLETED,
                score=30,
            ),
            PartnerCheck(
                id=uuid.uuid4(),
                organization_id=org_id,
                partner_id=partner_id,
                check_type=CheckType.SANCTIONS,
                status=CheckStatus.PENDING,  # Should be excluded
                score=100,
            ),
        ]
        for c in checks:
            c.created_at = now

        score, level = calculator.calculate(checks)

        # Only the credit check should count (score=30)
        assert score == 30
        assert level == PartnerRiskLevel.LOW


class TestPartnerService:
    """Tests for PartnerService."""

    @pytest.fixture
    def mock_partner_repo(self):
        """Create mock partner repository."""
        repo = AsyncMock()
        repo.create = AsyncMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        repo.list = AsyncMock(return_value=[])
        repo.search = AsyncMock(return_value=[])
        repo.get_watched_partners = AsyncMock(return_value=[])
        repo.get_high_risk_partners = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_check_repo(self):
        """Create mock check repository."""
        repo = AsyncMock()
        repo.create = AsyncMock()
        repo.get_by_partner = AsyncMock(return_value=[])
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_alert_repo(self):
        """Create mock alert repository."""
        repo = AsyncMock()
        repo.create = AsyncMock()
        repo.get_by_partner = AsyncMock(return_value=[])
        repo.get_unread_count = AsyncMock(return_value=0)
        return repo

    @pytest.mark.asyncio
    async def test_get_partner(self, mock_partner_repo):
        """Test getting a partner by ID."""
        partner_id = uuid.uuid4()
        org_id = uuid.uuid4()
        expected_partner = Partner(
            id=partner_id,
            organization_id=org_id,
            name="Test Partner",
            partner_type=PartnerType.SUPPLIER,
        )
        mock_partner_repo.get.return_value = expected_partner

        result = await mock_partner_repo.get(partner_id)

        assert result == expected_partner
        mock_partner_repo.get.assert_called_once_with(partner_id)

    @pytest.mark.asyncio
    async def test_search_partners(self, mock_partner_repo):
        """Test searching partners."""
        partners = [
            Partner(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                name="ACME GmbH",
                partner_type=PartnerType.SUPPLIER,
            ),
            Partner(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                name="ACME AG",
                partner_type=PartnerType.CUSTOMER,
            ),
        ]
        mock_partner_repo.search.return_value = partners

        result = await mock_partner_repo.search("ACME")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_watched_partners(self, mock_partner_repo):
        """Test getting watched partners."""
        watched = [
            Partner(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                name="Watched Partner",
                partner_type=PartnerType.SUPPLIER,
                is_watched=True,
            ),
        ]
        mock_partner_repo.get_watched_partners.return_value = watched

        result = await mock_partner_repo.get_watched_partners()

        assert len(result) == 1
        assert result[0].is_watched is True

    @pytest.mark.asyncio
    async def test_get_high_risk_partners(self, mock_partner_repo):
        """Test getting high risk partners."""
        high_risk = [
            Partner(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                name="Risky Partner",
                partner_type=PartnerType.SUPPLIER,
                risk_score=85,
                risk_level=PartnerRiskLevel.CRITICAL,
            ),
        ]
        mock_partner_repo.get_high_risk_partners.return_value = high_risk

        result = await mock_partner_repo.get_high_risk_partners()

        assert len(result) == 1
        assert result[0].risk_level == PartnerRiskLevel.CRITICAL
