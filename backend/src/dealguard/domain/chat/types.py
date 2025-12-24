"""Shared chat domain types.

Keep these types small and provider-agnostic so both Anthropic and OpenAI/
DeepSeek handlers can reuse them without circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


@dataclass
class ChatMessage:
    """A message in the chat conversation."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tool_calls: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None

