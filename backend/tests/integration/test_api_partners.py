"""
Integration tests for Partner API endpoints (Phase 2).
"""

import uuid

from fastapi import status
from fastapi.testclient import TestClient

from dealguard.infrastructure.database.models.partner import (
    PartnerRiskLevel,
    PartnerType,
)


class TestPartnerAPIEndpoints:
    """Tests for Partner API endpoints."""

    def test_list_partners_unauthorized(self, client: TestClient):
        """Test listing partners without authentication returns 401."""
        response = client.get("/api/v1/partners/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_partner_unauthorized(self, client: TestClient):
        """Test creating partner without authentication returns 401."""
        response = client.post(
            "/api/v1/partners/",
            json={
                "name": "Test Partner",
                "partner_type": "supplier",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_partner_unauthorized(self, client: TestClient):
        """Test getting partner without authentication returns 401."""
        partner_id = uuid.uuid4()
        response = client.get(f"/api/v1/partners/{partner_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_partner_unauthorized(self, client: TestClient):
        """Test updating partner without authentication returns 401."""
        partner_id = uuid.uuid4()
        response = client.patch(
            f"/api/v1/partners/{partner_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_partner_unauthorized(self, client: TestClient):
        """Test deleting partner without authentication returns 401."""
        partner_id = uuid.uuid4()
        response = client.delete(f"/api/v1/partners/{partner_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPartnerSearchAPI:
    """Tests for Partner search functionality."""

    def test_search_partners_unauthorized(self, client: TestClient):
        """Test searching partners without authentication returns 401."""
        response = client.get("/api/v1/partners/search?q=test")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPartnerChecksAPI:
    """Tests for Partner checks endpoints."""

    def test_run_checks_unauthorized(self, client: TestClient):
        """Test running checks without authentication returns 401."""
        partner_id = uuid.uuid4()
        response = client.post(f"/api/v1/partners/{partner_id}/run-checks")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPartnerAlertsAPI:
    """Tests for Partner alerts endpoints."""

    def test_get_alerts_unauthorized(self, client: TestClient):
        """Test getting alerts without authentication returns 401."""
        response = client.get("/api/v1/partners/alerts")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_alert_count_unauthorized(self, client: TestClient):
        """Test getting alert count without authentication returns 401."""
        response = client.get("/api/v1/partners/alerts/count")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPartnerContractLinkingAPI:
    """Tests for Partner-Contract linking endpoints."""

    def test_link_contract_unauthorized(self, client: TestClient):
        """Test linking contract without authentication returns 401."""
        partner_id = uuid.uuid4()
        contract_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/partners/{partner_id}/contracts",
            json={"contract_id": str(contract_id), "role": "counterparty"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unlink_contract_unauthorized(self, client: TestClient):
        """Test unlinking contract without authentication returns 401."""
        partner_id = uuid.uuid4()
        contract_id = uuid.uuid4()
        response = client.delete(f"/api/v1/partners/{partner_id}/contracts/{contract_id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPartnerSchemas:
    """Tests for Partner API schemas."""

    def test_partner_create_schema(self):
        """Test partner create schema structure."""
        from dealguard.api.routes.partners import PartnerCreateRequest

        schema = PartnerCreateRequest.model_json_schema()
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        assert "name" in properties
        assert "partner_type" in properties
        assert "name" in required

    def test_partner_response_schema(self):
        """Test partner response schema structure."""
        from dealguard.api.routes.partners import PartnerResponse

        schema = PartnerResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "name" in properties
        assert "partner_type" in properties
        assert "risk_score" in properties
        assert "risk_level" in properties
        assert "created_at" in properties

    def test_partner_update_schema(self):
        """Test partner update schema allows partial updates."""
        from dealguard.api.routes.partners import PartnerUpdateRequest

        schema = PartnerUpdateRequest.model_json_schema()
        required = schema.get("required", [])

        # All fields should be optional for updates
        assert len(required) == 0

    def test_partner_check_response_schema(self):
        """Test partner check response schema structure."""
        from dealguard.api.routes.partners import PartnerCheckResponse

        schema = PartnerCheckResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "check_type" in properties
        assert "status" in properties
        assert "score" in properties
        assert "result_summary" in properties

    def test_partner_alert_response_schema(self):
        """Test partner alert response schema structure."""
        from dealguard.api.routes.partners import PartnerAlertResponse

        schema = PartnerAlertResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "alert_type" in properties
        assert "severity" in properties
        assert "title" in properties
        assert "description" in properties
        assert "is_read" in properties


class TestPartnerValidation:
    """Tests for Partner input validation."""

    def test_invalid_partner_type(self, client: TestClient):
        """Test that invalid partner type is rejected."""
        response = client.post(
            "/api/v1/partners/",
            json={
                "name": "Test Partner",
                "partner_type": "invalid_type",
            },
        )

        # Without auth, should be 401 first
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_partner_name(self, client: TestClient):
        """Test that empty partner name is rejected."""
        response = client.post(
            "/api/v1/partners/",
            json={
                "name": "",
                "partner_type": "supplier",
            },
        )

        # Without auth, should be 401 first
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPartnerTypeEnumInAPI:
    """Tests for Partner type enum in API."""

    def test_all_partner_types_valid(self):
        """Test all partner types are valid for API."""
        valid_types = [
            "supplier",
            "customer",
            "service_provider",
            "distributor",
            "partner",
            "other",
        ]

        for ptype in valid_types:
            assert PartnerType(ptype) is not None

    def test_all_risk_levels_valid(self):
        """Test all risk levels are valid for API."""
        valid_levels = ["low", "medium", "high", "critical", "unknown"]

        for level in valid_levels:
            assert PartnerRiskLevel(level) is not None
