# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
import os
import re
import sys # For path manipulation if needed, though os.environ is key
from telethon import TelegramClient, events, functions, utils
from telethon.tl import types
from telethon.tl.types import Message, User as TelegramUser

import ai_processor

# For STT audio conversion
from pydub import AudioSegment

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
    cli_state_ref: dict,
    is_direct_auth_user_command: bool = False
):
    if not message_to_process or not message_to_process.text:
        is_stt_command_candidate = False
        if message_to_process and message_to_process.text:
             is_stt_command_candidate = message_to_process.text.strip().lower().startswith("/stt")
        if not is_stt_command_candidate:
            logger.debug("SakaiBot Core Logic: No valid message text to process and not an STT command.")
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return
        elif is_stt_command_candidate and not message_to_process.is_reply:
            await client.send_message(current_chat_id_for_response, "لطفاً دستور /stt را در پاسخ به یک پیام صوتی ارسال کنید.", reply_to=message_to_process.id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return

    command_text_to_parse = message_to_process.text.strip() if message_to_process.text else ""
    ai_reply_target_message_id = message_to_process.id

    openrouter_api_key = cli_state_ref.get("OPENROUTER_API_KEY_CLI")
    openrouter_model_name = cli_state_ref.get("OPENROUTER_MODEL_NAME_CLI")
    max_analyze_messages_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 5000)
    categorization_group_id = cli_state_ref.get("selected_target_group", {}).get('id') if cli_state_ref.get("selected_target_group") else None
    command_topic_map = cli_state_ref.get("active_command_to_topic_map", {})
    ffmpeg_path_from_cli = cli_state_ref.get("FFMPEG_PATH_CLI") # This is path to ffmpeg.exe

    command_sender_info = "You (direct)"
    if is_confirm_flow:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"
    elif is_direct_auth_user_command:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"

    if command_text_to_parse.lower().startswith("/stt"):
        if not message_to_process.is_reply:
            await client.send_message(current_chat_id_for_response, "لطفاً دستور /stt را در پاسخ به یک پیام صوتی ارسال کنید.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return

        replied_message = await message_to_process.get_reply_message()
        if not (replied_message and replied_message.voice):
            await client.send_message(current_chat_id_for_response, "پیام پاسخ داده شده یک پیام صوتی نیست.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return

        logger.info(f"SakaiBot Handler: STT /stt command from '{command_sender_info}' in chat {current_chat_id_for_response}.")
        thinking_msg = await client.send_message(current_chat_id_for_response, f"🎧 در حال پردازش پیام صوتی از طرف {command_sender_info}...", reply_to=ai_reply_target_message_id)

        downloaded_voice_path = None
        converted_wav_path = "temp_voice_message.wav"
        audio_segment_obj = None
        
        original_env_path = os.environ.get("PATH", "")
        ffmpeg_dir_to_add = None

        if ffmpeg_path_from_cli and os.path.isfile(ffmpeg_path_from_cli):
            ffmpeg_dir_to_add = os.path.dirname(ffmpeg_path_from_cli)
            if ffmpeg_dir_to_add not in original_env_path.split(os.pathsep):
                logger.info(f"STT: Temporarily adding '{ffmpeg_dir_to_add}' to PATH for pydub.")
                os.environ["PATH"] = ffmpeg_dir_to_add + os.pathsep + original_env_path
            else:
                logger.info(f"STT: ffmpeg directory '{ffmpeg_dir_to_add}' already in PATH.")
                ffmpeg_dir_to_add = None # No need to restore if it was already there
        else:
            logger.info("STT: ffmpeg_path not configured or invalid in config.ini. pydub will try to find ffmpeg/ffprobe in system PATH.")

        try:
            downloaded_voice_path = await client.download_media(replied_message.media, file="temp_voice_message_download")
            if not downloaded_voice_path or not os.path.exists(downloaded_voice_path):
                raise FileNotFoundError("فایل صوتی دانلود نشد یا پیدا نشد.")
            logger.info(f"STT: Voice message downloaded to '{downloaded_voice_path}'. Converting to WAV...")

            try:
                audio_segment_obj = AudioSegment.from_file(downloaded_voice_path)
            except FileNotFoundError as e_fnf_pydub:
                logger.error(f"STT: pydub's from_file failed with FileNotFoundError: {e_fnf_pydub}. This often means ffprobe was not found or couldn't be executed.", exc_info=True)
                await client.edit_message(thinking_msg, "خطا در پردازش فایل صوتی: `ffmpeg` یا `ffprobe` پیدا نشد. لطفاً مطمئن شوید `ffmpeg` به درستی نصب شده، مسیر `ffmpeg_executable` در `config.ini` به فایل `ffmpeg.exe` اشاره دارد و پوشه حاوی آن در PATH سیستم قرار دارد یا از طریق `config.ini` به درستی به برنامه معرفی شده است.")
                return
            except Exception as e_decode:
                logger.error(f"STT: pydub could not decode audio file '{downloaded_voice_path}'. Error: {e_decode}", exc_info=True)
                await client.edit_message(thinking_msg, f"خطا در رمزگشایی فایل صوتی: {e_decode}")
                return

            audio_segment_obj.export(converted_wav_path, format="wav")
            logger.info(f"STT: Voice message converted to '{converted_wav_path}'.")

            del audio_segment_obj
            audio_segment_obj = None

            transcribed_text = await ai_processor.transcribe_voice_to_text(converted_wav_path)

            if "STT Error:" in transcribed_text:
                await client.edit_message(thinking_msg, f"⚠️ {transcribed_text}")
            else:
                response_text_stt = f"🎤 **متن پیام صوتی:**\n\n{transcribed_text}"
                if len(response_text_stt) > MAX_MESSAGE_LENGTH:
                    response_text_stt = response_text_stt[:MAX_MESSAGE_LENGTH - 20] + "... (بریده شد)"
                await client.edit_message(thinking_msg, response_text_stt)

        except FileNotFoundError as fnf_err:
            logger.error(f"STT Error: File operation failed (e.g., download). {fnf_err}", exc_info=True)
            await client.edit_message(thinking_msg, f"خطای STT: فایل مورد نیاز پیدا نشد. ({fnf_err}).")
        except Exception as e_stt_main:
            logger.error(f"STT Error: An unexpected error occurred in /stt handler: {e_stt_main}", exc_info=True)
            await client.edit_message(thinking_msg, f"خطای STT: یک خطای پیش‌بینی نشده رخ داد: {e_stt_main}")
        finally:
            if ffmpeg_dir_to_add: # Restore original PATH only if we modified it
                os.environ["PATH"] = original_env_path
                logger.info(f"STT: Restored original PATH.")
            
            if audio_segment_obj:
                del audio_segment_obj

            files_to_clean = [downloaded_voice_path, converted_wav_path]
            for f_path in files_to_clean:
                if f_path and os.path.exists(f_path):
                    for _ in range(3): # Try to remove a few times with a small delay
                        try:
                            os.remove(f_path)
                            logger.info(f"STT: Cleaned up temporary file: {f_path}")
                            break # Exit loop if successful
                        except PermissionError as e_perm:
                            logger.warning(f"STT: PermissionError cleaning up file {f_path} (attempt {_ + 1}/3): {e_perm}. Retrying...")
                            await asyncio.sleep(0.1) # Small delay before retrying
                        except Exception as e_clean:
                            logger.error(f"STT: Error cleaning up file {f_path}: {e_clean}")
                            break # Exit loop on other errors
                    else: # If loop completed without break (all retries failed)
                        logger.error(f"STT: Failed to clean up file {f_path} after multiple attempts due to PermissionError.")


        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return

    # ... (بقیه دستورات AI و دسته‌بندی مثل قبل) ...
    elif command_text_to_parse.lower().startswith("/prompt="):
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 10 and openrouter_model_name): # Basic check
            await client.send_message(current_chat_id_for_response, "AI Error: OpenRouter API key or model name not configured correctly.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return
        user_prompt_text = command_text_to_parse[len("/prompt="):].strip()
        if not user_prompt_text:
            await client.send_message(current_chat_id_for_response, "Usage: /prompt=<your question or instruction>", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return
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
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 10 and openrouter_model_name):
            await client.send_message(current_chat_id_for_response, "AI Error: OpenRouter API key or model name not configured correctly.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return
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
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 10 and openrouter_model_name):
            await client.send_message(current_chat_id_for_response, "AI Error: OpenRouter API key or model not configured.", reply_to=ai_reply_target_message_id)
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete(); return
        try:
            num_messages_to_analyze_str = command_text_to_parse[len("/analyze="):].strip()
            if not num_messages_to_analyze_str.isdigit(): await client.send_message(current_chat_id_for_response, "Usage: /analyze=<number>", reply_to=ai_reply_target_message_id); return
            num_messages_to_analyze = int(num_messages_to_analyze_str)
            if not (1 <= num_messages_to_analyze <= max_analyze_messages_limit):
                await client.send_message(current_chat_id_for_response, f"Number for /analyze must be 1-{max_analyze_messages_limit}.", reply_to=ai_reply_target_message_id); return
        except ValueError: await client.send_message(current_chat_id_for_response, "Invalid number for /analyze.", reply_to=ai_reply_target_message_id); return

        chat_to_analyze_id = current_chat_id_for_response
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
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 10 and openrouter_model_name):
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
            if not (1 <= num_messages_for_tellme <= max_analyze_messages_limit):
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

    if message_to_process.is_reply and command_text_to_parse.startswith('/'):
        if categorization_group_id is None or not command_topic_map:
            logger.debug("SakaiBot Handler: Categorization target group or command map not set/empty. Skipping categorization.")
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete();
        command_for_categorization = command_text_to_parse[1:].lower().strip()
        if command_for_categorization in command_topic_map:
            logger.info(f"SakaiBot Handler: Processing categorization command '/{command_for_categorization}'.")
            if not actual_message_for_categorization_content:
                logger.warning("SakaiBot Handler: No actual message content found to categorize.");
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
                return
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
            return
    elif is_confirm_flow:
        logger.info(f"SakaiBot Handler (Confirm Flow): Friend's message '{command_text_to_parse[:50]}...' was not a recognized AI or categorization command.")
        if your_confirm_message: await your_confirm_message.delete()


async def categorization_reply_handler_owner(event: events.NewMessage.Event, **kwargs):
    your_message = event.message
    client_instance = kwargs['client']
    cli_state_ref = kwargs['cli_state_ref']

    message_to_process_cmd = None
    is_confirm_flow_local = False
    your_confirm_message_local = None
    actual_message_for_categorization_content_owner = None

    if your_message.is_reply and your_message.text and your_message.text.strip().lower() == CONFIRMATION_KEYWORD:
        logger.info(f"SakaiBot Owner Handler: Detected '{CONFIRMATION_KEYWORD}' reply from you.")
        friends_command_message = await your_message.get_reply_message()
        if friends_command_message:
            message_to_process_cmd = friends_command_message
            is_confirm_flow_local = True
            your_confirm_message_local = your_message
            if friends_command_message.is_reply and friends_command_message.reply_to_msg_id:
                actual_message_for_categorization_content_owner = await friends_command_message.get_reply_message()
            elif friends_command_message.voice and friends_command_message.text and friends_command_message.text.strip().lower().startswith("/stt"):
                 actual_message_for_categorization_content_owner = friends_command_message
        else:
            logger.warning("SakaiBot Owner Handler: Your 'confirm' was a reply, but could not fetch the friend's command message.")
            await client_instance.send_message(event.chat_id, "Could not process 'confirm'. Replied message not found.", reply_to=your_message.id)
            return
    else:
        message_to_process_cmd = your_message
        is_confirm_flow_local = False
        your_confirm_message_local = None
        if your_message.is_reply and your_message.reply_to_msg_id:
            actual_message_for_categorization_content_owner = await your_message.get_reply_message()
        elif your_message.voice and your_message.text and your_message.text.strip().lower().startswith("/stt"):
             actual_message_for_categorization_content_owner = your_message

    if not message_to_process_cmd:
        logger.debug("SakaiBot Owner Handler: message_to_process_cmd was not set (e.g. owner sent only 'confirm' not as reply).")
        return

    await process_command_logic(
        message_to_process=message_to_process_cmd,
        client=client_instance,
        current_chat_id_for_response=event.chat_id,
        is_confirm_flow=is_confirm_flow_local,
        your_confirm_message=your_confirm_message_local,
        actual_message_for_categorization_content=actual_message_for_categorization_content_owner,
        cli_state_ref=cli_state_ref,
        is_direct_auth_user_command=False
    )

async def authorized_user_command_handler(event: events.NewMessage.Event, **kwargs):
    logger.info(f"SakaiBot AuthUser Handler: Incoming message from authorized user. Chat ID: {event.chat_id}, Sender ID: {event.sender_id}, Msg ID: {event.message.id}")
    message_from_auth_user = event.message
    client_instance = kwargs['client']
    cli_state_ref = kwargs['cli_state_ref']

    actual_message_for_categorization_content_auth = None
    if message_from_auth_user.is_reply and message_from_auth_user.reply_to_msg_id:
        actual_message_for_categorization_content_auth = await message_from_auth_user.get_reply_message()
    elif message_from_auth_user.voice and message_from_auth_user.text and message_from_auth_user.text.strip().lower().startswith("/stt"):
        actual_message_for_categorization_content_auth = message_from_auth_user

    await process_command_logic(
        message_to_process=message_from_auth_user,
        client=client_instance,
        current_chat_id_for_response=event.chat_id,
        is_confirm_flow=False,
        your_confirm_message=None,
        actual_message_for_categorization_content=actual_message_for_categorization_content_auth,
        cli_state_ref=cli_state_ref,
        is_direct_auth_user_command=True
    )

