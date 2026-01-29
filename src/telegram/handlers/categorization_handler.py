"""Categorization command handler for message forwarding to topics."""

import random
from typing import Dict, Any, Optional

from telethon import TelegramClient, events, functions
from telethon.tl.types import Message

from ...core.constants import CONFIRMATION_KEYWORD
from ...utils.logging import get_logger
from .base import BaseHandler


class CategorizationHandler(BaseHandler):
    """Handles message categorization and forwarding to topics."""
    
    def __init__(self):
        """Initialize categorization handler."""
        super().__init__()
    
    async def handle_categorization_commands(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        actual_message_content: Optional[Message],
        cli_state_ref: Dict[str, Any]
    ) -> None:
        """Handle categorization commands."""
        if not (message.is_reply and message.text and message.text.startswith('/')):
            return
        
        if actual_message_content is None:
            try:
                actual_message_content = await message.get_reply_message()
            except Exception as fetch_err:
                self._logger.warning(f"Unable to fetch replied message for categorization: {fetch_err}")
                actual_message_content = None
        
        # Handle both old format (int) and new format (dict) for selected_target_group
        selected_target_group = cli_state_ref.get("selected_target_group", {})
        if isinstance(selected_target_group, dict):
            categorization_group_id = selected_target_group.get('id')
        else:
            # Old format - selected_target_group is just the group ID
            categorization_group_id = selected_target_group
        command_topic_map = cli_state_ref.get("active_command_to_topic_map", {})
        if not isinstance(command_topic_map, dict):
            self._logger.warning("Active command-to-topic map is malformed; skipping categorization.")
            return
        
        if not categorization_group_id or not command_topic_map:
            self._logger.debug("Categorization target group or command map not set")
            return
        
        command_for_categorization = message.text[1:].lower().strip()
        
        # Check if command exists in the mapping (handles both new and legacy formats)
        target_topic_id = None
        is_command_mapped = False

        # New format: {topic_id: [commands]}
        if any(isinstance(v, list) for v in command_topic_map.values()):
            for topic_id, commands in command_topic_map.items():
                if not isinstance(commands, list):
                    continue
                if isinstance(topic_id, str):
                    try:
                        topic_id_int = int(topic_id)
                    except ValueError:
                        self._logger.warning(f"Ignoring mapping with invalid topic identifier '{topic_id}'.")
                        continue
                else:
                    topic_id_int = topic_id
                if command_for_categorization in commands:
                    target_topic_id = topic_id_int
                    is_command_mapped = True
                    break
        # Legacy format: {command: topic_id}
        else:
            if command_for_categorization in command_topic_map:
                target_topic_id = command_topic_map[command_for_categorization]
                is_command_mapped = True

        if is_command_mapped:
            self._logger.info(f"Processing categorization command '/{command_for_categorization}'")
            
            if not actual_message_content:
                self._logger.warning("No actual message content found to categorize")
                return
            
            log_target = f"Topic ID {target_topic_id}" if target_topic_id else "Main Group Chat"
            
            self._logger.info(
                f"Categorization command '/{command_for_categorization}' "
                f"maps to {log_target} in group {categorization_group_id}"
            )
            
            try:
                # Forward message for categorization
                source_peer = await client.get_input_entity(actual_message_content.chat_id)
                dest_peer = await client.get_input_entity(categorization_group_id)
                
                random_id = random.randint(-2**63, 2**63 - 1)
                
                fwd_params = {
                    'from_peer': source_peer,
                    'id': [actual_message_content.id],
                    'to_peer': dest_peer,
                    'random_id': [random_id]
                }
                
                if target_topic_id is not None:
                    fwd_params['top_msg_id'] = target_topic_id
                
                await client(functions.messages.ForwardMessagesRequest(**fwd_params))
                
                self._logger.info(
                    f"Message successfully forwarded for categorization command "
                    f"'/{command_for_categorization}'"
                )
            
            except Exception as e:
                self._logger.error(f"Error forwarding for categorization: {e}", exc_info=True)
                await client.send_message(
                    chat_id,
                    f"Error forwarding message for categorization: {e}",
                    reply_to=message.id
                )
    
    async def categorization_reply_handler_owner(
        self,
        event: events.NewMessage.Event,
        process_command_logic_func,
        **kwargs
    ) -> None:
        """Handle owner's messages for categorization and commands."""
        your_message = event.message
        client_instance = kwargs['client']
        cli_state_ref = kwargs['cli_state_ref']
        
        message_to_process = None
        is_confirm_flow = False
        your_confirm_message = None
        actual_message_content = None
        
        # Check for confirmation flow
        if (your_message.is_reply and your_message.text and 
            your_message.text.strip().lower() == CONFIRMATION_KEYWORD):
            
            self._logger.info(f"Detected '{CONFIRMATION_KEYWORD}' reply from you")
            friends_command_message = await your_message.get_reply_message()
            
            if friends_command_message:
                message_to_process = friends_command_message
                is_confirm_flow = True
                your_confirm_message = your_message
                
                if friends_command_message.is_reply:
                    actual_message_content = await friends_command_message.get_reply_message()
            else:
                self._logger.warning("Could not fetch the friend's command message")
                await client_instance.send_message(
                    event.chat_id,
                    "❌ Could not process 'confirm'. Replied message not found.",
                    reply_to=your_message.id
                )
                return
        else:
            message_to_process = your_message
            if your_message.is_reply:
                actual_message_content = await your_message.get_reply_message()
        
        if message_to_process:
            await process_command_logic_func(
                message_to_process=message_to_process,
                client=client_instance,
                current_chat_id_for_response=event.chat_id,
                is_confirm_flow=is_confirm_flow,
                your_confirm_message=your_confirm_message,
                actual_message_for_categorization_content=actual_message_content,
                cli_state_ref=cli_state_ref,
                is_direct_auth_user_command=False
            )
    
    async def authorized_user_command_handler(
        self,
        event: events.NewMessage.Event,
        process_command_logic_func,
        **kwargs
    ) -> None:
        """Handle commands from authorized users."""
        self._logger.info(
            f"Incoming message from authorized user. "
            f"Chat ID: {event.chat_id}, Sender ID: {event.sender_id}, "
            f"Text: {event.message.text[:50] if event.message.text else 'N/A'}"
        )
        
        client_instance = kwargs['client']
        cli_state_ref = kwargs['cli_state_ref']
        
        await process_command_logic_func(
            message_to_process=event.message,
            client=client_instance,
            current_chat_id_for_response=event.chat_id,
            is_confirm_flow=False,
            your_confirm_message=None,
            actual_message_for_categorization_content=None,
            cli_state_ref=cli_state_ref,
            is_direct_auth_user_command=True
        )

