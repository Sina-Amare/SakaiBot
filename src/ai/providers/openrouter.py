"""OpenRouter LLM provider implementation (fallback provider)."""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from openai import AsyncOpenAI
import httpx

from ..llm_interface import LLMProvider
from ..response_metadata import AIResponseMetadata
from ..api_key_manager import APIKeyManager
from ...core.constants import OPENROUTER_HEADERS, COMPLEX_TASKS, SIMPLE_TASKS
from ...core.exceptions import AIProcessorError
from ...utils.logging import get_logger
from ..prompts import (
    TRANSLATION_AUTO_DETECT_PROMPT,
    TRANSLATION_SOURCE_TARGET_PROMPT,
    CONVERSATION_ANALYSIS_PROMPT,
    QUESTION_ANSWER_PROMPT,
    VOICE_MESSAGE_SUMMARY_PROMPT,
    ANALYZE_GENERAL_PROMPT,
    ANALYZE_FUN_PROMPT,
    ANALYZE_ROMANCE_PROMPT,
    DEFAULT_CHAT_SUMMARY_PROMPT,
    get_telegram_formatting_guidelines,
    get_response_scaling_instructions
)


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider for LLM operations (used as Gemini fallback)."""

    def __init__(self, config: Any) -> None:
        """Initialize OpenRouter provider with multi-key support."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client: Optional[AsyncOpenAI] = None
        self._current_api_key: Optional[str] = None
        self._last_used_key: Optional[str] = None  # Track for client recreation

        # Model configuration - pro for complex tasks, flash for simple
        self._model = config.openrouter_model
        self._model_pro = getattr(
            config, 'openrouter_model_pro', 'google/gemini-2.5-pro'
        )
        self._model_flash = getattr(
            config, 'openrouter_model_flash', 'google/gemini-2.5-flash'
        )

        # Initialize key manager with all OpenRouter keys (sequential rotation)
        api_keys = getattr(config, 'openrouter_api_keys', [])
        if api_keys:
            self._key_manager = APIKeyManager(
                api_keys, cooldown_seconds=60, provider_name="OpenRouter"
            )
            self._logger.info(
                f"OpenRouter initialized with {len(api_keys)} API keys"
            )
        else:
            self._key_manager = None
            # Fallback to legacy single key
            legacy_key = getattr(config, 'openrouter_api_key', None)
            if legacy_key and len(legacy_key) > 10:
                self._current_api_key = legacy_key
                self._logger.info("OpenRouter using legacy single API key")

    @property
    def is_configured(self) -> bool:
        """Check if OpenRouter is properly configured."""
        if self._key_manager:
            return self._key_manager.num_keys > 0
        return bool(
            self._current_api_key
            and len(self._current_api_key) > 10
        )

    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "OpenRouter"
    
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self._model
    
    def get_model_for_task(self, task_type: str) -> str:
        """Get appropriate model based on task complexity."""
        if task_type in COMPLEX_TASKS:
            return self._model_pro
        elif task_type in SIMPLE_TASKS:
            return self._model_flash
        return self._model  # Legacy default
    
    def _calculate_max_tokens(self, task_type: str, num_messages: Optional[int] = None) -> int:
        """
        Calculate fixed max_tokens based on task type.
        
        Args:
            task_type: Type of task ('analyze', 'tellme', 'prompt', 'translate', etc.)
            num_messages: Number of messages in conversation (unused, kept for compatibility)
            
        Returns:
            Fixed max_tokens value based on task type
        """
        if task_type in ("analyze", "tellme", "prompt"):
            # Fixed 32k cap for complex tasks
            return 32000
        elif task_type in ("translate", "prompt_enhancer"):
            # Fixed 8k cap for simple tasks
            return 8000
        else:
            # Default fallback
            return 16000
    
    def _get_current_api_key(self) -> Optional[str]:
        """Get current API key from manager or legacy field."""
        if self._key_manager:
            return self._key_manager.get_current_key()
        return self._current_api_key

    def _get_client(self, api_key: Optional[str] = None) -> AsyncOpenAI:
        """Get or create OpenAI client for OpenRouter.

        Args:
            api_key: Specific API key to use. If None, uses current key.
        """
        if not self.is_configured:
            raise AIProcessorError(
                "OpenRouter API key not configured or invalid"
            )

        key = api_key or self._get_current_api_key()
        if not key:
            raise AIProcessorError("No available OpenRouter API key")

        # Recreate client if key changed
        if self._client is None or self._last_used_key != key:
            import httpx as _httpx

            http_client = _httpx.AsyncClient(
                timeout=_httpx.Timeout(600.0, connect=30.0),
                limits=_httpx.Limits(
                    max_keepalive_connections=5, max_connections=10
                ),
                follow_redirects=True
            )

            self._client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=key,
                http_client=http_client,
                max_retries=3
            )
            self._last_used_key = key
            self._logger.info(
                f"OpenRouter client created with key {key[:12]}..."
            )

        return self._client

    
    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        task_type: str = "default",
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> AIResponseMetadata:
        """Execute a prompt using OpenRouter with task-based model selection."""
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("OpenRouter API key not configured or invalid")
        
        # Select model based on task type
        model = self.get_model_for_task(task_type)
        
        # Add thinking mode instructions if enabled
        if use_thinking:
            thinking_instruction = (
                "\n\n**THINKING MODE ENABLED:** "
                "Before generating your final response, perform step-by-step reasoning internally. "
                "Think through the problem systematically, consider multiple perspectives, "
                "and reason through to a well-justified conclusion. "
                "Do NOT show your intermediate reasoning steps in the output - only provide the final, "
                "well-reasoned answer. The quality and depth of your internal reasoning should be "
                "reflected in the thoroughness and accuracy of your final response."
            )
            user_prompt = user_prompt + thinking_instruction
        
        # Note: OpenRouter doesn't support Google Search tool directly
        if use_web_search:
            self._logger.warning("Web search requested but OpenRouter doesn't support Google Search tool")
        
        # Track key attempts for rotation on 429
        max_key_attempts = self._key_manager.num_keys if self._key_manager else 1
        keys_tried = 0
        last_error = None
        
        while keys_tried < max_key_attempts:
            try:
                client = self._get_client()
                
                # Prompt is already self-contained (system messages merged)
                messages = [{"role": "user", "content": user_prompt}]
                
                self._logger.info(
                    f"Sending prompt to OpenRouter model '{model}'. "
                    f"Prompt preview: '{user_prompt[:100]}...'"
                )
                
                # Add timeout for large requests
                try:
                    completion = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        extra_headers=OPENROUTER_HEADERS,
                        timeout=600.0  # 10 minute timeout for large requests
                    )
                    
                    # Success - break out of retry loop
                    break
                    
                except httpx.TimeoutException:
                    self._logger.error(
                        f"Request timed out after 10 minutes for model '{model}'"
                    )
                    raise AIProcessorError(
                        "Request timed out. Try with fewer messages."
                    )
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Rate limit - mark key as exhausted and rotate
                        keys_tried += 1
                        self._logger.warning(
                            f"OpenRouter rate limit (429) on key attempt {keys_tried}"
                        )
                        
                        if self._key_manager:
                            self._key_manager.mark_key_rate_limited()
                            if keys_tried < max_key_attempts:
                                # Force client recreation with new key
                                self._client = None
                                self._last_used_key = None
                                self._logger.info(
                                    f"Rotating to next OpenRouter key "
                                    f"({keys_tried}/{max_key_attempts})"
                                )
                                last_error = AIProcessorError(
                                    "OpenRouter rate limit exceeded"
                                )
                                continue
                        
                        # All keys exhausted or no key manager
                        raise AIProcessorError(
                            f"All OpenRouter keys exhausted (429 rate limit)"
                        )
                    else:
                        self._logger.error(
                            f"HTTP error {e.response.status_code}: "
                            f"{e.response.text}"
                        )
                        raise AIProcessorError(
                            f"API returned error {e.response.status_code}: "
                            f"{e.response.text[:200]}"
                        )
            except AIProcessorError:
                raise
            except Exception as e:
                self._logger.error(f"OpenRouter request failed: {e}")
                raise AIProcessorError(f"OpenRouter API error: {e}")
        else:
            # Exited loop without success (exhausted all attempts without break)
            if last_error:
                raise last_error
            raise AIProcessorError("All OpenRouter API keys exhausted")
        
        # ---- Response handling (reached via break on successful API call) ----
        # Debug log the response
        self._logger.debug(f"Raw completion object: {completion}")
        
        # Handle response extraction safely
        response_text = None
        
        # Check if we have choices and extract content
        if completion and hasattr(completion, "choices") and completion.choices:
            choice = completion.choices[0]
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None)

            if isinstance(content, str):
                response_text = content.strip()
            elif isinstance(content, list):
                extracted_parts = []
                for part in content:
                    text_part = ""
                    if hasattr(part, "text"):
                        text_part = part.text
                    elif isinstance(part, dict):
                        text_part = part.get("text", "")
                    if text_part:
                        extracted_parts.append(text_part)
                if extracted_parts:
                    response_text = "\n".join(extracted_parts).strip()
            elif content is None and hasattr(choice, "delta"):
                delta = getattr(choice, "delta", None)
                if delta is not None:
                    delta_content = getattr(delta, "content", None)
                    if isinstance(delta_content, str):
                        response_text = delta_content.strip()
            # Additional check for safety filter responses
            elif hasattr(choice, 'finish_reason') and choice.finish_reason:
                finish_reason = str(choice.finish_reason).lower()
                if 'content_filter' in finish_reason or 'safety' in finish_reason:
                    self._logger.warning(
                        f"Response blocked by content filter: {choice.finish_reason}"
                    )
                    raise AIProcessorError(
                        "Content was filtered by AI provider. Try with different text."
                    )

            if response_text:
                self._logger.info(f"Got response text: {len(response_text)} chars")
            else:
                self._logger.warning("Message content is None or empty")
        else:
            self._logger.warning("No choices in completion response")
            # Check if indicates filtering
            if hasattr(completion, 'usage') and completion.usage is None:
                self._logger.warning("Completion usage is None, possibly safety filter")
                raise AIProcessorError(
                    "Content was filtered by AI provider. Try with different text."
                )
        
        if not response_text:
            self._logger.error(
                f"Could not extract text from completion. Type: {type(completion)}"
            )
            if completion and hasattr(completion, 'model'):
                self._logger.error(f"Model used: {completion.model}")
            raise AIProcessorError(
                "OpenRouter did not return content. Response may have been filtered."
            )
        
        self._logger.info(
            f"OpenRouter model '{model}' processing complete. "
            f"Response length: {len(response_text)} chars"
        )
        
        # Return AIResponseMetadata for consistency with GeminiProvider
        return AIResponseMetadata(
            response_text=response_text,
            thinking_requested=use_thinking,
            thinking_applied=use_thinking,  # Prompt-based thinking
            web_search_requested=use_web_search,
            web_search_applied=False,  # OpenRouter doesn't support web search
            fallback_reason="OpenRouter doesn't support web search" if use_web_search else None,
            model_used=model
        )
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """Translate text using OpenRouter with Persian phonetic support."""
        if not text:
            raise AIProcessorError("No text provided for translation")
        
        # Get the full language name for the prompt
        from ...utils.translation_utils import get_language_name
        target_language_name = get_language_name(target_language)
        
        # Log the exact text being translated for debugging purposes
        self._logger.debug(f"Translation request - Text: '{text[:100]}...', Target: {target_language} ({target_language_name}), Source: {source_language}")
        
        # Build translation prompt from centralized prompts
        if source_language.lower() == "auto":
            prompt = TRANSLATION_AUTO_DETECT_PROMPT.format(
                target_language_name=target_language_name,
                text=text
            )
        else:
            source_language_name = get_language_name(source_language)
            prompt = TRANSLATION_SOURCE_TARGET_PROMPT.format(
                source_language_name=source_language_name,
                target_language_name=target_language_name,
                text=text
            )
        
        self._logger.info(
            f"Requesting translation for '{text[:50]}...' to {target_language_name} with phonetics."
        )
        
        # Use lower temperature for translation accuracy
        # No max_tokens limit to allow full translation
        # Use flash model for translation (simple task)
        result = await self.execute_prompt(
            prompt,
            max_tokens=self._calculate_max_tokens("translate"),
            temperature=0.2,
            task_type="translate"
        )
        raw_response = result.response_text
        
        # Extract translation and pronunciation from the response
        from ...utils.translation_utils import extract_translation_from_response
        translation, pronunciation = extract_translation_from_response(raw_response)
        
        if translation and pronunciation:
            # Format the response with the required structure
            from ...utils.translation_utils import format_translation_response
            return format_translation_response(translation, pronunciation, target_language)
        else:
            # If extraction failed, return the raw response
            return raw_response
    
    async def analyze_messages(
        self,
        messages: List[Dict[str, Any]],
        analysis_type: str = "summary",
        output_language: str = "english",
        use_thinking: bool = False
    ) -> str:
        """Analyze messages using OpenRouter."""
        if not messages:
            raise AIProcessorError("No messages provided for analysis")
        
        # Format messages for analysis
        formatted_messages = []
        tehran_tz = pytz.timezone('Asia/Tehran')
        timestamps = []
        senders = set()
        
        for msg in messages:  # Process ALL messages (up to 10000)
            timestamp_str = ""
            if 'timestamp' in msg:
                try:
                    if isinstance(msg['timestamp'], str):
                        timestamp = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    else:
                        timestamp = msg['timestamp']
                    
                    if timestamp.tzinfo is None:
                        timestamp = pytz.utc.localize(timestamp)
                    
                    timestamps.append(timestamp)
                    tehran_time = timestamp.astimezone(tehran_tz)
                    timestamp_str = tehran_time.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    self._logger.warning(f"Could not parse timestamp: {e}")
                    timestamp_str = str(msg.get('timestamp', ''))
            
            sender_name = msg.get('sender_name', 'Unknown')
            senders.add(sender_name)
            message_text = msg.get('text', '[No text]')
            
            formatted_messages.append(f"[{timestamp_str}] {sender_name}: {message_text}")
        
        messages_text = "\n".join(formatted_messages)
        num_messages = len(formatted_messages)
        num_senders = len(senders)
        
        # Calculate duration
        duration_minutes = 0
        if len(timestamps) >= 2:
            duration = max(timestamps) - min(timestamps)
            duration_minutes = int(duration.total_seconds() / 60)
        
        # Build analysis prompt based on type
        if analysis_type == "persian_detailed":
            # Use the detailed Persian analysis prompt
            prompt = CONVERSATION_ANALYSIS_PROMPT.format(
                num_messages=num_messages,
                num_senders=num_senders,
                duration_minutes=duration_minutes,
                actual_chat_messages=messages_text
            )
        elif analysis_type == "general":
            prompt = ANALYZE_GENERAL_PROMPT.format(messages_text=messages_text)
        elif analysis_type == "fun":
            prompt = ANALYZE_FUN_PROMPT.format(messages_text=messages_text)
        elif analysis_type == "romance":
            prompt = ANALYZE_ROMANCE_PROMPT.format(messages_text=messages_text)
        elif analysis_type == "voice_summary":
            # Summary for voice messages
            prompt = VOICE_MESSAGE_SUMMARY_PROMPT.format(
                transcribed_text=messages_text
            )
        else:
            # Default summary (from centralized prompts)
            prompt = DEFAULT_CHAT_SUMMARY_PROMPT.format(messages_text=messages_text)
        
        self._logger.info(
            f"Sending conversation ({num_messages} messages) for {analysis_type} analysis, language={output_language}"
        )
        
        # Add English analysis instructions if needed (system messages are merged into prompts)
        if output_language == "english":
            english_instructions = (
                "\n\n**CRITICAL**: You are a sharp, witty analyst with a Bill Burr-style observational humor. "
                "Write ENTIRELY in English. Be direct, funny, and insightful. "
                "Use dry wit and sarcasm while maintaining analytical accuracy. "
                "Structure your response with clear sections and appropriate emojis."
            )
            prompt = prompt + english_instructions
        
        # Append language instruction to prompt
        lang_instr = f"\n\n**CRITICAL**: Write your ENTIRE response in {output_language.upper()}. "
        if output_language == "persian":
            lang_instr += "Use colloquial Persian (یارو, رفیق), natural spacing (می‌آد not می اورد)."
        else:
            lang_instr += "Do NOT use Persian/Farsi. Write everything in English only."
        
        # Add Telegram-specific formatting guidelines (centralized in prompts.py)
        format_guidelines = get_telegram_formatting_guidelines(output_language)
        
        # Add response scaling instructions based on message count and analysis type
        scaling_instructions = get_response_scaling_instructions(num_messages, analysis_type)
        
        formatted_prompt = prompt + lang_instr + format_guidelines + scaling_instructions
        
        # Calculate tiered max_tokens based on conversation size
        max_tokens = self._calculate_max_tokens("analyze", num_messages)
        
        self._logger.info(
            f"Analysis task: {num_messages} messages, using max_tokens={max_tokens}"
        )
        
        # Use pro model for analysis (complex task)
        result = await self.execute_prompt(
            formatted_prompt, 
            max_tokens=max_tokens, 
            temperature=0.4,
            task_type="analyze",
            use_thinking=use_thinking
        )
        return result.response_text
    
    async def answer_question_from_history(
        self,
        messages: List[Dict[str, Any]],
        question: str,
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> str:
        """Answer a question based on chat history using Persian prompts."""
        if not messages:
            raise AIProcessorError("No messages provided for question answering")
        
        if not question:
            raise AIProcessorError("No question provided")
        
        # Format messages for context
        formatted_messages = []
        for msg in messages:  # Process ALL messages for full context
            sender = msg.get('sender_name', 'Unknown')
            text = msg.get('text', '')
            if text:
                formatted_messages.append(f"{sender}: {text}")
        
        if not formatted_messages:
            return "هیچ پیام متنی در تاریخچه ارائه شده یافت نشد."
        
        combined_history = "\n".join(formatted_messages)
        
        # Build Persian question-answering prompt with formatting guidelines
        prompt = QUESTION_ANSWER_PROMPT.format(
            combined_history_text=combined_history,
            user_question=question
        )
        
        # Add centralized formatting guidelines
        format_guidelines = get_telegram_formatting_guidelines("persian")
        formatted_prompt = prompt + format_guidelines
        
        self._logger.info(
            f"Answering question '{question[:50]}...' based on {len(formatted_messages)} messages"
        )
        
        # Calculate max_tokens for tellme (always 32k for comprehensive Q&A)
        max_tokens = self._calculate_max_tokens("tellme")
        
        # Note: OpenRouter doesn't support Google Search tool directly
        if use_web_search:
            self._logger.warning("Web search requested but OpenRouter doesn't support Google Search tool")
        
        # Use pro model for tellme (complex task)
        result = await self.execute_prompt(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=0.5,
            task_type="tellme",
            use_thinking=use_thinking,
            use_web_search=use_web_search
        )
        return result.response_text
    
    async def close(self) -> None:
        """Clean up OpenRouter client."""
        self._client = None
