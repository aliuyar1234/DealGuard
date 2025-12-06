"""Chat API v2 with Claude Tool-Calling.

This API provides a chat interface that integrates:
- Austrian legal data (RIS)
- Insolvency data (Ediktsdatei)
- User's contracts, partners, and deadlines
"""

import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.api.deps import get_current_user, get_db
from dealguard.api.ratelimit import limiter, RATE_LIMIT_AI
from dealguard.domain.chat import ChatService, ChatMessage
from dealguard.infrastructure.auth.provider import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat/v2", tags=["chat"])


# ----- Request/Response Models -----


class MessageInput(BaseModel):
    """A single message in the conversation."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    messages: list[MessageInput] = Field(
        ...,
        min_length=1,
        description="List of messages in the conversation",
    )


class ToolCall(BaseModel):
    """Information about a tool that was called."""

    name: str
    input: dict


class ToolResult(BaseModel):
    """Result of a tool execution (summarized)."""

    name: str
    result: str


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    message: str = Field(..., description="Claude's response")
    tool_calls: list[ToolCall] | None = Field(
        None,
        description="Tools that were called during the response",
    )
    tool_results: list[ToolResult] | None = Field(
        None,
        description="Summarized results from tool executions",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SimpleMessageRequest(BaseModel):
    """Simple request with just a message."""

    message: str = Field(..., min_length=1, max_length=10000)


# ----- API Endpoints -----


async def get_user_settings(db: AsyncSession, user_id: str) -> dict:
    """Get user settings from database with decrypted API keys."""
    from sqlalchemy import text
    from dealguard.shared.crypto import decrypt_secret, is_encrypted

    result = await db.execute(
        text("SELECT settings FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    )
    row = result.fetchone()
    if row and row[0]:
        settings = dict(row[0])
        # Decrypt API keys if they are encrypted
        for key in ["anthropic_api_key", "deepseek_api_key"]:
            if key in settings and settings[key] and is_encrypted(settings[key]):
                try:
                    settings[key] = decrypt_secret(settings[key])
                except ValueError:
                    logger.warning(f"Failed to decrypt {key} for user {user_id}")
                    settings[key] = None
        return settings
    return {}


@router.post("", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT_AI)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Send a message and get a response from DealGuard AI.

    The AI has access to:
    - RIS (Austrian legal database) for law lookups
    - Ediktsdatei for insolvency checks
    - Your contracts, partners, and deadlines

    Example messages:
    - "Welche Kündigungsfrist gilt laut ABGB für Mietverträge?"
    - "Ist die Firma ABC GmbH insolvent?"
    - "Welche Fristen habe ich in den nächsten 30 Tagen?"
    """
    try:
        # Get organization ID from user
        org_id = current_user.organization_id
        user_id = current_user.id

        # Load user settings (for API keys)
        user_settings = await get_user_settings(db, user_id)

        # Initialize chat service with user settings
        service = ChatService(organization_id=org_id, user_settings=user_settings)

        # Convert messages
        chat_messages = [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in chat_request.messages
        ]

        # Get response
        response = await service.chat(chat_messages)

        return ChatResponse(
            message=response.content,
            tool_calls=[
                ToolCall(name=tc["name"], input=tc["input"])
                for tc in response.tool_calls
            ] if response.tool_calls else None,
            tool_results=[
                ToolResult(name=tr["name"], result=tr["result"])
                for tr in response.tool_results
            ] if response.tool_results else None,
        )

    except ValueError as e:
        logger.error(f"Chat configuration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=f"Chat-Fehler: {str(e)}")


@router.post("/simple", response_model=ChatResponse)
@limiter.limit(RATE_LIMIT_AI)
async def chat_simple(
    request: Request,
    message_request: SimpleMessageRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Simplified chat endpoint - just send a message and get a response.

    This is a convenience endpoint for simple single-turn conversations.
    For multi-turn conversations, use the main /chat endpoint.
    """
    try:
        org_id = current_user.organization_id
        user_id = current_user.id

        # Load user settings
        user_settings = await get_user_settings(db, user_id)

        service = ChatService(organization_id=org_id, user_settings=user_settings)

        response = await service.chat([
            ChatMessage(role="user", content=message_request.message),
        ])

        return ChatResponse(
            message=response.content,
            tool_calls=[
                ToolCall(name=tc["name"], input=tc["input"])
                for tc in response.tool_calls
            ] if response.tool_calls else None,
            tool_results=[
                ToolResult(name=tr["name"], result=tr["result"])
                for tr in response.tool_results
            ] if response.tool_results else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Simple chat error")
        raise HTTPException(status_code=500, detail=f"Chat-Fehler: {str(e)}")


@router.get("/tools")
async def list_tools(
    _user: AuthUser = Depends(get_current_user),
) -> dict:
    """List all available tools that the AI can use.

    This endpoint requires authentication to prevent information leakage
    about internal integrations.
    """
    from dealguard.mcp.server_v2 import get_tool_definitions

    tools = get_tool_definitions()
    return {
        "tools": [
            {
                "name": t["name"],
                "description": t["description"][:200] + "..." if len(t["description"]) > 200 else t["description"],
            }
            for t in tools
        ],
        "count": len(tools),
    }


@router.get("/health")
async def chat_health(
    _user: AuthUser = Depends(get_current_user),
) -> dict:
    """Check if the chat service is configured correctly.

    Requires authentication to prevent information leakage.
    """
    from dealguard.config import get_settings
    from dealguard.mcp.server_v2 import get_tool_definitions

    settings = get_settings()

    # Check if any AI provider is configured
    has_api_key = bool(settings.anthropic_api_key or settings.deepseek_api_key)

    return {
        "status": "ok" if has_api_key else "missing_api_key",
        "provider": settings.ai_provider,
        "model": settings.anthropic_model if settings.ai_provider == "anthropic" else settings.deepseek_model,
        "tools_available": len(get_tool_definitions()) if has_api_key else 0,
    }
