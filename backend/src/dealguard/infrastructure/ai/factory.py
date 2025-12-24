"""AI client factory - returns the configured AI provider."""

from functools import lru_cache
from typing import Protocol
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


@lru_cache(maxsize=1)
def get_cost_tracker() -> CostTracker:
    """Get a shared CostTracker instance."""
    return CostTracker()


def _build_ai_client(
    *,
    cost_tracker: CostTracker,
) -> AnthropicClient | DeepSeekClient:
    settings = get_settings()
    provider = settings.ai_provider

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY ist nicht konfiguriert")
        logger.info(
            "using_ai_provider",
            provider="deepseek",
            model=settings.deepseek_model,
        )
        return DeepSeekClient(cost_tracker=cost_tracker)

    # Default to Anthropic
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY ist nicht konfiguriert")
    logger.info(
        "using_ai_provider",
        provider="anthropic",
        model=settings.anthropic_model,
    )
    return AnthropicClient(cost_tracker=cost_tracker)


@lru_cache(maxsize=1)
def _get_cached_ai_client() -> AnthropicClient | DeepSeekClient:
    return _build_ai_client(cost_tracker=get_cost_tracker())


def get_ai_client(
    cost_tracker: CostTracker | None = None,
) -> AnthropicClient | DeepSeekClient:
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
    if cost_tracker is not None:
        return _build_ai_client(cost_tracker=cost_tracker)
    return _get_cached_ai_client()


async def close_ai_client() -> None:
    """Close and clear the shared AI client (used at app shutdown)."""
    if _get_cached_ai_client.cache_info().currsize:
        client = _get_cached_ai_client()
        await client.close()
    _get_cached_ai_client.cache_clear()
    get_cost_tracker.cache_clear()
