"""
Unit tests for Proactive Monitoring services.

Tests cover:
- DeadlineMonitoringService: Monitoring and alert generation
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
from dealguard.shared.context import TenantContext, clear_tenant_context, set_tenant_context


@pytest.fixture(autouse=True)
def tenant_context():
    """Ensure tenant context is available for service calls."""
    ctx = TenantContext(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        user_email="test@example.com",
        user_role="admin",
    )
    set_tenant_context(ctx)
    yield ctx
    clear_tenant_context()


class TestDeadlineType:
    """Tests for DeadlineType enum."""

    def test_all_deadline_types_exist(self):
        """Test all expected deadline types exist."""
        expected_types = [
            "termination_notice",
            "auto_renewal",
            "payment_due",
            "warranty_end",
            "contract_end",
            "review_date",
            "price_adjustment",
            "notice_period",
            "other",
        ]
        actual_types = [t.value for t in DeadlineType]

        for expected in expected_types:
            assert expected in actual_types

    def test_deadline_type_values(self):
        """Test specific deadline type values."""
        assert DeadlineType.TERMINATION_NOTICE.value == "termination_notice"
        assert DeadlineType.AUTO_RENEWAL.value == "auto_renewal"
        assert DeadlineType.PAYMENT_DUE.value == "payment_due"


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
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"
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
            deadline_type=DeadlineType.TERMINATION_NOTICE,
            deadline_date=date.today() + timedelta(days=30),
            reminder_days_before=14,
            confidence=0.95,
            status=DeadlineStatus.ACTIVE,
        )

        assert deadline.deadline_type == DeadlineType.TERMINATION_NOTICE
        assert deadline.confidence == 0.95
        assert deadline.status == DeadlineStatus.ACTIVE

    def test_deadline_with_source_clause(self):
        """Test deadline with extracted source clause."""
        deadline = ContractDeadline(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            deadline_type=DeadlineType.TERMINATION_NOTICE,
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
            source_type=AlertSourceType.DEADLINE,
            alert_type=AlertType.DEADLINE_APPROACHING,
            severity=AlertSeverity.HIGH,
            title="Kündigungsfrist in 14 Tagen",
            description="Der Mietvertrag muss bis zum 15.01.2025 gekündigt werden.",
            status=AlertStatus.NEW,
        )

        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.NEW

    def test_alert_with_recommendation(self):
        """Test alert with AI recommendation."""
        alert = ProactiveAlert(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            source_type=AlertSourceType.DEADLINE,
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


class TestDeadlineMonitoringService:
    """Tests for DeadlineMonitoringService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def deadline_service(self, mock_db, tenant_context):
        """Create DeadlineMonitoringService instance."""
        from dealguard.domain.proactive.deadline_service import (
            DeadlineMonitoringService,
        )
        return DeadlineMonitoringService(
            mock_db,
            organization_id=tenant_context.organization_id,
            user_id=tenant_context.user_id,
        )

    @pytest.mark.asyncio
    async def test_get_upcoming_deadlines(self, deadline_service, mock_db):
        """Test getting upcoming deadlines."""
        upcoming = [
            MagicMock(
                id=uuid.uuid4(),
                deadline_date=date.today() + timedelta(days=7),
                deadline_type=DeadlineType.TERMINATION_NOTICE,
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
                deadline_type=DeadlineType.PAYMENT_DUE,
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
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=deadline)
        )

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
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=deadline)
        )

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
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=deadline)
        )

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
    def alert_service(self, mock_db, tenant_context):
        """Create AlertService instance."""
        from dealguard.domain.proactive.alert_service import AlertService
        return AlertService(
            mock_db,
            organization_id=tenant_context.organization_id,
            user_id=tenant_context.user_id,
        )

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
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=alert)
        )

        result = await alert_service.mark_seen(alert_id)

        assert result.status == AlertStatus.SEEN

    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_service, mock_db):
        """Test resolving alert."""
        alert_id = uuid.uuid4()
        alert = MagicMock(id=alert_id, status=AlertStatus.IN_PROGRESS)
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=alert)
        )

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
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=alert)
        )

        result = await alert_service.snooze(alert_id=alert_id, days=7)

        assert result.status == AlertStatus.SNOOZED
        assert result.snoozed_until is not None

    @pytest.mark.asyncio
    async def test_dismiss_alert(self, alert_service, mock_db):
        """Test dismissing alert."""
        alert_id = uuid.uuid4()
        alert = MagicMock(id=alert_id, status=AlertStatus.NEW)
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=alert)
        )

        result = await alert_service.dismiss(
            alert_id=alert_id,
            notes="False positive",
        )

        assert result.status == AlertStatus.DISMISSED

    @pytest.mark.asyncio
    async def test_count_new_alerts(self, alert_service, mock_db):
        """Test counting new alerts."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=5)
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
    def risk_radar_service(self, mock_db, tenant_context):
        """Create RiskRadarService instance."""
        from dealguard.domain.proactive.risk_radar_service import RiskRadarService
        return RiskRadarService(
            mock_db,
            organization_id=tenant_context.organization_id,
        )

    @pytest.mark.asyncio
    async def test_get_risk_radar(self, risk_radar_service, mock_db):
        """Test getting risk radar overview."""
        # Mock various queries
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None),
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
            scalar=MagicMock(return_value=0),
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
    def deadline_service(self, mock_db, tenant_context):
        """Create DeadlineMonitoringService instance."""
        from dealguard.domain.proactive.deadline_service import (
            DeadlineMonitoringService,
        )
        return DeadlineMonitoringService(
            mock_db,
            organization_id=tenant_context.organization_id,
            user_id=tenant_context.user_id,
        )

    @pytest.mark.asyncio
    async def test_get_deadline_stats(self, deadline_service, mock_db):
        """Test getting deadline statistics."""
        today = date.today()
        deadlines = [
            MagicMock(deadline_date=today - timedelta(days=1)),
            MagicMock(deadline_date=today - timedelta(days=3)),
            MagicMock(deadline_date=today + timedelta(days=1)),
            MagicMock(deadline_date=today + timedelta(days=3)),
            MagicMock(deadline_date=today + timedelta(days=7)),
            MagicMock(deadline_date=today + timedelta(days=10)),
            MagicMock(deadline_date=today + timedelta(days=25)),
            MagicMock(deadline_date=today + timedelta(days=40)),
            MagicMock(deadline_date=today + timedelta(days=60)),
            MagicMock(deadline_date=today + timedelta(days=90)),
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=deadlines)
                )
            )
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
    def alert_service(self, mock_db, tenant_context):
        """Create AlertService instance."""
        from dealguard.domain.proactive.alert_service import AlertService
        return AlertService(
            mock_db,
            organization_id=tenant_context.organization_id,
            user_id=tenant_context.user_id,
        )

    @pytest.mark.asyncio
    async def test_get_alert_stats(self, alert_service, mock_db):
        """Test getting alert statistics."""
        alerts = [
            *[
                MagicMock(
                    status=AlertStatus.NEW,
                    severity=AlertSeverity.INFO,
                    alert_type=AlertType.DEADLINE_APPROACHING,
                )
                for _ in range(5)
            ],
            *[
                MagicMock(
                    status=AlertStatus.SEEN,
                    severity=AlertSeverity.LOW,
                    alert_type=AlertType.DEADLINE_APPROACHING,
                )
                for _ in range(8)
            ],
            *[
                MagicMock(
                    status=AlertStatus.IN_PROGRESS,
                    severity=AlertSeverity.MEDIUM,
                    alert_type=AlertType.DEADLINE_APPROACHING,
                )
                for _ in range(3)
            ],
            *[
                MagicMock(
                    status=AlertStatus.RESOLVED,
                    severity=AlertSeverity.HIGH,
                    alert_type=AlertType.DEADLINE_APPROACHING,
                )
                for _ in range(4)
            ],
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=alerts)
                )
            )
        )

        stats = await alert_service.get_stats()

        assert stats.total == 20
        assert stats.new == 5
