"""Tool executor for chat service.

This module handles execution of MCP tools called by AI providers.
Uses a strategy dict pattern for cleaner tool dispatch.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class ToolExecution:
    """Result of executing a tool."""

    tool_name: str
    tool_input: dict[str, Any]
    result: str
    error: str | None = None


class ToolExecutor:
    """Executes MCP tools for the chat service.

    Tool names have 'dealguard_' prefix per MCP best practices.
    """

    def __init__(self, organization_id: UUID):
        """Initialize the tool executor.

        Args:
            organization_id: The user's organization (for DB queries)
        """
        self.organization_id = organization_id

    async def execute(self, tool_name: str, tool_input: dict) -> ToolExecution:
        """Execute a single tool and return the result.

        Uses a strategy dict pattern for cleaner tool dispatch.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            ToolExecution with result or error
        """
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

        try:
            # Import tools and models
            from dealguard.mcp import server_v2 as tools
            from dealguard.mcp import models

            # Strategy dict: tool_name -> (InputModel, handler_func, needs_org_id)
            TOOL_HANDLERS: dict[str, tuple[type, callable, bool]] = {
                # RIS tools (Austrian legal database)
                "dealguard_search_ris": (
                    models.SearchRISInput,
                    tools.dealguard_search_ris,
                    False,
                ),
                "dealguard_get_law_text": (
                    models.GetLawTextInput,
                    tools.dealguard_get_law_text,
                    False,
                ),
                # Insolvency tools
                "dealguard_search_insolvency": (
                    models.SearchEdiktsdateiInput,
                    tools.dealguard_search_insolvency,
                    False,
                ),
                # Company tools (Firmenbuch)
                "dealguard_search_companies": (
                    models.SearchFirmenbuchInput,
                    tools.dealguard_search_companies,
                    False,
                ),
                "dealguard_get_company_details": (
                    models.GetFirmenbuchAuszugInput,
                    tools.dealguard_get_company_details,
                    False,
                ),
                "dealguard_check_company_austria": (
                    models.CheckCompanyAustriaInput,
                    tools.dealguard_check_company_austria,
                    False,
                ),
                # Sanctions/Compliance tools
                "dealguard_check_sanctions": (
                    models.CheckSanctionsInput,
                    tools.dealguard_check_sanctions,
                    False,
                ),
                "dealguard_check_pep": (
                    models.CheckPEPInput,
                    tools.dealguard_check_pep,
                    False,
                ),
                "dealguard_comprehensive_compliance": (
                    models.ComprehensiveComplianceInput,
                    tools.dealguard_comprehensive_compliance,
                    False,
                ),
                # DB tools need organization_id
                "dealguard_search_contracts": (
                    models.SearchContractsInput,
                    tools.dealguard_search_contracts,
                    True,
                ),
                "dealguard_get_contract": (
                    models.GetContractInput,
                    tools.dealguard_get_contract,
                    True,
                ),
                "dealguard_get_partners": (
                    models.GetPartnersInput,
                    tools.dealguard_get_partners,
                    True,
                ),
                "dealguard_get_deadlines": (
                    models.GetDeadlinesInput,
                    tools.dealguard_get_deadlines,
                    True,
                ),
            }

            if tool_name not in TOOL_HANDLERS:
                available = ", ".join(TOOL_HANDLERS.keys())
                result = f"Unbekanntes Tool: {tool_name}\n\nVerfügbare Tools: {available}"
                return ToolExecution(tool_name=tool_name, tool_input=tool_input, result=result)

            input_model, handler, needs_org_id = TOOL_HANDLERS[tool_name]
            params = input_model(**tool_input)

            if needs_org_id:
                result = await handler(params, organization_id=str(self.organization_id))
            else:
                result = await handler(params)

            return ToolExecution(tool_name=tool_name, tool_input=tool_input, result=result)

        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            error_msg = str(e)
            if "validation error" in error_msg.lower():
                error_msg = f"Eingabefehler bei {tool_name}: {error_msg}. Bitte prüfe die Parameter."
            return ToolExecution(tool_name=tool_name, tool_input=tool_input, result="", error=error_msg)
