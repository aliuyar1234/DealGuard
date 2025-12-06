"""Chat domain module.

This module provides the chat service for interacting with Claude
and executing tools against Austrian legal data and DealGuard's database.
"""

from dealguard.domain.chat.service_v2 import ChatService, ChatMessage

__all__ = ["ChatService", "ChatMessage"]
