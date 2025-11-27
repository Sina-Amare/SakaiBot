"""STT (Speech-to-Text) command handler."""

import asyncio
import os
import re
from pathlib import Path
from typing import Optional, List

from telethon import TelegramClient
from telethon.tl.types import Message
from pydub import AudioSegment

from ...ai.stt import SpeechToTextProcessor
from ...ai.processor import AIProcessor
from ...ai.prompts import (
    VOICE_MESSAGE_SUMMARY_PROMPT,
    VOICE_MESSAGE_SUMMARY_SYSTEM_MESSAGE
)
from ...core.constants import MAX_MESSAGE_LENGTH
from ...core.exceptions import AIProcessorError
from ...utils.helpers import clean_temp_files, split_message
from ...utils.logging import get_logger
from ...utils.message_sender import MessageSender
from .base import BaseHandler


class STTHandler(BaseHandler):
    """Handles STT (Speech-to-Text) commands."""
    
    def __init__(
        self,
        stt_processor: SpeechToTextProcessor,
        ai_processor: AIProcessor,
        ffmpeg_path: Optional[str] = None
    ):
        """
        Initialize STT handler.
        
        Args:
            stt_processor: Speech-to-text processor
            ai_processor: AI processor for summarization
            ffmpeg_path: Optional path to FFmpeg executable
        """
        super().__init__(ffmpeg_path)
        self._stt_processor = stt_processor
        self._ai_processor = ai_processor
    
    async def process_stt_command(
        self,
        original_message: Message,
        replied_voice_message: Message,
            
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
            # Use centralized prompts from prompts.py
            summary_prompt = VOICE_MESSAGE_SUMMARY_PROMPT.format(
                transcribed_text=transcribed_text
            )
            system_message = VOICE_MESSAGE_SUMMARY_SYSTEM_MESSAGE

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
            
            # Use MessageSender for reliable delivery with pagination
            message_sender = MessageSender(client)
            await message_sender.send_long_message(
                chat_id=chat_id,
                text=final_response,
                reply_to=reply_to_id,
                parse_mode=None,  # STT responses don't use markdown
                edit_message=thinking_msg
            )
        
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
        # Use centralized prompt from prompts.py
        prompt = VOICE_MESSAGE_SUMMARY_PROMPT.format(
            transcribed_text=transcribed_text
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
        blacklist = ("اگر", "خوشحال", "Please wait اطلاعات بیشتر", "اگر نیاز")
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

