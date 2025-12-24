"""Anthropic/Claude API handler for chat service.

This module handles Anthropic-specific API calls and response processing.
"""

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any, cast

import anthropic
from anthropic.types import MessageParam, TextBlock, ToolParam, ToolResultBlockParam, ToolUseBlock
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from dealguard.domain.chat.tool_executor import ToolExecution, ToolExecutor
from dealguard.domain.chat.types import ChatMessage

logger = logging.getLogger(__name__)

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
        tools: list[ToolParam],
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
    async def call_api(self, messages: list[MessageParam]) -> anthropic.types.Message:
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
        messages: list[MessageParam],
        track_usage_fn: Callable[[Any, str], None],
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

        max_tool_concurrency = int(os.getenv("DEALGUARD_CHAT_TOOL_CONCURRENCY", "4"))
        max_tool_concurrency = max(1, min(16, max_tool_concurrency))

        # Check if there are tool calls to execute
        while response.stop_reason == "tool_use":
            # Find all tool use blocks
            tool_calls: list[ToolUseBlock] = [
                block for block in response.content if isinstance(block, ToolUseBlock)
            ]

            if not tool_calls:
                break

            semaphore = asyncio.Semaphore(min(max_tool_concurrency, len(tool_calls)))

            async def _execute_tool(
                tool_call: ToolUseBlock,
                *,
                _semaphore: asyncio.Semaphore = semaphore,
            ) -> ToolExecution:
                await _semaphore.acquire()
                try:
                    return await self.tool_executor.execute(tool_call.name, tool_call.input)
                finally:
                    _semaphore.release()

            executions = await asyncio.gather(*(_execute_tool(tc) for tc in tool_calls))
            tool_executions.extend(executions)

            tool_results: list[ToolResultBlockParam] = [
                ToolResultBlockParam(
                    type="tool_result",
                    tool_use_id=tc.id,
                    content=execution.result
                    if not execution.error
                    else f"Error: {execution.error}",
                    is_error=bool(execution.error),
                )
                for tc, execution in zip(tool_calls, executions, strict=True)
            ]

            # Add assistant message with tool calls
            messages.append(
                MessageParam(
                    role="assistant",
                    content=cast(Any, response.content),
                )
            )

            # Add tool results
            messages.append(
                MessageParam(
                    role="user",
                    content=tool_results,
                )
            )

            # Call Claude again with tool results (with retry logic)
            response = await self.call_api(messages)

            # Track follow-up API call
            track_usage_fn(response, "chat_v2_tool_followup")

        # Extract final text response
        for block in response.content:
            if isinstance(block, TextBlock):
                final_text += block.text

        return ChatMessage(
            role="assistant",
            content=final_text,
            tool_calls=[
                {
                    "name": e.tool_name,
                    "input": e.tool_input,
                }
                for e in tool_executions
            ]
            if tool_executions
            else None,
            tool_results=[
                {
                    "name": e.tool_name,
                    "result": e.result[:500] + "..." if len(e.result) > 500 else e.result,
                }
                for e in tool_executions
            ]
            if tool_executions
            else None,
        )
