# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
import os # Import os for urandom
from telethon import TelegramClient, events, functions, utils 
from telethon.tl import types 
from telethon.tl.types import Message 

logger = logging.getLogger(__name__) 

async def categorization_reply_handler(
    event: events.NewMessage.Event, 
    client: TelegramClient, 
    monitored_pv_id: int, 
    categorization_group_id: int, 
    command_topic_map: dict
):
    """
    Handles outgoing reply messages in the monitored PV for categorization.
    Uses functions.messages.ForwardMessagesRequest for robust forwarding
    to topics or main group chat, ensuring "Forwarded from" is shown.
    Uses os.urandom to generate random_id.
    """
    try:
        message = event.message
        logger.debug(f"SakaiBot Handler: NewMessage Event. Chat ID: {message.chat_id}, Monitored PV: {monitored_pv_id}, Msg ID: {message.id}")

        if not (message.out and message.is_reply and message.chat_id == monitored_pv_id):
            logger.debug("SakaiBot Handler: Event did not meet all initial conditions.")
            return 

        logger.info(f"SakaiBot Handler: Processing command in monitored PV {monitored_pv_id} for message ID {message.id}.")
        
        reply_text = message.message 
        if not reply_text or not reply_text.startswith('/'):
            logger.debug(f"SakaiBot Handler: Reply text '{reply_text}' is not a command or is empty.")
            return

        command = reply_text[1:].lower().strip()
        logger.info(f"SakaiBot Handler: Detected command '/{command}'.")

        if command in command_topic_map:
            target_topic_id = command_topic_map[command] 
            log_target_desc = f"Topic ID {target_topic_id}" if target_topic_id is not None else "Main Group Chat"
            logger.info(f"SakaiBot Handler: Command '/{command}' maps to {log_target_desc}.")
            
            replied_to_message_id = message.reply_to_msg_id
            if not replied_to_message_id: 
                logger.warning("SakaiBot Handler: Could not get the ID of the message replied to.")
                return

            logger.debug(f"SakaiBot Handler: Attempting to fetch original message (ID: {replied_to_message_id}) from chat {message.chat_id}.")
            original_message_to_forward = await client.get_messages(message.chat_id, ids=replied_to_message_id)
            
            if not original_message_to_forward:
                logger.warning(f"SakaiBot Handler: Could not fetch the original message (ID: {replied_to_message_id}) to forward.")
                return
            
            media_type_log = type(original_message_to_forward.media).__name__ if original_message_to_forward.media else "Text"
            logger.info(f"SakaiBot Handler: Preparing to forward original message (ID {original_message_to_forward.id}, Type: {media_type_log}) from chat ID {message.chat_id} to group ID {categorization_group_id}, target: {log_target_desc}.")
            
            try:
                source_peer_input = await client.get_input_entity(message.chat_id)
                destination_peer_input = await client.get_input_entity(categorization_group_id)

                # Generate a random 64-bit signed integer for random_id
                # os.urandom(8) gives 8 random bytes.
                # int.from_bytes converts these bytes to an integer.
                # 'little' is the byte order, signed=True makes it a signed integer.
                generated_random_id = int.from_bytes(os.urandom(8), 'little', signed=True)

                fwd_request_params = {
                    'from_peer': source_peer_input,
                    'id': [original_message_to_forward.id], 
                    'to_peer': destination_peer_input,
                    'random_id': [generated_random_id] # Use the generated random_id
                }

                if target_topic_id is not None:
                    fwd_request_params['top_msg_id'] = target_topic_id
                
                await client(functions.messages.ForwardMessagesRequest(**fwd_request_params))
                
                logger.info(f"SakaiBot Handler: Message successfully forwarded for command '/{command}'.")
                
            except Exception as e_fwd:
                logger.error(f"SakaiBot Handler: Error forwarding message using raw request for command '/{command}': {e_fwd}", exc_info=True)
        else:
            logger.info(f"SakaiBot Handler: Command '/{command}' not found in defined mappings: {list(command_topic_map.keys())}")

    except Exception as e:
        logger.error(f"SakaiBot Handler: Unexpected error in categorization_reply_handler: {e}", exc_info=True)

