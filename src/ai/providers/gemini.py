"""Google Gemini LLM provider implementation with key rotation."""

import os
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from ..llm_interface import LLMProvider
from ...core.exceptions import AIProcessorError
from ...core.constants import COMPLEX_TASKS, SIMPLE_TASKS
from ...utils.logging import get_logger
from ..api_key_manager import GeminiKeyManager, initialize_gemini_key_manager, get_gemini_key_manager
from ..prompts import (
    TRANSLATION_SYSTEM_MESSAGE,
    TRANSLATION_AUTO_DETECT_PROMPT,
    TRANSLATION_SOURCE_TARGET_PROMPT,
    CONVERSATION_ANALYSIS_PROMPT,
    CONVERSATION_ANALYSIS_SYSTEM_MESSAGE,
    QUESTION_ANSWER_PROMPT,
    QUESTION_ANSWER_SYSTEM_MESSAGE,
    VOICE_MESSAGE_SUMMARY_PROMPT,
    ANALYZE_GENERAL_PROMPT,
    ANALYZE_FUN_PROMPT,
    ANALYZE_ROMANCE_PROMPT,
    ANALYZE_FUN_SYSTEM_MESSAGE,
    ENGLISH_ANALYSIS_SYSTEM_MESSAGE,
    DEFAULT_CHAT_SUMMARY_PROMPT,
    get_telegram_formatting_guidelines,
    get_response_scaling_instructions
)


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
        """Get appropriate model based on task complexity."""
        if task_type in COMPLEX_TASKS:
            return self._model_pro
        elif task_type in SIMPLE_TASKS:
            return self._model_flash
        return self._model  # Legacy default
    
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
    
    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        task_type: str = "default"
    ) -> str:
        """Execute a prompt using Google Gemini with retry logic and key rotation."""
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        # Select model based on task type
        model = self.get_model_for_task(task_type)
        
        # Combine system message and user prompt if needed
        if system_message and system_message.strip():
            full_prompt = f"{system_message}\n\n{user_prompt}"
            self._logger.debug(f"Using system message with prompt")
        else:
            full_prompt = user_prompt
        
        # Log the exact prompt being sent for debugging
        self._logger.debug(f"Sending prompt to Gemini: '{full_prompt[:100]}...'")
        
        # Retry logic with key rotation support
        max_retries = 3
        retry_delay = 1.0
        keys_tried = 0
        max_key_attempts = 3 if self._key_manager else 1
        
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
                    generation_config = {
                        "temperature": temperature,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 16000,
                    }

                    # Use asyncio to run the async call with timeout
                    try:
                        response = await asyncio.wait_for(
                            client.generate_content_async(
                                full_prompt
                            ),
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
                            # Last attempt failed
                            response_text = "من درخواست شما رو دریافت کردم ولی نتونستم جواب مناسبی بدم. ممکنه مشکل از API باشه یا محتوا فیلتر شده. دوباره امتحان کن."
                    
                    if response_text:
                        # Mark key as successful
                        if self._key_manager:
                            self._key_manager.mark_success()

                        self._logger.info(
                            f"Gemini '{model}' completed successfully. Response: {len(response_text)} chars"
                        )
                        return response_text

                except Exception as e:
                    error_str = str(e).lower()

                    # Try to get an HTTP status code if available (no regex needed)
                    status_code = None
                    response = getattr(e, "response", None)
                    if response is not None:
                        status_code = getattr(response, "status_code", None)

                    is_429 = (status_code == 429) or ("429" in error_str)

                    if is_429 and self._key_manager:
                        # For free tier usage, treat any 429 as daily quota exhaustion.
                        # Gemini RPD limits reset at midnight Pacific time:
                        # https://ai.google.dev/gemini-api/docs/rate-limits#free-tier
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
                                "Requests per day (RPD) reset at midnight Pacific time. "
                                "See https://ai.google.dev/gemini-api/docs/rate-limits#free-tier"
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
        
        # Use lower temperature for translation accuracy
        # No max_tokens limit to allow full translation
        # Use flash model for translation (simple task)
        raw_response = await self.execute_prompt(
            prompt,
            temperature=0.2,
            system_message=TRANSLATION_SYSTEM_MESSAGE,
            task_type="translate"
        )
        
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
        output_language: str = "english"
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
            system_message = CONVERSATION_ANALYSIS_SYSTEM_MESSAGE
        elif analysis_type == "general":
            prompt = ANALYZE_GENERAL_PROMPT.format(messages_text=messages_text)
            system_message = None
        elif analysis_type == "fun":
            prompt = ANALYZE_FUN_PROMPT.format(messages_text=messages_text)
            system_message = ANALYZE_FUN_SYSTEM_MESSAGE
        elif analysis_type == "romance":
            prompt = ANALYZE_ROMANCE_PROMPT.format(messages_text=messages_text)
            system_message = None
        elif analysis_type == "voice_summary":
            # Summary for voice messages
            prompt = VOICE_MESSAGE_SUMMARY_PROMPT.format(
                transcribed_text=messages_text
            )
            system_message = None
        else:
            # Default summary (from centralized prompts)
            prompt = DEFAULT_CHAT_SUMMARY_PROMPT.format(messages_text=messages_text)
            system_message = None
        
        self._logger.info(
            f"Sending conversation ({num_messages} messages) for {analysis_type} analysis, language={output_language}"
        )
        
        # Override system message for English output (from centralized prompts)
        if output_language == "english":
            system_message = ENGLISH_ANALYSIS_SYSTEM_MESSAGE
        
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
        
        # Use lower temperature for analysis accuracy
        # Use pro model for analysis (complex task)
        return await self.execute_prompt(
            formatted_prompt, 
            max_tokens=100000, 
            temperature=0.4,
            system_message=system_message,
            task_type="analyze"
        )
    
    async def answer_question_from_history(
        self,
        messages: List[Dict[str, Any]],
        question: str
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
        
        # Use pro model for tellme (complex task)
        return await self.execute_prompt(
            formatted_prompt,
            max_tokens=100000,
            temperature=0.5,
            system_message=QUESTION_ANSWER_SYSTEM_MESSAGE,
            task_type="tellme"
        )
    
    async def close(self) -> None:
        """Clean up Gemini clients."""
        self._client = None
        self._clients.clear()
