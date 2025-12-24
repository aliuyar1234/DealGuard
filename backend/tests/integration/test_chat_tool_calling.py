"""Integration test for chat tool-calling flow."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from dealguard.domain.chat.tool_executor import ToolExecution

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-encryption-32chars")


@pytest.mark.asyncio
async def test_chat_service_tool_calling_deepseek():
    with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            ai_provider="deepseek",
            deepseek_api_key="sk-test",
            deepseek_model="deepseek-chat",
            deepseek_base_url="https://api.deepseek.test",
            anthropic_max_tokens=256,
        )

        with patch("dealguard.domain.chat.service_v2.get_tool_definitions") as mock_tools:
            mock_tools.return_value = [
                {
                    "name": "dealguard_search_ris",
                    "description": "Search Austrian laws",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ]

            with patch("dealguard.domain.chat.service_v2.AsyncOpenAI"):
                from dealguard.domain.chat.service_v2 import ChatService, ChatMessage

                service = ChatService(
                    organization_id=uuid4(),
                    user_settings={
                        "ai_provider": "deepseek",
                        "deepseek_api_key": "sk-user",
                    },
                )

                service.handler.tool_executor.execute = AsyncMock(
                    return_value=ToolExecution(
                        tool_name="dealguard_search_ris",
                        tool_input={"query": "ABGB"},
                        result="tool-result",
                    )
                )

                tool_call = SimpleNamespace(
                    id="call_1",
                    function=SimpleNamespace(
                        name="dealguard_search_ris",
                        arguments='{"query": "ABGB"}',
                    ),
                )

                first_response = SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            finish_reason="tool_calls",
                            message=SimpleNamespace(
                                content="Tool call requested",
                                tool_calls=[tool_call],
                            ),
                        )
                    ],
                    usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                )

                second_response = SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            finish_reason="stop",
                            message=SimpleNamespace(
                                content="Final answer",
                                tool_calls=None,
                            ),
                        )
                    ],
                    usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
                )

                service.handler.call_api = AsyncMock(
                    side_effect=[first_response, second_response]
                )

                result = await service.chat(
                    [ChatMessage(role="user", content="Test")]
                )

                assert result.content == "Final answer"
                assert result.tool_calls == [
                    {"name": "dealguard_search_ris", "input": {"query": "ABGB"}}
                ]
                assert result.tool_results is not None
                assert result.tool_results[0]["result"] == "tool-result"
                assert service.handler.call_api.await_count == 2
