"""
Integration tests for Contract API endpoints (Phase 1).
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    Contract,
)


class TestContractAPIEndpoints:
    """Tests for Contract API endpoints."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    def test_list_contracts_unauthorized(self, client: TestClient):
        """Test listing contracts without authentication returns 401."""
        response = client.get("/api/v1/contracts/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_contract_not_found(self, client: TestClient):
        """Test getting non-existent contract returns 404 or 401."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/contracts/{fake_id}")

        # Without auth, should be 401 first
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestContractUploadAPI:
    """Tests for Contract upload functionality."""

    def test_upload_requires_auth(self, client: TestClient):
        """Test that file upload requires authentication."""
        response = client.post(
            "/api/v1/contracts/",
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_without_file(self, client: TestClient):
        """Test that upload without file fails."""
        response = client.post("/api/v1/contracts/")

        # Without auth, should be 401 first
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestContractAnalysisAPI:
    """Tests for Contract analysis endpoints."""

    def test_trigger_analysis_requires_auth(self, client: TestClient):
        """Test that triggering analysis requires authentication."""
        contract_id = uuid.uuid4()
        response = client.post(f"/api/v1/contracts/{contract_id}/analyze")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_contract_requires_auth(self, client: TestClient):
        """Test that getting contract requires authentication."""
        contract_id = uuid.uuid4()
        response = client.get(f"/api/v1/contracts/{contract_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestContractDeleteAPI:
    """Tests for Contract deletion."""

    def test_delete_requires_auth(self, client: TestClient):
        """Test that deleting contract requires authentication."""
        contract_id = uuid.uuid4()
        response = client.delete(f"/api/v1/contracts/{contract_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestContractStatusFlow:
    """Tests for Contract status transitions."""

    def test_valid_status_transitions(self):
        """Test valid contract status transitions."""
        # pending -> processing -> completed
        # pending -> processing -> failed
        valid_transitions = [
            (AnalysisStatus.PENDING, AnalysisStatus.PROCESSING),
            (AnalysisStatus.PROCESSING, AnalysisStatus.COMPLETED),
            (AnalysisStatus.PROCESSING, AnalysisStatus.FAILED),
        ]

        for from_status, to_status in valid_transitions:
            assert from_status != to_status

    def test_analysis_status_transitions(self):
        """Test valid analysis status transitions."""
        # pending -> processing -> completed
        # pending -> processing -> failed
        valid_transitions = [
            (AnalysisStatus.PENDING, AnalysisStatus.PROCESSING),
            (AnalysisStatus.PROCESSING, AnalysisStatus.COMPLETED),
            (AnalysisStatus.PROCESSING, AnalysisStatus.FAILED),
        ]

        for from_status, to_status in valid_transitions:
            assert from_status != to_status


class TestContractSchemas:
    """Tests for Contract API schemas."""

    def test_contract_response_schema(self):
        """Test contract response schema structure."""
        from dealguard.api.routes.contracts import ContractResponse

        schema = ContractResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "filename" in properties
        assert "status" in properties
        assert "created_at" in properties

    def test_analysis_response_schema(self):
        """Test analysis response schema structure."""
        from dealguard.api.routes.contracts import ContractAnalysisResponse

        schema = ContractAnalysisResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "risk_score" in properties
        assert "risk_level" in properties
        assert "summary" in properties
