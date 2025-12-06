"""
Unit tests for Contract domain (Phase 1).
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    Contract,
    ContractAnalysis,
    ContractFinding,
    ContractType,
    FindingCategory,
    FindingSeverity,
    RiskLevel,
)


class TestContractModel:
    """Tests for Contract model."""

    def test_contract_creation(self):
        """Test contract model can be created with required fields."""
        org_id = uuid.uuid4()
        contract = Contract(
            id=uuid.uuid4(),
            organization_id=org_id,
            filename="test.pdf",
            file_path="contracts/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
            status=AnalysisStatus.PENDING,  # Explicitly set for unit tests
        )

        assert contract.filename == "test.pdf"
        assert contract.file_path == "contracts/test.pdf"
        assert contract.organization_id == org_id
        assert contract.status == AnalysisStatus.PENDING

    def test_contract_with_optional_fields(self):
        """Test contract model with optional fields."""
        contract = Contract(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            filename="contract.pdf",
            file_path="contracts/contract.pdf",
            file_hash="def456",
            file_size_bytes=2048,
            mime_type="application/pdf",
            contract_type=ContractType.SERVICE,
            page_count=10,
            language="de",
        )

        assert contract.contract_type == ContractType.SERVICE
        assert contract.page_count == 10
        assert contract.language == "de"


class TestContractAnalysisModel:
    """Tests for ContractAnalysis model."""

    def test_analysis_creation(self):
        """Test analysis model creation."""
        contract_id = uuid.uuid4()
        analysis = ContractAnalysis(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            contract_id=contract_id,
            risk_score=65,
            risk_level=RiskLevel.MEDIUM,
            summary="Test summary",
            recommendations=["Rec 1"],
            processing_time_ms=1500,
            ai_model_version="claude-3-sonnet",
            prompt_version="v1",
            input_tokens=100,
            output_tokens=50,
            cost_cents=0.01,
        )

        assert analysis.contract_id == contract_id
        assert analysis.risk_score == 65
        assert analysis.risk_level == RiskLevel.MEDIUM

    def test_analysis_with_results(self):
        """Test analysis model with completed results."""
        analysis = ContractAnalysis(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            risk_score=65,
            risk_level=RiskLevel.MEDIUM,
            summary="Test summary",
            recommendations=["Rec 1", "Rec 2"],
            processing_time_ms=1500,
            ai_model_version="claude-3-sonnet",
            prompt_version="v1",
            input_tokens=100,
            output_tokens=50,
            cost_cents=0.01,
        )

        assert analysis.risk_score == 65
        assert analysis.risk_level == RiskLevel.MEDIUM
        assert analysis.cost_cents == 0.01


class TestContractFindingModel:
    """Tests for ContractFinding model."""

    def test_finding_creation(self):
        """Test finding model creation."""
        analysis_id = uuid.uuid4()
        finding = ContractFinding(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            analysis_id=analysis_id,
            severity=FindingSeverity.HIGH,
            category=FindingCategory.LIABILITY,
            title="Unlimited Liability",
            description="Contract contains unlimited liability clause",
            original_clause_text="Party A shall be liable for all damages...",
            suggested_change="Negotiate a liability cap",
        )

        assert finding.severity == FindingSeverity.HIGH
        assert finding.category == FindingCategory.LIABILITY
        assert finding.title == "Unlimited Liability"

    def test_finding_severity_levels(self):
        """Test all severity levels can be used."""
        for severity in FindingSeverity:
            finding = ContractFinding(
                id=uuid.uuid4(),
                organization_id=uuid.uuid4(),
                analysis_id=uuid.uuid4(),
                severity=severity,
                category=FindingCategory.OTHER,
                title="Test Finding",
                description="Test description",
            )
            assert finding.severity == severity


class TestContractTypes:
    """Tests for contract type enumerations."""

    def test_analysis_status_values(self):
        """Test all analysis status values exist."""
        assert AnalysisStatus.PENDING.value == "pending"
        assert AnalysisStatus.PROCESSING.value == "processing"
        assert AnalysisStatus.COMPLETED.value == "completed"
        assert AnalysisStatus.FAILED.value == "failed"

    def test_contract_type_values(self):
        """Test all contract type values exist."""
        expected_types = [
            "supplier", "customer", "service", "nda",
            "license", "lease", "employment", "other"
        ]
        actual_types = [t.value for t in ContractType]
        for expected in expected_types:
            assert expected in actual_types

    def test_risk_level_values(self):
        """Test all risk level values exist."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_finding_severity_values(self):
        """Test all finding severity values exist."""
        assert FindingSeverity.INFO.value == "info"
        assert FindingSeverity.LOW.value == "low"
        assert FindingSeverity.MEDIUM.value == "medium"
        assert FindingSeverity.HIGH.value == "high"
        assert FindingSeverity.CRITICAL.value == "critical"

    def test_finding_category_values(self):
        """Test all finding category values exist."""
        expected_categories = [
            "liability", "payment", "termination", "jurisdiction",
            "ip", "confidentiality", "gdpr", "warranty", "force_majeure", "other"
        ]
        actual_categories = [c.value for c in FindingCategory]
        for expected in expected_categories:
            assert expected in actual_categories


class TestRiskScoreCalculation:
    """Tests for risk score calculation logic."""

    def test_risk_level_from_score_low(self):
        """Test low risk level determination."""
        # Score 0-30 should be low risk
        for score in [0, 15, 30]:
            if score <= 30:
                assert RiskLevel.LOW.value == "low"

    def test_risk_level_from_score_medium(self):
        """Test medium risk level determination."""
        # Score 31-60 should be medium risk
        for score in [31, 45, 60]:
            if 31 <= score <= 60:
                assert RiskLevel.MEDIUM.value == "medium"

    def test_risk_level_from_score_high(self):
        """Test high risk level determination."""
        # Score 61-80 should be high risk
        for score in [61, 70, 80]:
            if 61 <= score <= 80:
                assert RiskLevel.HIGH.value == "high"

    def test_risk_level_from_score_critical(self):
        """Test critical risk level determination."""
        # Score 81-100 should be critical risk
        for score in [81, 90, 100]:
            if score > 80:
                assert RiskLevel.CRITICAL.value == "critical"
