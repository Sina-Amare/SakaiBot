"""
Telegram module for SakaiBot.

This module provides comprehensive Telegram integration including
client management, event handling, utilities, and data models.
"""

from .client import SakaiBotTelegramClient, create_telegram_client
from .handlers import (
    CommandProcessor,
    TaskManager,
    CategorizationHandler,
    process_command_logic,
    categorization_reply_handler_owner,
    authorized_user_command_handler
)
from .utils import (
    fetch_all_private_chats,
    fetch_user_groups,
    get_group_topics,
    get_topic_info_by_id,
    send_message_safe,
    edit_message_safe,
    forward_message_safe,
    get_message_context,
    validate_chat_id,
    validate_message_text,
    extract_user_info,
    extract_chat_info
)
from .models import (
    TelegramUser,
    TelegramChat,
    ForumTopic,
    MessageContext,
    CommandData,
    TaskResult,
    AuthorizationContext,
    CategorizationTarget,
    ProcessingTask,
    AudioProcessingParams
)

__all__ = [
    # Client
    "SakaiBotTelegramClient",
    "create_telegram_client",
    
    # Handlers
    "CommandProcessor",
    "TaskManager",
    "CategorizationHandler",
    "process_command_logic",
    "categorization_reply_handler_owner",
    "authorized_user_command_handler",
    
    # Utils
    "fetch_all_private_chats",
    "fetch_user_groups",
    "get_group_topics",
    "get_topic_info_by_id",
    "send_message_safe",
    "edit_message_safe",
    "forward_message_safe",
    "get_message_context",
    "validate_chat_id",
    "validate_message_text",
    "extract_user_info",
    "extract_chat_info",
    
    # Models
    "TelegramUser",
    "TelegramChat",
    "ForumTopic",
    "MessageContext",
    "CommandData",
    "TaskResult",
    "AuthorizationContext",
    "CategorizationTarget",
    "ProcessingTask",
    "AudioProcessingParams",
]