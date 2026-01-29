"""Google Gemini LLM provider implementation with key rotation."""

import os
import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import pytz

from ..llm_interface import LLMProvider
from ..response_metadata import AIResponseMetadata
from ...core.exceptions import AIProcessorError
from ...core.constants import COMPLEX_TASKS, SIMPLE_TASKS
from ...utils.logging import get_logger
from ..api_key_manager import GeminiKeyManager, initialize_gemini_key_manager, get_gemini_key_manager
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

# Constants
THINKING_BUDGET_DEFAULT: int = 4096
THINKING_SUMMARY_MAX_CHARS: int = 600


class GeminiProvider(LLMProvider):
    """Google Gemini provider for LLM operations with key rotation support."""
    
    def __init__(self, config: Any) -> None:
        """Initialize Gemini provider with key manager."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client = None
        self._clients: Dict[str, Any] = {}  # Cache clients per API key
        
        # Initialize key manager if multiple keys available
        api_keys = getattr(config, 'gemini_api_keys', [])
        if api_keys:
            self._key_manager = initialize_gemini_key_manager(api_keys, cooldown_seconds=60)
            self._api_key = self._key_manager.get_current_key() if self._key_manager else None
            self._logger.info(f"Initialized with {len(api_keys)} Gemini API keys for rotation")
        else:
            # Fallback to single key
            self._key_manager = None
            self._api_key = config.gemini_api_key
        
        # Model configuration - pro for complex tasks, flash for simple
        self._model_pro = getattr(config, 'gemini_model_pro', 'gemini-2.5-pro')
        self._model_flash = getattr(config, 'gemini_model_flash', 'gemini-2.5-flash')
        self._model = config.gemini_model  # Legacy default
        
        # Pro model fallback state - when Pro is exhausted, fallback to Flash
        self._pro_model_exhausted_until: Optional[datetime] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
        # Check if key manager has keys or fallback to single key
        if self._key_manager:
            return not self._key_manager.all_keys_exhausted()
        return bool(
            self._api_key
            and "YOUR_GEMINI_API_KEY_HERE" not in (self._api_key or "")
            and len(self._api_key or "") > 10
        )
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "Google Gemini"
    
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self._model
    
    def get_model_for_task(self, task_type: str) -> str:
        """Get appropriate model based on task complexity.
        
        If Pro model is exhausted (429), automatically falls back to Flash.
        """
        if task_type in COMPLEX_TASKS:
            # Check if Pro model is exhausted
            if self._is_pro_model_exhausted():
                self._logger.info(
                    f"Pro model exhausted, using Flash for {task_type}"
                )
                return self._model_flash
            return self._model_pro
        elif task_type in SIMPLE_TASKS:
            return self._model_flash
        return self._model  # Legacy default
    
    def _is_pro_model_exhausted(self) -> bool:
        """Check if Pro model is exhausted for the current quota period."""
        if self._pro_model_exhausted_until is None:
            return False
        
        import pytz
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        if now_utc < self._pro_model_exhausted_until:
            return True
        
        # Reset - quota period has passed
        self._pro_model_exhausted_until = None
        self._logger.info("Pro model quota reset - Pro model available again")
        return False
    
    def _mark_pro_model_exhausted(self):
        """Mark Pro model as exhausted until next Pacific midnight."""
        import pytz
        pacific_tz = pytz.timezone("America/Los_Angeles")
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        now_pacific = now_utc.astimezone(pacific_tz)
        
        # Calculate next Pacific midnight
        today_midnight = now_pacific.replace(hour=0, minute=0, second=0, microsecond=0)
        if now_pacific >= today_midnight:
            next_midnight = today_midnight + timedelta(days=1)
        else:
            next_midnight = today_midnight
        
        self._pro_model_exhausted_until = next_midnight.astimezone(pytz.utc)
        self._logger.warning(
            f"Pro model (gemini-2.5-pro) exhausted until "
            f"{self._pro_model_exhausted_until.isoformat()} UTC. Using Flash as fallback."
        )
    
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
    
    def _get_client(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Get or create Gemini client for specified key and model."""
        key = api_key or self._api_key
        model_name = model or self._model
        
        if not key:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        # Create cache key
        cache_key = f"{key[:8]}_{model_name}"
        
        if cache_key not in self._clients:
            try:
                import google.generativeai as genai
                
                # Configure the GenAI library with the API key
                genai.configure(api_key=key)
                
                # Create client with model
                self._clients[cache_key] = genai.GenerativeModel(model_name)
                
                masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
                self._logger.info(f"Initialized Gemini client: key={masked_key}, model={model_name}")
                
            except ImportError:
                raise AIProcessorError(
                    "Google GenAI library not installed. Run: pip install google-generativeai"
                )
            except Exception as e:
                raise AIProcessorError(f"Failed to initialize Gemini client: {e}")
        
        return self._clients[cache_key]
    
    async def _execute_with_native_thinking(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 32000,
        use_web_search: bool = False
    ) -> AIResponseMetadata:
        """
        Execute prompt using native Gemini ThinkingConfig API with key rotation.
        
        Uses the new google.genai SDK for real thinking mode with thought summaries.
        Includes retry logic and key rotation for resilience.
        
        Args:
            prompt: The user prompt
            model: Model name to use
            temperature: Temperature for generation
            max_tokens: Maximum output tokens
            use_web_search: Whether to enable web search
            
        Returns:
            AIResponseMetadata with thinking_summary populated
        """
        from google import genai
        from google.genai import types
        
        max_retries = 3
        retry_delay = 1.0
        keys_tried = 0
        max_key_attempts = self._key_manager.num_keys if self._key_manager else 1
        last_error = None
        
        self._logger.info(
            f"[THINKING] Starting native thinking for model={model}, "
            f"budget={THINKING_BUDGET_DEFAULT}, max_keys={max_key_attempts}"
        )
        
        while keys_tried < max_key_attempts:
            # Get current API key
            current_key = (
                self._key_manager.get_current_key() 
                if self._key_manager 
                else self._api_key
            )
            
            if not current_key:
                if self._key_manager and self._key_manager.all_keys_exhausted():
                    raise AIProcessorError(
                        "All Gemini API keys are rate-limited. Please try again later."
                    )
                raise AIProcessorError("No valid Gemini API key available")
            
            # Create client with new SDK
            client = genai.Client(api_key=current_key)
            
            for attempt in range(max_retries):
                try:
                    self._logger.info(
                        f"[THINKING] Attempt {attempt + 1}: model={model}, "
                        f"key={current_key[:8]}..."
                    )
                    
                    # Build thinking config with include_thoughts=True
                    thinking_config = types.ThinkingConfig(
                        thinking_budget=THINKING_BUDGET_DEFAULT,
                        include_thoughts=True
                    )
                    
                    config = types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        thinking_config=thinking_config
                    )
                    
                    # Execute with thinking using ASYNC client
                    self._logger.debug(
                        f"[THINKING] Calling async generate_content with model={model}, "
                        f"budget={thinking_config.thinking_budget}"
                    )
                    response = await client.aio.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    )
                    
                    # Debug logging for troubleshooting (only in debug mode)
                    if self._logger.isEnabledFor(logging.DEBUG):
                        self._logger.debug(
                            f"[THINKING-DEBUG] Response type: {type(response)}, "
                            f"has_candidates: {bool(response.candidates)}"
                        )
                        if response.candidates and response.candidates[0].content.parts:
                            self._logger.debug(
                                f"[THINKING-DEBUG] Found {len(response.candidates[0].content.parts)} parts"
                            )
                    
                    # Extract parts: thought=True is reasoning, thought=None/False is answer
                    raw_thinking = None
                    answer_text = None
                    
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if not hasattr(part, 'text') or not part.text:
                                continue
                            
                            is_thinking_part = getattr(part, 'thought', None) is True
                            
                            if is_thinking_part:
                                raw_thinking = part.text
                                self._logger.info(
                                    f"Found thinking part: {len(raw_thinking)} chars"
                                )
                            else:
                                answer_text = part.text
                                self._logger.info(
                                    f"Found answer part: {len(answer_text)} chars"
                                )
                    
                    # Fallback to response.text if no answer found
                    if not answer_text:
                        answer_text = response.text if hasattr(response, 'text') else ""
                    
                    # Create brief summary of thinking
                    thinking_summary = None
                    if raw_thinking:
                        lines = raw_thinking.strip().split('\n')
                        preview_lines = []
                        char_count = 0
                        for line in lines:
                            if char_count + len(line) > THINKING_SUMMARY_MAX_CHARS:
                                break
                            preview_lines.append(line)
                            char_count += len(line)
                        thinking_summary = '\n'.join(preview_lines)
                        if len(raw_thinking) > len(thinking_summary):
                            thinking_summary += "\n[...truncated]"
                    
                    # Log thinking result (debug level only)
                    if raw_thinking:
                        self._logger.debug(
                            f"[THINKING] Received thinking parts: "
                            f"{len(raw_thinking)} chars, summary: {len(thinking_summary or '')} chars"
                        )
                    else:
                        self._logger.warning(
                            f"[THINKING] No thinking parts in response for model={model}. "
                            f"Model may not support thinking mode or API issue occurred."
                        )
                    
                    # Mark key as successful
                    if self._key_manager:
                        self._key_manager.mark_success()
                    
                    self._logger.info(
                        f"Native thinking completed. "
                        f"Answer: {len(answer_text or '')} chars, "
                        f"Thinking: {len(raw_thinking or '')} chars"
                    )
                    
                    return AIResponseMetadata(
                        response_text=answer_text.strip() if answer_text else "",
                        thinking_requested=True,
                        thinking_applied=True,
                        thinking_summary=thinking_summary,
                        web_search_requested=use_web_search,
                        web_search_applied=False,
                        model_used=model
                    )
                    
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # Check for rate limit (429)
                    is_429 = "429" in error_str or "rate" in error_str
                    
                    if is_429 and self._key_manager:
                        self._logger.warning(
                            f"Thinking mode: 429 rate limit hit. "
                            f"Rotating key and retrying..."
                        )
                        has_more_keys = self._key_manager.mark_key_exhausted_for_day()
                        if has_more_keys:
                            keys_tried += 1
                            retry_delay = 1.0
                            break  # Try next key
                        else:
                            # All keys exhausted - try Flash if we were using Pro
                            if model == self._model_pro:
                                self._mark_pro_model_exhausted()
                                raise AIProcessorError(
                                    "RETRY_WITH_FLASH: All Pro keys exhausted"
                                )
                            raise AIProcessorError(
                                "All Gemini API keys are exhausted for today. "
                                "Please try again later."
                            )
                    
                    self._logger.error(
                        f"Thinking mode attempt {attempt + 1} failed: {e}"
                    )
                    
                    if attempt < max_retries - 1:
                        self._logger.info(f"Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        # All attempts failed for this key
                        if self._key_manager:
                            self._key_manager.mark_key_error()
                            if not self._key_manager.all_keys_exhausted():
                                keys_tried += 1
                                retry_delay = 1.0
                                break  # Try next key
                        # No more keys or no key manager
                        raise AIProcessorError(
                            f"Thinking mode failed after {max_retries} attempts: {e}"
                        )
            else:
                # Inner loop completed without break - all attempts exhausted
                break
        
        # All keys exhausted
        raise AIProcessorError(
            f"Thinking mode failed with all available keys. Last error: {last_error}"
        )

    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        task_type: str = "default",
        use_thinking: bool = False,
        use_web_search: bool = False,
        _is_model_fallback_retry: bool = False
    ) -> AIResponseMetadata:
        """Execute a prompt using Google Gemini with retry logic and key rotation."""
        self._logger.info(
            f"[TRACE] execute_prompt called: use_thinking={use_thinking}, "
            f"task_type={task_type}, _is_model_fallback_retry={_is_model_fallback_retry}"
        )
        
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        # Select model based on task type
        model = self.get_model_for_task(task_type)
        
        # Prompt is already self-contained (system messages merged into prompts)
        full_prompt = user_prompt
        
        # Track if we're using model fallback
        model_fallback_applied = _is_model_fallback_retry
        model_fallback_reason = "Pro model quota exceeded" if _is_model_fallback_retry else None
        
        try:
            result = await self._execute_prompt_internal(
                full_prompt=full_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                task_type=task_type,
                use_thinking=use_thinking,
                use_web_search=use_web_search
            )
            # Set fallback info if this was a retry
            if model_fallback_applied:
                result.model_fallback_applied = True
                result.model_fallback_reason = model_fallback_reason
            return result
        except AIProcessorError as e:
            # Check if we should retry with Flash model
            if "RETRY_WITH_FLASH" in str(e) and not _is_model_fallback_retry:
                self._logger.info(
                    "Pro model exhausted, auto-retrying with Flash model"
                )
                # Reset keys for Flash - Pro and Flash have SEPARATE quotas
                if self._key_manager:
                    self._key_manager.reset_for_model_switch()
                return await self.execute_prompt(
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    task_type=task_type,
                    use_thinking=use_thinking,
                    use_web_search=use_web_search,
                    _is_model_fallback_retry=True
                )
            raise

    async def _execute_prompt_internal(
        self,
        full_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        task_type: str,
        use_thinking: bool,
        use_web_search: bool
    ) -> AIResponseMetadata:
        """Internal method that actually executes the prompt."""
        self._logger.info(
            f"[TRACE] _execute_prompt_internal: use_thinking={use_thinking}, model={model}"
        )
        
        # If thinking mode is enabled, use the NEW google.genai SDK for native thinking
        if use_thinking:
            self._logger.info(f"[TRACE] Thinking mode enabled, calling _execute_with_native_thinking")
            self._logger.info("Using native ThinkingConfig for deep reasoning")
            # Always use native thinking when requested - don't fall through to standard
            result = await self._execute_with_native_thinking(
                prompt=full_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                use_web_search=use_web_search
            )
            self._logger.info(f"[TRACE] Native thinking succeeded")
            return result
        else:
            self._logger.info(f"[TRACE] Thinking mode disabled, using standard execution")
        
        # Log the exact prompt being sent for debugging
        self._logger.debug(f"Sending prompt to Gemini: '{full_prompt[:100]}...'")
        
        # Retry logic with key rotation support
        max_retries = 3
        retry_delay = 1.0
        keys_tried = 0
        max_key_attempts = self._key_manager.num_keys if self._key_manager else 1
        
        # Track web search usage - may be disabled if 403 error occurs
        actual_use_web_search = use_web_search
        web_search_fallback_reason = None
        
        while keys_tried < max_key_attempts:
            # Get current API key
            current_key = self._key_manager.get_current_key() if self._key_manager else self._api_key
            
            if not current_key:
                if self._key_manager and self._key_manager.all_keys_exhausted():
                    raise AIProcessorError("All Gemini API keys are rate-limited. Please try again later.")
                raise AIProcessorError("No valid Gemini API key available")
            
            for attempt in range(max_retries):
                try:
                    client = self._get_client(api_key=current_key, model=model)

                    self._logger.info(
                        f"Attempt {attempt + 1}: Sending prompt to Gemini '{model}'. "
                        f"Prompt length: {len(full_prompt)} chars"
                    )
                    
                    # Configure the generation parameters
                    # Use the max_tokens parameter instead of hardcoded value
                    generation_config = {
                        "temperature": temperature,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": max_tokens,
                    }

                    # Prepare tools for web search if enabled
                    tools = None
                    if actual_use_web_search:
                        try:
                            import google.generativeai as genai
                            # Enable Google Search tool using correct protobuf format
                            # Tool.GoogleSearch is a nested class, not a top-level GoogleSearch
                            google_search_tool = genai.protos.Tool(
                                google_search=genai.protos.Tool.GoogleSearch()
                            )
                            tools = [google_search_tool]
                            self._logger.info("Google Search tool enabled for this request")
                        except Exception as e:
                            self._logger.warning(
                                f"Failed to enable Google Search tool: {e}. "
                                "Continuing without web search."
                            )
                            tools = None  # Ensure tools is None if setup fails
                    
                    # Use asyncio to run the async call with timeout
                    try:
                        # Build request parameters
                        if tools:
                            response = await asyncio.wait_for(
                                client.generate_content_async(
                                    full_prompt,
                                    tools=tools
                                ),
                                timeout=300 # 5 minute timeout for LLM response
                            )
                        else:
                            response = await asyncio.wait_for(
                                client.generate_content_async(full_prompt),
                                timeout=300 # 5 minute timeout for LLM response
                            )
                    except asyncio.TimeoutError:
                        self._logger.error(f"LLM response timed out after 5 minutes for model '{model}'")
                        raise AIProcessorError("Request timed out. The LLM did not respond within the expected time. Try again later or with a shorter prompt.")
                    
                    # Extract text from response
                    response_text = None
                    
                    # First try direct text attribute
                    if response and hasattr(response, 'text') and response.text:
                        response_text = response.text.strip()
                        self._logger.info(f"Got response text directly: {len(response_text)} chars")
                    elif response and hasattr(response, 'candidates') and response.candidates:
                        # If text attribute not available, check candidates
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and candidate.content:
                                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                    # Extract text from parts
                                    text_parts = []
                                    for part in candidate.content.parts:
                                        if hasattr(part, 'text') and part.text:
                                            text_parts.append(part.text)
                                    if text_parts:
                                        response_text = ' '.join(text_parts).strip()
                                        self._logger.info(f"Got response text from parts: {len(response_text)} chars")
                                        break
                    
                    # Check for safety blocks or other issues
                    if not response_text:
                        if hasattr(response, 'prompt_feedback'):
                            feedback = response.prompt_feedback
                            self._logger.error(f"Prompt feedback: {feedback}")
                            if 'block_reason' in str(feedback).lower():
                                raise AIProcessorError("Content was blocked by safety filters. Try rephrasing.")
                        
                        # If this is not the last attempt, retry
                        if attempt < max_retries - 1:
                            self._logger.warning(f"No response on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            # Last attempt failed - return user-friendly error message
                            response_text = (
                                "⚠️ <b>Processing Error</b>\n\n"
                                "I received your request but couldn't generate a proper response.\n\n"
                                "<i>💡 This may be due to API issues or content filtering. Please try again.</i>"
                            )
                    
                    if response_text:
                        # Mark key as successful
                        if self._key_manager:
                            self._key_manager.mark_success()

                        self._logger.info(
                            f"Gemini '{model}' completed successfully. Response: {len(response_text)} chars"
                        )
                        
                        # Build and return metadata with execution status
                        # Thinking is considered applied if it was requested and we got a response
                        # (since it's prompt-based, if the API call succeeded, thinking worked)
                        return AIResponseMetadata(
                            response_text=response_text,
                            thinking_requested=use_thinking,
                            thinking_applied=use_thinking,  # Prompt-based, always works if response received
                            web_search_requested=use_web_search,
                            web_search_applied=use_web_search and actual_use_web_search and tools is not None,
                            fallback_reason=web_search_fallback_reason,
                            model_used=model
                        )

                except Exception as e:
                    error_str = str(e).lower()

                    # Try to get an HTTP status code if available (no regex needed)
                    status_code = None
                    response = getattr(e, "response", None)
                    if response is not None:
                        status_code = getattr(response, "status_code", None)
                    
                    # Check for 403 Permission Denied (often means Google Search tool not available)
                    is_403 = (status_code == 403) or ("403" in error_str) or ("permissiondenied" in error_str)
                    
                    # If 403 and web search was enabled, disable it and retry
                    if is_403 and actual_use_web_search:
                        self._logger.warning(
                            f"Google Search tool returned 403 (Permission Denied). "
                            f"This may indicate the tool is not available for your API key or requires special permissions. "
                            f"Continuing without web search..."
                        )
                        # Disable web search for remaining attempts and track the fallback
                        actual_use_web_search = False
                        web_search_fallback_reason = "API returned 403 - billing may be required"
                        # Continue to retry without web search
                        if attempt < max_retries - 1:
                            continue

                    is_429 = (status_code == 429) or ("429" in error_str)

                    if is_429:
                        # Check if this is a Pro model request - if so, don't
                        # exhaust keys, just mark Pro model as exhausted
                        if model == self._model_pro and model != self._model_flash:
                            self._logger.warning(
                                "Gemini Pro model returned 429. "
                                "Marking Pro model exhausted and falling back to Flash."
                            )
                            self._mark_pro_model_exhausted()
                            raise AIProcessorError(
                                "RETRY_WITH_FLASH: Pro model quota exhausted. "
                                "Falling back to Flash model."
                            )
                        
                        # For Flash model 429s, exhaust keys as before
                        if self._key_manager:
                            self._logger.warning(
                                "Gemini returned 429 (rate limit / quota). "
                                "Marking current key exhausted until next Pacific midnight "
                                "and rotating to another key if available."
                            )
                            has_more_keys = self._key_manager.mark_key_exhausted_for_day()
                            if has_more_keys:
                                # Break inner loop to try next key
                                keys_tried += 1
                                retry_delay = 1.0  # Reset delay for new key
                                break
                            else:
                                raise AIProcessorError(
                                    "All Gemini API keys are exhausted for today. "
                                    "Requests per day (RPD) reset at midnight Pacific Time. "
                                    "See ai.google.dev/gemini-api/docs/rate-limits"
                                )

                    self._logger.error(
                        f"Attempt {attempt + 1} failed for Gemini '{model}': {e}",
                        exc_info=True
                    )

                    # If this is not the last attempt, retry
                    if attempt < max_retries - 1:
                        self._logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        # All attempts failed for this key
                        if self._key_manager:
                            self._key_manager.mark_key_error()
                            if not self._key_manager.all_keys_exhausted():
                                keys_tried += 1
                                retry_delay = 1.0
                                break  # Try next key
                        raise AIProcessorError(f"Failed after {max_retries} attempts: {e}")
            else:
                # Inner loop completed without break - success or exhausted retries
                break
        
        # Should not reach here
        raise AIProcessorError("Unexpected error in Gemini execution")
    
    async def execute_prompt_simple(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        task_type: str = "default",
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> str:
        """Execute prompt and return just the text (for backward compatibility)."""
        result = await self.execute_prompt(
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            task_type=task_type,
            use_thinking=use_thinking,
            use_web_search=use_web_search
        )
        return result.response_text
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """Translate text using Google Gemini with Persian phonetic support."""
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
        
        # Calculate max_tokens for translation
        max_tokens = self._calculate_max_tokens("translate")
        
        # Use lower temperature for translation accuracy
        # Use flash model for translation (simple task)
        result = await self.execute_prompt(
            prompt,
            max_tokens=max_tokens,
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
        """Analyze messages using Google Gemini with Persian analysis."""
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
        
        # Use lower temperature for analysis accuracy
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
    ) -> "AIResponseMetadata":
        """Answer a question based on chat history using Persian prompts.
        
        Returns AIResponseMetadata to preserve thinking_summary for display.
        """
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
            from ..response_metadata import AIResponseMetadata
            return AIResponseMetadata(
                response_text="هیچ پیام متنی در تاریخچه ارائه شده یافت نشد.",
                thinking_requested=use_thinking,
                thinking_applied=False
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
        
        # Use pro model for tellme (complex task)
        result = await self.execute_prompt(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=0.5,
            task_type="tellme",
            use_thinking=use_thinking,
            use_web_search=use_web_search
        )
        return result  # Return full AIResponseMetadata
    
    async def close(self) -> None:
        """Clean up Gemini clients."""
        self._client = None
        self._clients.clear()
