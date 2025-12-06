"""Proactive AI-Jurist domain.

This module provides proactive monitoring and alerting:
- DeadlineService: Extract and monitor contract deadlines
- AlertService: Generate and manage proactive alerts
- RiskRadarService: Combined risk monitoring
- ComplianceService: Periodic compliance scanning
"""

from dealguard.domain.proactive.deadline_service import DeadlineService, DeadlineStats
from dealguard.domain.proactive.alert_service import AlertService, AlertFilter, AlertStats
from dealguard.domain.proactive.risk_radar_service import RiskRadarService, RiskRadarResult, RiskCategory

__all__ = [
    "DeadlineService",
    "DeadlineStats",
    "AlertService",
    "AlertFilter",
    "AlertStats",
    "RiskRadarService",
    "RiskRadarResult",
    "RiskCategory",
]
