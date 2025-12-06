"""AI cost tracking for billing and monitoring."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from dealguard.shared.context import get_optional_tenant_context
from dealguard.shared.logging import get_logger

logger = get_logger(__name__)


# AI pricing per 1M tokens (as of December 2024)
MODEL_PRICING = {
    # Anthropic
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    # DeepSeek (much cheaper - great for testing!)
    "deepseek-chat": {"input": 0.14, "output": 0.28},  # ~20x cheaper than Claude Sonnet
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}


@dataclass
class UsageRecord:
    """Record of AI usage for billing."""

    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_cents: float
    action: str
    resource_id: UUID | None
    organization_id: UUID | None
    timestamp: datetime


class CostTracker:
    """Tracks AI usage and costs.

    Records every API call for:
    - Billing (per-organization usage)
    - Cost monitoring
    - Analytics
    """

    def __init__(self) -> None:
        # In-memory buffer for batch inserts
        self._buffer: list[UsageRecord] = []
        self._buffer_size = 100  # Flush after 100 records

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost in cents for token usage."""
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            logger.warning("unknown_model_pricing", model=model)
            # Use default pricing
            pricing = {"input": 5.00, "output": 15.00}

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        # Convert to cents
        return (input_cost + output_cost) * 100

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        action: str,
        resource_id: UUID | None = None,
    ) -> UsageRecord:
        """Record AI usage.

        Args:
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            action: Type of action (e.g., "contract_analysis")
            resource_id: Optional ID of the resource being processed

        Returns:
            UsageRecord for reference
        """
        cost_cents = self.calculate_cost(model, input_tokens, output_tokens)

        # Get organization from context if available
        ctx = get_optional_tenant_context()
        organization_id = ctx.organization_id if ctx else None

        record = UsageRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_cents=cost_cents,
            action=action,
            resource_id=resource_id,
            organization_id=organization_id,
            timestamp=datetime.now(timezone.utc),
        )

        logger.info(
            "ai_usage_recorded",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=round(cost_cents, 4),
            action=action,
            organization_id=str(organization_id) if organization_id else None,
        )

        self._buffer.append(record)

        # TODO: Flush to database when buffer is full
        # if len(self._buffer) >= self._buffer_size:
        #     await self._flush()

        return record

    async def get_monthly_usage(
        self,
        organization_id: UUID,
        year: int,
        month: int,
    ) -> dict:
        """Get monthly usage statistics for an organization.

        TODO: Implement database query
        """
        # Placeholder - will query usage_logs table
        return {
            "total_cost_cents": 0,
            "total_tokens": 0,
            "analysis_count": 0,
            "by_action": {},
        }
