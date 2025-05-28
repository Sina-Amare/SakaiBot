# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
import os # For os.urandom if we revert random_id generation, but not needed for current forward logic
from telethon import TelegramClient, events, functions, utils 
from telethon.tl import types 
from telethon.tl.types import Message 

import ai_processor # Ensure ai_processor is imported

logger = logging.getLogger(__name__) 

MAX_MESSAGE_LENGTH = 4096 # Telegram's message length limit

async def categorization_reply_handler(
    event: events.NewMessage.Event, 
    client: TelegramClient, 
    monitored_pv_id: int, 
    categorization_group_id: int or None, 
    command_topic_map: dict or None,
    openrouter_api_key: str or None,
    openrouter_model_name: str or None
):
    """
    Handles outgoing messages in the monitored PV for categorization
    AND AI commands like /prompt=, /analyze, /translate.
    """
    try:
        message = event.message
        logger.debug(f"SakaiBot Handler: NewMessage Event. Chat ID: {message.chat_id}, Monitored PV: {monitored_pv_id}, Msg ID: {message.id}, Out: {message.out}, IsReply: {message.is_reply}")

        if not message.out or message.chat_id != monitored_pv_id:
            logger.debug("SakaiBot Handler: Event not outgoing or not in monitored PV.")
            return 

        # --- AI Command Handling ---
        if message.message and message.message.lower().startswith("/prompt="):
            if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
                await client.send_message(event.chat_id, "AI Error: OpenRouter API key or model name not configured properly in config.ini.", reply_to=message.id)
                logger.error("SakaiBot Handler: /prompt command failed - OpenRouter API key or model not configured.")
                return
            
            user_prompt_text = message.message[len("/prompt="):].strip()
            if not user_prompt_text:
                await client.send_message(event.chat_id, "Usage: /prompt=<your question or instruction>", reply_to=message.id)
                return

            logger.info(f"SakaiBot Handler: Detected AI command '/prompt={user_prompt_text[:50]}...'")
            thinking_msg = None
            try:
                thinking_msg = await client.send_message(event.chat_id, f"🤖 Processing your prompt with {openrouter_model_name}...", reply_to=message.id)
                
                ai_response_raw = await ai_processor.execute_custom_prompt(
                    openrouter_api_key, 
                    openrouter_model_name, 
                    user_prompt_text
                )
                logger.debug(f"SakaiBot Handler: Raw AI Response: '{ai_response_raw}'")

                if not ai_response_raw or not ai_response_raw.strip():
                    logger.error("SakaiBot Handler: AI response was empty or only whitespace.")
                    ai_response_to_send = "AI Error: Received an empty response from the AI."
                else:
                    ai_response_to_send = ai_response_raw

                # Truncate if too long for Telegram
                if len(ai_response_to_send) > MAX_MESSAGE_LENGTH:
                    ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
                    logger.warning("SakaiBot Handler: AI response was truncated as it exceeded Telegram's limit.")

                await client.edit_message(thinking_msg, ai_response_to_send)
                logger.info(f"SakaiBot Handler: AI response sent for /prompt command.")

            except Exception as e_ai_send: # Catch errors during AI processing or sending
                logger.error(f"SakaiBot Handler: Error during AI prompt processing or sending response: {e_ai_send}", exc_info=True)
                error_message = "An error occurred while processing your AI request."
                if thinking_msg: # Try to edit the thinking message to an error message
                    await client.edit_message(thinking_msg, error_message)
                else: # If sending thinking_msg failed, send a new error message
                    await client.send_message(event.chat_id, error_message, reply_to=message.id)
            return 

        # --- Categorization Command Handling (requires reply) ---
        if not message.is_reply:
            logger.debug("SakaiBot Handler: Message is not a reply and not an AI command. Ignoring for categorization.")
            return

        logger.info(f"SakaiBot Handler: Processing categorization command in PV {monitored_pv_id} for message ID {message.id}.")
        
        reply_text = message.message 
        if not reply_text or not reply_text.startswith('/'):
            logger.debug(f"SakaiBot Handler: Reply text '{reply_text}' is not a categorization command.")
            return

        command = reply_text[1:].lower().strip()
        logger.info(f"SakaiBot Handler: Detected categorization command '/{command}'.")

        if categorization_group_id is None or command_topic_map is None:
            logger.warning("SakaiBot Handler: Categorization target group or command map not set for this command.")
            return

        if command in command_topic_map:
            target_topic_id = command_topic_map[command] 
            log_target_desc = f"Topic ID {target_topic_id}" if target_topic_id is not None else "Main Group Chat"
            logger.info(f"SakaiBot Handler: Command '/{command}' maps to {log_target_desc}.")
            
            replied_to_message_id = message.reply_to_msg_id
            if not replied_to_message_id: 
                logger.warning("SakaiBot Handler: Could not get ID of the message replied to for categorization.")
                return

            original_message_to_forward = await client.get_messages(message.chat_id, ids=replied_to_message_id)
            if not original_message_to_forward:
                logger.warning(f"SakaiBot Handler: Could not fetch original message (ID: {replied_to_message_id}) for categorization.")
                return
            
            media_type_log = type(original_message_to_forward.media).__name__ if original_message_to_forward.media else "Text"
            logger.info(f"SakaiBot Handler: Preparing to forward for categorization: original msg (ID {original_message_to_forward.id}, Type: {media_type_log}) to group ID {categorization_group_id}, target: {log_target_desc}.")
            
            try:
                source_peer_input = await client.get_input_entity(message.chat_id)
                destination_peer_input = await client.get_input_entity(categorization_group_id)
                # Use os.urandom for a robust random_id
                generated_random_id = int.from_bytes(os.urandom(8), 'little', signed=True)
                fwd_request_params = {
                    'from_peer': source_peer_input,
                    'id': [original_message_to_forward.id], 
                    'to_peer': destination_peer_input,
                    'random_id': [generated_random_id]
                }
                if target_topic_id is not None:
                    fwd_request_params['top_msg_id'] = target_topic_id
                
                await client(functions.messages.ForwardMessagesRequest(**fwd_request_params))
                logger.info(f"SakaiBot Handler: Message successfully forwarded for categorization command '/{command}'.")
            except Exception as e_fwd:
                logger.error(f"SakaiBot Handler: Error forwarding for categorization command '/{command}': {e_fwd}", exc_info=True)
        else:
            logger.info(f"SakaiBot Handler: Categorization command '/{command}' not found in defined mappings.")

    except Exception as e:
        logger.error(f"SakaiBot Handler: Unexpected error in handler: {e}", exc_info=True)
