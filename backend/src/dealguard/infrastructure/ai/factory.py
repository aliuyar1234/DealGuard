"""AI client factory - returns the configured AI provider."""

from typing import Protocol, Union
from uuid import UUID

from dealguard.config import get_settings
from dealguard.infrastructure.ai.client import AIResponse, AnthropicClient
from dealguard.infrastructure.ai.cost_tracker import CostTracker
from dealguard.infrastructure.ai.deepseek_client import DeepSeekClient
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


class AIClient(Protocol):
    """Protocol for AI clients."""

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.1,
        action: str = "ai_completion",
        resource_id: UUID | None = None,
    ) -> AIResponse: ...

    async def analyze_contract(
        self,
        contract_text: str,
        contract_type: str | None,
        resource_id: UUID | None = None,
    ) -> AIResponse: ...


def get_ai_client(cost_tracker: CostTracker | None = None) -> Union[AnthropicClient, DeepSeekClient]:
    """Get the configured AI client based on settings.

    Returns:
        Either AnthropicClient or DeepSeekClient based on AI_PROVIDER env var.

    Usage:
        # In .env:
        AI_PROVIDER=deepseek  # or "anthropic"
        DEEPSEEK_API_KEY=sk-...

        # In code:
        client = get_ai_client()
        response = await client.analyze_contract(text, contract_type)
    """
    settings = get_settings()
    provider = settings.ai_provider

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY ist nicht konfiguriert")
        logger.info("using_ai_provider", provider="deepseek", model=settings.deepseek_model)
        return DeepSeekClient(cost_tracker=cost_tracker)

    # Default to Anthropic
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY ist nicht konfiguriert")
    logger.info("using_ai_provider", provider="anthropic", model=settings.anthropic_model)
    return AnthropicClient(cost_tracker=cost_tracker)
