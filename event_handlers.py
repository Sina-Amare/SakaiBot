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
DEFAULT_TTS_VOICE = "fa-IR-DilaraNeural" # Default Persian female voice for edge-tts

# --- Worker Task for STT and AI Summary ---
async def _task_process_stt_and_summarize(
    original_event_message: Message,
    replied_voice_message: Message,
    client: TelegramClient,
    cli_state_ref: dict,
    command_sender_info: str
):
    # ... (This function remains the same as in event_handlers_py_v11_gtts_english_complete) ...
    chat_id_for_response = original_event_message.chat_id
    reply_to_msg_id = original_event_message.id
    
    thinking_msg = await client.send_message(
        chat_id_for_response,
        f"🎧 Processing voice message from {command_sender_info} (Step 1: Transcribing)...",
        reply_to=reply_to_msg_id
    )

    downloaded_voice_path = None
    converted_wav_path = f"temp_voice_stt_{original_event_message.id}_{replied_voice_message.id}.wav"
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

        base_download_name = f"temp_voice_download_stt_{original_event_message.id}_{replied_voice_message.id}"
        downloaded_voice_path = await client.download_media(replied_voice_message.media, file=base_download_name)
        if not downloaded_voice_path or not os.path.exists(downloaded_voice_path):
            raise FileNotFoundError("Downloaded voice file not found or download failed.")
        logger.info(f"STT_Task: Voice downloaded to '{downloaded_voice_path}'. Converting to WAV...")

        audio_segment_obj = AudioSegment.from_file(downloaded_voice_path)
        audio_segment_obj.export(converted_wav_path, format="wav")
        logger.info(f"STT_Task: Voice converted to '{converted_wav_path}'.")
        del audio_segment_obj
        audio_segment_obj = None

        transcribed_text = await ai_processor.transcribe_voice_to_text(converted_wav_path)

        if "STT Error:" in transcribed_text: 
            await client.edit_message(thinking_msg, f"⚠️ {transcribed_text}")
            return

        await client.edit_message(
            thinking_msg,
            f"🎤 **Transcribed Text:**\n{transcribed_text}\n\n"
            f"⏳ (Step 2: AI Summarization & Analysis)..."
        )

        openrouter_api_key = cli_state_ref.get("OPENROUTER_API_KEY_CLI")
        openrouter_model_name = cli_state_ref.get("OPENROUTER_MODEL_NAME_CLI")

        if not (openrouter_api_key and "YOUR_OPENROUTER_API_KEY_HERE" not in openrouter_api_key and len(openrouter_api_key) > 10 and openrouter_model_name):
            summary_text = "Configuration Error: OpenRouter API key or model not set for summarization."
            logger.warning("STT_Task: OpenRouter not configured for summarization.")
        else:
            summary_prompt = (
                f"The following text was transcribed from a voice message. Please provide a clear and concise summary of its main points in a few short sentences (in Persian if the original voice was Persian, otherwise in the detected language of the text):\n\n"
                f"---\n{transcribed_text}\n---\n\n"
                f"Summary:"
            )
            system_message_summary = "You are a helpful assistant that summarizes texts accurately and concisely."
            summary_text = await ai_processor.execute_custom_prompt(
                api_key=openrouter_api_key, model_name=openrouter_model_name,
                user_text_prompt=summary_prompt, system_message=system_message_summary,
                max_tokens=300, temperature=0.5
            )
            if "AI Error:" in summary_text:
                logger.error(f"STT_Task: AI summarization failed: {summary_text}")

        final_response = (
            f"🎤 **Transcribed Text:**\n{transcribed_text}\n\n"
            f"🔍 **AI Summary & Analysis:**\n{summary_text}"
        )
        if len(final_response) > MAX_MESSAGE_LENGTH:
            summary_part_len = len(summary_text)
            transcribed_part_len = len(transcribed_text)
            header_len = len(final_response) - summary_part_len - transcribed_part_len
            available_len_for_texts = MAX_MESSAGE_LENGTH - header_len - len("... (truncated)") - 5 
            
            if available_len_for_texts < 100: 
                final_response = final_response[:MAX_MESSAGE_LENGTH - len("... (truncated)")] + "... (truncated)"
            else:
                if summary_part_len < available_len_for_texts / 2 :
                    allowed_transcribed_len = available_len_for_texts - summary_part_len
                    transcribed_text_short = transcribed_text[:allowed_transcribed_len] + "..." if len(transcribed_text) > allowed_transcribed_len else transcribed_text
                    summary_text_short = summary_text 
                else: 
                    allowed_summary_len = int(available_len_for_texts * 0.4)
                    allowed_transcribed_len = available_len_for_texts - allowed_summary_len
                    transcribed_text_short = transcribed_text[:allowed_transcribed_len] + "..." if len(transcribed_text) > allowed_transcribed_len else transcribed_text
                    summary_text_short = summary_text[:allowed_summary_len] + "..." if len(summary_text) > allowed_summary_len else summary_text
                final_response = (
                    f"🎤 **Transcribed Text:**\n{transcribed_text_short}\n\n"
                    f"🔍 **AI Summary & Analysis:**\n{summary_text_short}\n... (parts truncated)"
                )
        await client.edit_message(thinking_msg, final_response)
    except FileNotFoundError as e_fnf:
        logger.error(f"STT_Task: FileNotFoundError: {e_fnf}", exc_info=True)
        await client.edit_message(thinking_msg, f"STT Error (Background Task): File not found. {e_fnf}")
    except Exception as e_task:
        logger.error(f"STT_Task: Unexpected error: {e_task}", exc_info=True)
        await client.edit_message(thinking_msg, f"STT Error (Background Task): An unexpected error occurred: {e_task}")
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

# --- Worker Task for TTS using edge-tts ---
async def _task_tts_edge_command_handler( # Renamed to be specific
    event_message: Message,
    client: TelegramClient,
    cli_state_ref: dict, 
    command_sender_info: str,
    text_to_speak: str,
    voice_id: str = DEFAULT_TTS_VOICE, 
    rate_tts: str = "+0%",
    volume_tts: str = "+0%"
):
    """
    Handles TTS processing using edge-tts and sending the voice message.
    Runs as a background asyncio task.
    User-facing messages are in English.
    """
    chat_id = event_message.chat_id
    reply_to_id = event_message.id
    
    temp_output_filename = f"temp_tts_output_{event_message.id}_{event_message.date.timestamp()}.mp3"

    thinking_msg = await client.send_message(
        chat_id,
        f"🗣️ Converting text to speech for {command_sender_info} using Edge-TTS (Voice: {voice_id})...",
        reply_to=reply_to_id
    )

    try:
        logger.info(f"TTS_Task (Edge): Calling ai_processor.text_to_speech_edge for text: '{text_to_speak[:50]}...'")
        success = await ai_processor.text_to_speech_edge(
            text_to_speak=text_to_speak,
            voice=voice_id,
            output_filename=temp_output_filename,
            rate=rate_tts,
            volume=volume_tts
        )

        if success and os.path.exists(temp_output_filename):
            logger.info(f"TTS_Task (Edge): Speech generated successfully: {temp_output_filename}. Sending voice message.")
            await client.send_file(
                chat_id,
                temp_output_filename,
                voice_note=True, 
                reply_to=reply_to_id,
                caption=f"🎙️ Speech for: \"{text_to_speak[:100]}{'...' if len(text_to_speak) > 100 else ''}\" (using Edge-TTS)"
            )
            await thinking_msg.delete() 
        else:
            error_msg = "TTS Error (Edge): Failed to generate speech file."
            logger.error(f"TTS_Task (Edge): {error_msg}")
            await client.edit_message(thinking_msg, f"⚠️ {error_msg}")

    except Exception as e_task:
        logger.error(f"TTS_Task (Edge): Unexpected error: {e_task}", exc_info=True)
        await client.edit_message(thinking_msg, f"TTS Error (Edge - Background Task): An unexpected error occurred: {e_task}")
    finally:
        if os.path.exists(temp_output_filename):
            try:
                os.remove(temp_output_filename)
                logger.info(f"TTS_Task (Edge): Cleaned up temporary TTS file: {temp_output_filename}")
            except Exception as e_clean:
                logger.error(f"TTS_Task (Edge): Error cleaning up TTS file {temp_output_filename}: {e_clean}")

# --- Worker Tasks for other AI commands ---
async def _task_ai_command_handler(
    command_type: str, 
    event_message: Message, 
    client: TelegramClient,
    cli_state_ref: dict,
    command_sender_info: str,
    **command_args 
):
    # ... (This function remains the same as in event_handlers_py_v11_gtts_english_complete) ...
    chat_id = event_message.chat_id
    reply_to_id = event_message.id
    openrouter_api_key = cli_state_ref.get("OPENROUTER_API_KEY_CLI")
    openrouter_model_name = cli_state_ref.get("OPENROUTER_MODEL_NAME_CLI")
    
    thinking_msg_text = f"🤖 Processing your {command_type} command from {command_sender_info}..."
    thinking_msg = await client.send_message(chat_id, thinking_msg_text, reply_to=reply_to_id)
    
    ai_response_to_send = "Internal Error: No result from command processing."

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
            chat_to_analyze_id = chat_id 
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
            chat_to_query_id = chat_id 
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
            await client.edit_message(thinking_msg, f"Error processing {command_type} (Background Task): An unexpected error occurred.")
        except Exception: 
            pass

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
    is_tts_command = False 

    if message_to_process and message_to_process.text:
        command_text_lower = message_to_process.text.strip().lower()
        is_stt_command = command_text_lower.startswith("/stt")
        is_tts_command = command_text_lower.startswith(("/tts", "/speak"))

    if not message_to_process or (not message_to_process.text and not is_stt_command and not is_tts_command) :
        logger.debug("SakaiBot Core Logic: No valid message text/STT/TTS command.")
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return
    
    command_text_to_parse = message_to_process.text.strip() if message_to_process.text else ""
    ai_reply_target_message_id = message_to_process.id

    command_sender_info = "You (direct)"
    if is_confirm_flow:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"
    elif is_direct_auth_user_command:
        sender_entity = message_to_process.sender
        command_sender_info = (sender_entity.first_name or sender_entity.username) if sender_entity and (hasattr(sender_entity, 'first_name') or hasattr(sender_entity, 'username')) else f"User {message_to_process.sender_id}"

    # --- STT Command Handling ---
    if is_stt_command:
        if not message_to_process.is_reply:
            await client.send_message(current_chat_id_for_response, "Please use /stt in reply to a voice message.", reply_to=ai_reply_target_message_id)
        else:
            replied_message = await message_to_process.get_reply_message()
            if not (replied_message and replied_message.voice):
                await client.send_message(current_chat_id_for_response, "The replied message is not a voice note.", reply_to=ai_reply_target_message_id)
            else:
                logger.info(f"SakaiBot Handler: Creating task for /stt command from '{command_sender_info}'.")
                asyncio.create_task(_task_process_stt_and_summarize(
                    original_event_message=message_to_process,
                    replied_voice_message=replied_message,
                    client=client,
                    cli_state_ref=cli_state_ref,
                    command_sender_info=command_sender_info
                ))
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return

    # --- TTS Command Handling (using edge-tts) ---
    if is_tts_command:
        text_to_speak_tts = ""
        tts_voice = DEFAULT_TTS_VOICE # Use default from top of file
        tts_rate = "+0%"
        tts_volume = "+0%"
        
        command_prefix_match = re.match(r"/(tts|speak)\s*", command_text_to_parse, re.IGNORECASE)
        if command_prefix_match:
            remaining_text_after_prefix = command_text_to_parse[command_prefix_match.end():].strip()
            
            param_pattern = re.compile(r"(voice|rate|volume)=([^\s\"']+|\"[^\"]*\"|'[^']*')\s*")
            params_found = {}
            
            temp_text_for_params = remaining_text_after_prefix
            processed_params_len = 0
            
            # Iteratively find parameters at the beginning of the string
            while True:
                match = param_pattern.match(temp_text_for_params)
                if match:
                    param_name = match.group(1).lower()
                    param_value = match.group(2).strip("\"'") # Remove quotes if any
                    params_found[param_name] = param_value
                    
                    # Advance pointer and trim
                    processed_params_len += match.end()
                    temp_text_for_params = remaining_text_after_prefix[processed_params_len:].strip()
                else:
                    break # No more parameters found at the beginning
            
            text_to_speak_tts = temp_text_for_params # What remains is the text to speak

            if "voice" in params_found: tts_voice = params_found["voice"]
            if "rate" in params_found: tts_rate = params_found["rate"]
            if "volume" in params_found: tts_volume = params_found["volume"]

        if not text_to_speak_tts and message_to_process.is_reply:
            replied_message_tts = await message_to_process.get_reply_message()
            if replied_message_tts and replied_message_tts.text:
                text_to_speak_tts = replied_message_tts.text.strip()
                # Parameters like voice, rate, volume if specified in the command will still apply to replied text
        
        if not text_to_speak_tts:
            await client.send_message(current_chat_id_for_response, 
                                      "Usage: /tts [params] <text> OR reply with /tts [params]\n"
                                      "Params: voice=<voice_id> rate=<±N%> volume=<±N%>\n"
                                      f"Example: /tts voice=en-US-JennyNeural rate=-10% Hello world\n"
                                      f"(Default Persian voice: {DEFAULT_TTS_VOICE})", 
                                      reply_to=ai_reply_target_message_id, parse_mode='md')
        else:
            logger.info(f"SakaiBot Handler: Creating task for /tts command from '{command_sender_info}'. Voice: {tts_voice}, Rate: {tts_rate}, Volume: {tts_volume}")
            asyncio.create_task(_task_tts_edge_command_handler( # Changed to edge handler
                event_message=message_to_process,
                client=client,
                cli_state_ref=cli_state_ref, 
                command_sender_info=command_sender_info,
                text_to_speak=text_to_speak_tts,
                voice_id=tts_voice,
                rate_tts=tts_rate,
                volume_tts=tts_volume
            ))
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return

    # --- Other AI Commands (Launch as Tasks) ---
    ai_task_args = None
    command_type_for_task = None
    # ... (Logic for /prompt, /translate, /analyze, /tellme remains the same as in v11) ...
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
        asyncio.create_task(_task_ai_command_handler(
            command_type=command_type_for_task,
            event_message=message_to_process,
            client=client,
            cli_state_ref=cli_state_ref,
            command_sender_info=command_sender_info,
            **ai_task_args
        ))
        if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
        return 

    # --- Categorization Command Handling ---
    # ... (Categorization logic remains the same as in v11) ...
    if message_to_process.is_reply and command_text_to_parse.startswith('/'):
        categorization_group_id = cli_state_ref.get("selected_target_group", {}).get('id') if cli_state_ref.get("selected_target_group") else None
        command_topic_map = cli_state_ref.get("active_command_to_topic_map", {})
        if categorization_group_id is None or not command_topic_map:
            logger.debug("SakaiBot Handler: Categorization target group or command map not set/empty. Skipping categorization.")
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete();
            return 
        
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
            except Exception as e_fwd:
                logger.error(f"SakaiBot Handler: Error forwarding for categorization: {e_fwd}", exc_info=True)
                await client.send_message(current_chat_id_for_response, f"Error forwarding message for categorization: {e_fwd}", reply_to=ai_reply_target_message_id)
            
            if is_confirm_flow and your_confirm_message: await your_confirm_message.delete()
            return 

    if is_confirm_flow and command_type_for_task is None and not (message_to_process.is_reply and command_text_to_parse.startswith('/') and command_text_to_parse[1:].lower().strip() in command_topic_map):
        logger.info(f"SakaiBot Handler (Confirm Flow): Friend's message '{command_text_to_parse[:50]}...' was not a recognized command.")
        if your_confirm_message: await your_confirm_message.delete()


async def categorization_reply_handler_owner(event: events.NewMessage.Event, **kwargs):
    # ... (This function remains the same as in v11) ...
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
        current_chat_id_for_response=event.chat_id, 
        is_confirm_flow=is_confirm_flow_local,
        your_confirm_message=your_confirm_message_local,
        actual_message_for_categorization_content=actual_message_for_categorization_content_owner,
        cli_state_ref=cli_state_ref,
        is_direct_auth_user_command=False
    )

async def authorized_user_command_handler(event: events.NewMessage.Event, **kwargs):
    # ... (This function remains the same as in v11) ...
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
        current_chat_id_for_response=event.chat_id, 
        is_confirm_flow=False, 
        your_confirm_message=None,
        actual_message_for_categorization_content=actual_message_for_categorization_content_auth,
        cli_state_ref=cli_state_ref,
        is_direct_auth_user_command=True
    )
