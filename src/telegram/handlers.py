"""Event handlers for Telegram messages in SakaiBot."""

import asyncio
import os
import re
from typing import Dict, Any, Optional, List, Tuple
import re
from pathlib import Path

from telethon import TelegramClient, events, functions
from telethon.tl.types import Message
from pydub import AudioSegment
from hazm import Normalizer

from ..core.constants import MAX_MESSAGE_LENGTH, CONFIRMATION_KEYWORD, DEFAULT_TTS_VOICE
from ..core.exceptions import TelegramError, AIProcessorError
from ..ai.processor import AIProcessor
from ..ai.stt import SpeechToTextProcessor
from ..ai.tts import TextToSpeechProcessor
from ..utils.logging import get_logger
from ..utils.helpers import clean_temp_files, parse_command_with_params


class EventHandlers:
    """Handles Telegram events and commands."""
    
    def __init__(
        self,
        ai_processor: AIProcessor,
        stt_processor: SpeechToTextProcessor,
        tts_processor: TextToSpeechProcessor,
        ffmpeg_path: Optional[str] = None
    ) -> None:
        self._ai_processor = ai_processor
        self._stt_processor = stt_processor
        self._tts_processor = tts_processor
        self._ffmpeg_path = ffmpeg_path
        self._logger = get_logger(self.__class__.__name__)
        self._normalizer = Normalizer()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for TTS processing."""
        return self._normalizer.normalize(text)
    
    async def _setup_ffmpeg_path(self) -> Tuple[bool, str]:
        """Setup FFmpeg path for audio processing."""
        original_path = os.environ.get("PATH", "")
        path_modified = False
        
        if self._ffmpeg_path and Path(self._ffmpeg_path).is_file():
            ffmpeg_dir = str(Path(self._ffmpeg_path).parent)
            if ffmpeg_dir not in original_path.split(os.pathsep):
                self._logger.info(f"Adding '{ffmpeg_dir}' to PATH for pydub")
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + original_path
                path_modified = True
            else:
                self._logger.info(f"FFmpeg directory '{ffmpeg_dir}' already in PATH")
        else:
            self._logger.info("FFmpeg path not configured. pydub will try to find ffmpeg in system PATH")
        
        return path_modified, original_path
        """Setup FFmpeg path for audio processing."""
        original_path = os.environ.get("PATH", "")
        path_modified = False
        
        if self._ffmpeg_path and Path(self._ffmpeg_path).is_file():
            ffmpeg_dir = str(Path(self._ffmpeg_path).parent)
            if ffmpeg_dir not in original_path.split(os.pathsep):
                self._logger.info(f"Adding '{ffmpeg_dir}' to PATH for pydub")
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + original_path
                path_modified = True
            else:
                self._logger.info(f"FFmpeg directory '{ffmpeg_dir}' already in PATH")
        else:
            self._logger.info("FFmpeg path not configured. pydub will try to find ffmpeg in system PATH")
        
        return path_modified, original_path
    
    async def _restore_ffmpeg_path(self, path_modified: bool, original_path: str) -> None:
        """Restore original PATH if it was modified."""
        if path_modified:
            os.environ["PATH"] = original_path
            self._logger.info("Restored original PATH")
    
    async def _process_stt_command(
        self,
        original_message: Message,
        replied_voice_message: Message,
        client: TelegramClient,
        command_sender_info: str
    ) -> None:
        """Process STT command and provide transcription with AI summary."""
        chat_id = original_message.chat_id
        reply_to_id = original_message.id
        
        thinking_msg = await client.send_message(
            chat_id,
            f"🎧 در حال پردازش پیام صوتی {command_sender_info} (گام ۱: تبدیل به متن)...",
            reply_to=reply_to_id
        )
        
        downloaded_voice_path = None
        converted_wav_path = f"temp_voice_stt_{original_message.id}_{replied_voice_message.id}.wav"
        path_modified = False
        original_path = ""
        
        try:
            # Setup FFmpeg path
            path_modified, original_path = await self._setup_ffmpeg_path()
            
            # Download voice message
            base_download_name = f"temp_voice_download_stt_{original_message.id}_{replied_voice_message.id}"
            downloaded_voice_path = await client.download_media(
                replied_voice_message.media,
                file=base_download_name
            )
            
            if not downloaded_voice_path or not Path(downloaded_voice_path).exists():
                raise FileNotFoundError("Downloaded voice file not found or download failed")
            
            self._logger.info(f"Voice downloaded to '{downloaded_voice_path}'. Converting to WAV...")
            
            # Convert to WAV using pydub
            audio_segment = AudioSegment.from_file(downloaded_voice_path)
            audio_segment.export(converted_wav_path, format="wav")
            self._logger.info(f"Voice converted to '{converted_wav_path}'")
            
            # Transcribe using STT processor
            transcribed_text = await self._stt_processor.transcribe_voice_to_text(converted_wav_path)
            
            # Update message with transcription
            await client.edit_message(
                thinking_msg,
                f"📝 **متن پیاده‌سازی شده:**\n{transcribed_text}\n\n"
                f"⏳ (گام ۲: خلاصه‌سازی و تحلیل هوش مصنوعی)..."
            )
            
            summary_text = None
            # Generate AI summary if AI is configured
            summary_prompt = (
                "متن زیر یک نسخهٔ پیاده‌سازی شدهٔ از یک پیام صوتی فارسی است. "
                "لطفاً یک خلاصهٔ طبیعی و جامع از محتوای گفته‌شده ارائه دهید. "
                "دقیقاً بگو چه چیزی گفته شده است و چه هدفی دارد، "
                "نه تحلیل یا تفسیری از آن.\n\n"
                f"متن اصلی:\n{transcribed_text}"
            )
            system_message = (
                "تو یک تحلیل‌گر حرفه‌ای گفتگوهای صوتی فارسی هستی. "
                "همیشه پاسخ را به زبان فارسی و با لحن طبیعی بنویس. "
                "فقط خلاصهٔ محتوای گفته‌شده را بدون اضافه کردن تحلیل شخصی ارائه بده."
            )

            if self._ai_processor.is_configured:
                try:
                    summary_text = await self._ai_processor.execute_custom_prompt(
                        user_prompt=summary_prompt,
                        system_message=system_message,
                        max_tokens=300,
                        temperature=0.5
                    )
                except AIProcessorError as e:
                    self._logger.error(f"AI summarization failed via primary provider: {e}")
                    summary_text = await self._generate_persian_summary_with_gemini(transcribed_text)
                    if not summary_text:
                        summary_text = f"AI Error: {e}"
            else:
                summary_text = await self._generate_persian_summary_with_gemini(transcribed_text)
                if not summary_text:
                    summary_text = "AI features not configured for summarization."
            
            if not summary_text or summary_text.startswith("AI Error"):
                fallback_summary = await self._generate_persian_summary_with_gemini(transcribed_text)
                if fallback_summary:
                    summary_text = fallback_summary
                elif not summary_text:
                    summary_text = "خلاصه‌ای در دسترس نبود."

            if summary_text:
                cleaned_lines = [line.strip() for line in summary_text.splitlines() if line.strip()]
                if cleaned_lines:
                    summary_text = " ".join(cleaned_lines)
                summary_text = self._trim_summary_text(summary_text)

            # Prepare final response
            final_response = (
                f"📝 **متن پیاده‌سازی شده:**\n{transcribed_text}\n\n"
                f"🔍 **جمع‌بندی و تحلیل هوش مصنوعی:**\n{summary_text}"
            )
            
            # Truncate if too long
            if len(final_response) > MAX_MESSAGE_LENGTH:
                available_length = MAX_MESSAGE_LENGTH - 100  # Reserve space for truncation notice
                final_response = final_response[:available_length] + "\n... (truncated)"
            
            await client.edit_message(thinking_msg, final_response)
        
        except AIProcessorError as e:
            await client.edit_message(thinking_msg, f"⚠️ STT Error: {e}")
        
        except FileNotFoundError as e:
            self._logger.error(f"File not found: {e}", exc_info=True)
            await client.edit_message(thinking_msg, f"STT Error: File not found - {e}")
        
        except Exception as e:
            self._logger.error(f"Unexpected error in STT processing: {e}", exc_info=True)
            await client.edit_message(thinking_msg, f"STT Error: An unexpected error occurred - {e}")
        
        finally:
            # Restore PATH if modified
            await self._restore_ffmpeg_path(path_modified, original_path)
            
            # Clean up temporary files
            clean_temp_files(downloaded_voice_path, converted_wav_path)
    
    async def _generate_persian_summary_with_gemini(self, transcribed_text: str) -> Optional[str]:
        """Fallback summarization using Google Gemini if available."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        
        model_name = os.getenv("GEMINI_SUMMARY_MODEL", "gemini-1.5-flash-latest")
        prompt = (
            "متن پیاده‌سازی‌شده یک پیام صوتی فارسی در ادامه آمده است. "
            "در یک پاراگراف کوتاه، جمع‌بندی روان و دقیق ارائه بده. "
            "از تیتر یا بولت استفاده نکن و اگر بخشی مبهم است خیلی کوتاه در همان پاراگراف توضیح بده.\n\n"
            f"{transcribed_text}"
        )
        
        def _call_gemini() -> Optional[str]:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            candidate = getattr(response, "text", None)
            if candidate and candidate.strip():
                return candidate.strip()
            
            parts = getattr(response, "candidates", None)
            if not parts:
                return None
            
            try:
                text_parts = []
                for part in response.candidates:
                    if hasattr(part, "content") and part.content:
                        for item in part.content.parts:
                            text_value = getattr(item, "text", None)
                            if text_value:
                                text_parts.append(text_value)
                combined = " ".join(text_parts).strip()
                return combined or None
            except Exception:
                return None
        
        try:
            result = await asyncio.to_thread(_call_gemini)
            if result:
                return result
        except Exception as exc:
            self._logger.error(f"Gemini fallback summarization failed: {exc}", exc_info=True)
        return None

    def _trim_summary_text(self, text: str) -> str:
        """Normalize summary text to two concise Persian sentences."""
        normalized = (
            text.replace("<|begin_of_sentence|>", "")
            .replace("<|end_of_sentence|>", "")
            .replace("<｜begin▁of▁sentence｜>", "")
            .replace("<｜end▁of▁sentence｜>", "")
        ).strip()
        sentences = re.split(r"(?<=[.!؟])\s+", normalized)
        kept: List[str] = []
        blacklist = ("اگر", "خوشحال", "لطفاً اطلاعات بیشتر", "اگر نیاز")
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            if any(phrase in s for phrase in blacklist):
                continue
            kept.append(s)
            if len(kept) == 2:
                break
        return " ".join(kept) if kept else normalized
    
    async def _process_tts_command(
        self,
        event_message: Message,
        client: TelegramClient,
        command_sender_info: str,
        text_to_speak: str,
        voice_id: str = DEFAULT_TTS_VOICE,
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> None:
        """Process TTS command and send voice message."""
        chat_id = event_message.chat_id
        reply_to_id = event_message.id
        
        temp_output_filename = f"temp_tts_output_{event_message.id}_{event_message.date.timestamp()}.mp3"
        
        thinking_msg = await client.send_message(
            chat_id,
            f"🗣️ در حال تبدیل متن به گفتار برای {command_sender_info}...",
            reply_to=reply_to_id
        )
        
        try:
            self._logger.info(
                f"Calling TTS processor for text: '{text_to_speak[:50]}...'"
            )
            
            success = await self._tts_processor.text_to_speech(
                text_to_speak=text_to_speak,
                voice=voice_id,
                output_filename=temp_output_filename,
                rate=rate,
                volume=volume
            )
            
            if success and Path(temp_output_filename).exists():
                self._logger.info(f"Speech generated successfully: {temp_output_filename}. Sending voice message")
                
                provider_used = getattr(self._tts_processor, "_last_provider", "unknown")
                if provider_used == "huggingface":
                    caption_provider = "Hugging Face FastSpeech2"
                elif provider_used == "google_translate":
                    caption_provider = "Google Translate"
                else:
                    caption_provider = "نامشخص"
                
                await client.edit_message(
                    thinking_msg,
                    f"✅ تبدیل متن به گفتار با موفقیت انجام شد (ارائه‌دهنده: {caption_provider})."
                )
                
                await client.send_file(
                    chat_id,
                    temp_output_filename,
                    voice_note=True,
                    reply_to=reply_to_id,
                    caption=(
                        f"🎤️ خروجی گفتار برای متن:\n"
                        f"\"{text_to_speak[:100]}{'...' if len(text_to_speak) > 100 else ''}\"\n"
                        f"(تولید شده با {caption_provider})"
                    )
                )
                
                # Delete the status message after sending the voice note
                await thinking_msg.delete()
            else:
                error_msg = getattr(self._tts_processor, "last_error", None)
                if not error_msg:
                    error_msg = "تبدیل متن به گفتار انجام نشد. لطفاً بعداً دوباره تلاش کنید."
                self._logger.error(f"TTS Error: {error_msg}")
                await client.edit_message(thinking_msg, f"⚠️ TTS Error: {error_msg}")
        
        except Exception as e:
            self._logger.error(f"Unexpected error in TTS processing: {e}", exc_info=True)
            await client.edit_message(
                thinking_msg,
                f"TTS Error: An unexpected error occurred - {e}"
            )
        
        finally:
            # Clean up temporary file
            clean_temp_files(temp_output_filename)
    
    async def _process_ai_command(
        self,
        command_type: str,
        event_message: Message,
        client: TelegramClient,
        command_sender_info: str,
        **command_args
    ) -> None:
        """Process AI commands (prompt, translate, analyze, tellme)."""
        chat_id = event_message.chat_id
        reply_to_id = event_message.id
        
        thinking_msg_text = f"🤖 Processing your {command_type} command from {command_sender_info}..."
        thinking_msg = await client.send_message(chat_id, thinking_msg_text, reply_to=reply_to_id)
        
        try:
            if not self._ai_processor.is_configured:
                provider_name = self._ai_processor.provider_name if self._ai_processor else "AI"
                response = f"AI Error: {provider_name} API key or model name not configured correctly."
            elif command_type == "/prompt":
                response = await self._handle_prompt_command(**command_args)
            elif command_type == "/translate":
                response = await self._handle_translate_command(**command_args)
            elif command_type == "/analyze":
                response = await self._handle_analyze_command(client, chat_id, **command_args)
            elif command_type == "/tellme":
                response = await self._handle_tellme_command(client, chat_id, **command_args)
            else:
                response = f"Unknown command type: {command_type}"
            
            # Log successful response
            self._logger.info(f"AI command {command_type} completed. Response length: {len(response)} chars")
            
            # Truncate if too long
            if len(response) > MAX_MESSAGE_LENGTH:
                response = response[:MAX_MESSAGE_LENGTH - 20] + "... (truncated)"
            
            await client.edit_message(thinking_msg, response)
            
            # Send a simple completion message without humor
            from datetime import datetime
            time_str = datetime.now().strftime('%H:%M')
            completion_msg = f"✅ انجام شد - {time_str}"
            
            # Send as a separate message for visibility
            await client.send_message(chat_id, completion_msg, reply_to=reply_to_id)
        
        except Exception as e:
            self._logger.error(f"AI command ({command_type}) error: {e}", exc_info=True)
            try:
                await client.edit_message(
                    thinking_msg,
                    f"Error processing {command_type}: An unexpected error occurred"
                )
            except Exception:
                pass
    
    async def _handle_prompt_command(self, user_prompt_text: str) -> str:
        """Handle /prompt command."""
        if not user_prompt_text:
            return "Usage: /prompt=<your question or instruction>"
        
        try:
            # Import Persian comedian system message
            from ..ai.persian_prompts import PERSIAN_COMEDIAN_SYSTEM
            
            response = await self._ai_processor.execute_custom_prompt(
                user_prompt=user_prompt_text,
                system_message=PERSIAN_COMEDIAN_SYSTEM
            )
            if response and response.strip():
                return response
            else:
                self._logger.warning(f"Empty response from AI for prompt command. Response was: {response}")
                return "⚠️ AI responded but the message was empty. This might be due to content filtering. Try rephrasing your request."
        except AIProcessorError as e:
            return f"AI Error: {e}"
    
    async def _handle_translate_command(
        self,
        text_for_ai: str,
        target_language: str,
        source_lang_for_ai: str = "auto"
    ) -> str:
        """Handle /translate command."""
        if not text_for_ai or not target_language:
            return "Usage: /translate=<lang>[,source_lang] [text] or reply with /translate=<lang>"
        
        try:
            response = await self._ai_processor.translate_text_with_phonetics(
                text_to_translate=text_for_ai,
                target_language=target_language,
                source_language=source_lang_for_ai
            )
            if response and response.strip():
                # Clean the response to ensure it follows the format: "translated text (persian pronunciation)"
                # Remove any extra commentary or text that might have been added
                # First, look for the pattern "translated text (pronunciation)" in the response
                match = re.search(r'(.+?)\s*\(\s*(.+?)\s*\)', response.strip(), re.DOTALL)
                if match:
                    translated_text = match.group(1).strip()
                    pronunciation = match.group(2).strip()
                    # Extract just the content without prefixes like "Translation:", "Phonetic:", etc.
                    # Look for the actual translated text part
                    translation_match = re.search(r'Translation:\s*(.+?)(?:\s*\n|$)', response)
                    phonetic_match = re.search(r'Phonetic:\s*\((.+?)\)', response)
                    
                    if translation_match and phonetic_match:
                        clean_translation = translation_match.group(1).strip()
                        clean_pronunciation = phonetic_match.group(1).strip()
                        return f"{clean_translation} ({clean_pronunciation})"
                    else:
                        # If we have the match from the general pattern, return that
                        return f"{translated_text} ({pronunciation})"
                else:
                    # If the response doesn't match the expected format, return it as is
                    # but try to extract the most relevant part
                    lines = response.split('\n')
                    for line in lines:
                        line = line.strip()
                        if '(' in line and ')' in line and line.count('(') == line.count(')'):
                            # This line likely contains the translation and pronunciation
                            return line.strip()
                
                # If no proper format found, return the cleaned response
                return response.strip()
            else:
                self._logger.warning(f"Empty response from AI for translation. Response was: {response}")
                return "⚠️ Translation failed - the AI couldn't generate a translation. Try with different text or language."
        except AIProcessorError as e:
            return f"AI Error: {e}"
    
    async def _handle_analyze_command(
        self,
        client: TelegramClient,
        chat_id: int,
        num_messages: int
    ) -> str:
        """Handle /analyze command."""
        try:
            # Get chat history
            history = await client.get_messages(chat_id, limit=num_messages)
            me_user = await client.get_me()
            
            messages_data = []
            for msg in reversed(history):
                if msg and msg.text:
                    sender_name = (
                        "You" if msg.sender_id == me_user.id
                        else (
                            getattr(msg.sender, 'first_name', None) or
                            getattr(msg.sender, 'username', None) or
                            f"User_{msg.sender_id}"
                        )
                    )
                    messages_data.append({
                        'sender': sender_name,
                        'text': msg.text,
                        'timestamp': msg.date
                    })
            
            if not messages_data:
                return "No text messages found in the specified history to analyze."
            
            response = await self._ai_processor.analyze_conversation_messages(messages_data)
            if response and response.strip():
                return response
            else:
                self._logger.warning(f"Empty response from AI for analysis. Response was: {response}")
                return "⚠️ Analysis incomplete - the AI processed your messages but couldn't generate a summary. This might be due to content in the messages. Try analyzing fewer messages."
        
        except AIProcessorError as e:
            return f"AI Error: {e}"
        except Exception as e:
            self._logger.error(f"Error in analyze command: {e}", exc_info=True)
            return f"Error: {e}"
    
    async def _handle_tellme_command(
        self,
        client: TelegramClient,
        chat_id: int,
        num_messages: int,
        user_question: str
    ) -> str:
        """Handle /tellme command."""
        try:
            # Get chat history
            history = await client.get_messages(chat_id, limit=num_messages)
            me_user = await client.get_me()
            
            messages_data = []
            for msg in reversed(history):
                if msg and msg.text:
                    sender_name = (
                        "You" if msg.sender_id == me_user.id
                        else (
                            getattr(msg.sender, 'first_name', None) or
                            getattr(msg.sender, 'username', None) or
                            f"User_{msg.sender_id}"
                        )
                    )
                    messages_data.append({
                        'sender': sender_name,
                        'text': msg.text,
                        'timestamp': msg.date
                    })
            
            if not messages_data:
                return "No text messages found in history to answer your question."
            
            response = await self._ai_processor.answer_question_from_chat_history(
                messages_data, user_question
            )
            if response and response.strip():
                return response
            else:
                self._logger.warning(f"Empty response from AI for tellme command. Response was: {response}")
                return "⚠️ The AI couldn't answer your question based on the chat history. Try asking a different question or including more message history."
        
        except AIProcessorError as e:
            return f"AI Error: {e}"
        except Exception as e:
            self._logger.error(f"Error in tellme command: {e}", exc_info=True)
            return f"Error: {e}"
    
    async def process_command_logic(
        self,
        message_to_process: Message,
        client: TelegramClient,
        current_chat_id_for_response: int,
        is_confirm_flow: bool,
        your_confirm_message: Optional[Message],
        actual_message_for_categorization_content: Optional[Message],
        cli_state_ref: Dict[str, Any],
        is_direct_auth_user_command: bool = False
    ) -> None:
        """Process command logic for various types of commands."""
        if not message_to_process:
            self._logger.debug("No valid message to process")
            if is_confirm_flow and your_confirm_message:
                await your_confirm_message.delete()
            return
        
        command_text = message_to_process.text.strip() if message_to_process.text else ""
        command_text_lower = command_text.lower()
        
        # Determine command sender info
        if is_confirm_flow or is_direct_auth_user_command:
            sender_entity = message_to_process.sender
            command_sender_info = (
                (sender_entity.first_name or sender_entity.username)
                if sender_entity and (
                    hasattr(sender_entity, 'first_name') or 
                    hasattr(sender_entity, 'username')
                )
                else f"User {message_to_process.sender_id}"
            )
        else:
            command_sender_info = "You (direct)"
        
        # Handle STT command
        if command_text_lower.startswith("/stt"):
            await self._handle_stt_command(
                message_to_process, client, current_chat_id_for_response, command_sender_info
            )
            if is_confirm_flow and your_confirm_message:
                await your_confirm_message.delete()
            return
        
        # Handle TTS command
        if command_text_lower.startswith(("/tts", "/speak")):
            await self._handle_tts_command(
                message_to_process, client, current_chat_id_for_response, command_sender_info
            )
            if is_confirm_flow and your_confirm_message:
                await your_confirm_message.delete()
            return
        
        # Handle other AI commands
        await self._handle_other_ai_commands(
            message_to_process, client, current_chat_id_for_response, 
            command_sender_info, cli_state_ref
        )
        
        # Handle categorization commands
        await self._handle_categorization_commands(
            message_to_process, client, current_chat_id_for_response,
            actual_message_for_categorization_content, cli_state_ref
        )
        
        if is_confirm_flow and your_confirm_message:
            await your_confirm_message.delete()
    
    async def _handle_stt_command(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str
    ) -> None:
        """Handle STT command processing."""
        if not message.is_reply:
            await client.send_message(
                chat_id,
                "Please use /stt in reply to a voice message.",
                reply_to=message.id
            )
            return
        
        replied_message = await message.get_reply_message()
        if not (replied_message and replied_message.voice):
            await client.send_message(
                chat_id,
                "The replied message is not a voice note.",
                reply_to=message.id
            )
            return
        
        self._logger.info(f"Creating task for /stt command from '{sender_info}'")
        asyncio.create_task(
            self._process_stt_command(message, replied_message, client, sender_info)
        )
    
    async def _handle_tts_command(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str
    ) -> None:
        """Handle TTS command processing."""
        self._logger.debug(f"TTS HANDLER RECEIVED MESSAGE: {message}")
        command_text = message.text.strip() if message.text else ""
        text_to_speak = None
        params = {}

        if message.is_reply:
            replied_message = await message.get_reply_message()
            if replied_message and replied_message.text:
                text_to_speak = replied_message.text.strip()
            # in a reply, the command text is just for parameters
            params, _ = parse_command_with_params(command_text, "/tts")
            if not _:
                params, _ = parse_command_with_params(command_text, "/speak")
        else:
            params, text_to_speak = parse_command_with_params(command_text, "/tts")
            if not text_to_speak:
                params, text_to_speak = parse_command_with_params(command_text, "/speak")

        if not text_to_speak:
            await client.send_message(
                chat_id,
                "Usage: /tts [params] <text> OR reply to a message with /tts [params]\n"
                "Params: voice=<voice_id> rate=<±N%> volume=<±N%>\n"
                f"Example: /tts voice=en-US-JennyNeural rate=-10% Hello world\n"
                f"(Default Persian voice: {DEFAULT_TTS_VOICE})",
                reply_to=message.id,
                parse_mode='md'
            )
            return

        # Get voice parameters
        voice = params.get("voice", DEFAULT_TTS_VOICE)
        rate = params.get("rate", "+0%")
        volume = params.get("volume", "+0%")

        # Extract only the actual transcribed text when replying to STT results
        # Remove any formatting like emojis (📝, 🔍) to make voice output natural
        if message.is_reply and replied_message and replied_message.text:
            # Remove formatting elements like emojis and markdown
            import re
            cleaned_text = re.sub(r'[📝🔍💬👤]', '', replied_message.text)
            cleaned_text = re.sub(r'\*\*.*?\*\*', '', cleaned_text) # Remove bold formatting
            cleaned_text = re.sub(r'#+\s*', '', cleaned_text)  # Remove headers
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Normalize whitespace
            text_to_speak = cleaned_text.strip()

        # Normalize the text
        normalized_text = self._normalize_text(text_to_speak)

        self._logger.info(
            f"Creating task for /tts command from '{sender_info}'. "
            f"Voice: {voice}, Rate: {rate}, Volume: {volume}"
        )
        
        asyncio.create_task(
            self._process_tts_command(
                message, client, sender_info, normalized_text, voice, rate, volume
            )
        )
    
    async def _handle_other_ai_commands(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str,
        cli_state_ref: Dict[str, Any]
    ) -> None:
        """Handle other AI commands (prompt, translate, analyze, tellme)."""
        command_text = message.text.strip() if message.text else ""
        command_type = None
        command_args = {}
        
        # Parse different command types
        if command_text.lower().startswith("/prompt="):
            command_type = "/prompt"
            user_prompt_text = command_text[len("/prompt="):].strip()
            if user_prompt_text:
                command_args = {"user_prompt_text": user_prompt_text}
            else:
                await client.send_message(
                    chat_id,
                    "Usage: /prompt=<your question or instruction>",
                    reply_to=message.id
                )
                return
        
        elif command_text.lower().startswith("/translate="):
            command_type = "/translate"
            command_args = await self._parse_translate_command(message, command_text)
            if not command_args:
                await client.send_message(
                    chat_id,
                    "Usage: /translate=<lang>[,source_lang] [text] or reply with /translate=<lang>",
                    reply_to=message.id
                )
                return
        
        elif command_text.lower().startswith("/analyze="):
            command_type = "/analyze"
            command_args = self._parse_analyze_command(command_text, cli_state_ref)
            if not command_args:
                max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)
                await client.send_message(
                    chat_id,
                    f"Usage: /analyze=<number_between_1_and_{max_limit}>",
                    reply_to=message.id
                )
                return
        
        elif command_text.lower().startswith("/tellme="):
            command_type = "/tellme"
            command_args = self._parse_tellme_command(command_text, cli_state_ref)
            if not command_args:
                await client.send_message(
                    chat_id,
                    "Usage: /tellme=<number_of_messages>=<your_question>",
                    reply_to=message.id
                )
                return
        
        if command_type and command_args:
            self._logger.info(f"Creating task for {command_type} from '{sender_info}'")
            asyncio.create_task(
                self._process_ai_command(
                    command_type, message, client, sender_info, **command_args
                )
            )
    
    async def _parse_translate_command(
        self, message: Message, command_text: str
    ) -> Optional[Dict[str, str]]:
        """Parse translate command parameters."""
        command_parts = command_text[len("/translate="):].strip()
        
        # Match patterns for translate command - handle both "lang=text" and "lang text" formats
        target_language = None
        source_language = "auto"
        text_to_translate = None
        
        # First try to match the pattern with "=" separator
        match_with_equals = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?\s*=\s*(.+)", command_parts, re.DOTALL)
        if match_with_equals:
            target_language = match_with_equals.group(1).strip()
            if match_with_equals.group(2):
                source_language = match_with_equals.group(2).strip()
            text_to_translate = match_with_equals.group(3).strip()
        else:
            # If no "=" found, try the pattern with space separator
            match_with_space = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?\s+(.+)", command_parts, re.DOTALL)
            if match_with_space:
                target_language = match_with_space.group(1).strip()
                if match_with_space.group(2):
                    source_language = match_with_space.group(2).strip()
                text_to_translate = match_with_space.group(3).strip()
        
        # For cases where only language is specified (when replying to a message)
        match_lang_only = re.match(r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?$", command_parts)
        
        # If no text was matched from the main patterns, check if we only have language
        if not target_language and not text_to_translate:
            if match_lang_only:
                target_language = match_lang_only.group(1).strip()
                if match_lang_only.group(2):
                    source_language = match_lang_only.group(2).strip()
        
        # If no text provided, check if replying to a message
        if not text_to_translate and message.is_reply:
            replied_msg = await message.get_reply_message()
            if replied_msg and replied_msg.text:
                original_text = replied_msg.text
                
                # Extract only the actual transcribed text when replying to STT results
                # Remove formatting like emojis, labels, and AI analysis sections
                # Extract text between "📝 متن پیاده‌سازی شده:" and "🔍 جمع‌بندی و تحلیل هوش مصنوعی:"
                
                # Look for STT result format: "📝 **متن پیاده‌سازی شده:**\n{transcribed_text}\n\n🔍 **جمع‌بندی و تحلیل هوش مصنوعی:**"
                stt_pattern = r"📝\s*\*\*متن\s*پیاده‌سازی\s*شده:\*\*\s*\n(.*?)\s*\n\s*\n🔍\s*\*\*جمع‌بندی\s*و\s*تحلیل\s*هوش\s*مصنوعی:\*\*"
                match = re.search(stt_pattern, original_text, re.DOTALL)
                
                if match:
                    # Extract just the transcribed text part
                    text_to_translate = match.group(1).strip()
                    self._logger.info("Extracted transcribed text from STT result for translation")
                else:
                    # If not in STT format, clean the text by removing formatting
                    cleaned_text = re.sub(r'[📝🔍💬👤]', '', original_text)
                    cleaned_text = re.sub(r'\*\*.*?\*\*', '', cleaned_text)  # Remove bold formatting
                    cleaned_text = re.sub(r'#+\s*', '', cleaned_text)  # Remove headers
                    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Normalize whitespace
                    text_to_translate = cleaned_text.strip()
        
        if target_language and text_to_translate:
            return {
                "text_for_ai": text_to_translate,
                "target_language": target_language,
                "source_lang_for_ai": source_language
            }
        
        return None
    
    def _parse_analyze_command(
        self, command_text: str, cli_state_ref: Dict[str, Any]
    ) -> Optional[Dict[str, int]]:
        """Parse analyze command parameters."""
        try:
            num_messages_str = command_text[len("/analyze="):].strip()
            if not num_messages_str.isdigit():
                return None
            
            num_messages = int(num_messages_str)
            max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)
            
            if not (1 <= num_messages <= max_limit):
                return None
            
            return {"num_messages": num_messages}
        except ValueError:
            return None
    
    def _parse_tellme_command(
        self, command_text: str, cli_state_ref: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse tellme command parameters."""
        tellme_match = re.match(
            r"/tellme=(\d+)=(.+)", command_text, re.IGNORECASE | re.DOTALL
        )
        
        if not tellme_match:
            return None
        
        try:
            num_messages = int(tellme_match.group(1))
            user_question = tellme_match.group(2).strip()
            
            max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)
            
            if not (1 <= num_messages <= max_limit) or not user_question:
                return None
            
            return {
                "num_messages": num_messages,
                "user_question": user_question
            }
        except ValueError:
            return None
    
    async def _handle_categorization_commands(
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
                
                import random
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
        self, event: events.NewMessage.Event, **kwargs
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
                    "Could not process 'confirm'. Replied message not found.",
                    reply_to=your_message.id
                )
                return
        else:
            message_to_process = your_message
            if your_message.is_reply:
                actual_message_content = await your_message.get_reply_message()
        
        if message_to_process:
            await self.process_command_logic(
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
        self, event: events.NewMessage.Event, **kwargs
    ) -> None:
        """Handle commands from authorized users."""
        self._logger.info(
            f"Incoming message from authorized user. "
            f"Chat ID: {event.chat_id}, Sender ID: {event.sender_id}, "
            f"Message ID: {event.message.id}"
        )
        
        message_from_auth_user = event.message
        client_instance = kwargs['client']
        cli_state_ref = kwargs['cli_state_ref']
        
        actual_message_content = None
        if message_from_auth_user.is_reply:
            actual_message_content = await message_from_auth_user.get_reply_message()
        
        await self.process_command_logic(
            message_to_process=message_from_auth_user,
            client=client_instance,
            current_chat_id_for_response=event.chat_id,
            is_confirm_flow=False,
            your_confirm_message=None,
            actual_message_for_categorization_content=actual_message_content,
            cli_state_ref=cli_state_ref,
            is_direct_auth_user_command=True
        )
