"""DeepSeek API handler for chat service.

This module handles DeepSeek-specific API calls and response processing.
DeepSeek uses an OpenAI-compatible API.
"""

import asyncio
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import openai
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion_message_function_tool_call_param import Function

from dealguard.domain.chat.tool_executor import ToolExecution, ToolExecutor
from dealguard.domain.chat.types import ChatMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ToolCall:
    id: str
    name: str
    arguments: str


class DeepSeekHandler:
    """Handles DeepSeek API interactions (OpenAI-compatible).

    Includes:
    - API calls
    - Tool execution loop
    - Response processing
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        max_tokens: int,
        system_prompt: str,
        tools: list[ChatCompletionToolParam],
        tool_executor: ToolExecutor,
    ):
        """Initialize the DeepSeek handler.

        Args:
            client: OpenAI async client configured for DeepSeek
            model: Model name (e.g., deepseek-chat)
            max_tokens: Maximum tokens for response
            system_prompt: System prompt for the conversation
            tools: Tool definitions in OpenAI format
            tool_executor: Executor for MCP tools
        """
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_executor = tool_executor

    async def call_api(self, messages: list[ChatCompletionMessageParam]) -> ChatCompletion:
        """Call OpenAI-compatible API (DeepSeek).

        Args:
            messages: List of messages in OpenAI format

        Returns:
            OpenAI ChatCompletion response

        Raises:
            openai.APITimeoutError: On timeout
            openai.APIConnectionError: On connection error
        """
        # Add system message to the beginning
        system_message: ChatCompletionSystemMessageParam = ChatCompletionSystemMessageParam(
            role="system",
            content=self.system_prompt,
        )
        full_messages: list[ChatCompletionMessageParam] = [system_message, *messages]

        try:
            if self.tools:
                return await self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=full_messages,
                    tools=self.tools,
                )

            return await self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=full_messages,
            )
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            # Re-raise for potential retry handling
            raise e

    async def process_response(
        self,
        response: ChatCompletion,
        messages: list[ChatCompletionMessageParam],
        track_usage_fn: Callable[[Any, str], None],
    ) -> ChatMessage:
        """Process OpenAI/DeepSeek response, executing tools if needed.

        Args:
            response: Initial API response
            messages: Conversation messages (will be modified)
            track_usage_fn: Function to track API usage

        Returns:
            Final ChatMessage with response content
        """
        tool_executions: list[ToolExecution] = []

        max_tool_concurrency = int(os.getenv("DEALGUARD_CHAT_TOOL_CONCURRENCY", "4"))
        max_tool_concurrency = max(1, min(16, max_tool_concurrency))

        # Get the first choice
        choice = response.choices[0]
        message = choice.message

        # Check if there are tool calls to execute
        while choice.finish_reason == "tool_calls" and message.tool_calls:
            tool_calls: list[_ToolCall] = []
            for tc in message.tool_calls:
                if isinstance(tc, ChatCompletionMessageToolCall):
                    tool_calls.append(
                        _ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        )
                    )
                    continue

                tc_id = getattr(tc, "id", None)
                tc_function = getattr(tc, "function", None)
                tc_name = getattr(tc_function, "name", None)
                tc_arguments = getattr(tc_function, "arguments", None)
                if (
                    isinstance(tc_id, str)
                    and isinstance(tc_name, str)
                    and isinstance(tc_arguments, str)
                ):
                    tool_calls.append(_ToolCall(id=tc_id, name=tc_name, arguments=tc_arguments))
            if not tool_calls:
                break
            semaphore = asyncio.Semaphore(min(max_tool_concurrency, len(tool_calls)))

            async def _execute_tool(
                tool_call: _ToolCall,
                *,
                _semaphore: asyncio.Semaphore = semaphore,
            ) -> ToolExecution:
                await _semaphore.acquire()
                try:
                    try:
                        tool_input = json.loads(tool_call.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    return await self.tool_executor.execute(
                        tool_call.name,
                        tool_input,
                    )
                finally:
                    _semaphore.release()

            executions = await asyncio.gather(*(_execute_tool(tc) for tc in tool_calls))
            tool_executions.extend(executions)

            tool_results = [
                ChatCompletionToolMessageParam(
                    role="tool",
                    tool_call_id=tc.id,
                    content=execution.result
                    if not execution.error
                    else f"Error: {execution.error}",
                )
                for tc, execution in zip(tool_calls, executions, strict=True)
            ]

            # Add assistant message with tool calls
            tool_call_params: list[ChatCompletionMessageToolCallParam] = [
                ChatCompletionMessageToolCallParam(
                    id=tc.id,
                    type="function",
                    function=Function(
                        name=tc.name,
                        arguments=tc.arguments,
                    ),
                )
                for tc in tool_calls
            ]
            messages.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=message.content or "",
                    tool_calls=tool_call_params,
                )
            )

            # Add tool results
            messages.extend(tool_results)

            # Call API again with tool results
            response = await self.call_api(messages)

            # Track follow-up API call
            track_usage_fn(response, "chat_v2_tool_followup")

            choice = response.choices[0]
            message = choice.message

        # Extract final text response
        final_text = message.content or ""

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
