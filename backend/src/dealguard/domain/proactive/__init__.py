"""Proactive AI-Jurist domain.

This module provides proactive monitoring and alerting:
- DeadlineExtractionService: Extract contract deadlines using AI
- DeadlineMonitoringService: Monitor deadlines and generate alerts
- AlertService: Generate and manage proactive alerts
- RiskRadarService: Combined risk monitoring
- ComplianceService: Periodic compliance scanning
"""

from dealguard.domain.proactive.deadline_service import (
    DeadlineExtractionService,
    DeadlineMonitoringService,
    DeadlineStats,
)
from dealguard.domain.proactive.alert_service import AlertService, AlertFilter, AlertStats
from dealguard.domain.proactive.risk_radar_service import RiskRadarService, RiskRadarResult, RiskCategory

__all__ = [
    "DeadlineExtractionService",
    "DeadlineMonitoringService",
    "DeadlineStats",
    "AlertService",
    "AlertFilter",
    "AlertStats",
    "RiskRadarService",
    "RiskRadarResult",
    "RiskCategory",
]
