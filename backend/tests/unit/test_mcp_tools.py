"""
Unit tests for MCP (Model Context Protocol) tools.

Tests cover all 13 tools that Claude uses to access Austrian legal data
and DealGuard's internal database.
"""

import json
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from dealguard.mcp import models


class TestSearchRISInput:
    """Tests for SearchRISInput model validation."""

    def test_valid_input(self):
        """Test valid input with defaults."""
        input_model = models.SearchRISInput(query="Kündigungsfrist")
        assert input_model.query == "Kündigungsfrist"
        assert input_model.law_type == "Bundesrecht"
        assert input_model.limit == 5

    def test_all_law_types(self):
        """Test all valid law types."""
        valid_types = ["Bundesrecht", "Landesrecht", "Justiz", "Vfgh", "Vwgh"]
        for law_type in valid_types:
            input_model = models.SearchRISInput(query="test", law_type=law_type)
            assert input_model.law_type == law_type

    def test_limit_constraints(self):
        """Test limit min/max constraints."""
        # Min limit
        input_model = models.SearchRISInput(query="test", limit=1)
        assert input_model.limit == 1

        # Max limit
        input_model = models.SearchRISInput(query="test", limit=20)
        assert input_model.limit == 20

    def test_empty_query_raises(self):
        """Test that empty query raises validation error."""
        with pytest.raises(ValueError):
            models.SearchRISInput(query="")


class TestGetLawTextInput:
    """Tests for GetLawTextInput model validation."""

    def test_valid_input(self):
        """Test valid document number."""
        input_model = models.GetLawTextInput(document_number="NOR40000001")
        assert input_model.document_number == "NOR40000001"
        assert input_model.response_format == models.ResponseFormat.MARKDOWN

    def test_with_response_format(self):
        """Test with response format override."""
        input_model = models.GetLawTextInput(
            document_number="NOR40000001",
            response_format="json",
        )
        assert input_model.response_format == models.ResponseFormat.JSON


class TestSearchEdiktsdateiInput:
    """Tests for SearchEdiktsdateiInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.SearchEdiktsdateiInput(name="ACME GmbH")
        assert input_model.name == "ACME GmbH"
        assert input_model.bundesland is None

    def test_bundesland_filter(self):
        """Test bundesland filter parsing."""
        input_model = models.SearchEdiktsdateiInput(
            name="test",
            bundesland="W",
        )
        assert input_model.bundesland == models.Bundesland.WIEN


class TestSearchFirmenbuchInput:
    """Tests for SearchFirmenbuchInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.SearchFirmenbuchInput(query="ACME")
        assert input_model.query == "ACME"
        assert input_model.limit == 5

    def test_custom_limit(self):
        """Test custom limit."""
        input_model = models.SearchFirmenbuchInput(query="test", limit=5)
        assert input_model.limit == 5


class TestGetFirmenbuchAuszugInput:
    """Tests for GetFirmenbuchAuszugInput model validation."""

    def test_valid_company_number(self):
        """Test valid company number."""
        input_model = models.GetFirmenbuchAuszugInput(firmenbuchnummer="FN123456a")
        assert input_model.firmenbuchnummer == "123456a"


class TestCheckCompanyAustriaInput:
    """Tests for CheckCompanyAustriaInput model validation."""

    def test_valid_input(self):
        """Test valid company name."""
        input_model = models.CheckCompanyAustriaInput(company_name="ACME GmbH")
        assert input_model.company_name == "ACME GmbH"


class TestCheckSanctionsInput:
    """Tests for CheckSanctionsInput model validation."""

    def test_valid_input(self):
        """Test valid input with name only."""
        input_model = models.CheckSanctionsInput(name="John Doe")
        assert input_model.name == "John Doe"
        assert input_model.country == "AT"

    def test_with_country(self):
        """Test input with country."""
        input_model = models.CheckSanctionsInput(name="John Doe", country="AT")
        assert input_model.country == "AT"


class TestCheckPEPInput:
    """Tests for CheckPEPInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.CheckPEPInput(person_name="Max Mustermann")
        assert input_model.person_name == "Max Mustermann"

    def test_with_country(self):
        """Test input with country override."""
        input_model = models.CheckPEPInput(person_name="Max Mustermann", country="DE")
        assert input_model.country == "DE"


class TestComprehensiveComplianceInput:
    """Tests for ComprehensiveComplianceInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.ComprehensiveComplianceInput(name="Company XYZ")
        assert input_model.name == "Company XYZ"
        assert input_model.entity_type == models.EntityType.COMPANY

    def test_with_all_fields(self):
        """Test with all optional fields."""
        input_model = models.ComprehensiveComplianceInput(
            name="Max Mustermann",
            country="DE",
            entity_type="person",
        )
        assert input_model.country == "DE"
        assert input_model.entity_type == models.EntityType.PERSON


class TestSearchContractsInput:
    """Tests for SearchContractsInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.SearchContractsInput(query="Mietvertrag")
        assert input_model.query == "Mietvertrag"
        assert input_model.limit == 10

    def test_missing_query_raises(self):
        """Test missing query raises validation error."""
        with pytest.raises(ValidationError):
            models.SearchContractsInput()


class TestGetContractInput:
    """Tests for GetContractInput model validation."""

    def test_valid_input(self):
        """Test valid contract ID."""
        contract_id = str(uuid.uuid4())
        input_model = models.GetContractInput(contract_id=contract_id)
        assert input_model.contract_id == contract_id


class TestGetPartnersInput:
    """Tests for GetPartnersInput model validation."""

    def test_valid_input(self):
        """Test valid input with defaults."""
        input_model = models.GetPartnersInput()
        assert input_model.risk_level is None
        assert input_model.limit == 20

    def test_with_risk_level(self):
        """Test with risk level filter."""
        input_model = models.GetPartnersInput(risk_level="high")
        assert input_model.risk_level == "high"


class TestGetDeadlinesInput:
    """Tests for GetDeadlinesInput model validation."""

    def test_valid_input(self):
        """Test valid input with defaults."""
        input_model = models.GetDeadlinesInput()
        assert input_model.days_ahead == 30
        assert input_model.include_overdue is True

    def test_custom_days(self):
        """Test custom days ahead."""
        input_model = models.GetDeadlinesInput(days_ahead=7)
        assert input_model.days_ahead == 7


class TestToolExecutor:
    """Tests for ToolExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create ToolExecutor instance."""
        from dealguard.domain.chat.tool_executor import ToolExecutor

        org_id = uuid.uuid4()
        return ToolExecutor(org_id)

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, executor):
        """Test that unknown tool returns helpful error."""
        result = await executor.execute("unknown_tool", {})
        assert "Unbekanntes Tool" in result.result
        assert "dealguard_search_ris" in result.result

    @pytest.mark.asyncio
    async def test_validation_error_returns_helpful_message(self, executor):
        """Test that validation errors return helpful message."""
        # Missing required field
        result = await executor.execute("dealguard_search_ris", {})
        assert result.error is not None
        assert "Eingabefehler" in result.error or "validation" in result.error.lower()

    @pytest.mark.asyncio
    @patch("dealguard.mcp.server_v2.dealguard_search_ris")
    async def test_ris_tool_execution(self, mock_search, executor):
        """Test RIS tool execution."""
        mock_search.return_value = "# RIS Suchergebnisse\n- §1116 ABGB"

        result = await executor.execute(
            "dealguard_search_ris",
            {"query": "Kündigungsfrist"},
        )

        assert result.error is None
        mock_search.assert_called_once()

    @pytest.mark.asyncio
    @patch("dealguard.mcp.server_v2.dealguard_search_contracts")
    async def test_db_tool_receives_org_id(self, mock_search, executor):
        """Test that DB tools receive organization_id."""
        mock_search.return_value = "# Verträge\n- Mietvertrag.pdf"

        result = await executor.execute(
            "dealguard_search_contracts",
            {"query": "Mietvertrag"},
        )
        assert result.error is None

        # Verify organization_id was passed
        call_kwargs = mock_search.call_args[1]
        assert "organization_id" in call_kwargs
        assert call_kwargs["organization_id"] == str(executor.organization_id)


class TestRISTools:
    """Tests for RIS (Rechtsinformationssystem) tools."""

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.ris_tools.get_ris_rest_client")
    async def test_search_ris_returns_formatted_results(self, mock_client):
        """Test that search_ris returns formatted results."""
        from dealguard.mcp.tools.ris_tools import search_ris

        mock_instance = AsyncMock()
        mock_instance.search_bundesrecht.return_value = [
            {
                "Dokumentnummer": "NOR40000001",
                "Kurztitel": "ABGB §1116",
                "Abkuerzung": "ABGB",
            }
        ]
        mock_client.return_value = mock_instance

        result = await search_ris("Kündigungsfrist", "Bundesrecht", 5)

        assert "ABGB" in result
        assert "NOR40000001" in result

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.ris_tools.get_ris_rest_client")
    async def test_search_ris_empty_results(self, mock_client):
        """Test search_ris with no results."""
        from dealguard.mcp.tools.ris_tools import search_ris

        mock_instance = AsyncMock()
        mock_instance.search_bundesrecht.return_value = []
        mock_client.return_value = mock_instance

        result = await search_ris("xxxinvalidxxx", "Bundesrecht", 5)

        assert "Keine Ergebnisse" in result
        assert "Tipps" in result


class TestEdiktsdateiTools:
    """Tests for Ediktsdatei (insolvency) tools."""

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.edikte_tools.get_edikte_client")
    async def test_search_insolvency_formats_results(self, mock_client):
        """Test insolvency search formatting."""
        from dealguard.mcp.ediktsdatei_client import EdikteSearchResult, InsolvenzEdikt
        from dealguard.mcp.tools.edikte_tools import search_ediktsdatei

        mock_instance = AsyncMock()
        mock_instance.search_insolvenzen.return_value = EdikteSearchResult(
            total=1,
            page=1,
            page_size=10,
            items=[
                InsolvenzEdikt(
                    id="1",
                    aktenzeichen="123S456/23",
                    gericht="LG Wien",
                    gericht_code="LGW",
                    schuldner_name="ACME GmbH",
                    schuldner_adresse="Wien",
                    verfahrensart="Konkurs",
                    status="offen",
                    eroeffnungsdatum=date(2024, 1, 1),
                    kundmachungsdatum=date(2024, 1, 2),
                    frist_forderungsanmeldung=None,
                    insolvenzverwalter=None,
                    details_url="https://example.com",
                )
            ],
        )
        mock_client.return_value = mock_instance

        result = await search_ediktsdatei("ACME")

        assert "ACME GmbH" in result
        assert "LG Wien" in result


class TestFirmenbuchTools:
    """Tests for Firmenbuch (company registry) tools."""

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.firmenbuch_tools.OpenFirmenbuchProvider")
    async def test_search_companies_formats_results(self, mock_provider_cls):
        """Test company search formatting."""
        from dealguard.mcp.tools.firmenbuch_tools import search_firmenbuch

        mock_provider = AsyncMock()
        company = MagicMock()
        company.handelsregister_id = "FN123456a"
        company.name = "ACME GmbH"
        company.legal_form = "GmbH"
        company.city = "Wien"
        company.status = "active"
        mock_provider.search_companies.return_value = [company]
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        result = await search_firmenbuch("ACME", 10)
        data = json.loads(result)

        assert data["status"] == "ok"
        assert data["companies"][0]["name"] == "ACME GmbH"
        assert data["companies"][0]["firmenbuchnummer"] == "FN123456a"


class TestSanctionsTools:
    """Tests for sanctions/compliance tools."""

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.sanctions_tools.OpenSanctionsProvider")
    async def test_check_sanctions_no_hits(self, mock_provider_cls):
        """Test sanctions check with no hits."""
        from dealguard.mcp.tools.sanctions_tools import check_sanctions

        mock_provider = AsyncMock()
        mock_provider.check_sanctions.return_value = MagicMock(
            is_sanctioned=False,
            score=0.0,
            lists_checked=["EU"],
            summary="No matches",
            matches=[],
        )
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        result = await check_sanctions("Normal Person")
        data = json.loads(result)

        assert data["status"] == "ok"
        assert data["ist_sanktioniert"] is False

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.sanctions_tools.OpenSanctionsProvider")
    async def test_check_sanctions_with_hits(self, mock_provider_cls):
        """Test sanctions check with hits."""
        from dealguard.mcp.tools.sanctions_tools import check_sanctions

        mock_provider = AsyncMock()
        mock_provider.check_sanctions.return_value = MagicMock(
            is_sanctioned=True,
            score=0.95,
            lists_checked=["EU"],
            summary="Match found",
            matches=[
                {
                    "name": "Sanctioned Person",
                    "schema": "Person",
                    "score": 0.95,
                    "datasets": ["EU Sanctions"],
                    "countries": ["AT"],
                }
            ],
        )
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        result = await check_sanctions("Sanctioned Person")
        data = json.loads(result)

        assert data["ist_sanktioniert"] is True
        assert data["treffer"][0]["name"] == "Sanctioned Person"
        assert "warnung" in data


class TestDBTools:
    """Tests for DealGuard database tools."""

    @pytest.mark.asyncio
    async def test_search_contracts_returns_results(self):
        """Test contract search."""
        from dealguard.mcp.tools.db_tools import DbToolContext, search_contracts

        mock_session = AsyncMock()
        result = MagicMock()
        result.fetchall.return_value = [
            MagicMock(
                _mapping={
                    "id": uuid.uuid4(),
                    "filename": "Mietvertrag.pdf",
                    "contract_type": "lease",
                    "status": "analyzed",
                    "created_at": "2024-01-01",
                    "risk_score": 45,
                    "summary": "Kurzfassung.",
                }
            )
        ]
        mock_session.execute.return_value = result
        session_cm = AsyncMock()
        session_cm.__aenter__.return_value = mock_session
        session_factory = MagicMock(return_value=session_cm)
        ctx = DbToolContext(session_factory=session_factory, organization_id=uuid.uuid4())

        result = await search_contracts(ctx, query="Mietvertrag")

        assert "Mietvertrag" in result

    @pytest.mark.asyncio
    async def test_get_deadlines_filters_by_days(self):
        """Test deadline retrieval with days filter."""
        from dealguard.mcp.tools.db_tools import DbToolContext, get_deadlines

        mock_session = AsyncMock()
        result = MagicMock()
        result.fetchall.return_value = []
        mock_session.execute.return_value = result
        session_cm = AsyncMock()
        session_cm.__aenter__.return_value = mock_session
        session_factory = MagicMock(return_value=session_cm)
        ctx = DbToolContext(session_factory=session_factory, organization_id=uuid.uuid4())

        result = await get_deadlines(ctx, days_ahead=7)

        # Should return message about no deadlines
        assert result is not None


class TestToolAnnotations:
    """Tests for tool annotations (MCP metadata)."""

    def test_ris_tools_are_readonly(self):
        """Test that RIS tools are marked as read-only."""
        from dealguard.mcp.server_v2 import get_tool_definitions

        tools = get_tool_definitions()
        ris_tools = [t for t in tools if "ris" in t["name"].lower()]

        for tool in ris_tools:
            annotations = tool.get("annotations", {})
            assert annotations.get("readOnlyHint") is True

    def test_db_tools_are_readonly(self):
        """Test that DB tools are marked as read-only."""
        from dealguard.mcp.server_v2 import get_tool_definitions

        tools = get_tool_definitions()
        db_tools = [
            t
            for t in tools
            if "contract" in t["name"] or "partner" in t["name"] or "deadline" in t["name"]
        ]

        for tool in db_tools:
            annotations = tool.get("annotations", {})
            assert annotations.get("readOnlyHint") is True

    def test_all_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        from dealguard.mcp.server_v2 import get_tool_definitions

        tools = get_tool_definitions()

        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 20  # Meaningful description

    def test_all_tools_have_input_schemas(self):
        """Test that all tools have input schemas."""
        from dealguard.mcp.server_v2 import get_tool_definitions

        tools = get_tool_definitions()

        for tool in tools:
            assert "input_schema" in tool
            assert "type" in tool["input_schema"]
            assert tool["input_schema"]["type"] == "object"


class TestToolCount:
    """Tests for expected tool count."""

    def test_expected_tool_count(self):
        """Test that we have exactly 13 tools."""
        from dealguard.mcp.server_v2 import get_tool_definitions

        tools = get_tool_definitions()
        assert len(tools) == 13

    def test_all_tools_have_dealguard_prefix(self):
        """Test that all tools have dealguard_ prefix."""
        from dealguard.mcp.server_v2 import get_tool_definitions

        tools = get_tool_definitions()

        for tool in tools:
            assert tool["name"].startswith("dealguard_"), f"Tool {tool['name']} missing prefix"
