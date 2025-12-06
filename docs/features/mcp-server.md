# MCP Server (Model Context Protocol)

## Overview

The MCP Server provides Claude with access to Austrian legal data and DealGuard's internal database through 13 specialized tools. This enables Claude to answer questions with real, verified data instead of hallucinating.

## Why MCP?

Traditional LLMs have a knowledge cutoff and no access to:
- Current Austrian laws (ABGB, UGB, KSchG)
- Real-time insolvency data
- Company registry information
- User's contracts and partners

With MCP, Claude can:
1. Search for relevant laws
2. Get exact legal text with citations
3. Check partner insolvency status
4. Access the user's contract database

## Available Tools

### RIS Tools (Austrian Legal Database)

#### `dealguard_search_ris`
Search Austrian laws and court decisions.

```json
{
  "query": "Kündigungsfrist Mietvertrag",
  "law_type": "Bundesrecht",
  "limit": 5
}
```

**Law types:**
- `Bundesrecht` - Federal laws (ABGB, UGB, KSchG)
- `Landesrecht` - State laws
- `Justiz` - OGH (Supreme Court) decisions
- `Vfgh` - Constitutional Court
- `Vwgh` - Administrative Court

#### `dealguard_get_law_text`
Get the full text of a specific law section.

```json
{
  "document_number": "NOR40000001",
  "include_references": true
}
```

### Insolvency Tools (Ediktsdatei)

#### `dealguard_search_insolvency`
Search Austrian insolvency database.

```json
{
  "query": "ACME GmbH",
  "search_type": "company",
  "limit": 10
}
```

### Company Tools (Firmenbuch)

#### `dealguard_search_companies`
Search Austrian company registry.

```json
{
  "query": "ACME",
  "limit": 10
}
```

#### `dealguard_get_company_details`
Get detailed company information.

```json
{
  "company_number": "FN123456a"
}
```

#### `dealguard_check_company_austria`
Quick company verification.

```json
{
  "company_name": "ACME GmbH"
}
```

### Sanctions Tools (OpenSanctions)

#### `dealguard_check_sanctions`
Check against sanctions lists.

```json
{
  "name": "John Doe",
  "country": "AT"
}
```

#### `dealguard_check_pep`
Check for Politically Exposed Persons.

```json
{
  "name": "Max Mustermann",
  "birth_year": 1970
}
```

#### `dealguard_comprehensive_compliance`
Combined sanctions + PEP check.

```json
{
  "name": "Company XYZ",
  "country": "DE"
}
```

### Database Tools (DealGuard)

#### `dealguard_search_contracts`
Search user's contracts.

```json
{
  "query": "Mietvertrag",
  "limit": 10
}
```

#### `dealguard_get_contract`
Get contract details.

```json
{
  "contract_id": "uuid-here"
}
```

#### `dealguard_get_partners`
List business partners.

```json
{
  "risk_level": "high",
  "limit": 20
}
```

#### `dealguard_get_deadlines`
Get upcoming deadlines.

```json
{
  "days_ahead": 30,
  "include_overdue": true
}
```

## Tool Annotations

Each tool includes metadata for Claude:

```python
annotations=ToolAnnotations(
    readOnlyHint=True,      # Tool only reads data
    destructiveHint=False,  # Tool doesn't modify data
    idempotentHint=True,    # Same input = same output
    openWorldHint=False,    # Limited to known data sources
)
```

## Response Format

All tools support two output formats:

```json
{
  "response_format": "markdown"  // or "json"
}
```

**Markdown** (default): Human-readable, with headers and lists
**JSON**: Machine-parseable, for programmatic use

## Pagination

For list results:

```json
{
  "results": [...],
  "has_more": true,
  "next_offset": 10,
  "total_count": 45
}
```

## Character Limits

Responses are truncated at 25,000 characters with a note:

```
[Output truncated. Use pagination (offset=10, limit=10) to see more results.]
```

## Error Handling

Errors are returned in a LLM-friendly format:

```
Error: Ungültige Firmenbuchnummer

Was ist passiert: Das Format der Firmenbuchnummer ist ungültig.
Was tun: Verwende das Format 'FN123456x' (FN + Zahlen + Prüfbuchstabe).
Beispiel: dealguard_get_company_details(company_number="FN123456a")
```

## Integration with Chat

The MCP tools are integrated into the Chat v2 service:

```python
# service_v2.py
class ChatService:
    def __init__(self, organization_id: UUID):
        self.tool_executor = ToolExecutor(organization_id)
        self.tools = get_tool_definitions()  # From MCP server_v2
```

Claude automatically decides which tools to call based on the user's question.

## Configuration

```env
# No configuration needed - tools use public Austrian APIs
# Database tools use the user's organization_id automatically
```

## Data Sources

| Tool | Source | Cost | Rate Limit |
|------|--------|------|------------|
| RIS | data.bka.gv.at | Free | Fair use |
| Ediktsdatei | edikte.justiz.gv.at | Free | Fair use |
| OpenFirmenbuch | openfirmenbuch.at | Free | Fair use |
| OpenSanctions | opensanctions.org | Free | Fair use |
| DB Tools | PostgreSQL | Free | N/A |

## Related Files

- `backend/src/dealguard/mcp/server_v2.py` - MCP server with tool definitions
- `backend/src/dealguard/mcp/models.py` - Pydantic input models
- `backend/src/dealguard/mcp/ris_client.py` - RIS API client
- `backend/src/dealguard/mcp/ediktsdatei_client.py` - Ediktsdatei client
- `backend/src/dealguard/mcp/tools/` - Tool implementations
- `backend/src/dealguard/domain/chat/tool_executor.py` - Tool dispatcher
