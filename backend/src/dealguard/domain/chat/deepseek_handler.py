"""DeepSeek API handler for chat service.

This module handles DeepSeek-specific API calls and response processing.
DeepSeek uses an OpenAI-compatible API.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

import openai
from openai import AsyncOpenAI

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
        tools: list[dict],
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

    async def call_api(self, messages: list[dict]):
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
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        try:
            return await self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=full_messages,
                tools=self.tools if self.tools else None,
            )
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            # Re-raise for potential retry handling
            raise e

    async def process_response(
        self,
        response,
        messages: list[dict],
        track_usage_fn: callable,
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

        # Get the first choice
        choice = response.choices[0]
        message = choice.message

        # Check if there are tool calls to execute
        while choice.finish_reason == "tool_calls" and message.tool_calls:
            # Execute all tools
            tool_results = []
            for tool_call in message.tool_calls:
                # Parse the function arguments
                try:
                    tool_input = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_input = {}

                execution = await self.tool_executor.execute(
                    tool_call.function.name,
                    tool_input,
                )
                tool_executions.append(execution)

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": execution.result if not execution.error else f"Error: {execution.error}",
                })

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

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
            tool_calls=[{
                "name": e.tool_name,
                "input": e.tool_input,
            } for e in tool_executions] if tool_executions else None,
            tool_results=[{
                "name": e.tool_name,
                "result": e.result[:500] + "..." if len(e.result) > 500 else e.result,
            } for e in tool_executions] if tool_executions else None,
        )
