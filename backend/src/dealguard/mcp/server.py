"""MCP Server for DealGuard.

This server provides Claude with tools to access:
- Austrian legal data (RIS: laws, court decisions)
- Ediktsdatei (insolvency and auction data)
- Austrian company data (Firmenbuch via OpenFirmenbuch)
- Sanctions and PEP screening (via OpenSanctions)
- DealGuard's database (contracts, partners, deadlines)

The server can be run in two modes:
1. Stdio mode: For integration with Claude Code
2. HTTP mode: For integration with web applications

Usage with Claude Code:
    Add to your Claude Code MCP configuration:
    {
        "mcpServers": {
            "dealguard": {
                "command": "python",
                "args": ["-m", "dealguard.mcp.server"],
                "env": {
                    "DATABASE_URL": "postgresql://..."
                }
            }
        }
    }
"""

import asyncio
import json
import logging
import sys
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Tool definitions for Claude API
TOOL_DEFINITIONS = [
    {
        "name": "search_ris",
        "description": """Durchsucht das österreichische Rechtsinformationssystem (RIS) nach Gesetzen und Rechtsprechung.

Verwende dieses Tool um ECHTE, aktuelle Gesetzestexte zu finden:
- ABGB (Allgemeines Bürgerliches Gesetzbuch)
- UGB (Unternehmensgesetzbuch)
- KSchG (Konsumentenschutzgesetz)
- GmbHG (GmbH-Gesetz)
- AktG (Aktiengesetz)
- OGH/VwGH/VfGH Entscheidungen

WICHTIG: Nutze dieses Tool IMMER wenn du Gesetzestexte zitieren sollst.
Halluziniere niemals Paragraphen - hole sie aus dem RIS!

Beispiele:
- search_ris("Kündigungsfrist Mietvertrag") → Findet §1116 ABGB
- search_ris("Gewährleistung Kauf") → Findet §§922-933 ABGB
- search_ris("Geschäftsführerhaftung GmbH") → Findet §25 GmbHG""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Suchbegriffe (z.B. 'Kündigungsfrist ABGB', 'Gewährleistung')",
                },
                "law_type": {
                    "type": "string",
                    "enum": ["Bundesrecht", "Landesrecht", "Justiz", "Vfgh", "Vwgh"],
                    "default": "Bundesrecht",
                    "description": "Art der Rechtsquelle (Standard: Bundesrecht für Gesetze)",
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximale Anzahl Ergebnisse",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_law_text",
        "description": """Holt den vollständigen Text eines spezifischen Paragraphen aus dem RIS.

Verwende dies nach search_ris, um den exakten Gesetzestext zu erhalten.
Die Dokumentnummer erhältst du aus den search_ris Ergebnissen.

Beispiel: get_law_text("NOR40000001") → Volltext von §1116 ABGB""",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_number": {
                    "type": "string",
                    "description": "RIS Dokumentnummer (z.B. 'NOR40000001')",
                },
            },
            "required": ["document_number"],
        },
    },
    {
        "name": "search_ediktsdatei",
        "description": """Durchsucht die österreichische Ediktsdatei nach Insolvenzen und Zwangsversteigerungen.

KRITISCH für Partner-Prüfung! Prüfe IMMER die Ediktsdatei bevor du Aussagen
über die Bonität eines Unternehmens machst.

Was gefunden werden kann:
- Konkurse (Bankruptcy)
- Sanierungsverfahren (Restructuring)
- Zwangsversteigerungen (Forced auctions)
- Pfändungen (Seizures)

Beispiel: search_ediktsdatei("ABC GmbH") → Findet laufende Insolvenzverfahren""",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Firmenname oder Personenname",
                },
                "bundesland": {
                    "type": "string",
                    "enum": ["W", "N", "O", "S", "T", "V", "K", "ST", "B"],
                    "description": "Bundesland-Kürzel (optional)",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "search_contracts",
        "description": """Durchsucht die Verträge des Benutzers nach Stichwörtern.

Verwende dies um relevante Vertragsklauseln zu finden, die mit einer
Rechtsfrage zusammenhängen.

Beispiel: search_contracts("Kündigungsfrist") → Findet alle Verträge mit Kündigungsklauseln""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Suchbegriffe",
                },
                "contract_type": {
                    "type": "string",
                    "description": "Vertragstyp filtern (optional)",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximale Anzahl Ergebnisse",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_contract",
        "description": """Holt die Details eines spezifischen Vertrags inkl. Analyse.

Verwende dies um den vollständigen Text und die AI-Analyse eines
Vertrags zu erhalten.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "contract_id": {
                    "type": "string",
                    "description": "UUID des Vertrags",
                },
            },
            "required": ["contract_id"],
        },
    },
    {
        "name": "get_partners",
        "description": """Listet alle Geschäftspartner des Benutzers mit Risiko-Scores.

Verwende dies um einen Überblick über die Partner zu bekommen oder
um einen Partner für weitere Prüfungen zu identifizieren.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Nach Risikostufe filtern (optional)",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximale Anzahl Ergebnisse",
                },
            },
        },
    },
    {
        "name": "get_deadlines",
        "description": """Holt anstehende Fristen aus den Verträgen des Benutzers.

WICHTIG: Verwende dies proaktiv wenn der Benutzer nach Fristen fragt
oder wenn du eine Übersicht geben sollst.

Arten von Fristen:
- Kündigungsfristen
- Zahlungsfristen
- Vertragsverlängerungen
- Review-Termine""",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "default": 30,
                    "description": "Wie viele Tage vorausschauen",
                },
                "include_overdue": {
                    "type": "boolean",
                    "default": True,
                    "description": "Überfällige Fristen einschließen",
                },
            },
        },
    },
    # Firmenbuch tools
    {
        "name": "search_firmenbuch",
        "description": """Durchsucht das österreichische Firmenbuch nach Unternehmen.

Liefert Firmenwortlaut, FN-Nummer, Rechtsform und Sitz.
Verwende dieses Tool für Unternehmensrecherchen in Österreich.

Beispiel: search_firmenbuch("Red Bull") → Findet Red Bull GmbH""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Firmenname oder Teil davon (z.B. 'Red Bull', 'OMV')",
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximale Anzahl Ergebnisse",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_firmenbuch_auszug",
        "description": """Holt detaillierte Firmendaten aus dem Firmenbuch anhand der FN-Nummer.

Liefert Geschäftsführer, Stammkapital, Unternehmensgegenstand, etc.

Beispiel: get_firmenbuch_auszug("123456a") → Details zur Firma""",
        "input_schema": {
            "type": "object",
            "properties": {
                "firmenbuchnummer": {
                    "type": "string",
                    "description": "Firmenbuchnummer (z.B. '123456a' oder 'FN 123456a')",
                },
            },
            "required": ["firmenbuchnummer"],
        },
    },
    {
        "name": "check_company_austria",
        "description": """Schnelle Prüfung eines österreichischen Unternehmens.

Sucht nach dem Namen und liefert Basisdaten des besten Treffers.
Ideal für Partner-Checks und Due Diligence.

Beispiel: check_company_austria("ABC GmbH") → Basisdaten""",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name des zu prüfenden Unternehmens",
                },
            },
            "required": ["company_name"],
        },
    },
    # Sanctions tools
    {
        "name": "check_sanctions",
        "description": """Prüft ob ein Unternehmen oder eine Person auf Sanktionslisten steht.

Durchsucht internationale Sanktionslisten:
- EU Sanktionslisten (CFSP)
- UN Consolidated Sanctions
- US OFAC SDN List
- UK HMT Sanctions
- Schweizer SECO Liste

WICHTIG: Bei Treffern KEINE Geschäftsbeziehung ohne rechtliche Klärung!

Beispiel: check_sanctions("Russian Export Company") → Sanktionsstatus""",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name des Unternehmens oder der Person",
                },
                "country": {
                    "type": "string",
                    "default": "AT",
                    "description": "Ländercode (z.B. 'AT', 'DE')",
                },
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative Namen zum Prüfen",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "check_pep",
        "description": """Prüft ob eine Person ein PEP (Politically Exposed Person) ist.

Wichtig für KYC/AML Compliance und Geldwäsche-Prävention.
Bei PEPs gelten erhöhte Sorgfaltspflichten (Enhanced Due Diligence).

Beispiel: check_pep("Max Mustermann") → PEP-Status""",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": "Vollständiger Name der Person",
                },
                "country": {
                    "type": "string",
                    "default": "AT",
                    "description": "Ländercode für Kontext",
                },
            },
            "required": ["person_name"],
        },
    },
    {
        "name": "comprehensive_compliance_check",
        "description": """Umfassende Compliance-Prüfung: Sanktionen + PEP in einem Aufruf.

Ideal für Onboarding neuer Geschäftspartner und Due Diligence.
Kombiniert Sanktionslisten-Prüfung und PEP-Screening.

Beispiel: comprehensive_compliance_check("ABC GmbH", "company") → Compliance-Report""",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name des Unternehmens oder der Person",
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["company", "person"],
                    "default": "company",
                    "description": "Art der Entität",
                },
                "country": {
                    "type": "string",
                    "default": "AT",
                    "description": "Ländercode",
                },
            },
            "required": ["name"],
        },
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get the tool definitions for Claude API."""
    return TOOL_DEFINITIONS


class MCPServer:
    """MCP Server for DealGuard tools.

    This server implements the Model Context Protocol for integration
    with Claude Code and other MCP-compatible clients.
    """

    def __init__(self):
        self.tools = {tool["name"]: tool for tool in TOOL_DEFINITIONS}

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an MCP request."""
        method = request.get("method")

        if method == "tools/list":
            return {
                "tools": list(self.tools.values()),
            }

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "error": f"Unknown tool: {tool_name}",
                }

            result = await self.execute_tool(tool_name, arguments)
            return {
                "content": [{"type": "text", "text": result}],
            }

        else:
            return {
                "error": f"Unknown method: {method}",
            }

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return the result as a string."""
        # Import tools here to avoid circular imports
        from dealguard.mcp.tools import (
            get_contract,
            get_deadlines,
            get_partners,
            search_contracts,
            search_ediktsdatei,
            search_ris,
            get_law_text,
            # Firmenbuch tools
            search_firmenbuch,
            get_firmenbuch_auszug,
            check_company_austria,
            # Sanctions tools
            check_sanctions,
            check_pep,
            comprehensive_compliance_check,
        )

        try:
            if name == "search_ris":
                result = await search_ris(
                    query=arguments["query"],
                    law_type=arguments.get("law_type", "Bundesrecht"),
                    limit=arguments.get("limit", 5),
                )
            elif name == "get_law_text":
                result = await get_law_text(
                    document_number=arguments["document_number"],
                )
            elif name == "search_ediktsdatei":
                result = await search_ediktsdatei(
                    name=arguments["name"],
                    bundesland=arguments.get("bundesland"),
                )
            elif name == "search_contracts":
                result = await search_contracts(
                    query=arguments["query"],
                    contract_type=arguments.get("contract_type"),
                    limit=arguments.get("limit", 10),
                )
            elif name == "get_contract":
                result = await get_contract(
                    contract_id=arguments["contract_id"],
                )
            elif name == "get_partners":
                result = await get_partners(
                    risk_level=arguments.get("risk_level"),
                    limit=arguments.get("limit", 20),
                )
            elif name == "get_deadlines":
                result = await get_deadlines(
                    days_ahead=arguments.get("days_ahead", 30),
                    include_overdue=arguments.get("include_overdue", True),
                )
            # Firmenbuch tools
            elif name == "search_firmenbuch":
                result = await search_firmenbuch(
                    query=arguments["query"],
                    limit=arguments.get("limit", 5),
                )
            elif name == "get_firmenbuch_auszug":
                result = await get_firmenbuch_auszug(
                    firmenbuchnummer=arguments["firmenbuchnummer"],
                )
            elif name == "check_company_austria":
                result = await check_company_austria(
                    company_name=arguments["company_name"],
                )
            # Sanctions tools
            elif name == "check_sanctions":
                result = await check_sanctions(
                    name=arguments["name"],
                    country=arguments.get("country", "AT"),
                    aliases=arguments.get("aliases"),
                )
            elif name == "check_pep":
                result = await check_pep(
                    person_name=arguments["person_name"],
                    country=arguments.get("country", "AT"),
                )
            elif name == "comprehensive_compliance_check":
                result = await comprehensive_compliance_check(
                    name=arguments["name"],
                    entity_type=arguments.get("entity_type", "company"),
                    country=arguments.get("country", "AT"),
                )
            else:
                result = f"Unknown tool: {name}"

            return result

        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            return f"Error: {str(e)}"

    async def run_stdio(self):
        """Run the server in stdio mode for Claude Code integration."""
        logger.info("Starting DealGuard MCP Server (stdio mode)")

        while True:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break

                # Parse JSON request
                request = json.loads(line.strip())

                # Handle request
                response = await self.handle_request(request)

                # Write response to stdout
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
            except Exception as e:
                logger.exception(f"Error handling request: {e}")


async def main():
    """Run the MCP server."""
    server = MCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
