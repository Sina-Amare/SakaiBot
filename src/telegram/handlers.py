# -*- coding: utf-8 -*-
"""
Telegram event handlers for SakaiBot.

This module contains all event handlers for processing Telegram messages,
commands, and user interactions with proper error handling and task management.
"""

import logging
import os
import re
import asyncio
from typing import Dict, Any, Optional, Union
from datetime import datetime

from telethon import TelegramClient, events, functions
from telethon.tl.types import Message, User as TelegramUser
from pydub import AudioSegment

from ..core.exceptions import (
    TelegramError,
    MessageError,
    ValidationError,
    AudioError,
    STTError,
    TTSError,
    FFmpegError
)
from ..core.constants import (
    MAX_MESSAGE_LENGTH,
    CONFIRMATION_KEYWORD,
    DEFAULT_TTS_VOICE_FA,
    CommandType
)
from .models import (
    MessageContext,
    CommandData,
    TaskResult,
    AuthorizationContext,
    CategorizationTarget,
    AudioProcessingParams
)
from .utils import (
    send_message_safe,
    edit_message_safe,
    forward_message_safe,
    get_message_context,
    validate_message_text
)

# Import AI processor (this will need to be updated when AI module is refactored)
import ai_processor


logger = logging.getLogger(__name__)


class CommandProcessor:
    """
    Processes various bot commands with proper separation of concerns.
    """
    
    def __init__(self, cli_state: Dict[str, Any]):
        """Initialize command processor with CLI state reference."""
        self.cli_state = cli_state
    
    def parse_command(self, message: Message) -> Optional[CommandData]:
        """
        Parse a command message into structured data.
        
        Args:
            message: Telegram message containing command
            
        Returns:
            Optional[CommandData]: Parsed command data or None if invalid
        """
        if not message.text or not message.text.strip().startswith('/'):
            return None
        
        text = message.text.strip()
        
        # Parse different command types
        if text.lower().startswith('/prompt='):
            return self._parse_prompt_command(text)
        elif text.lower().startswith('/translate='):
            return self._parse_translate_command(text)
        elif text.lower().startswith('/analyze='):
            return self._parse_analyze_command(text)
        elif text.lower().startswith('/tellme='):
            return self._parse_tellme_command(text)
        elif text.lower().startswith(('/tts', '/speak')):
            return self._parse_tts_command(text)
        elif text.lower().startswith('/stt'):
            return CommandData(command_type="/stt", raw_text=text)
        
        return None
    
    def _parse_prompt_command(self, text: str) -> CommandData:
        """Parse /prompt= command."""
        prompt_text = text[len('/prompt='):].strip()
        return CommandData(
            command_type="/prompt",
            raw_text=text,
            target_text=prompt_text if prompt_text else None
        )
    
    def _parse_translate_command(self, text: str) -> CommandData:
        """Parse /translate= command."""
        command_parts = text[len('/translate='):].strip()
        
        # Match patterns: lang [text] or lang,source_lang [text]
        match_with_text = re.match(
            r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?\s+(.+)",
            command_parts,
            re.DOTALL
        )
        match_lang_only = re.match(
            r"([a-zA-Z\s]+?)(?:,([a-zA-Z\s]+?))?$",
            command_parts
        )
        
        target_language = None
        source_language = "auto"
        target_text = None
        
        if match_with_text:
            target_language = match_with_text.group(1).strip()
            if match_with_text.group(2):
                source_language = match_with_text.group(2).strip()
            target_text = match_with_text.group(3).strip()
        elif match_lang_only:
            target_language = match_lang_only.group(1).strip()
            if match_lang_only.group(2):
                source_language = match_lang_only.group(2).strip()
        
        return CommandData(
            command_type="/translate",
            raw_text=text,
            target_language=target_language,
            source_language=source_language,
            target_text=target_text
        )
    
    def _parse_analyze_command(self, text: str) -> CommandData:
        """Parse /analyze= command."""
        try:
            num_str = text[len('/analyze='):].strip()
            if not num_str.isdigit():
                raise ValueError("Not a number")
            
            num_messages = int(num_str)
            max_limit = self.cli_state.get("MAX_ANALYZE_MESSAGES_CLI", 5000)
            
            if not (1 <= num_messages <= max_limit):
                raise ValueError(f"Must be between 1 and {max_limit}")
            
            return CommandData(
                command_type="/analyze",
                raw_text=text,
                num_messages=num_messages
            )
        except ValueError as e:
            logger.warning(f"Invalid analyze command: {text} - {e}")
            return CommandData(command_type="/analyze", raw_text=text)
    
    def _parse_tellme_command(self, text: str) -> CommandData:
        """Parse /tellme= command."""
        match = re.match(r"/tellme=(\d+)=(.+)", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return CommandData(command_type="/tellme", raw_text=text)
        
        try:
            num_messages = int(match.group(1))
            user_question = match.group(2).strip()
            
            max_limit = self.cli_state.get("MAX_ANALYZE_MESSAGES_CLI", 5000)
            if not (1 <= num_messages <= max_limit):
                raise ValueError(f"Must be between 1 and {max_limit}")
            
            if not user_question:
                raise ValueError("Question cannot be empty")
            
            return CommandData(
                command_type="/tellme",
                raw_text=text,
                num_messages=num_messages,
                user_question=user_question
            )
        except ValueError as e:
            logger.warning(f"Invalid tellme command: {text} - {e}")
            return CommandData(command_type="/tellme", raw_text=text)
    
    def _parse_tts_command(self, text: str) -> CommandData:
        """Parse /tts or /speak command."""
        # Determine command type
        if text.lower().startswith('/speak'):
            command_type = "/speak"
            prefix_len = len('/speak')
        else:
            command_type = "/tts"
            prefix_len = len('/tts')
        
        remaining_text = text[prefix_len:].strip()
        
        # Parse parameters
        voice_params = {
            'voice': DEFAULT_TTS_VOICE_FA,
            'rate': '+0%',
            'volume': '+0%'
        }
        
        # Pattern to match parameters
        param_pattern = re.compile(
            r"(voice|rate|volume)=([^\s\"']+|\"[^\"]*\"|'[^']*')\s*"
        )
        
        # Extract parameters from beginning of text
        processed_len = 0
        temp_text = remaining_text
        
        while True:
            match = param_pattern.match(temp_text)
            if not match:
                break
            
            param_name = match.group(1).lower()
            param_value = match.group(2).strip("\"'")
            voice_params[param_name] = param_value
            
            processed_len += match.end()
            temp_text = remaining_text[processed_len:].strip()
        
        # Remaining text is the target text
        target_text = temp_text if temp_text else None
        
        return CommandData(
            command_type=command_type,
            raw_text=text,
            target_text=target_text,
            voice_params=voice_params
        )


class TaskManager:
    """
    Manages async tasks for various bot operations.
    """
    
    def __init__(self, client: TelegramClient, cli_state: Dict[str, Any]):
        """Initialize task manager."""
        self.client = client
        self.cli_state = cli_state
        self.active_tasks: Dict[str, asyncio.Task] = {}
    
    async def process_stt_task(
        self,
        original_message: Message,
        voice_message: Message,
        sender_info: str
    ) -> TaskResult:
        """
        Process Speech-to-Text task.
        
        Args:
            original_message: Original command message
            voice_message: Voice message to transcribe
            sender_info: Information about command sender
            
        Returns:
            TaskResult: Result of STT processing
        """
        task_start = datetime.now()
        chat_id = original_message.chat_id
        reply_to_id = original_message.id
        
        # Send processing message
        thinking_msg = await send_message_safe(
            self.client,
            chat_id,
            f"🎧 Processing voice message from {sender_info} (Step 1: Transcribing)...",
            reply_to=reply_to_id
        )
        
        downloaded_path = None
        converted_path = None
        
        try:
            # Setup FFmpeg path if configured
            ffmpeg_setup = self._setup_ffmpeg_path()
            
            # Download voice message
            base_name = f"temp_voice_stt_{original_message.id}_{voice_message.id}"
            downloaded_path = await self.client.download_media(
                voice_message.media,
                file=base_name
            )
            
            if not downloaded_path or not os.path.exists(downloaded_path):
                raise STTError("Failed to download voice message")
            
            logger.info(f"Downloaded voice to: {downloaded_path}")
            
            # Convert to WAV
            converted_path = f"{base_name}.wav"
            audio_segment = AudioSegment.from_file(downloaded_path)
            audio_segment.export(converted_path, format="wav")
            logger.info(f"Converted voice to WAV: {converted_path}")
            
            # Transcribe
            transcribed_text = await ai_processor.transcribe_voice_to_text(converted_path)
            
            if "STT Error:" in transcribed_text:
                raise STTError(transcribed_text)
            
            # Update message with transcription
            await edit_message_safe(
                self.client,
                thinking_msg,
                f"🎤 **Transcribed Text:**\n{transcribed_text}\n\n"
                f"⏳ (Step 2: AI Summarization & Analysis)..."
            )
            
            # Get AI summary
            summary = await self._get_ai_summary(transcribed_text)
            
            # Prepare final response
            final_response = (
                f"🎤 **Transcribed Text:**\n{transcribed_text}\n\n"
                f"🔍 **AI Summary & Analysis:**\n{summary}"
            )
            
            # Truncate if necessary
            if len(final_response) > MAX_MESSAGE_LENGTH:
                final_response = self._truncate_stt_response(
                    transcribed_text, summary
                )
            
            await edit_message_safe(self.client, thinking_msg, final_response)
            
            duration = (datetime.now() - task_start).total_seconds()
            return TaskResult.success_result(
                final_response,
                duration=duration,
                transcribed_text=transcribed_text,
                summary=summary
            )
        
        except Exception as e:
            logger.error(f"STT task failed: {e}", exc_info=True)
            
            error_msg = f"STT Error: {e}"
            if thinking_msg:
                await edit_message_safe(self.client, thinking_msg, f"⚠️ {error_msg}")
            
            duration = (datetime.now() - task_start).total_seconds()
            return TaskResult.error_result(e, duration=duration)
        
        finally:
            # Cleanup
            self._cleanup_ffmpeg_path(ffmpeg_setup)
            await self._cleanup_temp_files([downloaded_path, converted_path])
    
    async def process_tts_task(
        self,
        message: Message,
        sender_info: str,
        text_to_speak: str,
        audio_params: AudioProcessingParams
    ) -> TaskResult:
        """
        Process Text-to-Speech task.
        
        Args:
            message: Original command message
            sender_info: Information about command sender
            text_to_speak: Text to convert to speech
            audio_params: Audio processing parameters
            
        Returns:
            TaskResult: Result of TTS processing
        """
        task_start = datetime.now()
        chat_id = message.chat_id
        reply_to_id = message.id
        
        temp_filename = f"temp_tts_{message.id}_{int(task_start.timestamp())}.mp3"
        
        # Send processing message
        thinking_msg = await send_message_safe(
            self.client,
            chat_id,
            f"🗣️ Converting text to speech for {sender_info} "
            f"(Voice: {audio_params.voice_id})...",
            reply_to=reply_to_id
        )
        
        try:
            # Validate audio parameters
            if not audio_params.validate():
                raise TTSError("Invalid audio parameters")
            
            # Generate speech
            logger.info(f"Generating TTS for text: '{text_to_speak[:50]}...'")
            success = await ai_processor.text_to_speech_edge(
                text_to_speak=text_to_speak,
                voice=audio_params.voice_id,
                output_filename=temp_filename,
                rate=audio_params.rate,
                volume=audio_params.volume
            )
            
            if not success or not os.path.exists(temp_filename):
                raise TTSError("Failed to generate speech file")
            
            # Send voice message
            caption = (
                f"🎙️ Speech: \"{text_to_speak[:100]}"
                f"{'...' if len(text_to_speak) > 100 else ''}\" (Edge-TTS)"
            )
            
            await self.client.send_file(
                chat_id,
                temp_filename,
                voice_note=True,
                reply_to=reply_to_id,
                caption=caption
            )
            
            # Delete thinking message
            await thinking_msg.delete()
            
            duration = (datetime.now() - task_start).total_seconds()
            return TaskResult.success_result(
                "TTS completed successfully",
                duration=duration,
                output_file=temp_filename
            )
        
        except Exception as e:
            logger.error(f"TTS task failed: {e}", exc_info=True)
            
            error_msg = f"TTS Error: {e}"
            if thinking_msg:
                await edit_message_safe(self.client, thinking_msg, f"⚠️ {error_msg}")
            
            duration = (datetime.now() - task_start).total_seconds()
            return TaskResult.error_result(e, duration=duration)
        
        finally:
            # Cleanup temporary file
            if os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                    logger.info(f"Cleaned up TTS file: {temp_filename}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup TTS file: {cleanup_error}")
    
    async def process_ai_command_task(
        self,
        command_data: CommandData,
        message: Message,
        sender_info: str
    ) -> TaskResult:
        """
        Process AI command task (prompt, translate, analyze, tellme).
        
        Args:
            command_data: Parsed command data
            message: Original command message
            sender_info: Information about command sender
            
        Returns:
            TaskResult: Result of AI processing
        """
        task_start = datetime.now()
        chat_id = message.chat_id
        reply_to_id = message.id
        
        # Get API configuration
        api_key = self.cli_state.get("OPENROUTER_API_KEY_CLI")
        model_name = self.cli_state.get("OPENROUTER_MODEL_NAME_CLI")
        
        # Send processing message
        thinking_msg = await send_message_safe(
            self.client,
            chat_id,
            f"🤖 Processing {command_data.command_type} command from {sender_info}...",
            reply_to=reply_to_id
        )
        
        try:
            # Validate API configuration
            if not self._validate_api_config(api_key, model_name):
                raise ValidationError(
                    "OpenRouter API key or model not configured"
                )
            
            # Process based on command type
            result = await self._execute_ai_command(
                command_data, message, api_key, model_name
            )
            
            # Truncate response if necessary
            response_text = validate_message_text(result)
            
            await edit_message_safe(self.client, thinking_msg, response_text)
            
            duration = (datetime.now() - task_start).total_seconds()
            return TaskResult.success_result(
                response_text,
                duration=duration,
                command_type=command_data.command_type
            )
        
        except Exception as e:
            logger.error(f"AI command task failed: {e}", exc_info=True)
            
            error_msg = f"AI Error: {e}"
            if thinking_msg:
                await edit_message_safe(
                    self.client, thinking_msg, f"⚠️ {error_msg}"
                )
            
            duration = (datetime.now() - task_start).total_seconds()
            return TaskResult.error_result(e, duration=duration)
    
    async def _execute_ai_command(
        self,
        command_data: CommandData,
        message: Message,
        api_key: str,
        model_name: str
    ) -> str:
        """Execute specific AI command."""
        if command_data.command_type == "/prompt":
            return await ai_processor.execute_custom_prompt(
                api_key=api_key,
                model_name=model_name,
                user_text_prompt=command_data.target_text
            )
        
        elif command_data.command_type == "/translate":
            return await ai_processor.translate_text_with_phonetics(
                api_key,
                model_name,
                command_data.target_text,
                command_data.target_language,
                source_language=command_data.source_language
            )
        
        elif command_data.command_type == "/analyze":
            return await self._analyze_chat_history(
                message.chat_id, command_data.num_messages, api_key, model_name
            )
        
        elif command_data.command_type == "/tellme":
            return await self._answer_from_history(
                message.chat_id, command_data.num_messages,
                command_data.user_question, api_key, model_name
            )
        
        else:
            raise ValidationError(f"Unknown command type: {command_data.command_type}")
    
    async def _analyze_chat_history(
        self, chat_id: int, num_messages: int, api_key: str, model_name: str
    ) -> str:
        """Analyze chat history."""
        messages_data = await self._get_chat_history(chat_id, num_messages)
        if not messages_data:
            return "No text messages found to analyze"
        
        return await ai_processor.analyze_conversation_messages(
            api_key, model_name, messages_data
        )
    
    async def _answer_from_history(
        self, chat_id: int, num_messages: int, question: str, 
        api_key: str, model_name: str
    ) -> str:
        """Answer question from chat history."""
        messages_data = await self._get_chat_history(chat_id, num_messages)
        if not messages_data:
            return "No text messages found in history"
        
        return await ai_processor.answer_question_from_chat_history(
            api_key, model_name, messages_data, question
        )
    
    async def _get_chat_history(self, chat_id: int, limit: int) -> List[Dict[str, Any]]:
        """Get chat history for analysis."""
        messages_data = []
        
        try:
            history = await self.client.get_messages(chat_id, limit=limit)
            me_user = await self.client.get_me()
            
            for msg in reversed(history):
                if msg and msg.text:
                    sender_name = (
                        "You" if msg.sender_id == me_user.id
                        else self._get_sender_name(msg)
                    )
                    
                    messages_data.append({
                        'sender': sender_name,
                        'text': msg.text,
                        'timestamp': msg.date
                    })
            
            return messages_data
        
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}", exc_info=True)
            raise TelegramError(f"Failed to get chat history: {e}") from e
    
    def _get_sender_name(self, message: Message) -> str:
        """Get sender name from message."""
        if hasattr(message, 'sender') and message.sender:
            sender = message.sender
            if hasattr(sender, 'first_name') and sender.first_name:
                return sender.first_name
            elif hasattr(sender, 'username') and sender.username:
                return sender.username
        
        return f"User_{message.sender_id}"
    
    async def _get_ai_summary(self, text: str) -> str:
        """Get AI summary of transcribed text."""
        api_key = self.cli_state.get("OPENROUTER_API_KEY_CLI")
        model_name = self.cli_state.get("OPENROUTER_MODEL_NAME_CLI")
        
        if not self._validate_api_config(api_key, model_name):
            return "Configuration Error: OpenRouter not configured"
        
        prompt = (
            f"The following text was transcribed from a voice message. "
            f"Please provide a clear and concise summary of its main points "
            f"in a few short sentences (in Persian if the original voice was Persian, "
            f"otherwise in the detected language):\n\n---\n{text}\n---\n\nSummary:"
        )
        
        system_message = "You are a helpful assistant that summarizes texts accurately and concisely."
        
        try:
            summary = await ai_processor.execute_custom_prompt(
                api_key=api_key,
                model_name=model_name,
                user_text_prompt=prompt,
                system_message=system_message,
                max_tokens=300,
                temperature=0.5
            )
            
            if "AI Error:" in summary:
                logger.error(f"AI summarization failed: {summary}")
                return "Summarization failed"
            
            return summary
        
        except Exception as e:
            logger.error(f"Failed to get AI summary: {e}", exc_info=True)
            return f"Summary Error: {e}"
    
    def _truncate_stt_response(self, transcribed: str, summary: str) -> str:
        """Truncate STT response to fit message limits."""
        summary_len = len(summary)
        transcribed_len = len(transcribed)
        
        # Calculate available space
        header_len = len("🎤 **Transcribed Text:**\n\n🔍 **AI Summary & Analysis:**\n")
        available_len = MAX_MESSAGE_LENGTH - header_len - len("... (truncated)") - 10
        
        if available_len < 100:
            return "Response too long to display"
        
        if summary_len < available_len / 2:
            # Summary fits, truncate transcription
            allowed_transcribed = available_len - summary_len
            transcribed_short = (
                transcribed[:allowed_transcribed] + "..."
                if len(transcribed) > allowed_transcribed else transcribed
            )
            return (
                f"🎤 **Transcribed Text:**\n{transcribed_short}\n\n"
                f"🔍 **AI Summary & Analysis:**\n{summary}"
            )
        else:
            # Truncate both proportionally
            summary_allowed = int(available_len * 0.4)
            transcribed_allowed = available_len - summary_allowed
            
            transcribed_short = (
                transcribed[:transcribed_allowed] + "..."
                if len(transcribed) > transcribed_allowed else transcribed
            )
            summary_short = (
                summary[:summary_allowed] + "..."
                if len(summary) > summary_allowed else summary
            )
            
            return (
                f"🎤 **Transcribed Text:**\n{transcribed_short}\n\n"
                f"🔍 **AI Summary & Analysis:**\n{summary_short}\n... (parts truncated)"
            )
    
    def _setup_ffmpeg_path(self) -> Optional[str]:
        """Setup FFmpeg path for audio processing."""
        ffmpeg_path = self.cli_state.get("FFMPEG_PATH_CLI")
        if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
            return None
        
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        original_path = os.environ.get("PATH", "")
        
        if ffmpeg_dir not in original_path.split(os.pathsep):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + original_path
            logger.info(f"Added FFmpeg directory to PATH: {ffmpeg_dir}")
            return original_path
        
        return None
    
    def _cleanup_ffmpeg_path(self, original_path: Optional[str]) -> None:
        """Restore original PATH if modified."""
        if original_path:
            os.environ["PATH"] = original_path
            logger.info("Restored original PATH")
    
    async def _cleanup_temp_files(self, file_paths: List[Optional[str]]) -> None:
        """Cleanup temporary files."""
        for file_path in file_paths:
            if not file_path or not os.path.exists(file_path):
                continue
            
            # Try to remove file with retries
            for attempt in range(3):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
                    break
                except PermissionError:
                    if attempt < 2:
                        logger.warning(f"Permission error cleaning {file_path}, retrying...")
                        await asyncio.sleep(0.1)
                    else:
                        logger.error(f"Failed to cleanup {file_path} after 3 attempts")
                except Exception as e:
                    logger.error(f"Error cleaning up {file_path}: {e}")
                    break
    
    def _validate_api_config(self, api_key: str, model_name: str) -> bool:
        """Validate API configuration."""
        return (
            api_key and 
            "YOUR_OPENROUTER_API_KEY_HERE" not in api_key and 
            len(api_key) > 10 and 
            model_name
        )


class CategorizationHandler:
    """
    Handles message categorization and forwarding.
    """
    
    def __init__(self, client: TelegramClient, cli_state: Dict[str, Any]):
        """Initialize categorization handler."""
        self.client = client
        self.cli_state = cli_state
    
    async def process_categorization_command(
        self,
        command: str,
        original_message: Message,
        target_message: Message
    ) -> bool:
        """
        Process a categorization command.
        
        Args:
            command: Categorization command (without /)
            original_message: Command message
            target_message: Message to categorize
            
        Returns:
            bool: True if categorization was successful
        """
        # Get categorization configuration
        target_group = self.cli_state.get("selected_target_group", {})
        command_map = self.cli_state.get("active_command_to_topic_map", {})
        
        if not target_group or not command_map:
            logger.debug("Categorization not configured")
            return False
        
        group_id = target_group.get('id')
        if not group_id:
            logger.warning("No target group ID configured")
            return False
        
        if command not in command_map:
            logger.debug(f"Command '{command}' not in categorization map")
            return False
        
        # Get target topic
        topic_id = command_map[command]
        
        try:
            # Forward message
            await forward_message_safe(
                self.client,
                target_message.chat_id,
                target_message.id,
                group_id,
                topic_id
            )
            
            logger.info(
                f"Successfully categorized message with command '/{command}'"
            )
            return True
        
        except Exception as e:
            logger.error(f"Categorization failed: {e}", exc_info=True)
            await send_message_safe(
                self.client,
                original_message.chat_id,
                f"Error forwarding message for categorization: {e}",
                reply_to=original_message.id
            )
            return False


async def process_command_logic(
    message_to_process: Message,
    client: TelegramClient,
    chat_id_for_response: int,
    is_confirm_flow: bool,
    confirm_message: Optional[Message],
    categorization_content: Optional[Message],
    cli_state: Dict[str, Any],
    is_direct_auth_command: bool = False
) -> None:
    """
    Main command processing logic (refactored from original).
    
    Args:
        message_to_process: Message containing the command
        client: Telegram client instance
        chat_id_for_response: Chat ID to send responses to
        is_confirm_flow: Whether this is part of confirmation flow
        confirm_message: Confirmation message (if applicable)
        categorization_content: Message content for categorization
        cli_state: CLI state dictionary
        is_direct_auth_command: Whether this is a direct authorized user command
    """
    try:
        # Initialize processors
        command_processor = CommandProcessor(cli_state)
        task_manager = TaskManager(client, cli_state)
        categorization_handler = CategorizationHandler(client, cli_state)
        
        # Get message context
        context = await get_message_context(client, message_to_process)
        
        # Determine sender info
        sender_info = "You (direct)"
        if is_confirm_flow or is_direct_auth_command:
            sender_info = context.sender_info if context.sender else f"User {message_to_process.sender_id}"
        
        # Parse command
        command_data = command_processor.parse_command(message_to_process)
        
        # Handle STT command
        if command_data and command_data.command_type == "/stt":
            await _handle_stt_command(
                message_to_process, client, chat_id_for_response,
                task_manager, sender_info
            )
            if is_confirm_flow and confirm_message:
                await confirm_message.delete()
            return
        
        # Handle TTS command
        if command_data and command_data.command_type in ["/tts", "/speak"]:
            await _handle_tts_command(
                message_to_process, command_data, client, chat_id_for_response,
                task_manager, sender_info
            )
            if is_confirm_flow and confirm_message:
                await confirm_message.delete()
            return
        
        # Handle AI commands
        if command_data and command_data.command_type in ["/prompt", "/translate", "/analyze", "/tellme"]:
            if command_data.is_valid:
                asyncio.create_task(
                    task_manager.process_ai_command_task(
                        command_data, message_to_process, sender_info
                    )
                )
            else:
                await _send_command_usage(client, chat_id_for_response, command_data, message_to_process.id)
            
            if is_confirm_flow and confirm_message:
                await confirm_message.delete()
            return
        
        # Handle categorization commands
        if (message_to_process.is_reply and 
           message_to_process.text and 
           message_to_process.text.startswith('/')):
            
            command = message_to_process.text[1:].lower().strip()
            command_map = cli_state.get("active_command_to_topic_map", {})
            
            if command in command_map and categorization_content:
                await categorization_handler.process_categorization_command(
                    command, message_to_process, categorization_content
                )
            
            if is_confirm_flow and confirm_message:
                await confirm_message.delete()
            return
        
        # Clean up confirm message if no command was processed
        if is_confirm_flow and confirm_message and not command_data:
            logger.info(f"Unrecognized command in confirm flow: {message_to_process.text[:50]}...")
            await confirm_message.delete()
    
    except Exception as e:
        logger.error(f"Error in command processing logic: {e}", exc_info=True)
        if is_confirm_flow and confirm_message:
            try:
                await confirm_message.delete()
            except Exception:
                pass


async def _handle_stt_command(
    message: Message,
    client: TelegramClient,
    chat_id: int,
    task_manager: TaskManager,
    sender_info: str
) -> None:
    """Handle STT command processing."""
    if not message.is_reply:
        await send_message_safe(
            client, chat_id,
            "Please use /stt in reply to a voice message.",
            reply_to=message.id
        )
        return
    
    replied_message = await message.get_reply_message()
    if not (replied_message and replied_message.voice):
        await send_message_safe(
            client, chat_id,
            "The replied message is not a voice note.",
            reply_to=message.id
        )
        return
    
    # Create STT task
    logger.info(f"Creating STT task for command from '{sender_info}'")
    asyncio.create_task(
        task_manager.process_stt_task(message, replied_message, sender_info)
    )


async def _handle_tts_command(
    message: Message,
    command_data: CommandData,
    client: TelegramClient,
    chat_id: int,
    task_manager: TaskManager,
    sender_info: str
) -> None:
    """Handle TTS command processing."""
    text_to_speak = command_data.target_text
    
    # If no text provided and message is a reply, use replied text
    if not text_to_speak and message.is_reply:
        replied_message = await message.get_reply_message()
        if replied_message and replied_message.text:
            text_to_speak = replied_message.text.strip()
    
    if not text_to_speak:
        usage_msg = (
            "Usage: /tts [params] <text> OR reply with /tts [params]\n"
            "Params: voice=<voice_id> rate=<±N%> volume=<±N%>\n"
            f"Example: /tts voice=en-US-JennyNeural rate=-10% Hello world\n"
            f"(Default Persian voice: {DEFAULT_TTS_VOICE_FA})"
        )
        await send_message_safe(
            client, chat_id, usage_msg,
            reply_to=message.id, parse_mode='md'
        )
        return
    
    # Create audio parameters
    audio_params = AudioProcessingParams(
        voice_id=command_data.voice_params.get('voice', DEFAULT_TTS_VOICE_FA),
        rate=command_data.voice_params.get('rate', '+0%'),
        volume=command_data.voice_params.get('volume', '+0%')
    )
    
    # Create TTS task
    logger.info(
        f"Creating TTS task for command from '{sender_info}' "
        f"(Voice: {audio_params.voice_id})"
    )
    asyncio.create_task(
        task_manager.process_tts_task(message, sender_info, text_to_speak, audio_params)
    )


async def _send_command_usage(
    client: TelegramClient,
    chat_id: int,
    command_data: CommandData,
    reply_to_id: int
) -> None:
    """Send usage information for invalid commands."""
    usage_messages = {
        "/prompt": "Usage: /prompt=<your question or instruction>",
        "/translate": "Usage: /translate=<lang>[,source_lang] [text] or reply with /translate=<lang>",
        "/analyze": "Usage: /analyze=<number_between_1_and_5000>",
        "/tellme": "Usage: /tellme=<number_of_messages>=<your_question>"
    }
    
    usage_msg = usage_messages.get(
        command_data.command_type,
        f"Invalid command: {command_data.command_type}"
    )
    
    await send_message_safe(
        client, chat_id, usage_msg, reply_to=reply_to_id
    )


# Event Handler Functions (to be registered with client)

async def categorization_reply_handler_owner(
    event: events.NewMessage.Event,
    **kwargs
) -> None:
    """
    Handle categorization replies from bot owner.
    
    Args:
        event: Telegram message event
        **kwargs: Additional context (client, cli_state_ref)
    """
    client = kwargs['client']
    cli_state = kwargs['cli_state_ref']
    
    your_message = event.message
    
    try:
        # Handle confirmation flow
        if (
            your_message.is_reply and 
            your_message.text and 
            your_message.text.strip().lower() == CONFIRMATION_KEYWORD
        ):
            logger.info("Detected confirmation reply from owner")
            
            friends_command = await your_message.get_reply_message()
            if not friends_command:
                await send_message_safe(
                    client, event.chat_id,
                    "Could not process 'confirm'. Replied message not found.",
                    reply_to=your_message.id
                )
                return
            
            # Get categorization content
            categorization_content = None
            if friends_command.is_reply:
                categorization_content = await friends_command.get_reply_message()
            
            await process_command_logic(
                message_to_process=friends_command,
                client=client,
                chat_id_for_response=event.chat_id,
                is_confirm_flow=True,
                confirm_message=your_message,
                categorization_content=categorization_content,
                cli_state=cli_state,
                is_direct_auth_command=False
            )
        else:
            # Direct command from owner
            categorization_content = None
            if your_message.is_reply:
                categorization_content = await your_message.get_reply_message()
            
            await process_command_logic(
                message_to_process=your_message,
                client=client,
                chat_id_for_response=event.chat_id,
                is_confirm_flow=False,
                confirm_message=None,
                categorization_content=categorization_content,
                cli_state=cli_state,
                is_direct_auth_command=False
            )
    
    except Exception as e:
        logger.error(f"Error in owner categorization handler: {e}", exc_info=True)


async def authorized_user_command_handler(
    event: events.NewMessage.Event,
    **kwargs
) -> None:
    """
    Handle commands from authorized users.
    
    Args:
        event: Telegram message event
        **kwargs: Additional context (client, cli_state_ref)
    """
    client = kwargs['client']
    cli_state = kwargs['cli_state_ref']
    
    logger.info(
        f"Incoming message from authorized user - "
        f"Chat: {event.chat_id}, Sender: {event.sender_id}, "
        f"Message: {event.message.id}"
    )
    
    try:
        message = event.message
        
        # Get categorization content if this is a reply
        categorization_content = None
        if message.is_reply:
            categorization_content = await message.get_reply_message()
        
        await process_command_logic(
            message_to_process=message,
            client=client,
            chat_id_for_response=event.chat_id,
            is_confirm_flow=False,
            confirm_message=None,
            categorization_content=categorization_content,
            cli_state=cli_state,
            is_direct_auth_command=True
        )
    
    except Exception as e:
        logger.error(f"Error in authorized user handler: {e}", exc_info=True)
