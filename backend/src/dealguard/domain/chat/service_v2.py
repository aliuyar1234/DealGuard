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

import logging
from typing import AsyncIterator
from uuid import UUID

import anthropic
from openai import AsyncOpenAI

from dealguard.config import get_settings
from dealguard.infrastructure.ai.cost_tracker import CostTracker
from dealguard.mcp.server_v2 import get_tool_definitions

from dealguard.domain.chat.tool_executor import ToolExecutor, ToolExecution
from dealguard.domain.chat.anthropic_handler import AnthropicHandler, ChatMessage
from dealguard.domain.chat.deepseek_handler import DeepSeekHandler

logger = logging.getLogger(__name__)

# Shared cost tracker instance
_cost_tracker = CostTracker()

# Re-export for backwards compatibility
__all__ = ["ChatService", "ChatMessage", "ToolExecution"]

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
        self.max_tokens = settings.anthropic_max_tokens

        # Create tool executor
        tool_executor = ToolExecutor(organization_id)

        if self.ai_provider == "anthropic":
            self._init_anthropic(api_key, user_settings, settings, tool_executor)
        elif self.ai_provider == "deepseek":
            self._init_deepseek(user_settings, settings, tool_executor)
        else:
            raise ValueError(f"Unbekannter AI Provider: {self.ai_provider}")

    def _init_anthropic(
        self,
        api_key: str | None,
        user_settings: dict,
        settings,
        tool_executor: ToolExecutor,
    ) -> None:
        """Initialize Anthropic/Claude handler."""
        self.api_key = api_key or user_settings.get("anthropic_api_key") or settings.anthropic_api_key
        self.model = settings.anthropic_model

        if not self.api_key:
            raise ValueError(
                "Anthropic API Key nicht konfiguriert. "
                "Bitte in den Einstellungen hinterlegen."
            )

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        tools = self._convert_tools_for_anthropic()

        self.handler = AnthropicHandler(
            client=client,
            model=self.model,
            max_tokens=self.max_tokens,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            tool_executor=tool_executor,
        )
        self.deepseek_handler = None

    def _init_deepseek(
        self,
        user_settings: dict,
        settings,
        tool_executor: ToolExecutor,
    ) -> None:
        """Initialize DeepSeek handler."""
        self.api_key = user_settings.get("deepseek_api_key") or settings.deepseek_api_key
        self.model = settings.deepseek_model

        if not self.api_key:
            raise ValueError(
                "DeepSeek API Key nicht konfiguriert. "
                "Bitte in den Einstellungen hinterlegen."
            )

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=settings.deepseek_base_url,
        )
        tools = self._convert_tools_for_openai()

        self.handler = DeepSeekHandler(
            client=client,
            model=self.model,
            max_tokens=self.max_tokens,
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            tool_executor=tool_executor,
        )

    def _convert_tools_for_anthropic(self) -> list[dict]:
        """Convert tool definitions to Anthropic format."""
        tool_defs = get_tool_definitions()
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            for tool in tool_defs
        ]

    def _convert_tools_for_openai(self) -> list[dict]:
        """Convert tool definitions to OpenAI format."""
        tool_defs = get_tool_definitions()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in tool_defs
        ]

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

        # Call API and track usage
        if self.ai_provider == "anthropic":
            response = await self.handler.call_api(api_messages)
            self._track_usage(response, "chat_v2_initial")
            return await self.handler.process_response(response, api_messages, self._track_usage)
        else:
            response = await self.handler.call_api(api_messages)
            self._track_usage(response, "chat_v2_initial")
            return await self.handler.process_response(response, api_messages, self._track_usage)

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
