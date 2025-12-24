"""DealGuard MCP Server v2 - Built with FastMCP best practices.

This server provides Claude with tools to access Austrian legal and business data:
- RIS (Rechtsinformationssystem): Austrian laws and court decisions
- Ediktsdatei: Insolvency and auction data
- Firmenbuch: Austrian company registry (via OpenFirmenbuch)
- OpenSanctions: International sanctions and PEP screening
- DealGuard DB: User's contracts, partners, and deadlines

Key improvements over v1:
- FastMCP framework with proper tool registration
- Pydantic v2 models for input validation
- Tool annotations (readOnlyHint, destructiveHint, etc.)
- Response format options (markdown/json)
- Proper pagination with has_more, next_offset
- Character limits and truncation
- Actionable error messages for LLMs

Usage with Claude Code:
    Add to your .claude/settings.json:
    {
        "mcpServers": {
            "dealguard": {
                "command": "python",
                "args": ["-m", "dealguard.mcp.server_v2"],
                "env": {"DATABASE_URL": "postgresql://..."}
            }
        }
    }
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

# Configure logging - use stderr for MCP servers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("dealguard_mcp")

from dealguard.mcp.tools_v2.db import (
    dealguard_get_contract as _dealguard_get_contract,
    dealguard_get_deadlines as _dealguard_get_deadlines,
    dealguard_get_partners as _dealguard_get_partners,
    dealguard_search_contracts as _dealguard_search_contracts,
)
from dealguard.mcp.tools_v2.ediktsdatei import (
    dealguard_search_insolvency as _dealguard_search_insolvency,
)
from dealguard.mcp.tools_v2.firmenbuch import (
    dealguard_check_company_austria as _dealguard_check_company_austria,
    dealguard_get_company_details as _dealguard_get_company_details,
    dealguard_search_companies as _dealguard_search_companies,
)
from dealguard.mcp.tools_v2.ris import (
    dealguard_get_law_text as _dealguard_get_law_text,
    dealguard_search_ris as _dealguard_search_ris,
)
from dealguard.mcp.tools_v2.sanctions import (
    dealguard_check_pep as _dealguard_check_pep,
    dealguard_check_sanctions as _dealguard_check_sanctions,
    dealguard_comprehensive_compliance as _dealguard_comprehensive_compliance,
)

# Tool registrations
dealguard_search_ris = mcp.tool(
    name="dealguard_search_ris",
    annotations={
        "title": "RIS Gesetzessuche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_search_ris)

dealguard_get_law_text = mcp.tool(
    name="dealguard_get_law_text",
    annotations={
        "title": "RIS Gesetzestext abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_get_law_text)

dealguard_search_insolvency = mcp.tool(
    name="dealguard_search_insolvency",
    annotations={
        "title": "Insolvenz-Suche (Ediktsdatei)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_search_insolvency)

dealguard_search_companies = mcp.tool(
    name="dealguard_search_companies",
    annotations={
        "title": "Firmenbuch Suche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_search_companies)

dealguard_get_company_details = mcp.tool(
    name="dealguard_get_company_details",
    annotations={
        "title": "Firmenbuch Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_get_company_details)

dealguard_check_company_austria = mcp.tool(
    name="dealguard_check_company_austria",
    annotations={
        "title": "Schnelle Firmenpr?fung AT",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_check_company_austria)

dealguard_check_sanctions = mcp.tool(
    name="dealguard_check_sanctions",
    annotations={
        "title": "Sanktionslisten-Check",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_check_sanctions)

dealguard_check_pep = mcp.tool(
    name="dealguard_check_pep",
    annotations={
        "title": "PEP-Pr?fung",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_check_pep)

dealguard_comprehensive_compliance = mcp.tool(
    name="dealguard_comprehensive_compliance",
    annotations={
        "title": "Compliance-Vollpr?fung",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)(_dealguard_comprehensive_compliance)

dealguard_search_contracts = mcp.tool(
    name="dealguard_search_contracts",
    annotations={
        "title": "Vertr?ge durchsuchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(_dealguard_search_contracts)

dealguard_get_contract = mcp.tool(
    name="dealguard_get_contract",
    annotations={
        "title": "Vertrag abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(_dealguard_get_contract)

dealguard_get_partners = mcp.tool(
    name="dealguard_get_partners",
    annotations={
        "title": "Partner auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(_dealguard_get_partners)

dealguard_get_deadlines = mcp.tool(
    name="dealguard_get_deadlines",
    annotations={
        "title": "Fristen abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(_dealguard_get_deadlines)

# Tool Definitions Export (for Claude API integration)
# ============================================================================

def _resolve_refs(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve $ref references in a JSON schema."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            # Extract ref name (e.g., "#/$defs/LawType" -> "LawType")
            ref_path = schema["$ref"]
            ref_name = ref_path.split("/")[-1]
            if ref_name in defs:
                # Merge the referenced definition with any additional properties
                resolved = defs[ref_name].copy()
                # Keep any additional properties from the original (like default, description)
                for key, value in schema.items():
                    if key != "$ref":
                        resolved[key] = value
                return resolved
            return schema
        else:
            return {k: _resolve_refs(v, defs) for k, v in schema.items()}
    elif isinstance(schema, list):
        return [_resolve_refs(item, defs) for item in schema]
    else:
        return schema


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get tool definitions in Claude API format.

    This converts FastMCP tool definitions to the format expected by
    the Anthropic Claude API for tool_use.

    FastMCP wraps parameters in a 'params' object and uses $refs for
    enums. We need to:
    1. Extract the actual input model from $defs
    2. Resolve all $ref references inline
    """
    tools = []

    for tool in mcp._tool_manager._tools.values():
        parameters = tool.parameters
        defs = parameters.get("$defs", {})

        # Find the main input model (the one ending with "Input")
        input_model_name = None
        input_model = None
        for name, definition in defs.items():
            if name.endswith("Input"):
                input_model_name = name
                input_model = definition.copy()
                break

        if input_model is None:
            # Fallback: use the full parameters schema
            input_schema = parameters
        else:
            # Resolve all $ref references in the input model
            input_schema = _resolve_refs(input_model, defs)
            # Remove $defs from the resolved schema if it exists
            input_schema.pop("$defs", None)

        annotations = tool.annotations.model_dump() if tool.annotations else {}
        tool_def = {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": input_schema,
            "annotations": annotations,
        }
        tools.append(tool_def)

    return tools


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
