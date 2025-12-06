"""Anthropic/Claude API handler for chat service.

This module handles Anthropic-specific API calls and response processing.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from dealguard.domain.chat.tool_executor import ToolExecutor, ToolExecution

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A message in the chat conversation."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None


class AnthropicHandler:
    """Handles Anthropic/Claude API interactions.

    Includes:
    - API calls with retry logic
    - Tool execution loop
    - Response processing
    """

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        max_tokens: int,
        system_prompt: str,
        tools: list[dict],
        tool_executor: ToolExecutor,
    ):
        """Initialize the Anthropic handler.

        Args:
            client: Anthropic async client
            model: Model name (e.g., claude-3-opus)
            max_tokens: Maximum tokens for response
            system_prompt: System prompt for the conversation
            tools: Tool definitions in Anthropic format
            tool_executor: Executor for MCP tools
        """
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_executor = tool_executor

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((anthropic.APITimeoutError, anthropic.APIConnectionError)),
        reraise=True,
    )
    async def call_api(self, messages: list[dict]) -> anthropic.types.Message:
        """Call Anthropic API with retry logic for transient errors.

        Args:
            messages: List of messages in Anthropic format

        Returns:
            Anthropic Message response
        """
        return await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            tools=self.tools,
            messages=messages,
        )

    async def process_response(
        self,
        response: anthropic.types.Message,
        messages: list[dict],
        track_usage_fn: callable,
    ) -> ChatMessage:
        """Process Anthropic/Claude's response, executing tools if needed.

        Args:
            response: Initial API response
            messages: Conversation messages (will be modified)
            track_usage_fn: Function to track API usage

        Returns:
            Final ChatMessage with response content
        """
        tool_executions: list[ToolExecution] = []
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
                execution = await self.tool_executor.execute(
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
            response = await self.call_api(messages)

            # Track follow-up API call
            track_usage_fn(response, "chat_v2_tool_followup")

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
