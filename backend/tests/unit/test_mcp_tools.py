"""
Unit tests for MCP (Model Context Protocol) tools.

Tests cover all 13 tools that Claude uses to access Austrian legal data
and DealGuard's internal database.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
        assert input_model.include_references is False

    def test_with_references(self):
        """Test with references enabled."""
        input_model = models.GetLawTextInput(
            document_number="NOR40000001",
            include_references=True,
        )
        assert input_model.include_references is True


class TestSearchEdiktsdateiInput:
    """Tests for SearchEdiktsdateiInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.SearchEdiktsdateiInput(query="ACME GmbH")
        assert input_model.query == "ACME GmbH"
        assert input_model.search_type == "company"

    def test_search_types(self):
        """Test different search types."""
        for search_type in ["company", "person", "location"]:
            input_model = models.SearchEdiktsdateiInput(
                query="test",
                search_type=search_type,
            )
            assert input_model.search_type == search_type


class TestSearchFirmenbuchInput:
    """Tests for SearchFirmenbuchInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.SearchFirmenbuchInput(query="ACME")
        assert input_model.query == "ACME"
        assert input_model.limit == 10

    def test_custom_limit(self):
        """Test custom limit."""
        input_model = models.SearchFirmenbuchInput(query="test", limit=5)
        assert input_model.limit == 5


class TestGetFirmenbuchAuszugInput:
    """Tests for GetFirmenbuchAuszugInput model validation."""

    def test_valid_company_number(self):
        """Test valid company number."""
        input_model = models.GetFirmenbuchAuszugInput(company_number="FN123456a")
        assert input_model.company_number == "FN123456a"


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
        assert input_model.country is None

    def test_with_country(self):
        """Test input with country."""
        input_model = models.CheckSanctionsInput(name="John Doe", country="AT")
        assert input_model.country == "AT"


class TestCheckPEPInput:
    """Tests for CheckPEPInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.CheckPEPInput(name="Max Mustermann")
        assert input_model.name == "Max Mustermann"

    def test_with_birth_year(self):
        """Test input with birth year."""
        input_model = models.CheckPEPInput(name="Max Mustermann", birth_year=1970)
        assert input_model.birth_year == 1970


class TestComprehensiveComplianceInput:
    """Tests for ComprehensiveComplianceInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.ComprehensiveComplianceInput(name="Company XYZ")
        assert input_model.name == "Company XYZ"

    def test_with_all_fields(self):
        """Test with all optional fields."""
        input_model = models.ComprehensiveComplianceInput(
            name="Company XYZ",
            country="DE",
            include_pep=True,
        )
        assert input_model.country == "DE"
        assert input_model.include_pep is True


class TestSearchContractsInput:
    """Tests for SearchContractsInput model validation."""

    def test_valid_input(self):
        """Test valid input."""
        input_model = models.SearchContractsInput(query="Mietvertrag")
        assert input_model.query == "Mietvertrag"
        assert input_model.limit == 10

    def test_empty_query_allowed(self):
        """Test empty query is allowed for listing."""
        input_model = models.SearchContractsInput()
        assert input_model.query is None


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
    @patch("dealguard.mcp.tools.edikte_tools.get_ediktsdatei_client")
    async def test_search_insolvency_formats_results(self, mock_client):
        """Test insolvency search formatting."""
        from dealguard.mcp.tools.edikte_tools import search_ediktsdatei

        mock_instance = AsyncMock()
        mock_instance.search.return_value = [
            {
                "type": "insolvency",
                "debtor_name": "ACME GmbH",
                "court": "LG Wien",
                "file_number": "123S456/23",
            }
        ]
        mock_client.return_value = mock_instance

        result = await search_ediktsdatei("ACME", "company", 10)

        assert "ACME GmbH" in result
        assert "LG Wien" in result


class TestFirmenbuchTools:
    """Tests for Firmenbuch (company registry) tools."""

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.firmenbuch_tools.get_firmenbuch_client")
    async def test_search_companies_formats_results(self, mock_client):
        """Test company search formatting."""
        from dealguard.mcp.tools.firmenbuch_tools import search_firmenbuch

        mock_instance = AsyncMock()
        mock_instance.search.return_value = [
            {
                "company_name": "ACME GmbH",
                "company_number": "FN123456a",
                "legal_form": "GmbH",
                "registered_address": "Wien",
            }
        ]
        mock_client.return_value = mock_instance

        result = await search_firmenbuch("ACME", 10)

        assert "ACME GmbH" in result
        assert "FN123456a" in result


class TestSanctionsTools:
    """Tests for sanctions/compliance tools."""

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.sanctions_tools.get_sanctions_client")
    async def test_check_sanctions_no_hits(self, mock_client):
        """Test sanctions check with no hits."""
        from dealguard.mcp.tools.sanctions_tools import check_sanctions

        mock_instance = AsyncMock()
        mock_instance.check.return_value = {"hits": [], "count": 0}
        mock_client.return_value = mock_instance

        result = await check_sanctions("Normal Person", None)

        assert "Keine Treffer" in result or "No matches" in result.lower() or "clean" in result.lower()

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.sanctions_tools.get_sanctions_client")
    async def test_check_sanctions_with_hits(self, mock_client):
        """Test sanctions check with hits."""
        from dealguard.mcp.tools.sanctions_tools import check_sanctions

        mock_instance = AsyncMock()
        mock_instance.check.return_value = {
            "hits": [
                {
                    "name": "Sanctioned Person",
                    "dataset": "EU Sanctions",
                    "score": 95,
                }
            ],
            "count": 1,
        }
        mock_client.return_value = mock_instance

        result = await check_sanctions("Sanctioned Person", None)

        assert "Sanctioned Person" in result or "WARNUNG" in result


class TestDBTools:
    """Tests for DealGuard database tools."""

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.db_tools.get_db_session")
    async def test_search_contracts_returns_results(self, mock_session):
        """Test contract search."""
        from dealguard.mcp.tools.db_tools import search_contracts

        mock_instance = AsyncMock()
        mock_instance.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=[
                        MagicMock(
                            id=uuid.uuid4(),
                            filename="Mietvertrag.pdf",
                            status="analyzed",
                            risk_score=45,
                        )
                    ])
                )
            )
        )
        mock_session.return_value.__aenter__.return_value = mock_instance

        result = await search_contracts(
            models.SearchContractsInput(query="Mietvertrag"),
            organization_id=str(uuid.uuid4()),
        )

        assert "Mietvertrag" in result

    @pytest.mark.asyncio
    @patch("dealguard.mcp.tools.db_tools.get_db_session")
    async def test_get_deadlines_filters_by_days(self, mock_session):
        """Test deadline retrieval with days filter."""
        from dealguard.mcp.tools.db_tools import get_deadlines

        mock_instance = AsyncMock()
        mock_instance.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=[])
                )
            )
        )
        mock_session.return_value.__aenter__.return_value = mock_instance

        result = await get_deadlines(
            models.GetDeadlinesInput(days_ahead=7),
            organization_id=str(uuid.uuid4()),
        )

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
        db_tools = [t for t in tools if "contract" in t["name"] or "partner" in t["name"] or "deadline" in t["name"]]

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
