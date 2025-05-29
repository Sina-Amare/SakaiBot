# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
import os
import re
import sys
import asyncio # For asyncio.create_task()
from telethon import TelegramClient, events, functions, utils
from telethon.tl import types
from telethon.tl.types import Message, User as TelegramUser

import ai_processor

from pydub import AudioSegment

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096
CONFIRMATION_KEYWORD = "confirm"

# --- Worker Task for STT and AI Summary ---
async def _task_process_stt_and_summarize(
    original_event_message: Message, # The message that triggered the /stt command
    replied_voice_message: Message, # The voice message itself
    client: TelegramClient,
    cli_state_ref: dict,
    command_sender_info: str
):
    """
    Handles STT processing, AI summarization, and sending the result.
    Runs as a background asyncio task.
    """
    chat_id_for_response = original_event_message.chat_id
    reply_to_msg_id = original_event_message.id
    
    thinking_msg = await client.send_message(
        chat_id_for_response,
        f"🎧 در حال پردازش پیام صوتی از طرف {command_sender_info} (مرحله ۱: تبدیل به متن)...",
        reply_to=reply_to_msg_id
    )

    downloaded_voice_path = None
    converted_wav_path = f"temp_voice_message_{original_event_message.id}.wav" # Unique temp file name
    audio_segment_obj = None
    
    ffmpeg_path_from_cli = cli_state_ref.get("FFMPEG_PATH_CLI")
    original_env_path = os.environ.get("PATH", "")
    ffmpeg_dir_added_to_path = False

    try:
        if ffmpeg_path_from_cli and os.path.isfile(ffmpeg_path_from_cli):
            ffmpeg_dir = os.path.dirname(ffmpeg_path_from_cli)
            if ffmpeg_dir not in original_env_path.split(os.pathsep):
                logger.info(f"STT_Task: Temporarily adding '{ffmpeg_dir}' to PATH for pydub.")
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + original_env_path
                ffmpeg_dir_added_to_path = True
            else:
                logger.info(f"STT_Task: ffmpeg directory '{ffmpeg_dir}' already in PATH.")
        else:
            logger.info("STT_Task: ffmpeg_path not configured or invalid. pydub will try to find ffmpeg in system PATH.")

        # Download voice message
        base_download_name = f"temp_voice_message_download_{original_event_message.id}"
        downloaded_voice_path = await client.download_media(replied_voice_message.media, file=base_download_name)
        if not downloaded_voice_path or not os.path.exists(downloaded_voice_path):
            raise FileNotFoundError("فایل صوتی دانلود نشد یا پیدا نشد.")
        logger.info(f"STT_Task: Voice downloaded to '{downloaded_voice_path}'. Converting to WAV...")

        # Convert to WAV
        audio_segment_obj = AudioSegment.from_file(downloaded_voice_path)
        audio_segment_obj.export(converted_wav_path, format="wav")
        logger.info(f"STT_Task: Voice converted to '{converted_wav_path}'.")
        del audio_segment_obj
        audio_segment_obj = None

        # Transcribe
        transcribed_text = await ai_processor.transcribe_voice_to_text(converted_wav_path)

        if "STT Error:" in transcribed_text:
            await client.edit_message(thinking_msg, f"⚠️ {transcribed_text}")
            return

        await client.edit_message(
            thinking_msg,
            f"🎤 **متن پیام صوتی:**\n{transcribed_text}\n\n"
            f"⏳ (مرحله ۲: تحلیل و خلاصه‌سازی توسط AI)..."
        )

        # AI Summarization
        openrouter_api_key = cli_state_ref.get("OPENROUTER_API_KEY_CLI")
        openrouter_model_name = cli_state_ref.get("OPENROUTER_MODEL_NAME_CLI")

        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 10 and openrouter_model_name):
            summary_text = "خطای پیکربندی: کلید یا مدل OpenRouter برای خلاصه‌سازی تنظیم نشده است."
            logger.warning("STT_Task: OpenRouter not configured for summarization.")
        else:
            summary_prompt = (
                f"متن زیر از یک پیام صوتی استخراج شده است. لطفاً یک خلاصه واضح و شفاف از نکات اصلی آن به زبان فارسی و در چند جمله کوتاه ارائه دهید:\n\n"
                f"---\n{transcribed_text}\n---\n\n"
                f"خلاصه:"
            )
            system_message_summary = "شما یک دستیار خلاصه‌کننده متن هستید که متون فارسی را به طور دقیق و مختصر خلاصه می‌کنید."
            summary_text = await ai_processor.execute_custom_prompt(
                api_key=openrouter_api_key,
                model_name=openrouter_model_name,
                user_text_prompt=summary_prompt,
                system_message=system_message_summary,
                max_tokens=300, # Adjust as needed for summary length
                temperature=0.5
            )
            if "AI Error:" in summary_text:
                logger.error(f"STT_Task: AI summarization failed: {summary_text}")

        final_response = (
            f"🎤 **متن پیام صوتی:**\n{transcribed_text}\n\n"
            f"🔍 **خلاصه و تحلیل هوش مصنوعی:**\n{summary_text}"
        )
        if len(final_response) > MAX_MESSAGE_LENGTH:
            # Truncate intelligently if possible, or just the end
            summary_part_len = len(summary_text)
            transcribed_part_len = len(transcribed_text)
            header_len = len(final_response) - summary_part_len - transcribed_part_len
            
            available_len_for_texts = MAX_MESSAGE_LENGTH - header_len - 20 # 20 for "... (truncated)"
            
            if available_len_for_texts < 100: # Not enough space for anything meaningful
                final_response = final_response[:MAX_MESSAGE_LENGTH - 20] + "... (بریده شد)"
            else:
                # Prioritize showing full summary if possible
                if summary_part_len < available_len_for_texts / 2 :
                    allowed_transcribed_len = available_len_for_texts - summary_part_len
                    transcribed_text_short = transcribed_text[:allowed_transcribed_len] + "..." if len(transcribed_text) > allowed_transcribed_len else transcribed_text
                else: # Allocate space proportionally or prioritize summary
                    allowed_summary_len = int(available_len_for_texts * 0.4)
                    allowed_transcribed_len = available_len_for_texts - allowed_summary_len
                    transcribed_text_short = transcribed_text[:allowed_transcribed_len] + "..." if len(transcribed_text) > allowed_transcribed_len else transcribed_text
                    summary_text = summary_text[:allowed_summary_len] + "..." if len(summary_text) > allowed_summary_len else summary_text


                final_response = (
                    f"🎤 **متن پیام صوتی:**\n{transcribed_text_short}\n\n"
                    f"🔍 **خلاصه و تحلیل هوش مصنوعی:**\n{summary_text}\n... (بخش‌هایی بریده شد)"
                )


        await client.edit_message(thinking_msg, final_response)

    except FileNotFoundError as e_fnf:
        logger.error(f"STT_Task: FileNotFoundError: {e_fnf}", exc_info=True)
        await client.edit_message(thinking_msg, f"خطای STT (وظیفه پس‌زمینه): فایل پیدا نشد. {e_fnf}")
    except Exception as e_task:
        logger.error(f"STT_Task: Unexpected error: {e_task}", exc_info=True)
        await client.edit_message(thinking_msg, f"خطای STT (وظیفه پس‌زمینه): یک خطای پیش‌بینی نشده رخ داد: {e_task}")
    finally:
        if ffmpeg_dir_added_to_path:
            os.environ["PATH"] = original_env_path
            logger.info(f"STT_Task: Restored original PATH.")
        if audio_segment_obj: del audio_segment_obj
        files_to_clean = [downloaded_voice_path, converted_wav_path]
        for f_path in files_to_clean:
            if f_path and os.path.exists(f_path):
                for _ in range(3):
                    try:
                        os.remove(f_path)
                        logger.info(f"STT_Task: Cleaned up temp file: {f_path}")
                        break
                    except PermissionError as e_perm:
                        logger.warning(f"STT_Task: PermissionError cleaning up {f_path} (attempt {_ + 1}/3): {e_perm}. Retrying...")
                        await asyncio.sleep(0.1)
                    except Exception as e_clean:
                        logger.error(f"STT_Task: Error cleaning up {f_path}: {e_clean}")
                        break
                else:
                    logger.error(f"STT_Task: Failed to clean up {f_path} after multiple attempts.")

# --- Worker Tasks for other AI commands ---
async def _task_ai_command_handler(
    command_type: str, # e.g., "prompt", "translate", "analyze", "tellme"
    event_message: Message, # The message that triggered the command
    client: TelegramClient,
    cli_state_ref: dict,
    command_sender_info: str,
    **command_args # Specific args for each command like user_prompt, num_messages etc.
):
    chat_id = event_message.chat_id
    reply_to_id = event_message.id
    openrouter_api_key = cli_state_ref.get("OPENROUTER_API_KEY_CLI")
    openrouter_model_name = cli_state_ref.get("OPENROUTER_MODEL_NAME_CLI")
    max_analyze_messages = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 5000)

    thinking_msg_text = f"🤖 در حال پردازش دستور {command_type} شما از طرف {command_sender_info}..."
    thinking_msg = await client.send_message(chat_id, thinking_msg_text, reply_to=reply_to_id)
    
    ai_response_to_send = "خطای داخلی: نتیجه‌ای از پردازش دستور حاصل نشد."

    try:
        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 10 and openrouter_model_name):
            ai_response_to_send = "AI Error: OpenRouter API key or model name not configured correctly."
        elif command_type == "/prompt":
            user_prompt_text = command_args.get("user_prompt_text")
            if not user_prompt_text:
                ai_response_to_send = "Usage: /prompt=<your question or instruction>"
            else:
                ai_response_raw = await ai_processor.execute_custom_prompt(api_key=openrouter_api_key, model_name=openrouter_model_name, user_text_prompt=user_prompt_text)
                ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Received an empty response."
        
        elif command_type == "/translate":
            text_for_ai = command_args.get("text_for_ai")
            target_language = command_args.get("target_language")
            source_lang_for_ai = command_args.get("source_lang_for_ai", "auto")
            if not text_for_ai or not target_language:
                 ai_response_to_send = "Usage: /translate=<lang>[,source_lang] [text] or reply with /translate=<lang>"
            else:
                ai_response_raw = await ai_processor.translate_text_with_phonetics(openrouter_api_key, openrouter_model_name, text_for_ai, target_language, source_language=source_lang_for_ai)
                ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Empty translation."

        elif command_type == "/analyze":
            num_messages = command_args.get("num_messages")
            chat_to_analyze_id = chat_id # Always current chat
            messages_for_analysis_data = []
            history = await client.get_messages(chat_to_analyze_id, limit=num_messages)
            me_user = await client.get_me()
            for msg_from_history in reversed(history):
                if msg_from_history and msg_from_history.text:
                    sender_name_str = "You" if msg_from_history.sender_id == me_user.id else (getattr(msg_from_history.sender, 'first_name', None) or getattr(msg_from_history.sender, 'username', None) or f"User_{msg_from_history.sender_id}")
                    messages_for_analysis_data.append({'sender': sender_name_str, 'text': msg_from_history.text, 'timestamp': msg_from_history.date})
            if not messages_for_analysis_data:
                ai_response_to_send = "No text messages found in the specified history to analyze."
            else:
                ai_response_raw = await ai_processor.analyze_conversation_messages(openrouter_api_key, openrouter_model_name, messages_for_analysis_data)
                ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Empty analysis."
        
        elif command_type == "/tellme":
            num_messages = command_args.get("num_messages")
            user_question = command_args.get("user_question")
            chat_to_query_id = chat_id # Always current chat
            history_messages_data = []
            history = await client.get_messages(chat_to_query_id, limit=num_messages)
            me_user = await client.get_me()
            for msg_from_history in reversed(history):
                if msg_from_history and msg_from_history.text:
                    sender_name_str = "You" if msg_from_history.sender_id == me_user.id else (getattr(msg_from_history.sender, 'first_name', None) or getattr(msg_from_history.sender, 'username', None) or f"User_{msg_from_history.sender_id}")
                    history_messages_data.append({'sender': sender_name_str, 'text': msg_from_history.text, 'timestamp': msg_from_history.date})
            if not history_messages_data:
                ai_response_to_send = "No text messages found in history to answer your question."
            else:
                ai_response_raw = await ai_processor.answer_question_from_chat_history(openrouter_api_key,openrouter_model_name,history_messages_data,user_question)
                ai_response_to_send = ai_response_raw if ai_response_raw and ai_response_raw.strip() else "AI Error: Empty response."

        if len(ai_response_to_send) > MAX_MESSAGE_LENGTH:
            ai_response_to_send = ai_response_to_send[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
        await client.edit_message(thinking_msg, ai_response_to_send)

    except Exception as e_task:
        logger.error(f"AI_Task ({command_type}): Unexpected error: {e_task}", exc_info=True)
        try:
            await client.edit_message(thinking_msg, f"خطای {command_type} (وظیفه پس‌زمینه): یک خطای پیش‌بینی نشده رخ داد: {e_task}")
        except Exception: # If editing fails too
            pass # Error already logged


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
    is_stt_command = False
    if message_to_process and message_to_process.text:
        is_stt_command = message_to_process.text.strip().lower().startswith("/stt")

    if not message_to_process or (not message_to_process.text and not is_stt_command) :
        logger.debug("SakaiBot Core Logic: No valid message text/STT command.")
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return
    
    command_text_to_parse = message_to_process.text.strip() if message_to_process.text else ""
    ai_reply_target_message_id = message_to_process.id # Used for direct responses/errors

    # --- Determine Command Sender ---
    command_sender_info = "You (direct)"
    # ... (sender info logic remains same) ...
    if is_confirm_flow:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"
    elif is_direct_auth_user_command:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"


    # --- STT Command Handling (Launch as Task) ---
    if command_text_to_parse.lower().startswith("/stt"):
        if not message_to_process.is_reply:
            await client.send_message(current_chat_id_for_response, "لطفاً دستور /stt را در پاسخ به یک پیام صوتی ارسال کنید.", reply_to=ai_reply_target_message_id)
        else:
            replied_message = await message_to_process.get_reply_message()
            if not (replied_message and replied_message.voice):
                await client.send_message(current_chat_id_for_response, "پیام پاسخ داده شده یک پیام صوتی نیست.", reply_to=ai_reply_target_message_id)
            else:
                logger.info(f"SakaiBot Handler: Creating task for /stt command from '{command_sender_info}'.")
                # Send initial ack, task will edit this or send new
                # await client.send_message(current_chat_id_for_response, f"🎤 دستور /stt دریافت شد، پردازش در پس‌زمینه...", reply_to=ai_reply_target_message_id)
                asyncio.create_task(_task_process_stt_and_summarize(
                    original_event_message=message_to_process,
                    replied_voice_message=replied_message,
                    client=client,
                    cli_state_ref=cli_state_ref,
                    command_sender_info=command_sender_info
                ))
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return # Command launched as task

    # --- Other AI Commands (Launch as Tasks) ---
    ai_task_args = None
    command_type_for_task = None

    if command_text_to_parse.lower().startswith("/prompt="):
        command_type_for_task = "/prompt"
        user_prompt_text = command_text_to_parse[len("/prompt="):].strip()
        if not user_prompt_text:
             await client.send_message(current_chat_id_for_response, "Usage: /prompt=<your question or instruction>", reply_to=ai_reply_target_message_id)
        else:
            ai_task_args = {"user_prompt_text": user_prompt_text}

    elif command_text_to_parse.lower().startswith("/translate="):
        command_type_for_task = "/translate"
        command_parts_str = command_text_to_parse[len("/translate="):].strip()
        target_language, text_to_translate_direct, source_language_direct = None, None, "auto"
        # ... (parsing logic for /translate arguments as before) ...
        match_with_text = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?\s+(.+)", command_parts_str, re.DOTALL)
        match_lang_only = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?$", command_parts_str)
        if match_with_text:
            target_language = match_with_text.group(1).strip();
            if match_with_text.group(2): source_language_direct = match_with_text.group(2).strip()
            text_to_translate_direct = match_with_text.group(3).strip()
        elif match_lang_only:
            target_language = match_lang_only.group(1).strip()
            if match_lang_only.group(2): source_language_direct = match_lang_only.group(2).strip()
        
        text_for_ai = ""
        if text_to_translate_direct: text_for_ai = text_to_translate_direct
        elif message_to_process.is_reply:
            replied_msg_for_translate = await message_to_process.get_reply_message()
            if replied_msg_for_translate and replied_msg_for_translate.text: text_for_ai = replied_msg_for_translate.text
        
        if not target_language or not text_for_ai:
            await client.send_message(current_chat_id_for_response, "Usage: /translate=<lang>[,source_lang] [text] or reply with /translate=<lang>", reply_to=ai_reply_target_message_id)
        else:
            ai_task_args = {"text_for_ai": text_for_ai, "target_language": target_language, "source_lang_for_ai": source_language_direct}


    elif command_text_to_parse.lower().startswith("/analyze="):
        command_type_for_task = "/analyze"
        try:
            num_messages_to_analyze_str = command_text_to_parse[len("/analyze="):].strip()
            if not num_messages_to_analyze_str.isdigit(): raise ValueError("Not a digit")
            num_messages = int(num_messages_to_analyze_str)
            max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 5000)
            if not (1 <= num_messages <= max_limit): raise ValueError(f"Must be 1-{max_limit}")
            ai_task_args = {"num_messages": num_messages}
        except ValueError as e:
            await client.send_message(current_chat_id_for_response, f"Usage: /analyze=<number_between_1_and_{cli_state_ref.get('MAX_ANALYZE_MESSAGES_CLI', 5000)}>. Error: {e}", reply_to=ai_reply_target_message_id)


    elif command_text_to_parse.lower().startswith("/tellme="):
        command_type_for_task = "/tellme"
        tellme_match = re.match(r"/tellme=(\d+)=(.+)", command_text_to_parse, re.IGNORECASE | re.DOTALL)
        if not tellme_match:
            await client.send_message(current_chat_id_for_response, "Usage: /tellme=<number_of_messages>=<your_question>", reply_to=ai_reply_target_message_id)
        else:
            try:
                num_messages = int(tellme_match.group(1))
                user_question = tellme_match.group(2).strip()
                max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 5000)
                if not (1 <= num_messages <= max_limit): raise ValueError(f"Num messages must be 1-{max_limit}")
                if not user_question: raise ValueError("Question cannot be empty")
                ai_task_args = {"num_messages": num_messages, "user_question": user_question}
            except ValueError as e:
                 await client.send_message(current_chat_id_for_response, f"Error in /tellme format or values. {e}", reply_to=ai_reply_target_message_id)

    if command_type_for_task and ai_task_args is not None:
        logger.info(f"SakaiBot Handler: Creating task for {command_type_for_task} from '{command_sender_info}'.")
        # await client.send_message(current_chat_id_for_response, f"🤖 دستور {command_type_for_task} دریافت شد، پردازش در پس‌زمینه...", reply_to=ai_reply_target_message_id)
        asyncio.create_task(_task_ai_command_handler(
            command_type=command_type_for_task,
            event_message=message_to_process,
            client=client,
            cli_state_ref=cli_state_ref,
            command_sender_info=command_sender_info,
            **ai_task_args
        ))
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return # AI Command launched as task


    # --- Categorization Command Handling (Synchronous for now) ---
    if message_to_process.is_reply and command_text_to_parse.startswith('/'):
        categorization_group_id = cli_state_ref.get("selected_target_group", {}).get('id') if cli_state_ref.get("selected_target_group") else None
        command_topic_map = cli_state_ref.get("active_command_to_topic_map", {})
        if categorization_group_id is None or not command_topic_map:
            logger.debug("SakaiBot Handler: Categorization target group or command map not set/empty. Skipping categorization.")
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete();
            return # Explicitly return if no categorization settings, and it wasn't an AI command above
        
        command_for_categorization = command_text_to_parse[1:].lower().strip()
        if command_for_categorization in command_topic_map:
            logger.info(f"SakaiBot Handler: Processing categorization command '/{command_for_categorization}'.")
            if not actual_message_for_categorization_content:
                logger.warning("SakaiBot Handler: No actual message content found to categorize.");
                if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
                return
            
            target_topic_id = command_topic_map[command_for_categorization]
            # ... (rest of categorization logic as before) ...
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
            except Exception as e_fwd:
                logger.error(f"SakaiBot Handler: Error forwarding for categorization: {e_fwd}", exc_info=True)
                await client.send_message(current_chat_id_for_response, f"خطا در ارسال پیام برای دسته‌بندی: {e_fwd}", reply_to=ai_reply_target_message_id)
            
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return # Categorization handled

    # If it's a confirm flow and the friend's message was NOT any recognized command
    if is_confirm_flow and command_type_for_task is None and not (message_to_process.is_reply and command_text_to_parse.startswith('/') and command_text_to_parse[1:].lower().strip() in command_topic_map):
        logger.info(f"SakaiBot Handler (Confirm Flow): Friend's message '{command_text_to_parse[:50]}...' was not a recognized command.")
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
            # This case might be complex if friend's /stt needs the voice.
            # The actual_message_for_categorization_content is primarily for categorization's source message.
            # For /stt, the replied_voice_message is handled inside _task_process_stt_and_summarize
            # from the message_to_process_cmd.
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

    if not message_to_process_cmd:
        logger.debug("SakaiBot Owner Handler: message_to_process_cmd was not set.")
        return

    await process_command_logic(
        message_to_process=message_to_process_cmd,
        client=client_instance,
        current_chat_id_for_response=event.chat_id, # Respond in owner's chat
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

    await process_command_logic(
        message_to_process=message_from_auth_user,
        client=client_instance,
        current_chat_id_for_response=event.chat_id, # Respond in auth user's chat
        is_confirm_flow=False, # Not a confirm flow here
        your_confirm_message=None,
        actual_message_for_categorization_content=actual_message_for_categorization_content_auth,
        cli_state_ref=cli_state_ref,
        is_direct_auth_user_command=True
    )

