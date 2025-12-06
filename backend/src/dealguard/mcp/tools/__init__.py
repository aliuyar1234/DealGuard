"""MCP Tools for DealGuard.

These tools provide Claude with access to:
- Austrian legal data (RIS, Ediktsdatei)
- Austrian company data (Firmenbuch via OpenFirmenbuch)
- Sanctions and PEP screening (via OpenSanctions)
- DealGuard's internal database (contracts, partners, deadlines)
"""

from dealguard.mcp.tools.db_tools import (
    get_contract,
    get_deadlines,
    get_partners,
    search_contracts,
)
from dealguard.mcp.tools.edikte_tools import (
    check_insolvency,
    search_ediktsdatei,
)
from dealguard.mcp.tools.ris_tools import (
    get_law_text,
    search_ris,
)
from dealguard.mcp.tools.firmenbuch_tools import (
    search_firmenbuch,
    get_firmenbuch_auszug,
    check_company_austria,
)
from dealguard.mcp.tools.sanctions_tools import (
    check_sanctions,
    check_pep,
    comprehensive_compliance_check,
)

__all__ = [
    # RIS tools
    "search_ris",
    "get_law_text",
    # Ediktsdatei tools
    "search_ediktsdatei",
    "check_insolvency",
    # Firmenbuch tools
    "search_firmenbuch",
    "get_firmenbuch_auszug",
    "check_company_austria",
    # Sanctions tools
    "check_sanctions",
    "check_pep",
    "comprehensive_compliance_check",
    # DB tools
    "search_contracts",
    "get_contract",
    "get_partners",
    "get_deadlines",
]
