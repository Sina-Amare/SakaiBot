# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
import os 
import re 
from telethon import TelegramClient, events, functions, utils 
from telethon.tl import types 
from telethon.tl.types import Message, User as TelegramUser

import ai_processor

logger = logging.getLogger(__name__) 

MAX_MESSAGE_LENGTH = 4096
CONFIRMATION_KEYWORD = "confirm" 

async def process_command_logic(
    message_to_process: Message, 
    client: TelegramClient,
    current_chat_id_for_response: int, 
    is_confirm_flow: bool,
    your_confirm_message: Message or None, 
    actual_message_for_categorization_content: Message or None, 
    default_context_pv_id: int or None, # This will now be ignored by /analyze and /tellme
    categorization_group_id: int or None,
    command_topic_map: dict or None,
    openrouter_api_key: str or None,
    openrouter_model_name: str or None,
    max_analyze_messages_limit: int,
    is_direct_auth_user_command: bool = False
):
    """
    Core logic for processing commands.
    All AI commands (/prompt, /analyze, /tellme) now use the current chat context
    where the command was issued.
    """
    if not message_to_process or not message_to_process.text:
        logger.debug("SakaiBot Core Logic: No valid message text to process in message_to_process.")
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return

    command_text_to_parse = message_to_process.text.strip()
    ai_reply_target_message_id = message_to_process.id
    
    command_sender_info = "You (direct)"
    if is_confirm_flow:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"
    elif is_direct_auth_user_command:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"

    # --- AI Command Handling ---
    if command_text_to_parse.lower().startswith("/prompt="):
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
            await client.send_message(current_chat_id_for_response, "AI Error: OpenRouter API key or model name not configured.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete(); return
        user_prompt_text = command_text_to_parse[len("/prompt="):].strip()
        if not user_prompt_text:
            await client.send_message(current_chat_id_for_response, "Usage: /prompt=<your question or instruction>", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete(); return
        logger.info(f"SakaiBot Handler: AI /prompt from '{command_sender_info}' in chat {current_chat_id_for_response}: '{user_prompt_text[:50]}...'")
        thinking_msg = await client.send_message(current_chat_id_for_response, f"🤖 Processing your direct prompt from {command_sender_info}...", reply_to=ai_reply_target_message_id)
        ai_response_raw = await ai_processor.execute_custom_prompt(api_key=openrouter_api_key, model_name=openrouter_model_name, user_text_prompt=user_prompt_text, system_message=None, temperature=0.7, max_tokens=1500)
        logger.debug(f"SakaiBot Handler: Raw AI Response for /prompt: '{ai_response_raw}'")
        ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Received an empty or invalid response from AI."
        if len(ai_response_to_send) > MAX_MESSAGE_LENGTH: ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH-20] + "...(truncated)"
        await client.edit_message(thinking_msg, ai_response_to_send)
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return 

    elif command_text_to_parse.lower().startswith("/translate="):
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
            await client.send_message(current_chat_id_for_response, "AI Error: OpenRouter API key or model name not configured.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete(); return
        command_parts_str = command_text_to_parse[len("/translate="):].strip()
        target_language = None; text_to_translate_direct = None; source_language_direct = "auto" 
        match_with_text = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?\s+(.+)", command_parts_str, re.DOTALL)
        match_lang_only = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?$", command_parts_str)
        if match_with_text:
            target_language = match_with_text.group(1).strip(); 
            if match_with_text.group(2): source_language_direct = match_with_text.group(2).strip()
            text_to_translate_direct = match_with_text.group(3).strip()
        elif match_lang_only:
            target_language = match_lang_only.group(1).strip()
            if match_lang_only.group(2): source_language_direct = match_lang_only.group(2).strip()
        text_for_ai = ""; source_lang_for_ai = source_language_direct
        if text_to_translate_direct: text_for_ai = text_to_translate_direct
        elif message_to_process.is_reply: 
            replied_msg_for_translate = await message_to_process.get_reply_message()
            if replied_msg_for_translate and replied_msg_for_translate.text: text_for_ai = replied_msg_for_translate.text
            else: await client.send_message(current_chat_id_for_response, "Replied message (for translation) has no text.", reply_to=ai_reply_target_message_id); return
        else: await client.send_message(current_chat_id_for_response, "Usage: /translate=<lang> [text] or reply with /translate=<lang>", reply_to=ai_reply_target_message_id); return
        if not target_language: await client.send_message(current_chat_id_for_response, "Target language not specified.", reply_to=ai_reply_target_message_id); return
        if not text_for_ai: await client.send_message(current_chat_id_for_response, "No text to translate.", reply_to=ai_reply_target_message_id); return
        logger.info(f"SakaiBot Handler: AI /translate from '{command_sender_info}'. Target: {target_language}, Text: '{text_for_ai[:50]}...'")
        thinking_msg = await client.send_message(current_chat_id_for_response, f"🤖 Translating for {command_sender_info} to {target_language}...", reply_to=ai_reply_target_message_id)
        ai_response_raw = await ai_processor.translate_text_with_phonetics(openrouter_api_key, openrouter_model_name, text_for_ai, target_language, source_language=source_lang_for_ai)
        ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Empty translation."
        if len(ai_response_to_send) > MAX_MESSAGE_LENGTH: ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH-20] + "...(truncated)"
        await client.edit_message(thinking_msg, ai_response_to_send)
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return

    elif command_text_to_parse.lower().startswith("/analyze="):
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
            await client.send_message(current_chat_id_for_response, "AI Error: OpenRouter API key or model not configured.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete(); return
        try:
            num_messages_to_analyze_str = command_text_to_parse[len("/analyze="):].strip()
            if not num_messages_to_analyze_str.isdigit(): await client.send_message(current_chat_id_for_response, "Usage: /analyze=<number>", reply_to=ai_reply_target_message_id); return
            num_messages_to_analyze = int(num_messages_to_analyze_str)
            if not (1 <= num_messages_to_analyze <= max_analyze_messages_limit): 
                await client.send_message(current_chat_id_for_response, f"Number for /analyze must be 1-{max_analyze_messages_limit}.", reply_to=ai_reply_target_message_id); return
        except ValueError: await client.send_message(current_chat_id_for_response, "Invalid number for /analyze.", reply_to=ai_reply_target_message_id); return
        
        # <<< --- MODIFICATION for /analyze --- >>>
        # /analyze ALWAYS uses the history of the chat where the command was issued.
        chat_to_analyze_id = current_chat_id_for_response 
        logger.info(f"SakaiBot Handler: /analyze will use current chat ID: {chat_to_analyze_id} for history.")
        
        logger.info(f"SakaiBot Handler: AI /analyze={num_messages_to_analyze} for chat {chat_to_analyze_id} (requested by {command_sender_info})")
        thinking_msg = await client.send_message(current_chat_id_for_response, f"🤖 Analyzing last {num_messages_to_analyze} messages from chat '{chat_to_analyze_id}'...", reply_to=ai_reply_target_message_id)
        
        messages_for_analysis_data = []
        try:
            history = await client.get_messages(chat_to_analyze_id, limit=num_messages_to_analyze)
            me_user = await client.get_me()
            for msg_from_history in reversed(history): 
                if msg_from_history and msg_from_history.text:
                    sender_name_str = "You" if msg_from_history.sender_id == me_user.id else (getattr(msg_from_history.sender, 'first_name', None) or getattr(msg_from_history.sender, 'username', None) or f"User_{msg_from_history.sender_id}")
                    messages_for_analysis_data.append({'sender': sender_name_str, 'text': msg_from_history.text, 'timestamp': msg_from_history.date})
            if not messages_for_analysis_data: 
                await client.edit_message(thinking_msg, "No text messages found in the specified history to analyze.")
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
                return
            ai_response_raw = await ai_processor.analyze_conversation_messages(openrouter_api_key, openrouter_model_name, messages_for_analysis_data)
            ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Empty analysis."
            if len(ai_response_to_send) > MAX_MESSAGE_LENGTH: ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH-20] + "...(truncated)"
            await client.edit_message(thinking_msg, ai_response_to_send)
        except Exception as e_analyze_fetch:
            logger.error(f"SakaiBot Handler: Error in /analyze: {e_analyze_fetch}", exc_info=True)
            await client.edit_message(thinking_msg, "Error during analysis.")
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return

    elif command_text_to_parse.lower().startswith("/tellme="):
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 50 and openrouter_model_name):
            await client.send_message(current_chat_id_for_response, "AI Error: OpenRouter API key or model name not configured.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return

        tellme_match = re.match(r"/tellme=(\d+)=(.+)", command_text_to_parse, re.IGNORECASE | re.DOTALL)
        if not tellme_match:
            await client.send_message(current_chat_id_for_response, "Usage: /tellme=<number_of_messages>=<your_question>", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return

        try:
            num_messages_for_tellme = int(tellme_match.group(1))
            user_question_for_tellme = tellme_match.group(2).strip()

            if not (1 <= num_messages_for_tellme <= max_analyze_messages_limit): # Use the same limit as /analyze
                await client.send_message(current_chat_id_for_response, f"Number of messages for /tellme must be between 1 and {max_analyze_messages_limit}.", reply_to=ai_reply_target_message_id)
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
                return
            if not user_question_for_tellme:
                await client.send_message(current_chat_id_for_response, "Question part of /tellme cannot be empty.", reply_to=ai_reply_target_message_id)
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
                return
        except ValueError:
            await client.send_message(current_chat_id_for_response, "Invalid number for /tellme.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return

        # /tellme ALWAYS uses the history of the chat where the command was issued.
        chat_to_query_id = current_chat_id_for_response 
        
        logger.info(f"SakaiBot Handler: AI /tellme in chat {current_chat_id_for_response}. N={num_messages_for_tellme}, Q='{user_question_for_tellme[:50]}...' (Chat for history: {chat_to_query_id})")
        thinking_msg = await client.send_message(current_chat_id_for_response, f"🤖 Searching last {num_messages_for_tellme} messages in chat '{chat_to_query_id}' for your question...", reply_to=ai_reply_target_message_id)
        
        history_messages_data = []
        try:
            history = await client.get_messages(chat_to_query_id, limit=num_messages_for_tellme) 
            me_user = await client.get_me()
            for msg_from_history in reversed(history):
                if msg_from_history and msg_from_history.text:
                    sender_name_str = "You" if msg_from_history.sender_id == me_user.id else (getattr(msg_from_history.sender, 'first_name', None) or getattr(msg_from_history.sender, 'username', None) or f"User_{msg_from_history.sender_id}")
                    history_messages_data.append({'sender': sender_name_str, 'text': msg_from_history.text, 'timestamp': msg_from_history.date})
            
            if not history_messages_data:
                await client.edit_message(thinking_msg, "No text messages found in the specified history to answer your question.")
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
                return

            ai_response_raw = await ai_processor.answer_question_from_chat_history(
                openrouter_api_key,
                openrouter_model_name,
                history_messages_data,
                user_question_for_tellme
            )
            logger.debug(f"SakaiBot Handler: Raw AI Response for /tellme: '{ai_response_raw[:200]}...'")
            ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Received an empty or unclear response."
            if len(ai_response_to_send) > MAX_MESSAGE_LENGTH:
                ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
            await client.edit_message(thinking_msg, ai_response_to_send)
            logger.info(f"SakaiBot Handler: Response sent for /tellme in chat {current_chat_id_for_response}.")

        except Exception as e_tellme_fetch:
            logger.error(f"SakaiBot Handler: Error fetching/processing for /tellme: {e_tellme_fetch}", exc_info=True)
            await client.edit_message(thinking_msg, "Error occurred while preparing context for your question.")
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return


    # --- Categorization Command Handling ---
    if message_to_process.is_reply and command_text_to_parse.startswith('/'):
        if categorization_group_id is None or command_topic_map is None:
            logger.debug("SakaiBot Handler: Categorization target/map not set globally. Skipping categorization.")
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete(); return 
        command_for_categorization = command_text_to_parse[1:].lower().strip()
        logger.info(f"SakaiBot Handler: Processing categorization command '/{command_for_categorization}'.")
        if command_for_categorization in command_topic_map:
            if not actual_message_for_categorization_content: 
                logger.warning("SakaiBot Handler: No actual message content found to categorize."); 
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete(); return
            target_topic_id = command_topic_map[command_for_categorization] 
            log_target_desc = f"Topic ID {target_topic_id}" if target_topic_id is not None else "Main Group Chat"
            logger.info(f"SakaiBot Handler: Cat. command '/{command_for_categorization}' maps to {log_target_desc} in group {categorization_group_id}.")
            media_type_log = type(actual_message_for_categorization_content.media).__name__ if actual_message_for_categorization_content.media else "Text"
            logger.info(f"SakaiBot Handler: Forwarding for categorization: original msg (ID {actual_message_for_categorization_content.id}, Type: {media_type_log}) to group {categorization_group_id}, target: {log_target_desc}.")
            try:
                source_peer_input = await client.get_input_entity(actual_message_for_categorization_content.chat_id)
                destination_peer_input = await client.get_input_entity(categorization_group_id)
                generated_random_id = int.from_bytes(os.urandom(8), 'little', signed=True)
                fwd_request_params = {'from_peer': source_peer_input, 'id': [actual_message_for_categorization_content.id], 'to_peer': destination_peer_input, 'random_id': [generated_random_id]}
                if target_topic_id is not None: fwd_request_params['top_msg_id'] = target_topic_id
                await client(functions.messages.ForwardMessagesRequest(**fwd_request_params))
                logger.info(f"SakaiBot Handler: Message successfully forwarded for categorization command '/{command_for_categorization}'.")
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete() 
            except Exception as e_fwd: logger.error(f"SakaiBot Handler: Error forwarding for categorization: {e_fwd}", exc_info=True)
        else:
            logger.debug(f"SakaiBot Handler: Categorization command '/{command_for_categorization}' not found in defined mappings.")
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
    elif is_confirm_flow: 
        logger.info(f"SakaiBot Handler (Confirm Flow): Friend's message '{command_text_to_parse[:50]}...' was not a recognized AI or categorization command.")
        if your_confirm_message: await your_confirm_message.delete()

async def categorization_reply_handler_owner(event: events.NewMessage.Event, **kwargs):
    your_message = event.message 
    message_to_process_cmd = None
    is_confirm_flow_local = False 
    your_confirm_message_local = None
    actual_message_for_categorization_content_owner = None 
    if your_message.is_reply and your_message.text and your_message.text.strip().lower() == CONFIRMATION_KEYWORD:
        logger.info(f"SakaiBot Owner Handler: Detected '{CONFIRMATION_KEYWORD}' reply from you.")
        friends_command_message = await your_message.get_reply_message()
        if friends_command_message and friends_command_message.text:
            message_to_process_cmd = friends_command_message
            is_confirm_flow_local = True
            your_confirm_message_local = your_message 
            if friends_command_message.is_reply and friends_command_message.reply_to_msg_id:
                actual_message_for_categorization_content_owner = await friends_command_message.get_reply_message()
        else:
            logger.warning("SakaiBot Owner Handler: Your 'confirm' was a reply, but could not fetch the friend's command message or it had no text.")
            await kwargs['client'].send_message(event.chat_id, "Could not process 'confirm'. Replied message not found or no text.", reply_to=your_message.id)
            return
    else:
        message_to_process_cmd = your_message
        is_confirm_flow_local = False
        your_confirm_message_local = None 
        if your_message.is_reply and your_message.reply_to_msg_id:
            actual_message_for_categorization_content_owner = await your_message.get_reply_message()
    if not message_to_process_cmd: 
        logger.error("SakaiBot Owner Handler: message_to_process_cmd was not set.")
        return
    await process_command_logic(
        message_to_process=message_to_process_cmd, client=kwargs['client'],
        current_chat_id_for_response=event.chat_id, is_confirm_flow=is_confirm_flow_local,
        your_confirm_message=your_confirm_message_local,
        actual_message_for_categorization_content=actual_message_for_categorization_content_owner, 
        default_context_pv_id=kwargs['default_context_pv_id'],
        categorization_group_id=kwargs['categorization_group_id'], command_topic_map=kwargs['command_topic_map'],
        openrouter_api_key=kwargs['openrouter_api_key'], openrouter_model_name=kwargs['openrouter_model_name'],
        max_analyze_messages_limit=kwargs['max_analyze_messages_limit'], is_direct_auth_user_command=False
    )

async def authorized_user_command_handler(event: events.NewMessage.Event, **kwargs):
    logger.info(f"SakaiBot AuthUser Handler: Incoming message from authorized user. Chat ID: {event.chat_id}, Sender ID: {event.sender_id}, Msg ID: {event.message.id}")
    message_from_auth_user = event.message
    actual_message_for_categorization_content_auth = None
    if message_from_auth_user.is_reply and message_from_auth_user.reply_to_msg_id:
        actual_message_for_categorization_content_auth = await message_from_auth_user.get_reply_message()
    await process_command_logic(
        message_to_process=message_from_auth_user, client=kwargs['client'],
        current_chat_id_for_response=event.chat_id, is_confirm_flow=False, 
        your_confirm_message=None, actual_message_for_categorization_content=actual_message_for_categorization_content_auth, 
        default_context_pv_id=event.chat_id, 
        categorization_group_id=kwargs['categorization_group_id'], command_topic_map=kwargs['command_topic_map'],
        openrouter_api_key=kwargs['openrouter_api_key'], openrouter_model_name=kwargs['openrouter_model_name'],
        max_analyze_messages_limit=kwargs['max_analyze_messages_limit'], is_direct_auth_user_command=True
    )
