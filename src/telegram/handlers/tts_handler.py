"""TTS (Text-to-Speech) command handler."""

import asyncio
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import Message

from ...ai.tts import TextToSpeechProcessor
from ...ai.tts_queue import tts_queue, TTSStatus
from ...core.constants import DEFAULT_TTS_VOICE
from ...utils.helpers import clean_temp_files, parse_command_with_params
from ...utils.logging import get_logger
from .base import BaseHandler


class TTSHandler(BaseHandler):
    """Handles TTS (Text-to-Speech) commands."""
    
    def __init__(
        self,
        tts_processor: TextToSpeechProcessor,
        ffmpeg_path: Optional[str] = None
    ):
        """
        Initialize TTS handler.
        
        Args:
            tts_processor: Text-to-speech processor
            ffmpeg_path: Optional path to FFmpeg executable
        """
        super().__init__(ffmpeg_path)
        self._tts_processor = tts_processor
    
    async def process_tts_command(
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
        import os
        import tempfile
        chat_id = event_message.chat_id
        reply_to_id = event_message.id
        
        # Use /tmp for Docker (read-only root filesystem) or system temp
        temp_dir = "/tmp" if os.path.exists("/tmp") and os.access("/tmp", os.W_OK) else tempfile.gettempdir()
        temp_output_filename = os.path.join(temp_dir, f"temp_tts_output_{event_message.id}_{event_message.date.timestamp()}.wav")
        
        thinking_msg = await client.send_message(
            chat_id,
            f"🗣️ Converting text to speech for {command_sender_info}...",
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
                
                caption_provider = "Google GenAI TTS"
                
                await client.edit_message(
                    thinking_msg,
                    f"✅ Text-to-speech conversion successful (Provider: {caption_provider})."
                )
                
                await client.send_file(
                    chat_id,
                    temp_output_filename,
                    voice_note=True,
                    reply_to=reply_to_id,
                    caption=(
                        f"🎤️ Speech output for text:\n"
                        f"\"{text_to_speak[:100]}{'...' if len(text_to_speak) > 100 else ''}\"\n"
                        f"(Generated with {caption_provider})"
                    )
                )
                
                # Delete the status message after sending the voice note
                await thinking_msg.delete()
            else:
                error_msg = getattr(self._tts_processor, "last_error", None)
                if not error_msg:
                    error_msg = "Text-to-speech conversion failed. Please try again later."
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
    
    async def handle_tts_command(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str
    ) -> None:
        """Handle TTS command processing with queue support for reply messages."""
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
                "❌ Please provide text or reply to a message you want to convert.\n\n"
                "✅ Example:\n"
                "/tts=سلام دنیا\n"
                "or reply to a message with /tts",
                reply_to=message.id
            )
            return

        voice = params.get("voice", DEFAULT_TTS_VOICE)
        rate = params.get("rate", "+0%")
        volume = params.get("volume", "+0%")

        # Normalize text
        normalized_text = self._normalize_text(text_to_speak)

        # Add to TTS queue for processing
        request_id = await tts_queue.add_request(
            text=normalized_text,
            chat_id=chat_id,
            message_id=message.id,
            voice=voice
        )

        # Get queue position
        queue_position = tts_queue.get_request_position(request_id)

        # Send status message
        queue_status_msg = await client.send_message(
            chat_id,
            f"🗣️ Converting text to speech for {sender_info}...\n"
            f"📋 Status: In queue (Position: {queue_position})\n"
            f"🔊 Voice: {voice}",
            reply_to=message.id
        )
        
        # Monitor the request and send result when ready
        from ...utils.task_manager import get_task_manager
        task_manager = get_task_manager()
        task_manager.create_task(
            self._monitor_tts_request(
                request_id, queue_status_msg, client, chat_id, message
            )
        )
    
    async def _safe_edit_message(self, message: Message, new_text: str, client: TelegramClient) -> bool:
        """Safely edit a message, handling Telegram's duplicate content errors."""
        try:
            await client.edit_message(message, new_text)
            return True
        except Exception as e:
            # Ignore "Content of the message was not modified" errors
            error_str = str(e).lower()
            if "content of the message was not modified" in error_str or "message not modified" in error_str:
                # This is expected when trying to edit with same content - not an error
                return False
            # Log other edit errors but don't raise
            self._logger.debug(f"Could not edit message: {e}")
            return False
    
    async def _monitor_tts_request(
        self,
        request_id: str,
        status_message: Message,
        client: TelegramClient,
        chat_id: int,
        original_message: Message
    ) -> None:
        """Monitor TTS request and send result when ready.
        
        When TTS completes, deletes both the original command message and status message,
        then sends only the voice message to keep chat clean.
        """
        update_counter = 0
        last_position = None
        last_status_text = None
        
        try:
            while True:
                request = tts_queue.get_request_status(request_id)
                if not request:
                    break
                
                if request.status == TTSStatus.COMPLETED:
                    # Send the completed audio
                    audio_file = tts_queue.get_completed_audio(request_id)
                    if audio_file:
                        success_text = "✅ Text-to-speech conversion successful. Sending..."
                        if last_status_text != success_text:
                            await self._safe_edit_message(status_message, success_text, client)
                            last_status_text = success_text
                        
                        # Send voice message
                        await client.send_file(
                            chat_id,
                            audio_file,
                            voice_note=True,
                            caption=(
                                f"🎤️ Speech output for text:\n"
                                f"\"{request.text[:100]}{'...' if len(request.text) > 100 else ''}\"\n"
                                f"(Generated with Gemini TTS)"
                            )
                        )
                        
                        # Delete both original command message and status message
                        try:
                            await original_message.delete()
                        except Exception as e:
                            self._logger.debug(f"Could not delete original command message: {e}")
                        
                        try:
                            await status_message.delete()
                        except Exception as e:
                            self._logger.debug(f"Could not delete status message: {e}")
                    
                    # Clean up the completed request
                    tts_queue.cleanup_request(request_id)
                    break
                
                elif request.status == TTSStatus.FAILED:
                    error_text = f"⚠️ TTS Error: {request.error_message or 'Failed to generate audio'}"
                    if last_status_text != error_text:
                        await self._safe_edit_message(status_message, error_text, client)
                        last_status_text = error_text
                    
                    # Delete original command message on error (keep error message)
                    try:
                        await original_message.delete()
                    except Exception as e:
                        self._logger.debug(f"Could not delete original command message on error: {e}")
                    
                    # Clean up the failed request
                    tts_queue.cleanup_request(request_id)
                    break
                
                elif request.status == TTSStatus.PROCESSING:
                    # Update status to show processing
                    voice_name = request.voice or DEFAULT_TTS_VOICE
                    processing_text = f"⚙️ Processing...\n🔊 Voice: {voice_name}"
                    if last_status_text != processing_text:
                        await self._safe_edit_message(status_message, processing_text, client)
                        last_status_text = processing_text
                
                elif request.status == TTSStatus.PENDING:
                    # Update position periodically (every 2 seconds)
                    update_counter += 1
                    if update_counter % 2 == 0:
                        current_position = tts_queue.get_request_position(request_id)
                        if current_position != last_position:
                            last_position = current_position
                            if current_position:
                                voice_name = request.voice or DEFAULT_TTS_VOICE
                                pending_text = (
                                    f"🗣️ Converting text to speech...\n"
                                    f"📋 Status: In queue (Position: {current_position})\n"
                                    f"🔊 Voice: {voice_name}"
                                )
                                if last_status_text != pending_text:
                                    await self._safe_edit_message(status_message, pending_text, client)
                                    last_status_text = pending_text
                
                # Update status periodically
                await asyncio.sleep(1)
        
        except Exception as e:
            self._logger.error(f"Error monitoring TTS request {request_id}: {e}", exc_info=True)
            # Only show actual TTS errors, not message edit errors
            try:
                request = tts_queue.get_request_status(request_id)
                if request and request.status == TTSStatus.FAILED:
                    error_text = f"⚠️ TTS Error: {request.error_message or str(e)}"
                    await self._safe_edit_message(status_message, error_text, client)
            except Exception:
                # If we can't even get the request status, just log it
                pass

