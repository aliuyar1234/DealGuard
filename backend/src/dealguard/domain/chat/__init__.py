"""Chat domain module.

This module provides the chat service for interacting with Claude
and executing tools against Austrian legal data and DealGuard's database.

Modules:
- service_v2: Main ChatService orchestrator
- tool_executor: MCP tool execution with strategy pattern
- anthropic_handler: Anthropic/Claude API handling
- deepseek_handler: DeepSeek (OpenAI-compatible) API handling
"""

from dealguard.domain.chat.anthropic_handler import AnthropicHandler
from dealguard.domain.chat.deepseek_handler import DeepSeekHandler
from dealguard.domain.chat.service_v2 import ChatService, ToolExecution
from dealguard.domain.chat.tool_executor import ToolExecutor
from dealguard.domain.chat.types import ChatMessage

__all__ = [
    "ChatService",
    "ChatMessage",
    "ToolExecution",
    "ToolExecutor",
    "AnthropicHandler",
    "DeepSeekHandler",
]
