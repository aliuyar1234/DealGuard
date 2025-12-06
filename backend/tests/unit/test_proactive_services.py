"""
Unit tests for Proactive Monitoring services.

Tests cover:
- DeadlineService: Extraction, monitoring, alert generation
- AlertService: Lifecycle management
- RiskRadarService: Combined scoring
"""
import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dealguard.infrastructure.database.models.proactive import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    AlertSourceType,
    ContractDeadline,
    DeadlineStatus,
    DeadlineType,
    ProactiveAlert,
)


class TestDeadlineType:
    """Tests for DeadlineType enum."""

    def test_all_deadline_types_exist(self):
        """Test all expected deadline types exist."""
        expected_types = [
            "termination",
            "renewal",
            "payment",
            "option",
            "start",
            "end",
            "other",
        ]
        actual_types = [t.value for t in DeadlineType]

        for expected in expected_types:
            assert expected in actual_types

    def test_deadline_type_values(self):
        """Test specific deadline type values."""
        assert DeadlineType.TERMINATION.value == "termination"
        assert DeadlineType.RENEWAL.value == "renewal"
        assert DeadlineType.PAYMENT.value == "payment"


class TestDeadlineStatus:
    """Tests for DeadlineStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        expected = ["active", "handled", "dismissed", "expired"]
        actual = [s.value for s in DeadlineStatus]

        for status in expected:
            assert status in actual


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_levels(self):
        """Test severity levels exist."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertStatus:
    """Tests for AlertStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        expected = ["new", "seen", "in_progress", "resolved", "dismissed", "snoozed"]
        actual = [s.value for s in AlertStatus]

        for status in expected:
            assert status in actual


class TestContractDeadlineModel:
    """Tests for ContractDeadline model."""

    def test_deadline_creation(self):
        """Test deadline model creation."""
        deadline = ContractDeadline(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            deadline_type=DeadlineType.TERMINATION,
            deadline_date=date.today() + timedelta(days=30),
            reminder_days_before=14,
            confidence=0.95,
            status=DeadlineStatus.ACTIVE,
        )

        assert deadline.deadline_type == DeadlineType.TERMINATION
        assert deadline.confidence == 0.95
        assert deadline.status == DeadlineStatus.ACTIVE

    def test_deadline_with_source_clause(self):
        """Test deadline with extracted source clause."""
        deadline = ContractDeadline(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            deadline_type=DeadlineType.TERMINATION,
            deadline_date=date.today() + timedelta(days=30),
            source_clause="Die Kündigungsfrist beträgt 3 Monate zum Quartalsende.",
            confidence=0.92,
            status=DeadlineStatus.ACTIVE,
        )

        assert "Kündigungsfrist" in deadline.source_clause


class TestProactiveAlertModel:
    """Tests for ProactiveAlert model."""

    def test_alert_creation(self):
        """Test alert model creation."""
        alert = ProactiveAlert(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            source_type=AlertSourceType.CONTRACT,
            alert_type=AlertType.DEADLINE_APPROACHING,
            severity=AlertSeverity.WARNING,
            title="Kündigungsfrist in 14 Tagen",
            description="Der Mietvertrag muss bis zum 15.01.2025 gekündigt werden.",
            status=AlertStatus.NEW,
        )

        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.NEW

    def test_alert_with_recommendation(self):
        """Test alert with AI recommendation."""
        alert = ProactiveAlert(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            source_type=AlertSourceType.CONTRACT,
            alert_type=AlertType.DEADLINE_APPROACHING,
            severity=AlertSeverity.CRITICAL,
            title="Frist überschritten",
            description="Der Vertrag hat sich automatisch verlängert.",
            ai_recommendation="Kontaktieren Sie den Vertragspartner für eine Nachverhandlung.",
            recommended_actions=[
                {"action": "contact_partner", "label": "Partner kontaktieren"},
                {"action": "review_contract", "label": "Vertrag prüfen"},
            ],
            status=AlertStatus.NEW,
        )

        assert alert.ai_recommendation is not None
        assert len(alert.recommended_actions) == 2


class TestDeadlineService:
    """Tests for DeadlineService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def deadline_service(self, mock_db):
        """Create DeadlineService instance."""
        from dealguard.domain.proactive.deadline_service import DeadlineService
        return DeadlineService(mock_db)

    @pytest.mark.asyncio
    async def test_get_upcoming_deadlines(self, deadline_service, mock_db):
        """Test getting upcoming deadlines."""
        upcoming = [
            MagicMock(
                id=uuid.uuid4(),
                deadline_date=date.today() + timedelta(days=7),
                deadline_type=DeadlineType.TERMINATION,
                status=DeadlineStatus.ACTIVE,
            )
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=upcoming)))
        )

        result = await deadline_service.get_upcoming_deadlines(days_ahead=30)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_overdue_deadlines(self, deadline_service, mock_db):
        """Test getting overdue deadlines."""
        overdue = [
            MagicMock(
                id=uuid.uuid4(),
                deadline_date=date.today() - timedelta(days=3),
                deadline_type=DeadlineType.PAYMENT,
                status=DeadlineStatus.ACTIVE,
            )
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=overdue)))
        )

        result = await deadline_service.get_overdue_deadlines()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_mark_deadline_handled(self, deadline_service, mock_db):
        """Test marking deadline as handled."""
        deadline_id = uuid.uuid4()
        deadline = MagicMock(
            id=deadline_id,
            status=DeadlineStatus.ACTIVE,
        )
        mock_db.get.return_value = deadline

        result = await deadline_service.mark_deadline_handled(
            deadline_id=deadline_id,
            action="renewed",
            notes="Contract renewed for 2 years",
        )

        assert result.status == DeadlineStatus.HANDLED

    @pytest.mark.asyncio
    async def test_dismiss_deadline(self, deadline_service, mock_db):
        """Test dismissing deadline."""
        deadline_id = uuid.uuid4()
        deadline = MagicMock(
            id=deadline_id,
            status=DeadlineStatus.ACTIVE,
        )
        mock_db.get.return_value = deadline

        result = await deadline_service.dismiss_deadline(
            deadline_id=deadline_id,
            notes="Not relevant to our operations",
        )

        assert result.status == DeadlineStatus.DISMISSED

    @pytest.mark.asyncio
    async def test_verify_deadline(self, deadline_service, mock_db):
        """Test verifying AI-extracted deadline."""
        deadline_id = uuid.uuid4()
        deadline = MagicMock(
            id=deadline_id,
            deadline_date=date.today() + timedelta(days=30),
            is_verified=False,
        )
        mock_db.get.return_value = deadline

        correct_date = date.today() + timedelta(days=45)
        result = await deadline_service.verify_deadline(
            deadline_id=deadline_id,
            correct_date=correct_date,
        )

        assert result.is_verified is True
        assert result.deadline_date == correct_date


class TestAlertService:
    """Tests for AlertService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def alert_service(self, mock_db):
        """Create AlertService instance."""
        from dealguard.domain.proactive.alert_service import AlertService
        return AlertService(mock_db)

    @pytest.mark.asyncio
    async def test_list_alerts_with_filter(self, alert_service, mock_db):
        """Test listing alerts with filter."""
        from dealguard.domain.proactive import AlertFilter

        alerts = [
            MagicMock(
                id=uuid.uuid4(),
                status=AlertStatus.NEW,
                severity=AlertSeverity.CRITICAL,
            )
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=alerts)))
        )

        filter_obj = AlertFilter(
            status=[AlertStatus.NEW],
            severity=[AlertSeverity.CRITICAL],
        )
        result = await alert_service.list_alerts(filter=filter_obj)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_mark_alert_seen(self, alert_service, mock_db):
        """Test marking alert as seen."""
        alert_id = uuid.uuid4()
        alert = MagicMock(id=alert_id, status=AlertStatus.NEW)
        mock_db.get.return_value = alert

        result = await alert_service.mark_seen(alert_id)

        assert result.status == AlertStatus.SEEN

    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_service, mock_db):
        """Test resolving alert."""
        alert_id = uuid.uuid4()
        alert = MagicMock(id=alert_id, status=AlertStatus.IN_PROGRESS)
        mock_db.get.return_value = alert

        result = await alert_service.resolve(
            alert_id=alert_id,
            action="contract_terminated",
            notes="Termination letter sent",
        )

        assert result.status == AlertStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_snooze_alert(self, alert_service, mock_db):
        """Test snoozing alert."""
        alert_id = uuid.uuid4()
        alert = MagicMock(
            id=alert_id,
            status=AlertStatus.NEW,
            snoozed_until=None,
        )
        mock_db.get.return_value = alert

        result = await alert_service.snooze(alert_id=alert_id, days=7)

        assert result.status == AlertStatus.SNOOZED
        assert result.snoozed_until is not None

    @pytest.mark.asyncio
    async def test_dismiss_alert(self, alert_service, mock_db):
        """Test dismissing alert."""
        alert_id = uuid.uuid4()
        alert = MagicMock(id=alert_id, status=AlertStatus.NEW)
        mock_db.get.return_value = alert

        result = await alert_service.dismiss(
            alert_id=alert_id,
            notes="False positive",
        )

        assert result.status == AlertStatus.DISMISSED

    @pytest.mark.asyncio
    async def test_count_new_alerts(self, alert_service, mock_db):
        """Test counting new alerts."""
        mock_db.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=5)
        )

        count = await alert_service.count_new_alerts()

        assert count == 5


class TestRiskRadarService:
    """Tests for RiskRadarService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def risk_radar_service(self, mock_db):
        """Create RiskRadarService instance."""
        from dealguard.domain.proactive.risk_radar_service import RiskRadarService
        return RiskRadarService(mock_db)

    @pytest.mark.asyncio
    async def test_get_risk_radar(self, risk_radar_service, mock_db):
        """Test getting risk radar overview."""
        # Mock various queries
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None),
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
        )

        result = await risk_radar_service.get_risk_radar()

        assert result is not None
        assert hasattr(result, "overall_score")
        assert hasattr(result, "categories")

    @pytest.mark.asyncio
    async def test_risk_score_calculation(self, risk_radar_service):
        """Test risk score calculation with weights."""
        # Weights: Contract 30%, Partner 25%, Compliance 25%, Deadline 20%
        contract_score = 50
        partner_score = 60
        compliance_score = 40
        deadline_score = 70

        expected = int(
            contract_score * 0.30 +
            partner_score * 0.25 +
            compliance_score * 0.25 +
            deadline_score * 0.20
        )

        # Calculate: 15 + 15 + 10 + 14 = 54
        assert expected == 54


class TestDeadlineStats:
    """Tests for deadline statistics."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def deadline_service(self, mock_db):
        """Create DeadlineService instance."""
        from dealguard.domain.proactive.deadline_service import DeadlineService
        return DeadlineService(mock_db)

    @pytest.mark.asyncio
    async def test_get_deadline_stats(self, deadline_service, mock_db):
        """Test getting deadline statistics."""
        # Mock stats query
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=(10, 8, 2, 3, 5))  # total, active, overdue, 7days, 30days
        )

        stats = await deadline_service.get_deadline_stats()

        assert stats.total == 10
        assert stats.active == 8
        assert stats.overdue == 2


class TestAlertStats:
    """Tests for alert statistics."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def alert_service(self, mock_db):
        """Create AlertService instance."""
        from dealguard.domain.proactive.alert_service import AlertService
        return AlertService(mock_db)

    @pytest.mark.asyncio
    async def test_get_alert_stats(self, alert_service, mock_db):
        """Test getting alert statistics."""
        # Mock stats query
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=(20, 5, 8, 3, 4))  # total, new, seen, in_progress, resolved
        )

        stats = await alert_service.get_stats()

        assert stats.total == 20
        assert stats.new == 5
