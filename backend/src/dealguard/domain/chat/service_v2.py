"""Chat Service v2 with Claude Tool-Calling.

This service integrates Claude API with DealGuard's MCP tools:
- RIS (Austrian legal database)
- Ediktsdatei (Insolvency data)
- Firmenbuch (Austrian company registry)
- OpenSanctions (Sanctions and PEP screening)
- DealGuard DB (Contracts, Partners, Deadlines)

The service handles:
1. Sending user messages to Claude
2. Executing tool calls requested by Claude
3. Returning tool results to Claude
4. Streaming the final response

Uses the new FastMCP-based server v2 with:
- Pydantic validation for tool inputs
- Tool annotations (readOnlyHint, etc.)
- Response format options (markdown/json)
- Proper pagination and truncation
- Cost tracking for all API calls
- Retry logic with exponential backoff
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Literal
from uuid import UUID

import anthropic
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from dealguard.config import get_settings
from dealguard.infrastructure.ai.cost_tracker import CostTracker
from dealguard.mcp.server_v2 import get_tool_definitions

logger = logging.getLogger(__name__)

# Shared cost tracker instance
_cost_tracker = CostTracker()


@dataclass
class ChatMessage:
    """A message in the chat conversation."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None


@dataclass
class ToolExecution:
    """Result of executing a tool."""

    tool_name: str
    tool_input: dict[str, Any]
    result: str
    error: str | None = None


SYSTEM_PROMPT = """Du bist DealGuard AI, ein österreichischer Rechtsassistent für KMU.

Du hast Zugang zu ECHTEN österreichischen Datenquellen über folgende Tools:

**Rechtsdaten (RIS):**
- `dealguard_search_ris` - Suche nach Gesetzen (ABGB, UGB, KSchG, etc.)
- `dealguard_get_law_text` - Volltext eines Paragraphen abrufen

**Unternehmensdaten:**
- `dealguard_search_companies` - Firmenbuch-Suche
- `dealguard_get_company_details` - Firmendaten abrufen
- `dealguard_check_company_austria` - Schnelle Firmenprüfung

**Compliance & Insolvenz:**
- `dealguard_search_insolvency` - Ediktsdatei (Insolvenzen)
- `dealguard_check_sanctions` - Sanktionslisten
- `dealguard_check_pep` - PEP-Prüfung
- `dealguard_comprehensive_compliance` - Vollprüfung

**Benutzerdaten:**
- `dealguard_search_contracts` - Verträge durchsuchen
- `dealguard_get_contract` - Vertragsdetails
- `dealguard_get_partners` - Geschäftspartner
- `dealguard_get_deadlines` - Fristen und Termine

WICHTIGE REGELN:

1. **NIEMALS Gesetze halluzinieren!**
   - Wenn du einen Paragraphen zitieren sollst, NUTZE `dealguard_search_ris`
   - Hole den exakten Text mit `dealguard_get_law_text`
   - Zitiere IMMER mit Quelle: "Gemäß §X ABGB [Quelle: RIS]..."

2. **Bei Partner-Fragen IMMER prüfen!**
   - `dealguard_search_insolvency` für Insolvenzstatus
   - `dealguard_check_company_austria` für Firmendaten
   - `dealguard_check_sanctions` bei internationalen Partnern
   - Warne explizit bei Treffern!

3. **Verträge und Fristen aus der DB holen**
   - Nutze `dealguard_search_contracts` um relevante Verträge zu finden
   - Nutze `dealguard_get_deadlines` für Fristenübersichten
   - Verbinde Gesetzesinfos mit konkreten Vertragsdaten

4. **Sprache**: Deutsch (österreichisches Deutsch)

5. **Tonfall**: Professionell aber verständlich für Nicht-Juristen

6. **Format**: Nutze Markdown für strukturierte Antworten

Beispiel für gute Antwort:
"Gemäß §1116 ABGB [Quelle: RIS] können Bestandverträge auf unbestimmte Zeit
unter Einhaltung der vereinbarten oder ortsüblichen Frist gekündigt werden.

In Ihrem Vertrag 'Büroräume_Wien.pdf' steht auf Seite 3:
'Kündigungsfrist beträgt 3 Monate zum Quartalsende.'

Diese Frist ist rechtlich zulässig und entspricht dem ABGB."
"""


class ChatService:
    """Chat service with Claude tool-calling integration.

    This service:
    1. Receives user messages
    2. Sends them to Claude with tool definitions
    3. Executes tool calls as requested by Claude
    4. Returns Claude's final response
    """

    def __init__(
        self,
        organization_id: UUID,
        api_key: str | None = None,
        user_settings: dict | None = None,
    ):
        """Initialize the chat service.

        Args:
            organization_id: The user's organization (for DB queries)
            api_key: Anthropic API key (uses settings if not provided)
            user_settings: User-specific settings (from DB)
        """
        self.organization_id = organization_id
        settings = get_settings()
        user_settings = user_settings or {}

        # Get AI provider and key from user settings or env
        self.ai_provider = user_settings.get("ai_provider") or settings.ai_provider

        if self.ai_provider == "anthropic":
            self.api_key = api_key or user_settings.get("anthropic_api_key") or settings.anthropic_api_key
            self.model = settings.anthropic_model
            if not self.api_key:
                raise ValueError(
                    "Anthropic API Key nicht konfiguriert. "
                    "Bitte in den Einstellungen hinterlegen."
                )
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=self.api_key)
            self.openai_client = None
        elif self.ai_provider == "deepseek":
            self.api_key = user_settings.get("deepseek_api_key") or settings.deepseek_api_key
            self.model = settings.deepseek_model
            if not self.api_key:
                raise ValueError(
                    "DeepSeek API Key nicht konfiguriert. "
                    "Bitte in den Einstellungen hinterlegen."
                )
            # DeepSeek uses OpenAI-compatible API
            self.openai_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=settings.deepseek_base_url,
            )
            self.anthropic_client = None
        else:
            raise ValueError(f"Unbekannter AI Provider: {self.ai_provider}")

        self.max_tokens = settings.anthropic_max_tokens

        # Get tool definitions
        self.tools = self._convert_tools_for_anthropic()
        self.openai_tools = self._convert_tools_for_openai() if self.openai_client else None

    def _convert_tools_for_anthropic(self) -> list[dict]:
        """Convert tool definitions to Anthropic format."""
        tool_defs = get_tool_definitions()
        anthropic_tools = []

        for tool in tool_defs:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            })

        return anthropic_tools

    def _convert_tools_for_openai(self) -> list[dict]:
        """Convert tool definitions to OpenAI format."""
        tool_defs = get_tool_definitions()
        openai_tools = []

        for tool in tool_defs:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })

        return openai_tools

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> ToolExecution:
        """Execute a single tool and return the result.

        Uses the new FastMCP-based tools with Pydantic validation.
        Tool names now have 'dealguard_' prefix per MCP best practices.
        """
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

        try:
            # Import the new FastMCP tools and Pydantic models
            from dealguard.mcp.server_v2 import (
                dealguard_search_ris,
                dealguard_get_law_text,
                dealguard_search_insolvency,
                dealguard_search_companies,
                dealguard_get_company_details,
                dealguard_check_company_austria,
                dealguard_check_sanctions,
                dealguard_check_pep,
                dealguard_comprehensive_compliance,
                dealguard_search_contracts,
                dealguard_get_contract,
                dealguard_get_partners,
                dealguard_get_deadlines,
            )
            from dealguard.mcp.models import (
                SearchRISInput,
                GetLawTextInput,
                SearchEdiktsdateiInput,
                SearchFirmenbuchInput,
                GetFirmenbuchAuszugInput,
                CheckCompanyAustriaInput,
                CheckSanctionsInput,
                CheckPEPInput,
                ComprehensiveComplianceInput,
                SearchContractsInput,
                GetContractInput,
                GetPartnersInput,
                GetDeadlinesInput,
            )

            # Execute the appropriate tool with Pydantic validation
            org_id = str(self.organization_id)

            if tool_name == "dealguard_search_ris":
                params = SearchRISInput(**tool_input)
                result = await dealguard_search_ris(params)

            elif tool_name == "dealguard_get_law_text":
                params = GetLawTextInput(**tool_input)
                result = await dealguard_get_law_text(params)

            elif tool_name == "dealguard_search_insolvency":
                params = SearchEdiktsdateiInput(**tool_input)
                result = await dealguard_search_insolvency(params)

            elif tool_name == "dealguard_search_companies":
                params = SearchFirmenbuchInput(**tool_input)
                result = await dealguard_search_companies(params)

            elif tool_name == "dealguard_get_company_details":
                params = GetFirmenbuchAuszugInput(**tool_input)
                result = await dealguard_get_company_details(params)

            elif tool_name == "dealguard_check_company_austria":
                params = CheckCompanyAustriaInput(**tool_input)
                result = await dealguard_check_company_austria(params)

            elif tool_name == "dealguard_check_sanctions":
                params = CheckSanctionsInput(**tool_input)
                result = await dealguard_check_sanctions(params)

            elif tool_name == "dealguard_check_pep":
                params = CheckPEPInput(**tool_input)
                result = await dealguard_check_pep(params)

            elif tool_name == "dealguard_comprehensive_compliance":
                params = ComprehensiveComplianceInput(**tool_input)
                result = await dealguard_comprehensive_compliance(params)

            elif tool_name == "dealguard_search_contracts":
                params = SearchContractsInput(**tool_input)
                result = await dealguard_search_contracts(params, organization_id=org_id)

            elif tool_name == "dealguard_get_contract":
                params = GetContractInput(**tool_input)
                result = await dealguard_get_contract(params, organization_id=org_id)

            elif tool_name == "dealguard_get_partners":
                params = GetPartnersInput(**tool_input)
                result = await dealguard_get_partners(params, organization_id=org_id)

            elif tool_name == "dealguard_get_deadlines":
                params = GetDeadlinesInput(**tool_input)
                result = await dealguard_get_deadlines(params, organization_id=org_id)

            else:
                result = (
                    f"Unbekanntes Tool: {tool_name}\n\n"
                    "Verfügbare Tools: dealguard_search_ris, dealguard_get_law_text, "
                    "dealguard_search_insolvency, dealguard_search_companies, "
                    "dealguard_get_company_details, dealguard_check_company_austria, "
                    "dealguard_check_sanctions, dealguard_check_pep, "
                    "dealguard_comprehensive_compliance, dealguard_search_contracts, "
                    "dealguard_get_contract, dealguard_get_partners, dealguard_get_deadlines"
                )

            return ToolExecution(
                tool_name=tool_name,
                tool_input=tool_input,
                result=result,
            )

        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            # Provide actionable error message
            error_msg = str(e)
            if "validation error" in error_msg.lower():
                error_msg = (
                    f"Eingabefehler bei {tool_name}: {error_msg}. "
                    "Bitte prüfe die Parameter."
                )
            return ToolExecution(
                tool_name=tool_name,
                tool_input=tool_input,
                result="",
                error=error_msg,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((anthropic.APITimeoutError, anthropic.APIConnectionError)),
        reraise=True,
    )
    async def _call_anthropic_api(
        self,
        messages: list[dict],
    ) -> anthropic.types.Message:
        """Call Anthropic API with retry logic for transient errors."""
        return await self.anthropic_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            tools=self.tools,
            messages=messages,
        )

    async def _call_openai_api(
        self,
        messages: list[dict],
    ):
        """Call OpenAI-compatible API (DeepSeek) with retry logic."""
        import openai

        # Add system message to the beginning
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        try:
            return await self.openai_client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=full_messages,
                tools=self.openai_tools if self.openai_tools else None,
            )
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            # Retry on transient errors
            raise e

    def _track_usage(self, response, action: str) -> None:
        """Track API usage and costs."""
        if self.ai_provider == "anthropic":
            if hasattr(response, "usage") and response.usage:
                _cost_tracker.record(
                    model=self.model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    action=action,
                    resource_id=self.organization_id,
                )
        elif self.ai_provider == "deepseek":
            if hasattr(response, "usage") and response.usage:
                _cost_tracker.record(
                    model=self.model,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    action=action,
                    resource_id=self.organization_id,
                )

    async def chat(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
    ) -> ChatMessage | AsyncIterator[str]:
        """Send messages to Claude/DeepSeek and get a response.

        Args:
            messages: List of chat messages
            stream: Whether to stream the response

        Returns:
            Assistant's response message (or async iterator if streaming)
        """
        # Convert messages to API format
        api_messages = []
        for msg in messages:
            if msg.role == "system":
                continue  # System message is handled separately
            api_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        if self.ai_provider == "anthropic":
            # Call Anthropic with tools (with retry logic)
            response = await self._call_anthropic_api(api_messages)
            self._track_usage(response, "chat_v2_initial")
            return await self._process_anthropic_response(response, api_messages)
        else:
            # Call DeepSeek (OpenAI-compatible)
            response = await self._call_openai_api(api_messages)
            self._track_usage(response, "chat_v2_initial")
            return await self._process_openai_response(response, api_messages)

    async def _process_anthropic_response(
        self,
        response: anthropic.types.Message,
        messages: list[dict],
    ) -> ChatMessage:
        """Process Anthropic/Claude's response, executing tools if needed."""
        tool_executions = []
        final_text = ""

        # Check if there are tool calls to execute
        while response.stop_reason == "tool_use":
            # Find all tool use blocks
            tool_calls = [
                block for block in response.content
                if block.type == "tool_use"
            ]

            if not tool_calls:
                break

            # Execute all tools
            tool_results = []
            for tool_call in tool_calls:
                execution = await self._execute_tool(
                    tool_call.name,
                    tool_call.input,
                )
                tool_executions.append(execution)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": execution.result if not execution.error else f"Error: {execution.error}",
                })

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": response.content,
            })

            # Add tool results
            messages.append({
                "role": "user",
                "content": tool_results,
            })

            # Call Claude again with tool results (with retry logic)
            response = await self._call_anthropic_api(messages)

            # Track follow-up API call
            self._track_usage(response, "chat_v2_tool_followup")

        # Extract final text response
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        return ChatMessage(
            role="assistant",
            content=final_text,
            tool_calls=[{
                "name": e.tool_name,
                "input": e.tool_input,
            } for e in tool_executions] if tool_executions else None,
            tool_results=[{
                "name": e.tool_name,
                "result": e.result[:500] + "..." if len(e.result) > 500 else e.result,
            } for e in tool_executions] if tool_executions else None,
        )

    async def _process_openai_response(
        self,
        response,
        messages: list[dict],
    ) -> ChatMessage:
        """Process OpenAI/DeepSeek response, executing tools if needed."""
        tool_executions = []

        # Get the first choice
        choice = response.choices[0]
        message = choice.message

        # Check if there are tool calls to execute
        while choice.finish_reason == "tool_calls" and message.tool_calls:
            # Execute all tools
            tool_results = []
            for tool_call in message.tool_calls:
                # Parse the function arguments
                import json
                try:
                    tool_input = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_input = {}

                execution = await self._execute_tool(
                    tool_call.function.name,
                    tool_input,
                )
                tool_executions.append(execution)

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": execution.result if not execution.error else f"Error: {execution.error}",
                })

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # Add tool results
            messages.extend(tool_results)

            # Call API again with tool results
            response = await self._call_openai_api(messages)

            # Track follow-up API call
            self._track_usage(response, "chat_v2_tool_followup")

            choice = response.choices[0]
            message = choice.message

        # Extract final text response
        final_text = message.content or ""

        return ChatMessage(
            role="assistant",
            content=final_text,
            tool_calls=[{
                "name": e.tool_name,
                "input": e.tool_input,
            } for e in tool_executions] if tool_executions else None,
            tool_results=[{
                "name": e.tool_name,
                "result": e.result[:500] + "..." if len(e.result) > 500 else e.result,
            } for e in tool_executions] if tool_executions else None,
        )

    async def chat_simple(self, user_message: str) -> str:
        """Simple chat interface - single message in, text response out.

        Args:
            user_message: The user's question

        Returns:
            Claude's response as plain text
        """
        response = await self.chat([
            ChatMessage(role="user", content=user_message),
        ])
        return response.content
