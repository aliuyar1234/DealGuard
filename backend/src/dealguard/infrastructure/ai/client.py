"""Anthropic Claude API client wrapper."""

import time
from dataclasses import dataclass
from uuid import UUID

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from dealguard.config import get_settings
from dealguard.infrastructure.ai.cost_tracker import CostTracker
from dealguard.shared.exceptions import AIRateLimitError, AIServiceError
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AIResponse:
    """Response from AI completion."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_cents: float
    latency_ms: float


class AnthropicClient:
    """Wrapper for Anthropic Claude API.

    Features:
    - Automatic cost tracking
    - Retry logic with exponential backoff
    - Structured logging
    - Latency tracking
    - Async-first design (non-blocking)
    """

    def __init__(
        self,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        settings = get_settings()
        # Use async client to avoid blocking the event loop
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.default_model = settings.anthropic_model
        self.default_max_tokens = settings.anthropic_max_tokens
        self.cost_tracker = cost_tracker or CostTracker()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.1,
        action: str = "ai_completion",
        resource_id: UUID | None = None,
    ) -> AIResponse:
        """Send a completion request to Claude.

        Args:
            system_prompt: System prompt for context
            user_prompt: User message/prompt
            model: Model to use (default from settings)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            action: Action type for cost tracking
            resource_id: Resource ID for cost tracking

        Returns:
            AIResponse with content and usage info

        Raises:
            AIRateLimitError: If rate limited
            AIServiceError: For other API errors
        """
        model = model or self.default_model
        max_tokens = max_tokens or self.default_max_tokens
        start_time = time.monotonic()

        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            latency_ms = (time.monotonic() - start_time) * 1000

            # Track usage
            usage_record = self.cost_tracker.record(
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                action=action,
                resource_id=resource_id,
            )

            logger.debug(
                "ai_completion_success",
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=round(latency_ms, 2),
            )

            return AIResponse(
                content=response.content[0].text,
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=usage_record.total_tokens,
                cost_cents=usage_record.cost_cents,
                latency_ms=latency_ms,
            )

        except anthropic.RateLimitError as e:
            logger.warning("ai_rate_limited", error=str(e))
            raise AIRateLimitError("AI-Dienst ist überlastet. Bitte später erneut versuchen.")

        except anthropic.APIStatusError as e:
            logger.error("ai_api_error", status=e.status_code, error=str(e))
            raise AIServiceError(f"AI-Dienst Fehler: {e.status_code}")

        except anthropic.APIConnectionError as e:
            logger.error("ai_connection_error", error=str(e))
            raise AIServiceError("Verbindung zum AI-Dienst fehlgeschlagen")

        except Exception as e:
            logger.exception("ai_unexpected_error", error=str(e))
            raise AIServiceError(f"Unerwarteter AI-Fehler: {e}")

    async def analyze_contract(
        self,
        contract_text: str,
        contract_type: str | None,
        resource_id: UUID | None = None,
    ) -> AIResponse:
        """Analyze a contract using the contract analysis prompt.

        This is a convenience method that uses the versioned prompt system.
        """
        from dealguard.infrastructure.ai.prompts.contract_analysis_v1 import (
            ContractAnalysisPromptV1,
        )

        prompt = ContractAnalysisPromptV1()
        system = prompt.render_system()
        user = prompt.render_user(
            contract_text=contract_text,
            contract_type=contract_type,
        )

        return await self.complete(
            system_prompt=system,
            user_prompt=user,
            action="contract_analysis",
            resource_id=resource_id,
            temperature=0.1,  # Low temperature for consistent analysis
        )
