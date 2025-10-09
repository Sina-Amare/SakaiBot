"""Telegram utility functions for SakaiBot."""

from typing import List, Dict, Any, Optional, Tuple

from telethon import TelegramClient, functions
from telethon.tl.types import (
    User, Chat, Channel, ForumTopic,
    MessageActionTopicCreate, MessageActionChatEditTitle
)
from telethon.errors.rpcerrorlist import ChannelForumMissingError

from ..core.exceptions import TelegramError
from ..utils.logging import get_logger


class TelegramUtils:
    """Utility functions for Telegram operations."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
    
    async def fetch_all_private_chats(
        self,
        client: TelegramClient,
        offset_date: Optional[Any] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all private chats from Telegram."""
        private_chats_data = []
        self._logger.info(
            f"Fetching private chats from Telegram "
            f"(offset_date: {offset_date}, limit: {limit})"
        )
        
        try:
            async for dialog in client.iter_dialogs(limit=limit, offset_date=offset_date):
                if dialog.is_user and dialog.entity:
                    entity = dialog.entity
                    
                    if not isinstance(entity, User):
                        self._logger.debug(f"Skipping non-User entity in user dialog: {entity}")
                        continue
                    
                    if not entity.deleted and not entity.is_self:
                        user_id = entity.id
                        first_name = entity.first_name or ""
                        last_name = entity.last_name or ""
                        display_name = (first_name + " " + last_name).strip()
                        username_str = f"@{entity.username}" if entity.username else None
                        
                        chat_info = {
                            'id': user_id,
                            'display_name': display_name,
                            'username': username_str
                        }
                        private_chats_data.append(chat_info)
            
            if not private_chats_data:
                self._logger.info("No active private chats found")
            else:
                self._logger.info(f"Successfully fetched {len(private_chats_data)} private chats")
        
        except Exception as e:
            self._logger.error(f"Error fetching private chats: {e}", exc_info=True)
            raise TelegramError(f"Failed to fetch private chats: {e}")
        
        return private_chats_data
    
    async def fetch_user_groups(
        self,
        client: TelegramClient,
        limit: Optional[int] = None,
        require_admin_manage_topics: bool = True
    ) -> List[Dict[str, Any]]:
        """Fetch supergroups where user has admin rights."""
        user_groups_data = []
        action = (
            "all supergroups" if not require_admin_manage_topics
            else "supergroups where you are admin/owner with topic rights"
        )
        self._logger.info(f"Fetching {action} from Telegram (limit: {limit})")
        
        try:
            async for dialog in client.iter_dialogs(limit=limit):
                if dialog.is_channel and dialog.entity and dialog.entity.megagroup:
                    entity = dialog.entity
                    can_manage_topics = False
                    
                    if require_admin_manage_topics:
                        if entity.creator:
                            can_manage_topics = True
                        elif hasattr(entity, 'admin_rights') and entity.admin_rights:
                            admin_rights = entity.admin_rights
                            can_manage_topics = any([
                                admin_rights.change_info,
                                admin_rights.edit_messages,
                                admin_rights.delete_messages,
                                admin_rights.ban_users,
                                admin_rights.invite_users,
                                admin_rights.pin_messages,
                                getattr(admin_rights, 'manage_topics', False),
                                getattr(admin_rights, 'manage_call', False)
                            ])
                    else:
                        can_manage_topics = True
                    
                    if can_manage_topics:
                        group_id = dialog.id
                        is_forum = hasattr(entity, 'forum') and entity.forum is True
                        
                        group_info = {
                            'id': group_id,
                            'title': entity.title,
                            'is_supergroup': True,
                            'is_forum': is_forum
                        }
                        user_groups_data.append(group_info)
                        self._logger.debug(
                            f"Fetched group: {group_info['title']}, "
                            f"ID: {group_info['id']}, Is Forum: {group_info['is_forum']}"
                        )
            
            if not user_groups_data:
                self._logger.info(f"No {action} found")
            else:
                self._logger.info(f"Successfully fetched {len(user_groups_data)} groups")
        
        except Exception as e:
            self._logger.error(f"Error fetching user groups: {e}", exc_info=True)
            raise TelegramError(f"Failed to fetch user groups: {e}")
        
        return user_groups_data
    
    async def get_group_topics(
        self,
        client: TelegramClient,
        group_id: int
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Fetch all topics (forum threads) within a specific group."""
        group_topics_data = []
        is_forum = False
        group_entity = None
        
        try:
            group_entity = await client.get_entity(group_id)
            
            if not (isinstance(group_entity, Channel) and group_entity.megagroup):
                self._logger.warning(f"Group ID {group_id} is not a supergroup")
                return [], False
            
            # Check if it's a forum
            is_forum = hasattr(group_entity, 'forum') and group_entity.forum is True
            self._logger.info(
                f"Group ID {group_id}: Title='{group_entity.title}', "
                f"Is Forum={is_forum}"
            )
            
            if not is_forum:
                self._logger.info(f"Group ID {group_id} is not a forum")
                return [], False
            
            # Fetch topics
            self._logger.info(f"Fetching topics for forum group ID: {group_id}")
            result = await client(functions.channels.GetForumTopicsRequest(
                channel=group_entity,
                offset_date=0,
                offset_id=0,
                offset_topic=0,
                limit=100
            ))
            
            general_topic_added = False
            if result and hasattr(result, 'topics') and result.topics:
                for topic_obj in result.topics:
                    if isinstance(topic_obj, ForumTopic):
                        topic_info = {
                            'id': topic_obj.id,
                            'title': topic_obj.title
                        }
                        group_topics_data.append(topic_info)
                        
                        if topic_obj.id == 1:
                            general_topic_added = True
                
                self._logger.info(
                    f"Successfully fetched {len(group_topics_data)} topics "
                    f"for group ID: {group_id}"
                )
            
            # Add General topic if it wasn't in the API result
            if is_forum and not general_topic_added:
                if not any(t['id'] == 1 for t in group_topics_data):
                    self._logger.info(
                        f"Adding 'General' topic (ID: 1) for forum group {group_id}"
                    )
                    group_topics_data.append({'id': 1, 'title': "General"})
            
            if not group_topics_data and is_forum:
                self._logger.warning(
                    f"Group {group_id} is a forum, but no topics were found"
                )
            
            # Sort topics by ID
            group_topics_data.sort(key=lambda x: x['id'])
            return group_topics_data, True
        
        except ChannelForumMissingError:
            group_title = getattr(group_entity, 'title', 'N/A') if group_entity else 'N/A'
            self._logger.warning(
                f"Group ID {group_id} ('{group_title}') is not a forum "
                f"(ChannelForumMissingError)"
            )
            return [], False
        
        except Exception as e:
            self._logger.error(f"Error fetching topics for group ID {group_id}: {e}", exc_info=True)
            raise TelegramError(f"Failed to fetch group topics: {e}")
    
    async def get_forum_topics(
        self,
        client: TelegramClient,
        group_id: int
    ) -> List[Dict[str, Any]]:
        """Fetch all topics (forum threads) within a specific group."""
        group_topics_data = []
        
        try:
            group_entity = await client.get_entity(group_id)
            
            if not (isinstance(group_entity, Channel) and group_entity.megagroup):
                self._logger.warning(f"Group ID {group_id} is not a supergroup")
                return []
            
            # Check if it's a forum
            is_forum = hasattr(group_entity, 'forum') and group_entity.forum is True
            self._logger.info(
                f"Group ID {group_id}: Title='{group_entity.title}', "
                f"Is Forum={is_forum}"
            )
            
            if not is_forum:
                self._logger.info(f"Group ID {group_id} is not a forum")
                return []
            
            # Fetch topics
            self._logger.info(f"Fetching topics for forum group ID: {group_id}")
            result = await client(functions.channels.GetForumTopicsRequest(
                channel=group_entity,
                offset_date=0,
                offset_id=0,
                offset_topic=0,
                limit=100
            ))
            
            general_topic_added = False
            if result and hasattr(result, 'topics') and result.topics:
                for topic_obj in result.topics:
                    if isinstance(topic_obj, ForumTopic):
                        topic_info = {
                            'id': topic_obj.id,
                            'title': topic_obj.title
                        }
                        group_topics_data.append(topic_info)
                        
                        if topic_obj.id == 1:
                            general_topic_added = True
                
                self._logger.info(
                    f"Successfully fetched {len(group_topics_data)} topics "
                    f"for group ID: {group_id}"
                )
            
            # Add General topic if it wasn't in the API result
            if is_forum and not general_topic_added:
                if not any(t['id'] == 1 for t in group_topics_data):
                    self._logger.info(
                        f"Adding 'General' topic (ID: 1) for forum group {group_id}"
                    )
                    group_topics_data.append({'id': 1, 'title': "General"})
            
            if not group_topics_data and is_forum:
                self._logger.warning(
                    f"Group {group_id} is a forum, but no topics were found"
                )
            
            # Sort topics by ID
            group_topics_data.sort(key=lambda x: x['id'])
            return group_topics_data
        
        except ChannelForumMissingError:
            group_title = getattr(group_entity, 'title', 'N/A') if group_entity else 'N/A'
            self._logger.warning(
                f"Group ID {group_id} ('{group_title}') is not a forum "
                f"(ChannelForumMissingError)"
            )
            return []
        
        except Exception as e:
            self._logger.error(f"Error fetching topics for group ID {group_id}: {e}", exc_info=True)
            raise TelegramError(f"Failed to fetch group topics: {e}")

    async def get_topic_info_by_id(
        self,
        client: TelegramClient,
        group_id: int,
        topic_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get topic information by ID."""
        self._logger.info(f"Getting info for topic ID {topic_id} in group ID {group_id}")
        
        try:
            topic_message = await client.get_messages(group_id, ids=topic_id)
            
            if topic_message and hasattr(topic_message, 'action'):
                # Handle General topic (ID: 1)
                if (topic_id == 1 and
                    (topic_message.action is None or
                     isinstance(topic_message.action, MessageActionChatEditTitle))):
                    self._logger.info(f"Identified General topic (ID: 1) in group {group_id}")
                    return {'id': topic_id, 'title': "General"}
                
                # Handle topic creation messages
                if isinstance(topic_message.action, MessageActionTopicCreate):
                    title = topic_message.action.title
                    self._logger.info(
                        f"Successfully retrieved info for topic ID {topic_id}: "
                        f"Title='{title}'"
                    )
                    return {'id': topic_id, 'title': title}
                else:
                    self._logger.warning(
                        f"Message ID {topic_id} in group {group_id} is not a topic creation message. "
                        f"Action: {topic_message.action}"
                    )
                    return None
            else:
                self._logger.warning(
                    f"Could not find message with ID {topic_id} in group {group_id}"
                )
                return None
        
        except Exception as e:
            self._logger.error(
                f"Error getting info for topic ID {topic_id} in group {group_id}: {e}",
                exc_info=True
            )
            raise TelegramError(f"Failed to get topic info: {e}")
