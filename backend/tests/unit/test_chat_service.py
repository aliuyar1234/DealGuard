"""Unit tests for Chat Service v2.

Tests both Anthropic and DeepSeek client integration.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Set required env vars
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-encryption-32chars"


class TestChatServiceInitialization:
    """Test ChatService initialization with different providers."""

    def test_init_anthropic_provider(self):
        """Test initialization with Anthropic provider."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="anthropic",
                anthropic_api_key="sk-ant-test-key",
                anthropic_model="claude-3-sonnet",
                anthropic_max_tokens=4096,
            )

            from dealguard.domain.chat.service_v2 import ChatService

            service = ChatService(
                organization_id=uuid4(),
                user_settings={"ai_provider": "anthropic", "anthropic_api_key": "sk-ant-user-key"},
            )

            assert service.ai_provider == "anthropic"
            from dealguard.domain.chat.anthropic_handler import AnthropicHandler
            assert isinstance(service.handler, AnthropicHandler)

    def test_init_deepseek_provider(self):
        """Test initialization with DeepSeek provider."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="deepseek",
                deepseek_api_key="sk-deepseek-test",
                deepseek_model="deepseek-chat",
                deepseek_base_url="https://api.deepseek.com",
                anthropic_max_tokens=4096,
            )

            from dealguard.domain.chat.service_v2 import ChatService

            service = ChatService(
                organization_id=uuid4(),
                user_settings={"ai_provider": "deepseek", "deepseek_api_key": "sk-deepseek-user"},
            )

            assert service.ai_provider == "deepseek"
            from dealguard.domain.chat.deepseek_handler import DeepSeekHandler
            assert isinstance(service.handler, DeepSeekHandler)

    def test_init_missing_anthropic_key_raises(self):
        """Test that missing Anthropic key raises ValueError."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="anthropic",
                anthropic_api_key="",
                anthropic_model="claude-3-sonnet",
            )

            from dealguard.domain.chat.service_v2 import ChatService

            with pytest.raises(ValueError) as exc_info:
                ChatService(organization_id=uuid4())

            assert "Anthropic API Key" in str(exc_info.value)

    def test_init_missing_deepseek_key_raises(self):
        """Test that missing DeepSeek key raises ValueError."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="deepseek",
                deepseek_api_key="",
                deepseek_model="deepseek-chat",
            )

            from dealguard.domain.chat.service_v2 import ChatService

            with pytest.raises(ValueError) as exc_info:
                ChatService(organization_id=uuid4())

            assert "DeepSeek API Key" in str(exc_info.value)

    def test_init_unknown_provider_raises(self):
        """Test that unknown provider raises ValueError."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="unknown_provider",
            )

            from dealguard.domain.chat.service_v2 import ChatService

            with pytest.raises(ValueError) as exc_info:
                ChatService(
                    organization_id=uuid4(),
                    user_settings={"ai_provider": "unknown_provider"},
                )

            assert "Unbekannter AI Provider" in str(exc_info.value)


class TestToolConversion:
    """Test tool definition conversion for different APIs."""

    def test_convert_tools_for_anthropic(self):
        """Test tool conversion to Anthropic format."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="anthropic",
                anthropic_api_key="sk-ant-test",
                anthropic_model="claude-3-sonnet",
                anthropic_max_tokens=4096,
            )

            with patch("dealguard.domain.chat.service_v2.get_tool_definitions") as mock_tools:
                mock_tools.return_value = [
                    {
                        "name": "dealguard_search_ris",
                        "description": "Search Austrian laws",
                        "input_schema": {"type": "object", "properties": {}},
                    }
                ]

                from dealguard.domain.chat.service_v2 import ChatService

                service = ChatService(organization_id=uuid4())
                tools = service.handler.tools

                assert len(tools) == 1
                assert tools[0]["name"] == "dealguard_search_ris"
                assert "input_schema" in tools[0]

    def test_convert_tools_for_openai(self):
        """Test tool conversion to OpenAI format."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="deepseek",
                deepseek_api_key="sk-deepseek-test",
                deepseek_model="deepseek-chat",
                deepseek_base_url="https://api.deepseek.com",
                anthropic_max_tokens=4096,
            )

            with patch("dealguard.domain.chat.service_v2.get_tool_definitions") as mock_tools:
                mock_tools.return_value = [
                    {
                        "name": "dealguard_search_ris",
                        "description": "Search Austrian laws",
                        "input_schema": {"type": "object", "properties": {}},
                    }
                ]

                from dealguard.domain.chat.service_v2 import ChatService

                service = ChatService(organization_id=uuid4())
                tools = service.handler.tools

                assert len(tools) == 1
                assert tools[0]["type"] == "function"
                assert tools[0]["function"]["name"] == "dealguard_search_ris"
                assert "parameters" in tools[0]["function"]


class TestCostTracking:
    """Test cost tracking for API calls."""

    def test_track_usage_anthropic(self):
        """Test usage tracking for Anthropic responses."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="anthropic",
                anthropic_api_key="sk-ant-test",
                anthropic_model="claude-3-sonnet",
                anthropic_max_tokens=4096,
            )

            with patch("dealguard.domain.chat.service_v2.get_tool_definitions") as mock_tools:
                mock_tools.return_value = []

                with patch("dealguard.domain.chat.service_v2._cost_tracker") as mock_tracker:
                    from dealguard.domain.chat.service_v2 import ChatService

                    service = ChatService(organization_id=uuid4())

                    # Mock Anthropic response
                    mock_response = MagicMock()
                    mock_response.usage.input_tokens = 100
                    mock_response.usage.output_tokens = 50

                    service._track_usage(mock_response, "test_action")

                    mock_tracker.record.assert_called_once()
                    call_args = mock_tracker.record.call_args
                    assert call_args.kwargs["input_tokens"] == 100
                    assert call_args.kwargs["output_tokens"] == 50

    def test_track_usage_deepseek(self):
        """Test usage tracking for DeepSeek/OpenAI responses."""
        with patch("dealguard.domain.chat.service_v2.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ai_provider="deepseek",
                deepseek_api_key="sk-deepseek-test",
                deepseek_model="deepseek-chat",
                deepseek_base_url="https://api.deepseek.com",
                anthropic_max_tokens=4096,
            )

            with patch("dealguard.domain.chat.service_v2.get_tool_definitions") as mock_tools:
                mock_tools.return_value = []

                with patch("dealguard.domain.chat.service_v2._cost_tracker") as mock_tracker:
                    from dealguard.domain.chat.service_v2 import ChatService

                    service = ChatService(organization_id=uuid4())

                    # Mock OpenAI response
                    mock_response = MagicMock()
                    mock_response.usage.prompt_tokens = 200
                    mock_response.usage.completion_tokens = 100

                    service._track_usage(mock_response, "test_action")

                    mock_tracker.record.assert_called_once()
                    call_args = mock_tracker.record.call_args
                    assert call_args.kwargs["input_tokens"] == 200
                    assert call_args.kwargs["output_tokens"] == 100


class TestChatMessage:
    """Test ChatMessage dataclass."""

    def test_chat_message_creation(self):
        """Test creating a ChatMessage."""
        from dealguard.domain.chat.service_v2 import ChatMessage

        msg = ChatMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.tool_calls is None
        assert msg.tool_results is None

    def test_chat_message_with_tools(self):
        """Test ChatMessage with tool information."""
        from dealguard.domain.chat.service_v2 import ChatMessage

        msg = ChatMessage(
            role="assistant",
            content="Here's the result",
            tool_calls=[{"name": "search_ris", "input": {"query": "ABGB"}}],
            tool_results=[{"name": "search_ris", "result": "Found 10 results"}],
        )

        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_results is not None
        assert len(msg.tool_results) == 1


class TestToolExecution:
    """Test ToolExecution dataclass."""

    def test_tool_execution_success(self):
        """Test successful tool execution."""
        from dealguard.domain.chat.service_v2 import ToolExecution

        execution = ToolExecution(
            tool_name="dealguard_search_ris",
            tool_input={"query": "Mietrecht"},
            result="Found 5 matching laws",
        )

        assert execution.tool_name == "dealguard_search_ris"
        assert execution.error is None

    def test_tool_execution_error(self):
        """Test tool execution with error."""
        from dealguard.domain.chat.service_v2 import ToolExecution

        execution = ToolExecution(
            tool_name="dealguard_search_ris",
            tool_input={"query": "test"},
            result="",
            error="API timeout",
        )

        assert execution.error == "API timeout"
        assert execution.result == ""
