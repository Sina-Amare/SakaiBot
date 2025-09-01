# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
from telethon import TelegramClient, types, functions 
from telethon.tl.types import User, Chat, Channel, ChannelParticipantsAdmins, ChatAdminRights, MessageActionTopicCreate, ForumTopic
from telethon.errors.rpcerrorlist import ChannelForumMissingError 
from telethon.utils import get_peer_id

logger = logging.getLogger(__name__)

# ... (fetch_all_private_chats function remains the same as v7) ...
async def fetch_all_private_chats(client: TelegramClient, offset_date=None, limit=None):
    private_chats_data = []
    logger.info(f"Attempting to fetch private chats from Telegram... (Offset Date: {offset_date}, Limit: {limit})")
    try:
        async for dialog in client.iter_dialogs(limit=limit, offset_date=offset_date):
            if dialog.is_user and dialog.entity:
                entity = dialog.entity
                if not isinstance(entity, User): 
                    logger.debug(f"Skipping non-User entity in a user dialog: {entity}")
                    continue
                if not entity.deleted and not entity.is_self:
                    user_id = entity.id
                    first_name = entity.first_name if entity.first_name else ""
                    last_name = entity.last_name if entity.last_name else ""
                    display_name = (first_name + " " + last_name).strip()
                    username_str = f"@{entity.username}" if entity.username else None
                    chat_info = {
                        'id': user_id,
                        'display_name': display_name,
                        'username': username_str
                    }
                    private_chats_data.append(chat_info)
        if not private_chats_data:
            logger.info("No active private chats found based on current criteria.")
        else:
            logger.info(f"Successfully fetched {len(private_chats_data)} private chat(s) from Telegram.")
    except Exception as e:
        logger.error(f"Error fetching private chats from Telegram: {e}", exc_info=True)
    return private_chats_data

async def fetch_user_groups(client: TelegramClient, limit=None, require_admin_manage_topics=True):
    """
    Fetches supergroups where the user is an admin with rights to manage topics (or owner).
    Ensures 'is_forum' key is always present and correctly boolean.
    """
    user_groups_data = []
    action = "all supergroups" if not require_admin_manage_topics else "supergroups where you are admin/owner with topic rights"
    logger.info(f"Attempting to fetch {action} from Telegram... (Limit: {limit})")
    
    try:
        async for dialog in client.iter_dialogs(limit=limit):
            if dialog.is_channel and dialog.entity and dialog.entity.megagroup:
                entity = dialog.entity
                can_manage_topics_or_is_admin = False
                if require_admin_manage_topics:
                    if entity.creator: 
                        can_manage_topics_or_is_admin = True
                    elif hasattr(entity, 'admin_rights') and entity.admin_rights:
                        if entity.admin_rights.change_info or \
                           entity.admin_rights.edit_messages or \
                           entity.admin_rights.delete_messages or \
                           entity.admin_rights.ban_users or \
                           entity.admin_rights.invite_users or \
                           entity.admin_rights.pin_messages or \
                           (hasattr(entity.admin_rights, 'manage_topics') and entity.admin_rights.manage_topics is True) or \
                           (hasattr(entity.admin_rights, 'manage_call') and entity.admin_rights.manage_call):
                             can_manage_topics_or_is_admin = True
                else: 
                    can_manage_topics_or_is_admin = True 
                
                if can_manage_topics_or_is_admin:
                    group_id = dialog.id 
                    # Correctly determine if it's a forum: entity.forum should be True
                    is_forum = hasattr(entity, 'forum') and entity.forum is True
                    
                    group_info = {
                        'id': group_id,
                        'title': entity.title,
                        'is_supergroup': True,
                        'is_forum': is_forum # This will now be True or False
                    }
                    user_groups_data.append(group_info)
                    logger.debug(f"Fetched group: {group_info['title']}, ID: {group_info['id']}, Is Forum: {group_info['is_forum']}")

        if not user_groups_data:
            logger.info(f"No {action} found where the user is a member.")
        else:
            logger.info(f"Successfully fetched {len(user_groups_data)} {action} from Telegram.")
    except Exception as e:
        logger.error(f"Error fetching user's groups from Telegram: {e}", exc_info=True)
    return user_groups_data

async def get_group_topics(client: TelegramClient, group_id: int):
    """
    Fetches all topics (forum threads) within a specific group.
    Also returns whether the group is identified as a forum.
    """
    group_topics_data = []
    is_forum_explicit = False # Will be set based on entity.forum
    group_entity = None
    
    try:
        group_entity = await client.get_entity(group_id)
        if not (isinstance(group_entity, types.Channel) and group_entity.megagroup):
            logger.warning(f"Group ID {group_id} is not a supergroup. Cannot fetch topics.")
            return [], False

        # Explicitly check the 'forum' attribute
        is_forum_explicit = hasattr(group_entity, 'forum') and group_entity.forum is True
        logger.info(f"Group ID {group_id}: Title='{group_entity.title}', Entity reports is_forum = {is_forum_explicit}")

        if not is_forum_explicit:
            logger.info(f"Group ID {group_id} ('{group_entity.title}') is not reported as a forum by entity.forum flag.")
            return [], False

        # If entity.forum is True, proceed to fetch topics
        logger.info(f"Attempting to fetch topics for forum group ID: {group_id} using GetForumTopicsRequest...")
        result = await client(functions.channels.GetForumTopicsRequest(
            channel=group_entity,
            offset_date=0, offset_id=0, offset_topic=0, limit=100 
        ))
        
        general_topic_added_from_api = False
        if result and hasattr(result, 'topics') and result.topics:
            for topic_obj in result.topics:
                if isinstance(topic_obj, ForumTopic): # Use the imported ForumTopic
                    topic_info = {'id': topic_obj.id, 'title': topic_obj.title}
                    group_topics_data.append(topic_info)
                    if topic_obj.id == 1:
                        general_topic_added_from_api = True
            logger.info(f"Successfully fetched {len(group_topics_data)} topics (via GetForumTopics) for group ID: {group_id}.")

        # If it's a forum and "General" (ID 1) wasn't in the API result, add it.
        if is_forum_explicit and not general_topic_added_from_api:
            if not any(t['id'] == 1 for t in group_topics_data):
                logger.info(f"Adding 'General' topic (ID: 1) for forum group {group_id} as it was not in GetForumTopics result.")
                group_topics_data.append({'id': 1, 'title': "General"})
        
        if not group_topics_data and is_forum_explicit:
             logger.warning(f"Group {group_id} is a forum, but no topics were listed (even after trying to add General).")
        
        group_topics_data.sort(key=lambda x: x['id'])
        return group_topics_data, True # Return topics and True for is_forum

    except ChannelForumMissingError: # This error means topics are not enabled
        logger.warning(f"Group ID {group_id} ('{getattr(group_entity, 'title', 'N/A') if group_entity else 'N/A'}') raised ChannelForumMissingError. It's definitely not a forum.")
        return [], False
    except Exception as e:
        logger.error(f"Error fetching topics for group ID {group_id}: {e}", exc_info=True)
        return [], False # Default to not a forum on other errors

# ... (get_topic_info_by_id function remains the same as v6) ...
async def get_topic_info_by_id(client: TelegramClient, group_id: int, topic_id: int):
    logger.info(f"Attempting to get info for topic ID {topic_id} in group ID {group_id}...")
    try:
        topic_message = await client.get_messages(group_id, ids=topic_id)
        if topic_message and isinstance(topic_message, types.Message):
            if topic_id == 1 and (topic_message.action is None or isinstance(topic_message.action, types.MessageActionChatEditTitle)): 
                 logger.info(f"Identified General topic (ID: 1) in group {group_id}.")
                 return {'id': topic_id, 'title': "General"}
            if isinstance(topic_message.action, types.MessageActionTopicCreate):
                title = topic_message.action.title
                logger.info(f"Successfully retrieved info for topic ID {topic_id}: Title='{title}'")
                return {'id': topic_id, 'title': title}
            else:
                logger.warning(f"Message ID {topic_id} in group {group_id} is not a topic creation message. Action: {topic_message.action}")
                return None
        else:
            logger.warning(f"Could not find message with ID {topic_id} in group {group_id}, or it's not a single message.")
            return None
    except Exception as e:
        logger.error(f"Error getting info for topic ID {topic_id} in group {group_id}: {e}", exc_info=True)
        return None
