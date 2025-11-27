"""AI command handler for prompt, translate, analyze, and tellme commands."""

import re
from datetime import datetime
from typing import Dict, Any, Optional

from telethon import TelegramClient
from telethon.tl.types import Message

from ...ai.processor import AIProcessor
from ...core.constants import MAX_MESSAGE_LENGTH
from ...core.exceptions import AIProcessorError
from ...utils.helpers import split_message
from ...utils.logging import get_logger
from ...utils.task_manager import get_task_manager
from ...utils.rate_limiter import get_ai_rate_limiter
from ...utils.validators import InputValidator
from ...utils.message_sender import MessageSender
from ...utils.error_handler import ErrorHandler
from ...utils.metrics import get_metrics_collector, TimingContext
from .base import BaseHandler


class AIHandler(BaseHandler):
    """Handles AI commands (prompt, translate, analyze, tellme)."""
    
    def __init__(self, ai_processor: AIProcessor):
        """
        Initialize AI handler.
        
        Args:
            ai_processor: AI processor instance
        """
        super().__init__()
        self._ai_processor = ai_processor
    
    async def process_ai_command(
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
        user_id = event_message.sender_id
        
        # Track metrics
        metrics = get_metrics_collector()
        metrics.increment('ai_command.requests', tags={'command': command_type})
        
        # Check rate limit
        rate_limiter = get_ai_rate_limiter()
        if not await rate_limiter.check_rate_limit(user_id):
            remaining = await rate_limiter.get_remaining_requests(user_id)
            metrics.increment('ai_command.rate_limited', tags={'command': command_type})
            error_msg = (
                f"⚠️ Rate Limit Exceeded\n\n"
                f"You have reached your request limit.\n"
                f"Please wait {rate_limiter._window_seconds} seconds.\n"
                f"Remaining requests: {remaining}"
            )
            await client.send_message(chat_id, error_msg, reply_to=reply_to_id)
            return
        
        thinking_msg_text = f"🤖 Processing your {command_type} command from {command_sender_info}..."
        thinking_msg = await client.send_message(chat_id, thinking_msg_text, reply_to=reply_to_id)
        
        try:
            # Track timing
            with TimingContext('ai_command.duration', tags={'command': command_type}):
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
            
            # Log successful response and track metrics
            self._logger.info(f"AI command {command_type} completed. Response length: {len(response)} chars")
            metrics.increment('ai_command.success', tags={'command': command_type})
            metrics.set_gauge('ai_command.response_length', len(response), tags={'command': command_type})
            
            # Use MessageSender for reliable delivery with pagination
            message_sender = MessageSender(client)
            sent_messages = await message_sender.send_long_message(
                chat_id=chat_id,
                text=response,
                reply_to=reply_to_id,
                parse_mode='md',
                edit_message=thinking_msg
            )
            
            # Send completion message if we successfully sent response
            if sent_messages:
                time_str = datetime.now().strftime('%H:%M')
                completion_msg = f"✅ Done - {time_str}"
                await message_sender.send_message_safe(
                    chat_id,
                    completion_msg,
                    reply_to=reply_to_id
                )
        
        except Exception as e:
            metrics.increment('ai_command.errors', tags={'command': command_type, 'error_type': type(e).__name__})
            ErrorHandler.log_error(e, context=f"AI command {command_type}")
            user_message = ErrorHandler.get_user_message(e)
            try:
                message_sender = MessageSender(client)
                await message_sender.edit_message_safe(
                    thinking_msg,
                    user_message
                )
            except Exception:
                # If we can't edit, try sending a new message
                try:
                    await client.send_message(
                        chat_id,
                        user_message,
                        reply_to=reply_to_id
                    )
                except Exception:
                    pass
    
    async def _handle_prompt_command(self, user_prompt_text: str) -> str:
        """Handle /prompt command."""
        if not user_prompt_text:
            return "Usage: /prompt=<your question or instruction>"
        
        try:
            # Validate and sanitize prompt
            try:
                user_prompt_text = InputValidator.validate_prompt(user_prompt_text)
            except ValueError as e:
                return f"❌ Invalid prompt: {str(e)}"
            # Import Persian comedian system message
            from ...ai.prompts import PERSIAN_COMEDIAN_SYSTEM
            
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
            return "Usage: /translate=<lang>=<text> or reply with /translate=<lang>"
        
        # Validate language code
        if not InputValidator.validate_language_code(target_language):
            return f"❌ Invalid language code: {target_language}. Please use a valid ISO 639-1 language code (e.g., 'en', 'fa', 'es')."
        
        # Validate and sanitize text
        try:
            text_for_ai = InputValidator.validate_prompt(text_for_ai, max_length=5000)
        except ValueError as e:
            return f"❌ Invalid text: {str(e)}"
        
        try:
            response = await self._ai_processor.translate_text_with_phonetics(
                text_to_translate=text_for_ai,
                target_language=target_language,
                source_language=source_lang_for_ai
            )
            if response and response.strip():
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
        num_messages: int,
        analysis_mode: str = "general"
    ) -> str:
        """Handle /analyze command."""
        # Validate number of messages
        if not InputValidator.validate_number(str(num_messages), min_val=1, max_val=10000):
            return f"❌ Invalid number of messages: {num_messages}. Must be between 1 and 10000."
        
        # Validate analysis mode
        if analysis_mode not in ("general", "fun", "romance"):
            return f"❌ Invalid analysis mode: {analysis_mode}. Valid modes: general, fun, romance"
        
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
            
            response = await self._ai_processor.analyze_conversation_messages(
                messages_data,
                analysis_mode=analysis_mode
            )
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
        # Validate number of messages
        if not InputValidator.validate_number(str(num_messages), min_val=1, max_val=10000):
            return f"❌ Invalid number of messages: {num_messages}. Must be between 1 and 10000."
        
        # Validate and sanitize question
        try:
            user_question = InputValidator.validate_prompt(user_question, max_length=1000)
        except ValueError as e:
            return f"❌ Invalid question: {str(e)}"
        
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
    
    async def handle_other_ai_commands(
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
        
        # Sanitize command text
        command_text = InputValidator.sanitize_command_input(command_text)
        
        # Parse different command types
        if command_text.lower().startswith("/prompt="):
            command_type = "/prompt"
            user_prompt_text = command_text[len("/prompt="):].strip()
            if user_prompt_text:
                # Additional validation will happen in _handle_prompt_command
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
        
        elif command_text.lower().startswith("/analyze=") or command_text.lower().startswith("/analyze "):
            command_type = "/analyze"
            command_args = self._parse_analyze_command(command_text, cli_state_ref)
            if command_args and isinstance(command_args, dict) and command_args.get("error") == "unknown_mode":
                await client.send_message(
                    chat_id,
                    "حالت تحلیل نامعتبر است. حالت‌های مجاز: general, fun, romance",
                    reply_to=message.id
                )
                return
            if not command_args:
                max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)
                await client.send_message(
                    chat_id,
                    f"Usage: /analyze=<number_between_1_and_{max_limit}> یا /analyze=<mode>=<number> (mode: fun, romance, general)",
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
            task_manager = get_task_manager()
            task_manager.create_task(
                self.process_ai_command(
                    command_type, message, client, sender_info, **command_args
                )
            )
    
    async def _parse_translate_command(
        self, message: Message, command_text: str
    ) -> Optional[Dict[str, Any]]:
        """Parse translate command parameters using the simplified approach."""
        command_parts = command_text[len("/translate="):].strip()
        
        # Use the simplified translation command parser
        from ...utils.translation_utils import parse_translation_command
        target_language, text_to_translate, errors = parse_translation_command(command_parts)
        
        if errors:
            for error in errors:
                self._logger.warning(f"Translation command parsing error: {error}")
            return None
        
        # If no text to translate, check if replying to a message
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
            else:
                # No text provided and no replied message with text
                return None
        
        if target_language and (text_to_translate or message.is_reply):
            return {
                "text_for_ai": text_to_translate,
                "target_language": target_language,
                "source_lang_for_ai": "auto"
            }
        
        return None
    
    def _parse_analyze_command(
        self, command_text: str, cli_state_ref: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse analyze command parameters with optional mode.

        Supported:
          /analyze=<N>
          /analyze=fun=<N>
          /analyze=romance=<N>
          /analyze <N>
        """
        try:
            text = command_text.strip()
            max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)

            # Backward compatibility: '/analyze 5000'
            if text.lower().startswith("/analyze "):
                tail = text[len("/analyze "):].strip()
                if tail.isdigit():
                    n = int(tail)
                    if 1 <= n <= max_limit:
                        return {"num_messages": n, "analysis_mode": "general"}
                return None

            # Must start with '/analyze='
            if not text.lower().startswith("/analyze="):
                return None

            payload = text[len("/analyze="):]
            parts = payload.split("=")

            mode = "general"
            num_part = None

            if len(parts) == 1:
                # /analyze=<N>
                num_part = parts[0]
            elif len(parts) >= 2:
                # /analyze=<mode>=<N>
                mode_candidate = parts[0].strip().lower()
                num_part = parts[1].strip()
                if mode_candidate in ("fun", "romance", "general"):
                    mode = mode_candidate
                else:
                    return {"error": "unknown_mode"}

            if not num_part or not num_part.isdigit():
                return None

            n = int(num_part)
            if not (1 <= n <= max_limit):
                return None

            return {"num_messages": n, "analysis_mode": mode}
        except Exception:
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

