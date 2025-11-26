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

from ..core.constants import MAX_MESSAGE_LENGTH, CONFIRMATION_KEYWORD, DEFAULT_TTS_VOICE
from ..core.exceptions import TelegramError, AIProcessorError
from ..ai.processor import AIProcessor
from ..ai.stt import SpeechToTextProcessor
from ..ai.tts import TextToSpeechProcessor
from ..ai.tts_queue import tts_queue, TTSStatus
from ..ai.image_generator import ImageGenerator
from ..ai.prompt_enhancer import PromptEnhancer
from ..utils.logging import get_logger
from ..utils.helpers import clean_temp_files, parse_command_with_params, split_message
from ..utils.task_manager import get_task_manager

# Import specialized handlers
from .handlers.stt_handler import STTHandler
from .handlers.tts_handler import TTSHandler
from .handlers.ai_handler import AIHandler
from .handlers.image_handler import ImageHandler
from .handlers.categorization_handler import CategorizationHandler
from .commands import handle_auth_command, handle_help_command, handle_status_command


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
        
        # Store self-command handlers
        self._self_command_handlers = {
            'auth': handle_auth_command,
            'help': handle_help_command,
            'status': handle_status_command,
        }
        
        # Initialize specialized handlers using composition
        self._stt_handler = STTHandler(
            stt_processor=stt_processor,
            ai_processor=ai_processor,
            ffmpeg_path=ffmpeg_path
        )
        self._tts_handler = TTSHandler(
            tts_processor=tts_processor,
            ffmpeg_path=ffmpeg_path
        )
        self._ai_handler = AIHandler(ai_processor=ai_processor)
        
        # Initialize image generation components
        image_generator = ImageGenerator()
        prompt_enhancer = PromptEnhancer(ai_processor=ai_processor)
        self._image_handler = ImageHandler(
            ai_processor=ai_processor,
            image_generator=image_generator,
            prompt_enhancer=prompt_enhancer
        )
        
        self._categorization_handler = CategorizationHandler()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for TTS processing."""
        # Delegate to TTS handler
        return self._tts_handler._normalize_text(text)
    
    async def _setup_ffmpeg_path(self) -> Tuple[bool, str]:
        """Setup FFmpeg path for audio processing."""
        import platform
        from pydub import AudioSegment
        from pydub.utils import which
        
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
            
            # Explicitly set ffmpeg path for pydub on Windows
            if platform.system() == "Windows":
                AudioSegment.converter = self._ffmpeg_path
                AudioSegment.ffmpeg = self._ffmpeg_path
                self._logger.info(f"Set pydub converter path to: {self._ffmpeg_path}")
        else:
            self._logger.info("FFmpeg path not configured. pydub will try to find ffmpeg in system PATH")
        
        return path_modified, original_path
    
    async def _restore_ffmpeg_path(self, path_modified: bool, original_path: str) -> None:
        """Restore original PATH if it was modified."""
        if path_modified:
            os.environ["PATH"] = original_path
            self._logger.info("Restored original PATH")
    
    # STT, TTS, and AI command processing methods moved to specialized handlers
    # See: handlers/stt_handler.py, handlers/tts_handler.py, handlers/ai_handler.py
    
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
        
        # Check for self-commands (userbot commands like /auth, /help, /status)
        # These are only processed for outgoing messages from the bot owner
        if not is_confirm_flow and not is_direct_auth_user_command:
            for cmd_name, cmd_handler in self._self_command_handlers.items():
                if command_text_lower.startswith(f"/{cmd_name}"):
                    # Extract args (everything after the command)
                    args = command_text[len(cmd_name) + 1:].strip() if len(command_text) > len(cmd_name) + 1 else ""
                    self._logger.info(f"Processing self-command: /{cmd_name} {args}")
                    
                    # Create event-like object for compatibility
                    class SimpleEvent:
                        def __init__(self, msg, cli):
                            self.message = msg
                            self.client = cli
                        
                        async def edit(self, text, parse_mode=None):
                            await self.message.edit(text, parse_mode=parse_mode)
                    
                    event = SimpleEvent(message_to_process, client)
                    await cmd_handler(event, args)
                    return
        
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
        
        # Handle image generation command
        if command_text_lower.startswith("/image="):
            await self._handle_image_command(
                message_to_process, client, current_chat_id_for_response, command_sender_info
            )
            if is_confirm_flow and your_confirm_message:
                await your_confirm_message.delete()
            return
        
        # Handle other AI commands
        await self._ai_handler.handle_other_ai_commands(
            message_to_process, client, current_chat_id_for_response, 
            command_sender_info, cli_state_ref
        )
        
        # Handle categorization commands
        await self._categorization_handler.handle_categorization_commands(
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
        task_manager = get_task_manager()
        task_manager.create_task(
            self._stt_handler.process_stt_command(message, replied_message, client, sender_info)
        )
    
    async def _handle_tts_command(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str
    ) -> None:
        """Handle TTS command processing with queue support for reply messages."""
        # Delegate to TTS handler
        await self._tts_handler.handle_tts_command(message, client, chat_id, sender_info)
    
    async def _handle_image_command(
        self,
        message: Message,
        client: TelegramClient,
        chat_id: int,
        sender_info: str
    ) -> None:
        """Handle image generation command processing."""
        # Delegate to Image handler
        await self._image_handler.handle_image_command(message, client, chat_id, sender_info)
    
    # TTS monitoring and AI parsing methods moved to specialized handlers
    # See: handlers/tts_handler.py, handlers/ai_handler.py, handlers/image_handler.py
    
    async def categorization_reply_handler_owner(
        self, event: events.NewMessage.Event, **kwargs
    ) -> None:
        """Handle owner's messages for categorization and commands."""
        # Delegate to categorization handler
        await self._categorization_handler.categorization_reply_handler_owner(
            event, self.process_command_logic, **kwargs
        )
    
    async def authorized_user_command_handler(
        self, event: events.NewMessage.Event, **kwargs
    ) -> None:
        """Handle commands from authorized users."""
        # Delegate to categorization handler
        await self._categorization_handler.authorized_user_command_handler(
            event, self.process_command_logic, **kwargs
        )
