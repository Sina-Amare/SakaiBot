"""OpenRouter LLM provider implementation (fallback provider)."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

import openai
from openai import AsyncOpenAI

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

    @staticmethod
    def _extract_response_text(completion: Any) -> tuple:
        """Extract usable text and finish_reason from an OpenRouter completion.

        Handles plain string content, multimodal list content, streaming-style
        delta content, and DeepSeek-style ``reasoning`` / ``reasoning_content``
        fields — some DeepSeek models leave ``content`` empty and put the
        answer in a reasoning field, which the previous code discarded.

        Returns:
            ``(response_text, finish_reason)`` — ``response_text`` is the
            stripped text, or ``None`` if nothing usable was found;
            ``finish_reason`` is lowercased, or ``None``.
        """
        if not completion or not getattr(completion, "choices", None):
            return None, None

        choice = completion.choices[0]
        raw_finish = getattr(choice, "finish_reason", None)
        finish_reason = str(raw_finish).lower() if raw_finish else None

        message = getattr(choice, "message", None)

        # 1. Standard content field (string or multimodal list).
        content = getattr(message, "content", None) if message else None
        if isinstance(content, str) and content.strip():
            return content.strip(), finish_reason
        if isinstance(content, list):
            parts = []
            for part in content:
                text_part = ""
                if hasattr(part, "text"):
                    text_part = part.text or ""
                elif isinstance(part, dict):
                    text_part = part.get("text", "")
                if text_part:
                    parts.append(text_part)
            if parts:
                return "\n".join(parts).strip(), finish_reason

        # 2. DeepSeek-style reasoning fields (content empty, answer in
        #    reasoning). May be a typed attribute or a pydantic extra field.
        if message is not None:
            extra = getattr(message, "model_extra", None) or {}
            for attr in ("reasoning_content", "reasoning"):
                value = getattr(message, attr, None)
                if not value and isinstance(extra, dict):
                    value = extra.get(attr)
                if isinstance(value, str) and value.strip():
                    return value.strip(), finish_reason

        # 3. Streaming-style delta content.
        delta = getattr(choice, "delta", None)
        if delta is not None:
            delta_content = getattr(delta, "content", None)
            if isinstance(delta_content, str) and delta_content.strip():
                return delta_content.strip(), finish_reason

        return None, finish_reason

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
        
        # Retry loop: rotates keys on 429, and retries transient empty
        # responses (free models occasionally return no content under load).
        max_key_attempts = self._key_manager.num_keys if self._key_manager else 1
        max_attempts = max_key_attempts + 2
        attempts = 0
        last_error = None
        response_text = None

        while attempts < max_attempts:
            attempts += 1
            try:
                client = self._get_client()

                # Prompt is already self-contained (system messages merged)
                messages = [{"role": "user", "content": user_prompt}]

                self._logger.info(
                    f"Sending prompt to OpenRouter model '{model}' "
                    f"(attempt {attempts}/{max_attempts}). "
                    f"Prompt preview: '{user_prompt[:100]}...'"
                )

                try:
                    completion = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        extra_headers=OPENROUTER_HEADERS,
                        timeout=600.0  # 10 minute timeout for large requests
                    )
                except openai.APITimeoutError:
                    self._logger.error(
                        f"Request timed out for model '{model}'"
                    )
                    raise AIProcessorError(
                        "Request timed out. Try with fewer messages."
                    )
                except (openai.RateLimitError,
                        openai.APIConnectionError,
                        openai.InternalServerError) as e:
                    # Retryable: provider rate limit (429), network error, or
                    # 5xx. The OpenAI SDK wraps OpenRouter's HTTP errors in
                    # these types - a plain httpx handler never sees them.
                    self._logger.warning(
                        f"OpenRouter retryable error on attempt {attempts}: "
                        f"{type(e).__name__}: {str(e)[:160]}"
                    )
                    last_error = AIProcessorError(
                        f"OpenRouter error: {str(e)[:160]}"
                    )
                    if self._key_manager and self._key_manager.num_keys > 1:
                        self._key_manager.mark_key_rate_limited()
                    self._client = None
                    self._last_used_key = None
                    await asyncio.sleep(2.0)
                    continue
                except openai.APIStatusError as e:
                    # Non-retryable HTTP status (400/401/403/404, ...).
                    status = getattr(e, "status_code", "?")
                    self._logger.error(
                        f"OpenRouter API error {status}: {str(e)[:200]}"
                    )
                    raise AIProcessorError(
                        f"OpenRouter API error {status}: {str(e)[:200]}"
                    )

                self._logger.debug(f"Raw completion object: {completion}")

                # Extract usable text (handles content, multimodal list,
                # delta, and DeepSeek-style reasoning fields).
                response_text, finish_reason = self._extract_response_text(
                    completion
                )

                if response_text:
                    self._logger.info(
                        f"Got response text: {len(response_text)} chars"
                    )
                    break  # success

                # A genuine content-filter block is not retryable.
                if finish_reason and (
                    "content_filter" in finish_reason
                    or "safety" in finish_reason
                ):
                    self._logger.warning(
                        f"Response blocked by content filter: {finish_reason}"
                    )
                    raise AIProcessorError(
                        "Content was filtered by AI provider. "
                        "Try with different text."
                    )

                # Transient empty response - common with free models under
                # load. Retry, rotating to a different key when possible.
                self._logger.warning(
                    f"OpenRouter returned empty content "
                    f"(finish_reason={finish_reason}); retrying "
                    f"(attempt {attempts}/{max_attempts})"
                )
                last_error = AIProcessorError(
                    "OpenRouter returned an empty response"
                )
                if self._key_manager and self._key_manager.num_keys > 1:
                    self._key_manager.mark_key_rate_limited()
                self._client = None
                self._last_used_key = None
                await asyncio.sleep(1.0)
                continue

            except AIProcessorError:
                raise
            except Exception as e:
                self._logger.error(f"OpenRouter request failed: {e}")
                raise AIProcessorError(f"OpenRouter API error: {e}")
        else:
            # Loop exhausted without a usable response.
            self._logger.error(
                f"OpenRouter returned no usable content after "
                f"{attempts} attempt(s)"
            )
            raise last_error or AIProcessorError(
                "OpenRouter did not return content after retries."
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
    ) -> AIResponseMetadata:
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
            return AIResponseMetadata(
                response_text="هیچ پیام متنی در تاریخچه ارائه شده یافت نشد.",
                thinking_requested=use_thinking,
                thinking_applied=False,
                web_search_requested=use_web_search,
                web_search_applied=False,
            )
        
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
        return result
    
    async def close(self) -> None:
        """Clean up OpenRouter client."""
        self._client = None
