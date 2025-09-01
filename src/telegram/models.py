# -*- coding: utf-8 -*-
"""
Telegram data models for SakaiBot.

This module defines data classes and models for Telegram entities,
providing type safety and structured data handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from telethon.tl.types import User, Chat, Channel, Message

from ..core.constants import ChatType, UserRole, MessageType


@dataclass
class TelegramUser:
    """Represents a Telegram user."""
    
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    is_self: bool = False
    is_contact: bool = False
    is_mutual_contact: bool = False
    is_deleted: bool = False
    is_bot: bool = False
    is_verified: bool = False
    is_restricted: bool = False
    is_scam: bool = False
    is_fake: bool = False
    is_premium: bool = False
    
    @property
    def display_name(self) -> str:
        """Get formatted display name for the user."""
        if self.first_name or self.last_name:
            name_parts = []
            if self.first_name:
                name_parts.append(self.first_name)
            if self.last_name:
                name_parts.append(self.last_name)
            return " ".join(name_parts)
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.id}"
    
    @property
    def username_str(self) -> Optional[str]:
        """Get formatted username string."""
        return f"@{self.username}" if self.username else None
    
    @classmethod
    def from_telethon(cls, user: User) -> "TelegramUser":
        """Create TelegramUser from Telethon User object."""
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            phone=user.phone,
            is_self=user.is_self,
            is_contact=user.contact,
            is_mutual_contact=user.mutual_contact,
            is_deleted=user.deleted,
            is_bot=user.bot,
            is_verified=user.verified,
            is_restricted=user.restricted,
            is_scam=user.scam,
            is_fake=user.fake,
            is_premium=getattr(user, 'premium', False)
        )


@dataclass
class ForumTopic:
    """Represents a forum topic in a Telegram group."""
    
    id: int
    title: str
    icon_color: Optional[int] = None
    icon_emoji_id: Optional[int] = None
    closed: bool = False
    short: bool = False
    
    @property
    def is_general(self) -> bool:
        """Check if this is the General topic (ID 1)."""
        return self.id == 1


@dataclass
class TelegramChat:
    """Represents a Telegram chat (private, group, supergroup, or channel)."""
    
    id: int
    title: Optional[str] = None
    username: Optional[str] = None
    chat_type: ChatType = ChatType.PRIVATE
    is_supergroup: bool = False
    is_forum: bool = False
    is_channel: bool = False
    is_group: bool = False
    is_broadcast: bool = False
    is_verified: bool = False
    is_restricted: bool = False
    is_scam: bool = False
    is_fake: bool = False
    participant_count: Optional[int] = None
    admin_rights: Optional[Dict[str, bool]] = None
    topics: List[ForumTopic] = field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        """Get formatted display name for the chat."""
        if self.title:
            return self.title
        elif self.username:
            return f"@{self.username}"
        else:
            return f"Chat {self.id}"
    
    @property
    def username_str(self) -> Optional[str]:
        """Get formatted username string."""
        return f"@{self.username}" if self.username else None
    
    def can_manage_topics(self) -> bool:
        """Check if user can manage topics in this chat."""
        if not self.admin_rights:
            return False
        
        return any([
            self.admin_rights.get("creator", False),
            self.admin_rights.get("change_info", False),
            self.admin_rights.get("edit_messages", False),
            self.admin_rights.get("delete_messages", False),
            self.admin_rights.get("ban_users", False),
            self.admin_rights.get("invite_users", False),
            self.admin_rights.get("pin_messages", False),
            self.admin_rights.get("manage_topics", False),
            self.admin_rights.get("manage_call", False),
        ])
    
    @classmethod
    def from_telethon_dialog(cls, dialog) -> "TelegramChat":
        """Create TelegramChat from Telethon Dialog object."""
        entity = dialog.entity
        chat_type = ChatType.PRIVATE
        is_supergroup = False
        is_forum = False
        is_channel = False
        is_group = False
        is_broadcast = False
        admin_rights = {}
        
        if dialog.is_user:
            chat_type = ChatType.PRIVATE
        elif dialog.is_group:
            chat_type = ChatType.GROUP
            is_group = True
        elif dialog.is_channel:
            if hasattr(entity, 'megagroup') and entity.megagroup:
                chat_type = ChatType.SUPERGROUP
                is_supergroup = True
                if hasattr(entity, 'forum') and entity.forum:
                    chat_type = ChatType.FORUM
                    is_forum = True
            else:
                chat_type = ChatType.CHANNEL
                is_channel = True
                is_broadcast = getattr(entity, 'broadcast', False)
        
        # Extract admin rights
        if hasattr(entity, 'creator') and entity.creator:
            admin_rights['creator'] = True
        elif hasattr(entity, 'admin_rights') and entity.admin_rights:
            admin_rights = {
                'change_info': getattr(entity.admin_rights, 'change_info', False),
                'edit_messages': getattr(entity.admin_rights, 'edit_messages', False),
                'delete_messages': getattr(entity.admin_rights, 'delete_messages', False),
                'ban_users': getattr(entity.admin_rights, 'ban_users', False),
                'invite_users': getattr(entity.admin_rights, 'invite_users', False),
                'pin_messages': getattr(entity.admin_rights, 'pin_messages', False),
                'manage_topics': getattr(entity.admin_rights, 'manage_topics', False),
                'manage_call': getattr(entity.admin_rights, 'manage_call', False),
            }
        
        return cls(
            id=dialog.id,
            title=getattr(entity, 'title', None),
            username=getattr(entity, 'username', None),
            chat_type=chat_type,
            is_supergroup=is_supergroup,
            is_forum=is_forum,
            is_channel=is_channel,
            is_group=is_group,
            is_broadcast=is_broadcast,
            is_verified=getattr(entity, 'verified', False),
            is_restricted=getattr(entity, 'restricted', False),
            is_scam=getattr(entity, 'scam', False),
            is_fake=getattr(entity, 'fake', False),
            participant_count=getattr(entity, 'participants_count', None),
            admin_rights=admin_rights
        )


@dataclass
class MessageContext:
    """Context information for message processing."""
    
    message: Message
    chat: TelegramChat
    sender: Optional[TelegramUser] = None
    reply_to_message: Optional[Message] = None
    forwarded_from: Optional[Union[TelegramUser, TelegramChat]] = None
    message_type: MessageType = MessageType.TEXT
    is_command: bool = False
    command_name: Optional[str] = None
    command_args: Dict[str, Any] = field(default_factory=dict)
    processing_started_at: Optional[datetime] = None
    
    @property
    def sender_info(self) -> str:
        """Get formatted sender information."""
        if not self.sender:
            return f"Unknown (ID: {self.message.sender_id})"
        return self.sender.display_name
    
    @property
    def is_voice_message(self) -> bool:
        """Check if message contains voice."""
        return self.message_type == MessageType.VOICE or (
            self.message and hasattr(self.message, 'voice') and self.message.voice
        )
    
    @property
    def is_reply(self) -> bool:
        """Check if message is a reply."""
        return self.message.is_reply if self.message else False


@dataclass
class CommandData:
    """Structured command data for processing."""
    
    command_type: str
    raw_text: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_text: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    num_messages: Optional[int] = None
    user_question: Optional[str] = None
    voice_params: Dict[str, str] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Check if command has valid parameters."""
        if self.command_type in ["/prompt"]:
            return bool(self.target_text)
        elif self.command_type in ["/translate"]:
            return bool(self.target_text and self.target_language)
        elif self.command_type in ["/analyze"]:
            return bool(self.num_messages and self.num_messages > 0)
        elif self.command_type in ["/tellme"]:
            return bool(self.num_messages and self.num_messages > 0 and self.user_question)
        elif self.command_type in ["/tts", "/speak"]:
            return bool(self.target_text)
        return False


@dataclass
class TaskResult:
    """Result of an async task operation."""
    
    success: bool
    result: Optional[Any] = None
    error: Optional[Exception] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_result(cls, result: Any, duration: Optional[float] = None, **metadata) -> "TaskResult":
        """Create successful task result."""
        return cls(
            success=True,
            result=result,
            duration=duration,
            metadata=metadata
        )
    
    @classmethod
    def error_result(cls, error: Exception, duration: Optional[float] = None, **metadata) -> "TaskResult":
        """Create error task result."""
        return cls(
            success=False,
            error=error,
            duration=duration,
            metadata=metadata
        )


@dataclass
class AuthorizationContext:
    """Context for user authorization and permissions."""
    
    user_id: int
    chat_id: int
    role: UserRole = UserRole.USER
    is_owner: bool = False
    is_authorized: bool = False
    permissions: List[str] = field(default_factory=list)
    
    def can_execute_command(self, command: str) -> bool:
        """Check if user can execute a specific command."""
        if self.is_owner:
            return True
        if not self.is_authorized:
            return False
        
        # Define command permissions
        command_permissions = {
            "/prompt": ["ai_commands"],
            "/translate": ["ai_commands"],
            "/analyze": ["ai_commands", "history_access"],
            "/tellme": ["ai_commands", "history_access"],
            "/stt": ["audio_processing"],
            "/tts": ["audio_processing"],
            "/speak": ["audio_processing"]
        }
        
        required_perms = command_permissions.get(command, [])
        return all(perm in self.permissions for perm in required_perms)


@dataclass
class CategorizationTarget:
    """Target for message categorization."""
    
    group_id: int
    topic_id: Optional[int] = None
    command_map: Dict[str, Optional[int]] = field(default_factory=dict)
    
    @property
    def target_description(self) -> str:
        """Get description of the target."""
        if self.topic_id is not None:
            return f"Topic ID {self.topic_id}"
        return "Main Group Chat"


@dataclass
class ProcessingTask:
    """Represents an async processing task."""
    
    task_id: str
    task_type: str
    message_context: MessageContext
    command_data: Optional[CommandData] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.completed_at is not None
    
    @property
    def duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class AudioProcessingParams:
    """Parameters for audio processing operations."""
    
    voice_id: str = "fa-IR-DilaraNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    format: str = "mp3"
    quality: str = "high"
    
    def validate(self) -> bool:
        """Validate audio processing parameters."""
        # Basic validation logic
        try:
            # Check rate format
            if not self.rate.endswith('%'):
                return False
            rate_value = int(self.rate[:-1])
            if not -50 <= rate_value <= 100:
                return False
                
            # Check volume format
            if not self.volume.endswith('%'):
                return False
            volume_value = int(self.volume[:-1])
            if not -50 <= volume_value <= 100:
                return False
                
            return True
        except (ValueError, IndexError):
            return False
