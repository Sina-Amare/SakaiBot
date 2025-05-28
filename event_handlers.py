# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
import os 
import re 
from telethon import TelegramClient, events, functions, utils 
from telethon.tl import types 
from telethon.tl.types import Message, User as TelegramUser # Alias User to avoid conflict if any

import ai_processor

logger = logging.getLogger(__name__) 

MAX_MESSAGE_LENGTH = 4096

async def categorization_reply_handler(
    event: events.NewMessage.Event, 
    client: TelegramClient, 
    monitored_pv_id: int, 
    categorization_group_id: int or None, 
    command_topic_map: dict or None,
    openrouter_api_key: str or None,
    openrouter_model_name: str or None
):
    try:
        message = event.message
        logger.debug(f"SakaiBot Handler: NewMessage Event. Chat ID: {message.chat_id}, Monitored PV: {monitored_pv_id}, Msg ID: {message.id}, Out: {message.out}, IsReply: {message.is_reply}")

        if not message.out or message.chat_id != monitored_pv_id:
            logger.debug("SakaiBot Handler: Event not outgoing or not in monitored PV.")
            return 

        if message.message:
            msg_text_lower = message.message.lower()
            
            # /prompt= command
            if msg_text_lower.startswith("/prompt="):
                # ... (same as v14) ...
                if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
                    await client.send_message(event.chat_id, "AI Error: OpenRouter API key or model name not configured properly in config.ini.", reply_to=message.id)
                    logger.error("SakaiBot Handler: /prompt command failed - OpenRouter API key or model not configured.")
                    return
                user_prompt_text = message.message[len("/prompt="):].strip()
                if not user_prompt_text:
                    await client.send_message(event.chat_id, "Usage: /prompt=<your question or instruction>", reply_to=message.id)
                    return
                logger.info(f"SakaiBot Handler: Detected AI command '/prompt={user_prompt_text[:50]}...'")
                thinking_msg = await client.send_message(event.chat_id, f"🤖 Processing your prompt with {openrouter_model_name}...", reply_to=message.id)
                ai_response_raw = await ai_processor.execute_custom_prompt(
                    openrouter_api_key, openrouter_model_name, user_prompt_text
                )
                logger.debug(f"SakaiBot Handler: Raw AI Response for /prompt: '{ai_response_raw}'")
                ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Received an empty response."
                if len(ai_response_to_send) > MAX_MESSAGE_LENGTH:
                    ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
                await client.edit_message(thinking_msg, ai_response_to_send)
                logger.info(f"SakaiBot Handler: AI response sent for /prompt command.")
                return 

            # /translate= command
            elif msg_text_lower.startswith("/translate="):
                # ... (same as v14) ...
                if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
                    await client.send_message(event.chat_id, "AI Error: OpenRouter API key or model name not configured properly for translation.", reply_to=message.id)
                    logger.error("SakaiBot Handler: /translate command failed - OpenRouter API key or model not configured.")
                    return
                command_parts_str = message.message[len("/translate="):].strip()
                target_language = None
                text_to_translate_direct = None
                source_language_direct = "auto" 
                match_with_text = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?\s+(.+)", command_parts_str, re.DOTALL)
                match_lang_only = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?$", command_parts_str)
                if match_with_text:
                    target_language = match_with_text.group(1).strip()
                    if match_with_text.group(2): source_language_direct = match_with_text.group(2).strip()
                    text_to_translate_direct = match_with_text.group(3).strip()
                elif match_lang_only:
                    target_language = match_lang_only.group(1).strip()
                    if match_lang_only.group(2): source_language_direct = match_lang_only.group(2).strip()
                text_for_ai = ""
                source_lang_for_ai = source_language_direct
                if text_to_translate_direct:
                    text_for_ai = text_to_translate_direct
                elif message.is_reply:
                    replied_msg = await message.get_reply_message()
                    if replied_msg and replied_msg.text:
                        text_for_ai = replied_msg.text
                    else:
                        await client.send_message(event.chat_id, "Please reply to a message with text, or provide text directly for translation.", reply_to=message.id)
                        return
                else:
                    await client.send_message(event.chat_id, "Usage: /translate=<target_lang> [text_to_translate]\nOr reply to a message with /translate=<target_lang>", reply_to=message.id)
                    return
                if not target_language:
                    await client.send_message(event.chat_id, "Target language not specified. Usage: /translate=<target_lang>", reply_to=message.id)
                    return
                if not text_for_ai: 
                    await client.send_message(event.chat_id, "No text found to translate.", reply_to=message.id)
                    return
                logger.info(f"SakaiBot Handler: Detected AI command /translate. Target: {target_language}, Source: {source_lang_for_ai}, Text: '{text_for_ai[:50]}...'")
                thinking_msg = await client.send_message(event.chat_id, f"🤖 Translating to {target_language} with {openrouter_model_name}...", reply_to=message.id)
                ai_response_raw = await ai_processor.translate_text_with_phonetics(
                    openrouter_api_key, openrouter_model_name, text_for_ai, target_language, source_language=source_lang_for_ai
                )
                logger.debug(f"SakaiBot Handler: Raw AI Response for /translate: '{ai_response_raw}'")
                ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Received an empty response from translation."
                if len(ai_response_to_send) > MAX_MESSAGE_LENGTH:
                    ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
                await client.edit_message(thinking_msg, ai_response_to_send)
                logger.info(f"SakaiBot Handler: Translation response sent for /translate command.")
                return

            # /analyze=N command
            elif msg_text_lower.startswith("/analyze="):
                if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
                    await client.send_message(event.chat_id, "AI Error: OpenRouter API key or model name not configured for analysis.", reply_to=message.id)
                    logger.error("SakaiBot Handler: /analyze command failed - OpenRouter API key or model not configured.")
                    return

                try:
                    num_messages_to_analyze_str = message.message[len("/analyze="):].strip()
                    if not num_messages_to_analyze_str.isdigit():
                        await client.send_message(event.chat_id, "Usage: /analyze=<number_of_messages>", reply_to=message.id)
                        return
                    num_messages_to_analyze = int(num_messages_to_analyze_str)
                    if not (1 <= num_messages_to_analyze <= 500): # Limit to a reasonable number
                        await client.send_message(event.chat_id, "Number of messages for analysis must be between 1 and 500.", reply_to=message.id)
                        return
                except ValueError:
                    await client.send_message(event.chat_id, "Invalid number for /analyze. Usage: /analyze=<number>", reply_to=message.id)
                    return

                logger.info(f"SakaiBot Handler: Detected AI command /analyze={num_messages_to_analyze}")
                thinking_msg = await client.send_message(event.chat_id, f"🤖 Analyzing last {num_messages_to_analyze} messages with {openrouter_model_name}...", reply_to=message.id)
                
                messages_for_analysis_data = []
                try:
                    # Fetch last N messages from the current chat (monitored_pv_id)
                    # Note: event.chat_id is the same as monitored_pv_id here
                    history = await client.get_messages(event.chat_id, limit=num_messages_to_analyze)
                    me_user = await client.get_me() # Get current user's info

                    for msg_from_history in reversed(history): # Reverse to get chronological order for AI
                        if msg_from_history and msg_from_history.text: # Only consider text messages
                            sender_name = "You" # Default for outgoing messages from self
                            if msg_from_history.sender_id != me_user.id:
                                sender_entity = await msg_from_history.get_sender()
                                if sender_entity and isinstance(sender_entity, TelegramUser):
                                    sender_name = sender_entity.first_name or sender_entity.username or f"User_{sender_entity.id}"
                                elif sender_entity: # Could be a channel or other entity if PV is with a bot/channel
                                    sender_name = sender_entity.title if hasattr(sender_entity, 'title') else f"Entity_{sender_entity.id}"
                                else: # Should not happen if sender_id is present
                                    sender_name = f"User_{msg_from_history.sender_id}"
                            
                            messages_for_analysis_data.append({
                                'sender': sender_name,
                                'text': msg_from_history.text,
                                'timestamp': msg_from_history.date, # This is already a datetime object
                                # 'message_id': msg_from_history.id # Not used in the current AI prompt
                            })
                    
                    if not messages_for_analysis_data:
                        await client.edit_message(thinking_msg, "No text messages found in the recent history to analyze.")
                        return

                    ai_response_raw = await ai_processor.analyze_conversation_messages(
                        openrouter_api_key,
                        openrouter_model_name,
                        messages_for_analysis_data
                    )
                    logger.debug(f"SakaiBot Handler: Raw AI Response for /analyze: '{ai_response_raw[:200]}...'") # Log a snippet
                    ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Received an empty response from analysis."
                    if len(ai_response_to_send) > MAX_MESSAGE_LENGTH:
                        ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
                    await client.edit_message(thinking_msg, ai_response_to_send)
                    logger.info(f"SakaiBot Handler: Analysis response sent for /analyze command.")

                except Exception as e_analyze_fetch:
                    logger.error(f"SakaiBot Handler: Error fetching messages or processing for /analyze: {e_analyze_fetch}", exc_info=True)
                    await client.edit_message(thinking_msg, "Error occurred while preparing messages for analysis.")
                return


        # --- Categorization Command Handling (requires reply) ---
        if not message.is_reply:
            logger.debug("SakaiBot Handler: Message is not a reply and not an AI command. Ignoring for categorization.")
            return
        # ... (Rest of categorization logic remains the same as v12/v11) ...
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

