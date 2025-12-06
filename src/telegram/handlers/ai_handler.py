"""AI command handler for prompt, translate, analyze, and tellme commands."""

import re
from datetime import datetime
from typing import Dict, Any, Optional

from telethon import TelegramClient
from telethon.tl.types import Message

from ...ai.processor import AIProcessor
from ...ai.response_metadata import build_response_parts

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
from ...utils.rtl_fixer import ensure_rtl_safe
from ...ai.analyze_queue import analyze_queue
from .base import BaseHandler


def format_analysis_metadata(
    num_messages: int,
    unique_senders: list,
    first_date,
    last_date,
    analysis_type: str,
    language: str,
    model_name: Optional[str] = None,
    use_thinking: bool = False,
    use_web_search: bool = False
) -> str:
    """
    Generate metadata footer for analysis results.
    
    Uses Unicode LTR embedding to ensure proper display in RTL context.
    The metadata is primarily English/numbers and should display LTR.
    
    Args:
        num_messages: Total number of messages analyzed
        unique_senders: List of unique sender names
        first_date: First message timestamp
        last_date: Last message timestamp
        analysis_type: Type of analysis performed
        language: Output language
        model_name: Name of the LLM model used (e.g., "gemini-2.5-pro")
        
    Returns:
        Formatted metadata string with proper directional formatting
    """
    # Unicode directional controls for LTR display in RTL context
    LRE = '\u202A'  # Left-to-Right Embedding
    PDF = '\u202C'  # Pop Directional Formatting
    
    # Format sender names (max 10, then truncate)
    names = ', '.join(unique_senders[:10])
    if len(unique_senders) > 10:
        names += f', +{len(unique_senders)-10} more'
    
    # Format dates
    first = first_date.strftime('%b %d, %H:%M')
    last = last_date.strftime('%b %d, %H:%M')
    
    # Build metadata lines
    metadata_lines = [
        f"📊 **Analysis Metadata**",
        f"**Messages:** {num_messages}",
        f"**Participants:** {len(unique_senders)} ({names})",
        f"**Timeframe:** {first} - {last}",
        f"**Type:** {analysis_type.title()}",
        f"**Language:** {language.title()}"
    ]
    
    # Add model name if provided
    if model_name:
        metadata_lines.append(f"**Model:** {model_name}")
    
    # Add flags if enabled
    flags = []
    if use_thinking:
        flags.append("Thinking")
    if use_web_search:
        flags.append("Web Search")
    if flags:
        metadata_lines.append(f"**Mode:** {', '.join(flags)}")
    
    # Wrap entire metadata block in LTR embedding for proper display
    # This ensures English labels and values display correctly in RTL context
    metadata_content = "\n".join(metadata_lines)
    return f"""

───────────────────────
{LRE}{metadata_content}{PDF}
"""


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
                f"⚠️ **Rate Limit Exceeded**\n\n"
                f"You have reached the maximum number of requests allowed.\n\n"
                f"**Please wait:** {rate_limiter._window_seconds} seconds\n"
                f"**Remaining requests:** {remaining}"
            )
            await client.send_message(chat_id, error_msg, reply_to=reply_to_id)
            return
        
        # For expensive AI commands, check the queue to prevent concurrent operations per chat
        # This applies to /analyze, /prompt, and /tellme (all use pro model)
        analysis_mode = command_args.get('analysis_mode', 'general')
        protected_commands = {"/analyze", "/prompt", "/tellme"}
        
        if command_type in protected_commands:
            cmd_name = command_type.lstrip("/")
            analysis_type = analysis_mode if command_type == "/analyze" else "default"
            
            can_start, queue_error_msg = await analyze_queue.try_start_analysis(
                chat_id=chat_id,
                user_id=user_id,
                analysis_type=analysis_type,
                command_type=cmd_name
            )
            if not can_start:
                self._logger.info(f"{cmd_name} request rejected for chat {chat_id} - queue locked")
                await client.send_message(
                    chat_id,
                    queue_error_msg,
                    reply_to=reply_to_id,
                    parse_mode='html'
                )
                return
        
        # Professional processing message
        command_display = command_type.replace("/", "").title()
        thinking_msg_text = (
            f"🔄 **{command_display}**\n\n"
            f"Processing your request...\n"
            f"_Please wait_"
        )
        thinking_msg = await client.send_message(chat_id, thinking_msg_text, reply_to=reply_to_id, parse_mode='md')
        
        try:
            # Track timing
            with TimingContext('ai_command.duration', tags={'command': command_type}):
                if not self._ai_processor.is_configured:
                    provider_name = self._ai_processor.provider_name if self._ai_processor else "AI"
                    response = (
                        f"⚙️ **Configuration Error**\n\n"
                        f"{provider_name} API not configured.\n\n"
                        f"_Check /status for details_"
                    )
                elif command_type == "/prompt":
                    response = await self._handle_prompt_command(**command_args)
                elif command_type == "/translate":
                    response = await self._handle_translate_command(**command_args)
                elif command_type == "/analyze":
                    response = await self._handle_analyze_command(client, chat_id, **command_args)
                elif command_type == "/tellme":
                    response = await self._handle_tellme_command(client, chat_id, **command_args)
                else:
                    response = (
                        f"❌ **Unknown Command**\n\n"
                        f"`{command_type}` is not recognized.\n\n"
                        f"_Use /help for available commands_"
                    )
            
            # Log successful response and track metrics
            self._logger.info(f"AI command {command_type} completed. Response length: {len(response)} chars")
            metrics.increment('ai_command.success', tags={'command': command_type})
            metrics.set_gauge('ai_command.response_length', len(response), tags={'command': command_type})
            
            # Use MessageSender for reliable delivery with pagination
            # For /analyze, RTL fix is pre-applied to content only (not metadata)
            message_sender = MessageSender(client)
            skip_rtl = command_type == "/analyze"  # Pre-applied RTL fix for analyze
            sent_messages = await message_sender.send_long_message(
                chat_id=chat_id,
                text=response,
                reply_to=reply_to_id,
                parse_mode='md',
                edit_message=thinking_msg,
                skip_rtl_fix=skip_rtl
            )
            
            # Send completion message if we successfully sent response
            if sent_messages:
                time_str = datetime.now().strftime('%H:%M')
                command_display = command_type.replace("/", "").title()
                completion_msg = f"✅ **{command_display} Complete** • {time_str}"
                await message_sender.send_message_safe(
                    chat_id,
                    completion_msg,
                    reply_to=reply_to_id,
                    parse_mode='md'
                )
            
            # Release AI command queue lock on success
            if command_type in protected_commands:
                await analyze_queue.complete_analysis(chat_id)
        
        except Exception as e:
            # Release AI command queue lock on failure
            if command_type in protected_commands:
                await analyze_queue.fail_analysis(chat_id)
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
    
    async def _handle_prompt_command(
        self, 
        user_prompt_text: str, 
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> str:
        """Handle /prompt command with optional thinking and web search flags."""
        if not user_prompt_text:
            return "📋 **Command Usage**\n\n**Format:** `/prompt=<your question or instruction>`\n\nPlease provide a question or instruction after the equals sign."
        
        try:
            # Validate and sanitize prompt
            try:
                user_prompt_text = InputValidator.validate_prompt(user_prompt_text)
            except ValueError as e:
                return f"❌ **Invalid Input**\n\n{str(e)}\n\nPlease check your prompt and try again."
            # Import unified prompt and formatting
            from ...ai.prompts import PROMPT_ADAPTIVE_PROMPT, get_telegram_formatting_guidelines
            
            # Append formatting guidelines to user prompt
            format_guidelines = get_telegram_formatting_guidelines("persian")
            user_prompt_with_format = user_prompt_text + format_guidelines
            
            # Use adaptive prompt that detects tone and responds appropriately
            full_prompt = PROMPT_ADAPTIVE_PROMPT.format(user_prompt=user_prompt_with_format)
            
            response = await self._ai_processor.execute_custom_prompt(
                user_prompt=full_prompt,
                max_tokens=32000,  # Use full token budget for complete responses
                task_type="prompt",
                use_thinking=use_thinking,
                use_web_search=use_web_search
            )
            
            # Response is now AIResponseMetadata with execution status
            if response and response.response_text.strip():
                # Build header (thinking) and footer (metadata) separately
                header, footer = build_response_parts(response)
                return header + response.response_text + footer
            else:
                self._logger.warning(
                    f"Empty response from AI for prompt command. "
                    f"Response was: {response}"
                )
                return (
                    "⚠️ **Empty Response**\n\n"
                    "The AI processed your request but returned an empty message. "
                    "This may be due to content filtering.\n\n"
                    "**Suggestion:** Try rephrasing your request or using different wording."
                )
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
            return "📋 **Translation Command Usage**\n\n**Format:** `/translate=<target_language>=<text>`\n\n**Or:** Reply to a message with `/translate=<target_language>`\n\n**Example:** `/translate=en=Hello world`"
        
        # Validate language code
        if not InputValidator.validate_language_code(target_language):
            return f"❌ **Invalid Language Code**\n\n`{target_language}` is not a valid language code.\n\n**Please use:** ISO 639-1 language codes (e.g., `en`, `fa`, `es`, `de`, `fr`)"
        
        # Validate and sanitize text
        try:
            text_for_ai = InputValidator.validate_prompt(text_for_ai, max_length=5000)
        except ValueError as e:
                return f"❌ **Invalid Text Input**\n\n{str(e)}\n\nPlease check your text and try again."
        
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
                return "⚠️ **Translation Failed**\n\nThe AI was unable to generate a translation for your request.\n\n**Suggestions:**\n• Try with different text\n• Use a different target language\n• Ensure the text is clear and readable"
        except AIProcessorError as e:
            return f"AI Error: {e}"
    
    async def _handle_analyze_command(
        self,
        client: TelegramClient,
        chat_id: int,
        num_messages: int,
        analysis_mode: str = "general",
        output_language: str = "persian",
        use_thinking: bool = False
    ) -> str:
        """Handle /analyze command with optional Persian translation.
        
        Args:
            client: Telegram client
            chat_id: Chat ID
            num_messages: Number of messages to analyze
            analysis_mode: Analysis type (general/fun/romance)
            output_language: Output language ('persian' or 'english')
        
        Returns:
            Analysis text in requested language
        """
        # Validate number of messages
        if not InputValidator.validate_number(str(num_messages), min_val=1, max_val=10000):
            return f"❌ **Invalid Message Count**\n\n`{num_messages}` is not a valid number.\n\n**Valid range:** 1 to 10,000 messages"
        
        # Validate analysis mode
        if analysis_mode not in ("general", "fun", "romance"):
            return f"❌ **Invalid Analysis Mode**\n\n`{analysis_mode}` is not a valid analysis mode.\n\n**Valid modes:** `general`, `fun`, `romance`"
        
        try:
            # Get chat history
            history = await client.get_messages(chat_id, limit=num_messages)
            me_user = await client.get_me()
            
            messages_data = []
            for msg in reversed(history):
                if msg and msg.text:
                    # Fetch sender entity explicitly
                    try:
                        sender = await msg.get_sender()
                        sender_name = (
                            # Use actual Telegram name instead of "You" for bot's own messages
                            (me_user.first_name or me_user.username or "You")
                            if msg.sender_id == me_user.id
                            else (
                                getattr(sender, 'first_name', None) or
                                getattr(sender, 'username', None) or
                                f"User_{msg.sender_id}"
                            )
                        )
                    except Exception:
                        sender_name = f"User_{msg.sender_id}"

                    messages_data.append({
                        'sender': sender_name,
                        'text': msg.text,
                        'timestamp': msg.date
                    })
            
            if not messages_data:
                return "📭 **No Messages Found**\n\nNo text messages were found in the specified message history to analyze.\n\n**Suggestion:** Try analyzing a different number of messages or ensure the chat contains text messages."
            
            # Generate analysis DIRECTLY in target language
            analysis_result = await self._ai_processor.analyze_conversation_messages(
                messages_data,
                analysis_mode=analysis_mode,
                output_language=output_language,
                use_thinking=use_thinking
            )
            
            # Validate and return result
            if not analysis_result or not analysis_result.strip():
                self._logger.warning(f"Empty response from AI for analysis. Response was: {analysis_result}")
                return "⚠️ **Analysis Incomplete**\n\nThe AI processed your messages but was unable to generate a summary.\n\n**Possible reasons:**\n• Content filtering restrictions\n• Insufficient message content\n• Processing limitations\n\n**Suggestion:** Try analyzing fewer messages or a different time range."
            
            # Apply RTL fix to analysis content ONLY (not metadata)
            # This prevents LRM markers from being inserted into the English metadata
            rtl_fixed_content = ensure_rtl_safe(analysis_result.strip())
            
            # Generate metadata footer (English, should NOT be RTL-fixed)
            unique_senders = list(set(m['sender'] for m in messages_data))
            # Get the actual model used for analysis (pro model for analyze task)
            model_name = self._ai_processor.get_model_for_task("analyze")
            metadata = format_analysis_metadata(
                num_messages=len(messages_data),
                unique_senders=unique_senders,
                first_date=messages_data[0]['timestamp'],
                last_date=messages_data[-1]['timestamp'],
                analysis_type=analysis_mode,
                language=output_language,
                model_name=model_name,
                use_thinking=use_thinking
            )
            
            # Return pre-RTL-fixed content + clean metadata
            return rtl_fixed_content + metadata
        
        except AIProcessorError as e:
            return f"❌ **Analysis Processing Error**\n\n{e}\n\nPlease try again or contact support if the issue persists."
        except Exception as e:
            self._logger.error(f"Error in analyze command: {e}", exc_info=True)
            return f"❌ **Unexpected Error**\n\nAn unexpected error occurred while processing your analysis request.\n\n**Error:** {e}\n\nPlease try again later."
    
    async def _handle_tellme_command(
        self,
        client: TelegramClient,
        chat_id: int,
        num_messages: int,
        user_question: str,
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> str:
        """Handle /tellme command."""
        # Validate number of messages
        if not InputValidator.validate_number(str(num_messages), min_val=1, max_val=10000):
            return f"❌ **Invalid Message Count**\n\n`{num_messages}` is not a valid number.\n\n**Valid range:** 1 to 10,000 messages"
        
        # Validate and sanitize question
        try:
            user_question = InputValidator.validate_prompt(user_question, max_length=1000)
        except ValueError as e:
            return f"❌ **Invalid Question**\n\n{str(e)}\n\nPlease check your question and try again."
        
        try:
            # Get chat history
            history = await client.get_messages(chat_id, limit=num_messages)
            me_user = await client.get_me()
            
            messages_data = []
            for msg in reversed(history):
                if msg and msg.text:
                    # Fetch sender entity explicitly
                    try:
                        sender = await msg.get_sender()
                        sender_name = (
                            # Use actual Telegram name instead of "You" for bot's own messages
                            (me_user.first_name or me_user.username or "You")
                            if msg.sender_id == me_user.id
                            else (
                                getattr(sender, 'first_name', None) or
                                getattr(sender, 'username', None) or
                                f"User_{msg.sender_id}"
                            )
                        )
                    except Exception:
                        sender_name = f"User_{msg.sender_id}"

                    messages_data.append({
                        'sender': sender_name,
                        'text': msg.text,
                        'timestamp': msg.date
                    })
            
            if not messages_data:
                return "📭 **No Messages Found**\n\nNo text messages were found in the specified history to answer your question.\n\n**Suggestion:** Try analyzing a different number of messages or ensure the chat contains text messages."
            
            response = await self._ai_processor.answer_question_from_chat_history(
                messages_data, 
                user_question,
                use_thinking=use_thinking,
                use_web_search=use_web_search
            )
            
            # Response is now AIResponseMetadata with execution status
            if response and response.response_text.strip():
                # Build header (thinking) and footer (metadata) separately
                from ...ai.response_metadata import build_response_parts
                header, footer = build_response_parts(response)
                return header + response.response_text + footer
            else:
                self._logger.warning(f"Empty response from AI for tellme command. Response was: {response}")
                return "⚠️ **Unable to Answer**\n\nThe AI couldn't answer your question based on the available chat history.\n\n**Suggestions:**\n• Try asking a different question\n• Include more message history\n• Rephrase your question"
        
        except AIProcessorError as e:
            return f"❌ **Question Processing Error**\n\n{e}\n\nPlease try again or contact support if the issue persists."
        except Exception as e:
            self._logger.error(f"Error in tellme command: {e}", exc_info=True)
            return f"❌ **Unexpected Error**\n\nAn unexpected error occurred while processing your question.\n\n**Error:** {e}\n\nPlease try again later."
    
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
            payload = command_text[len("/prompt="):].strip()
            
            # Check for flags at the end
            use_thinking = False
            use_web_search = False
            
            if payload.lower().endswith("=think"):
                use_thinking = True
                payload = payload[:-6].strip()  # Remove '=think'
            elif payload.lower().endswith("=web"):
                use_web_search = True
                payload = payload[:-4].strip()  # Remove '=web'
            
            if payload:
                # Additional validation will happen in _handle_prompt_command
                command_args = {
                    "user_prompt_text": payload,
                    "use_thinking": use_thinking,
                    "use_web_search": use_web_search
                }
            else:
                await client.send_message(
                    chat_id,
                    "📋 **Prompt Command Usage**\n\n**Format:** `/prompt=<your question or instruction>`\n\n**Example:** `/prompt=What is artificial intelligence?`\n\n**Flags:** Add `=think` for thinking mode or `=web` for web search",
                    reply_to=message.id,
                    parse_mode='md'
                )
                return
        
        elif command_text.lower().startswith("/translate="):
            command_type = "/translate"
            command_args = await self._parse_translate_command(message, command_text)
            if not command_args:
                await client.send_message(
                    chat_id,
                    "📋 **Translation Command Usage**\n\n**Format:** `/translate=<target_language>=<text>`\n\n**Or:** Reply to a message with `/translate=<target_language>`\n\n**Example:** `/translate=en=Hello world`",
                    reply_to=message.id,
                    parse_mode='md'
                )
                return
        
        elif command_text.lower().startswith("/analyze=") or command_text.lower().startswith("/analyze "):
            command_type = "/analyze"
            command_args = self._parse_analyze_command(command_text, cli_state_ref)
            if command_args and isinstance(command_args, dict) and command_args.get("error") == "unknown_mode":
                await client.send_message(
                    chat_id,
                    "❌ **Invalid Analysis Mode**\n\nThe analysis mode you specified is not valid.\n\n**Valid modes:**\n• `general` - Comprehensive analysis\n• `fun` - Humorous, entertaining analysis\n• `romance` - Emotional/romantic analysis",
                    reply_to=message.id,
                    parse_mode='md'
                )
                return
            if not command_args:
                max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)
                await client.send_message(
                    chat_id,
                    f"📋 **Analysis Command Usage**\n\n**Format 1:** `/analyze=<number>`\n**Format 2:** `/analyze=<mode>=<number>`\n\n**Modes:** `general`, `fun`, `romance`\n**Range:** 1 to {max_limit} messages\n\n**Examples:**\n• `/analyze=100`\n• `/analyze=fun=500`\n• `/analyze=romance=200 en`",
                    reply_to=message.id,
                    parse_mode='md'
                )
                return
        
        elif command_text.lower().startswith("/tellme="):
            command_type = "/tellme"
            command_args = self._parse_tellme_command(command_text, cli_state_ref)
            if not command_args:
                await client.send_message(
                    chat_id,
                    "📋 **Tell Me Command Usage**\n\n**Format:** `/tellme=<number_of_messages>=<your_question>`\n\n**Example:** `/tellme=100=What did we discuss about the project?`",
                    reply_to=message.id,
                    parse_mode='md'
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
                
                # Look for STT result format: "📝 **Transcribed Text:**\n{transcribed_text}\n\n🔍 **AI Summary & Analysis:**"
                stt_pattern = r"📝\s*\*\*Transcribed\s*Text:\*\*\s*\n(.*?)\s*\n\s*\n🔍\s*\*\*AI\s*Summary\s*&\s*Analysis:\*\*"
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
        """Parse analyze command parameters with optional mode, language flag, and thinking mode.

        Supported:
          /analyze=<N>
          /analyze=fun=<N>
          /analyze=romance=<N>
          /analyze <N>
          
          Add 'en' flag for English output:
          /analyze=fun=500 en
          /analyze=500 en
          
          Add 'think' flag for thinking mode:
          /analyze=fun=500=think
          /analyze=500=think
        """
        try:
            text = command_text.strip()
            max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)

            # Check for 'en' language flag and remove it for parsing
            output_language = "persian"  # Default
            if text.lower().endswith(" en"):
                output_language = "english"
                text = text[:-3].strip()  # Remove ' en' from end

            # Check for 'think' flag
            use_thinking = False
            if text.lower().endswith("=think"):
                use_thinking = True
                text = text[:-6].strip()  # Remove '=think' from end

            # Backward compatibility: '/analyze 5000'
            if text.lower().startswith("/analyze "):
                tail = text[len("/analyze "):].strip()
                if tail.isdigit():
                    n = int(tail)
                    if 1 <= n <= max_limit:
                        return {
                            "num_messages": n,
                            "analysis_mode": "general",
                            "output_language": output_language,
                            "use_thinking": use_thinking
                        }
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
                # /analyze=<mode>=<N> or /analyze=<mode>=<N>=think
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

            return {
                "num_messages": n,
                "analysis_mode": mode,
                "output_language": output_language,
                "use_thinking": use_thinking
            }
        except Exception:
            return None
    
    def _parse_tellme_command(
        self, command_text: str, cli_state_ref: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse tellme command parameters with optional think and web flags.
        
        Supported:
          /tellme=<N>=<question>
          /tellme=<N>=<question>=think
          /tellme=<N>=<question>=web
        """
        # Match with optional flags at the end
        tellme_match = re.match(
            r"/tellme=(\d+)=(.+?)(?:=(think|web))?$", command_text, re.IGNORECASE | re.DOTALL
        )
        
        if not tellme_match:
            return None
        
        try:
            num_messages = int(tellme_match.group(1))
            user_question = tellme_match.group(2).strip()
            flag = tellme_match.group(3)
            
            max_limit = cli_state_ref.get("MAX_ANALYZE_MESSAGES_CLI", 10000)
            
            if not (1 <= num_messages <= max_limit) or not user_question:
                return None
            
            use_thinking = flag and flag.lower() == "think"
            use_web_search = flag and flag.lower() == "web"
            
            return {
                "num_messages": num_messages,
                "user_question": user_question,
                "use_thinking": use_thinking,
                "use_web_search": use_web_search
            }
        except ValueError:
            return None

