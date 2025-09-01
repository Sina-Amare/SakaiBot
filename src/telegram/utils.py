# -*- coding: utf-8 -*-
"""
Telegram utility functions for SakaiBot.

This module provides utility functions for Telegram operations including
chat fetching, group management, forum topic handling, and message utilities.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from telethon import TelegramClient, functions
from telethon.tl.types import (
    User, Chat, Channel, ChannelParticipantsAdmins, ChatAdminRights,
    MessageActionTopicCreate, ForumTopic, Message
)
from telethon.errors.rpcerrorlist import ChannelForumMissingError
from telethon.utils import get_peer_id

from ..core.exceptions import (
    TelegramError,
    MessageError,
    PermissionError as SakaiBotPermissionError,
    ValidationError
)
from ..core.constants import (
    MAX_MESSAGE_LENGTH,
    ChatType,
    MessageType
)
from .models import TelegramUser, TelegramChat, ForumTopic as ForumTopicModel, MessageContext


logger = logging.getLogger(__name__)


async def fetch_all_private_chats(
    client: TelegramClient,
    offset_date: Optional[datetime] = None,
    limit: Optional[int] = None
) -> List[TelegramUser]:
    """
    Fetch all private chats from Telegram.
    
    Args:
        client: Telegram client instance
        offset_date: Date to start fetching from
        limit: Maximum number of chats to fetch
        
    Returns:
        List[TelegramUser]: List of private chat users
        
    Raises:
        TelegramError: If fetching fails
    """
    private_chats: List[TelegramUser] = []
    
    logger.info(
        f"Fetching private chats from Telegram "
        f"(Offset Date: {offset_date}, Limit: {limit})"
    )
    
    try:
        async for dialog in client.iter_dialogs(limit=limit, offset_date=offset_date):
            if dialog.is_user and dialog.entity:
                entity = dialog.entity
                
                # Skip non-User entities and deleted/self users
                if not isinstance(entity, User):
                    logger.debug(f"Skipping non-User entity: {entity}")
                    continue
                
                if entity.deleted or entity.is_self:
                    logger.debug(f"Skipping deleted or self user: {entity.id}")
                    continue
                
                # Create TelegramUser from entity
                user = TelegramUser.from_telethon(entity)
                private_chats.append(user)
                
                logger.debug(
                    f"Added private chat: {user.display_name} (ID: {user.id})"
                )
        
        if not private_chats:
            logger.info("No active private chats found")
        else:
            logger.info(f"Successfully fetched {len(private_chats)} private chats")
    
    except Exception as e:
        logger.error(f"Error fetching private chats: {e}", exc_info=True)
        raise TelegramError(f"Failed to fetch private chats: {e}") from e
    
    return private_chats


async def fetch_user_groups(
    client: TelegramClient,
    limit: Optional[int] = None,
    require_admin_rights: bool = True
) -> List[TelegramChat]:
    """
    Fetch supergroups where the user has appropriate permissions.
    
    Args:
        client: Telegram client instance
        limit: Maximum number of groups to fetch
        require_admin_rights: Whether to filter by admin rights
        
    Returns:
        List[TelegramChat]: List of user groups
        
    Raises:
        TelegramError: If fetching fails
    """
    user_groups: List[TelegramChat] = []
    
    action_desc = (
        "supergroups with admin rights" if require_admin_rights 
        else "all supergroups"
    )
    logger.info(f"Fetching {action_desc} (Limit: {limit})")
    
    try:
        async for dialog in client.iter_dialogs(limit=limit):
            # Only process supergroups
            if not (dialog.is_channel and dialog.entity and 
                   hasattr(dialog.entity, 'megagroup') and dialog.entity.megagroup):
                continue
            
            entity = dialog.entity
            
            # Check admin rights if required
            if require_admin_rights:
                if not _has_admin_rights(entity):
                    continue
            
            # Create TelegramChat from dialog
            chat = TelegramChat.from_telethon_dialog(dialog)
            user_groups.append(chat)
            
            logger.debug(
                f"Added group: {chat.title} (ID: {chat.id}, "
                f"Forum: {chat.is_forum})"
            )
        
        if not user_groups:
            logger.info(f"No {action_desc} found")
        else:
            logger.info(f"Successfully fetched {len(user_groups)} groups")
    
    except Exception as e:
        logger.error(f"Error fetching user groups: {e}", exc_info=True)
        raise TelegramError(f"Failed to fetch user groups: {e}") from e
    
    return user_groups


def _has_admin_rights(entity: Channel) -> bool:
    """
    Check if user has admin rights in the channel/group.
    
    Args:
        entity: Telegram channel/group entity
        
    Returns:
        bool: True if user has admin rights
    """
    # Creator always has rights
    if getattr(entity, 'creator', False):
        return True
    
    # Check admin rights
    admin_rights = getattr(entity, 'admin_rights', None)
    if not admin_rights:
        return False
    
    # Check for any relevant admin permission
    return any([
        getattr(admin_rights, 'change_info', False),
        getattr(admin_rights, 'edit_messages', False),
        getattr(admin_rights, 'delete_messages', False),
        getattr(admin_rights, 'ban_users', False),
        getattr(admin_rights, 'invite_users', False),
        getattr(admin_rights, 'pin_messages', False),
        getattr(admin_rights, 'manage_topics', False),
        getattr(admin_rights, 'manage_call', False),
    ])


async def get_group_topics(
    client: TelegramClient,
    group_id: int
) -> Tuple[List[ForumTopicModel], bool]:
    """
    Fetch all topics (forum threads) within a specific group.
    
    Args:
        client: Telegram client instance
        group_id: ID of the group to fetch topics from
        
    Returns:
        Tuple[List[ForumTopicModel], bool]: Topics list and forum status
        
    Raises:
        TelegramError: If fetching fails
        ValidationError: If group ID is invalid
    """
    if not group_id:
        raise ValidationError("Group ID is required", field="group_id", value=group_id)
    
    topics: List[ForumTopicModel] = []
    is_forum = False
    group_entity = None
    
    try:
        # Get group entity
        group_entity = await client.get_entity(group_id)
        
        # Validate it's a supergroup
        if not (isinstance(group_entity, Channel) and 
               getattr(group_entity, 'megagroup', False)):
            logger.warning(f"Group ID {group_id} is not a supergroup")
            return [], False
        
        # Check if it's a forum
        is_forum = hasattr(group_entity, 'forum') and group_entity.forum is True
        
        logger.info(
            f"Group '{group_entity.title}' (ID: {group_id}) - "
            f"Forum status: {is_forum}"
        )
        
        if not is_forum:
            logger.info(f"Group is not a forum, no topics to fetch")
            return [], False
        
        # Fetch topics using Telegram API
        logger.info(f"Fetching topics for forum group: {group_id}")
        result = await client(functions.channels.GetForumTopicsRequest(
            channel=group_entity,
            offset_date=0,
            offset_id=0,
            offset_topic=0,
            limit=100
        ))
        
        general_topic_found = False
        if result and hasattr(result, 'topics') and result.topics:
            for topic_obj in result.topics:
                if isinstance(topic_obj, ForumTopic):
                    topic = ForumTopicModel(
                        id=topic_obj.id,
                        title=topic_obj.title,
                        icon_color=getattr(topic_obj, 'icon_color', None),
                        icon_emoji_id=getattr(topic_obj, 'icon_emoji_id', None),
                        closed=getattr(topic_obj, 'closed', False),
                        short=getattr(topic_obj, 'short', False)
                    )
                    topics.append(topic)
                    
                    if topic_obj.id == 1:
                        general_topic_found = True
            
            logger.info(f"Fetched {len(topics)} topics from API")
        
        # Add General topic if not found in API results
        if is_forum and not general_topic_found:
            if not any(t.id == 1 for t in topics):
                logger.info("Adding 'General' topic as it wasn't in API results")
                general_topic = ForumTopicModel(id=1, title="General")
                topics.append(general_topic)
        
        # Sort topics by ID
        topics.sort(key=lambda x: x.id)
        
        if not topics and is_forum:
            logger.warning(f"Forum group {group_id} has no topics")
        
        return topics, True
    
    except ChannelForumMissingError:
        logger.warning(
            f"Group '{getattr(group_entity, 'title', 'N/A')}' "
            f"(ID: {group_id}) is not a forum"
        )
        return [], False
    
    except Exception as e:
        logger.error(f"Error fetching topics for group {group_id}: {e}", exc_info=True)
        raise TelegramError(f"Failed to fetch group topics: {e}") from e


async def get_topic_info_by_id(
    client: TelegramClient,
    group_id: int,
    topic_id: int
) -> Optional[ForumTopicModel]:
    """
    Get information about a specific topic by ID.
    
    Args:
        client: Telegram client instance
        group_id: ID of the group containing the topic
        topic_id: ID of the topic to fetch
        
    Returns:
        Optional[ForumTopicModel]: Topic information or None if not found
        
    Raises:
        TelegramError: If fetching fails
        ValidationError: If parameters are invalid
    """
    if not group_id or not topic_id:
        raise ValidationError(
            "Group ID and topic ID are required",
            details={"group_id": group_id, "topic_id": topic_id}
        )
    
    logger.info(f"Fetching info for topic {topic_id} in group {group_id}")
    
    try:
        topic_message = await client.get_messages(group_id, ids=topic_id)
        
        if not topic_message or not isinstance(topic_message, Message):
            logger.warning(f"Topic message {topic_id} not found in group {group_id}")
            return None
        
        # Handle General topic (ID 1)
        if topic_id == 1:
            if (topic_message.action is None or 
               isinstance(topic_message.action, MessageActionTopicCreate)):
                logger.info(f"Identified General topic in group {group_id}")
                return ForumTopicModel(id=1, title="General")
        
        # Handle regular topics
        if isinstance(topic_message.action, MessageActionTopicCreate):
            title = topic_message.action.title
            logger.info(f"Found topic '{title}' (ID: {topic_id})")
            return ForumTopicModel(id=topic_id, title=title)
        else:
            logger.warning(
                f"Message {topic_id} in group {group_id} is not a topic creation message"
            )
            return None
    
    except Exception as e:
        logger.error(
            f"Error getting topic info for ID {topic_id} in group {group_id}: {e}",
            exc_info=True
        )
        raise TelegramError(f"Failed to get topic info: {e}") from e


async def send_message_safe(
    client: TelegramClient,
    chat_id: int,
    message: str,
    reply_to: Optional[int] = None,
    parse_mode: Optional[str] = None,
    **kwargs
) -> Optional[Message]:
    """
    Send a message with safe length handling and error management.
    
    Args:
        client: Telegram client instance
        chat_id: Target chat ID
        message: Message text to send
        reply_to: Message ID to reply to
        parse_mode: Message parse mode (md, html, etc.)
        **kwargs: Additional message parameters
        
    Returns:
        Optional[Message]: Sent message or None if failed
        
    Raises:
        MessageError: If sending fails
        ValidationError: If parameters are invalid
    """
    if not chat_id:
        raise ValidationError("Chat ID is required", field="chat_id", value=chat_id)
    
    if not message:
        raise ValidationError("Message text is required", field="message")
    
    try:
        # Truncate message if too long
        if len(message) > MAX_MESSAGE_LENGTH:
            truncated = message[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
            logger.warning(
                f"Message truncated from {len(message)} to {len(truncated)} characters"
            )
            message = truncated
        
        # Send message
        sent_message = await client.send_message(
            chat_id,
            message,
            reply_to=reply_to,
            parse_mode=parse_mode,
            **kwargs
        )
        
        logger.debug(f"Sent message to chat {chat_id} (ID: {sent_message.id})")
        return sent_message
    
    except Exception as e:
        logger.error(f"Failed to send message to chat {chat_id}: {e}", exc_info=True)
        raise MessageError(f"Failed to send message: {e}") from e


async def edit_message_safe(
    client: TelegramClient,
    message: Message,
    new_text: str,
    **kwargs
) -> bool:
    """
    Edit a message with safe length handling and error management.
    
    Args:
        client: Telegram client instance
        message: Message to edit
        new_text: New message text
        **kwargs: Additional edit parameters
        
    Returns:
        bool: True if edit was successful
        
    Raises:
        MessageError: If editing fails
        ValidationError: If parameters are invalid
    """
    if not message:
        raise ValidationError("Message is required")
    
    if not new_text:
        raise ValidationError("New text is required")
    
    try:
        # Truncate if too long
        if len(new_text) > MAX_MESSAGE_LENGTH:
            truncated = new_text[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
            logger.warning(
                f"Edit text truncated from {len(new_text)} to {len(truncated)} characters"
            )
            new_text = truncated
        
        # Edit message
        await client.edit_message(message, new_text, **kwargs)
        logger.debug(f"Edited message {message.id} in chat {message.chat_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to edit message {message.id}: {e}", exc_info=True)
        raise MessageError(f"Failed to edit message: {e}") from e


async def forward_message_safe(
    client: TelegramClient,
    source_chat_id: int,
    message_id: int,
    target_chat_id: int,
    target_topic_id: Optional[int] = None
) -> bool:
    """
    Forward a message with proper error handling.
    
    Args:
        client: Telegram client instance
        source_chat_id: Source chat ID
        message_id: Message ID to forward
        target_chat_id: Target chat ID
        target_topic_id: Target topic ID (for forum groups)
        
    Returns:
        bool: True if forwarding was successful
        
    Raises:
        MessageError: If forwarding fails
        ValidationError: If parameters are invalid
    """
    if not all([source_chat_id, message_id, target_chat_id]):
        raise ValidationError(
            "Source chat ID, message ID, and target chat ID are required",
            details={
                "source_chat_id": source_chat_id,
                "message_id": message_id,
                "target_chat_id": target_chat_id
            }
        )
    
    try:
        # Get peer inputs
        source_peer = await client.get_input_entity(source_chat_id)
        target_peer = await client.get_input_entity(target_chat_id)
        
        # Generate random ID
        import os
        random_id = int.from_bytes(os.urandom(8), 'little', signed=True)
        
        # Prepare forward request parameters
        forward_params = {
            'from_peer': source_peer,
            'id': [message_id],
            'to_peer': target_peer,
            'random_id': [random_id]
        }
        
        # Add topic ID if specified (for forum groups)
        if target_topic_id is not None:
            forward_params['top_msg_id'] = target_topic_id
        
        # Execute forward request
        await client(functions.messages.ForwardMessagesRequest(**forward_params))
        
        target_desc = (
            f"topic {target_topic_id}" if target_topic_id 
            else "main chat"
        )
        logger.info(
            f"Successfully forwarded message {message_id} from {source_chat_id} "
            f"to {target_chat_id} ({target_desc})"
        )
        return True
    
    except Exception as e:
        logger.error(
            f"Failed to forward message {message_id} from {source_chat_id} "
            f"to {target_chat_id}: {e}",
            exc_info=True
        )
        raise MessageError(f"Failed to forward message: {e}") from e


async def get_message_context(
    client: TelegramClient,
    message: Message,
    include_reply: bool = True
) -> MessageContext:
    """
    Get comprehensive context for a message.
    
    Args:
        client: Telegram client instance
        message: Message to get context for
        include_reply: Whether to fetch reply-to message
        
    Returns:
        MessageContext: Complete message context
        
    Raises:
        TelegramError: If context fetching fails
    """
    try:
        # Get chat information
        chat_entity = await client.get_entity(message.chat_id)
        chat = TelegramChat.from_telethon_dialog(type('Dialog', (), {
            'entity': chat_entity,
            'id': message.chat_id,
            'is_user': isinstance(chat_entity, User),
            'is_group': isinstance(chat_entity, Chat),
            'is_channel': isinstance(chat_entity, Channel)
        })())
        
        # Get sender information
        sender = None
        if message.sender_id:
            try:
                sender_entity = await client.get_entity(message.sender_id)
                if isinstance(sender_entity, User):
                    sender = TelegramUser.from_telethon(sender_entity)
            except Exception as e:
                logger.warning(f"Could not fetch sender info: {e}")
        
        # Get reply-to message if requested
        reply_to_message = None
        if include_reply and message.is_reply:
            try:
                reply_to_message = await message.get_reply_message()
            except Exception as e:
                logger.warning(f"Could not fetch reply message: {e}")
        
        # Determine message type
        message_type = _determine_message_type(message)
        
        # Check if it's a command
        is_command = bool(message.text and message.text.strip().startswith('/'))
        command_name = None
        if is_command and message.text:
            command_parts = message.text.strip().split('=', 1)[0].split()[0]
            command_name = command_parts[1:] if command_parts.startswith('/') else None
        
        return MessageContext(
            message=message,
            chat=chat,
            sender=sender,
            reply_to_message=reply_to_message,
            message_type=message_type,
            is_command=is_command,
            command_name=command_name
        )
    
    except Exception as e:
        logger.error(f"Failed to get message context: {e}", exc_info=True)
        raise TelegramError(f"Failed to get message context: {e}") from e


def _determine_message_type(message: Message) -> MessageType:
    """
    Determine the type of a Telegram message.
    
    Args:
        message: Telegram message to analyze
        
    Returns:
        MessageType: Detected message type
    """
    if not message.media:
        return MessageType.TEXT
    
    if message.voice:
        return MessageType.VOICE
    elif message.audio:
        return MessageType.AUDIO
    elif message.video:
        return MessageType.VIDEO
    elif message.document:
        return MessageType.DOCUMENT
    elif message.photo:
        return MessageType.PHOTO
    elif message.sticker:
        return MessageType.STICKER
    elif message.geo:
        return MessageType.LOCATION
    elif message.contact:
        return MessageType.CONTACT
    elif message.poll:
        return MessageType.POLL
    else:
        return MessageType.TEXT


def validate_chat_id(chat_id: Any) -> int:
    """
    Validate and convert chat ID to integer.
    
    Args:
        chat_id: Chat ID to validate
        
    Returns:
        int: Validated chat ID
        
    Raises:
        ValidationError: If chat ID is invalid
    """
    try:
        validated_id = int(chat_id)
        if validated_id == 0:
            raise ValidationError("Chat ID cannot be zero", field="chat_id", value=chat_id)
        return validated_id
    except (ValueError, TypeError):
        raise ValidationError(
            f"Invalid chat ID format: {chat_id}",
            field="chat_id",
            value=chat_id
        )


def validate_message_text(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """
    Validate and truncate message text if necessary.
    
    Args:
        text: Message text to validate
        max_length: Maximum allowed length
        
    Returns:
        str: Validated (and possibly truncated) text
        
    Raises:
        ValidationError: If text is invalid
    """
    if not isinstance(text, str):
        raise ValidationError(
            f"Message text must be a string, got {type(text)}",
            field="text",
            value=text
        )
    
    if not text.strip():
        raise ValidationError("Message text cannot be empty", field="text")
    
    # Truncate if necessary
    if len(text) > max_length:
        truncated = text[:max_length - 20] + "... (truncated)"
        logger.warning(
            f"Text truncated from {len(text)} to {len(truncated)} characters"
        )
        return truncated
    
    return text


def extract_user_info(user: User) -> Dict[str, Any]:
    """
    Extract user information as a dictionary (legacy compatibility).
    
    Args:
        user: Telethon User object
        
    Returns:
        Dict[str, Any]: User information dictionary
    """
    telegram_user = TelegramUser.from_telethon(user)
    return {
        'id': telegram_user.id,
        'display_name': telegram_user.display_name,
        'username': telegram_user.username_str
    }


def extract_chat_info(dialog) -> Dict[str, Any]:
    """
    Extract chat information as a dictionary (legacy compatibility).
    
    Args:
        dialog: Telethon Dialog object
        
    Returns:
        Dict[str, Any]: Chat information dictionary
    """
    telegram_chat = TelegramChat.from_telethon_dialog(dialog)
    return {
        'id': telegram_chat.id,
        'title': telegram_chat.title,
        'is_supergroup': telegram_chat.is_supergroup,
        'is_forum': telegram_chat.is_forum
    }
