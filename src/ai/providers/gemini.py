"""Google Gemini LLM provider implementation."""

import os
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from ..llm_interface import LLMProvider
from ...core.exceptions import AIProcessorError
from ...utils.logging import get_logger
from ..persian_prompts import (
    TRANSLATION_SYSTEM_MESSAGE,
    CONVERSATION_ANALYSIS_PROMPT,
    CONVERSATION_ANALYSIS_SYSTEM_MESSAGE,
    QUESTION_ANSWER_PROMPT,
    QUESTION_ANSWER_SYSTEM_MESSAGE,
    VOICE_MESSAGE_SUMMARY_PROMPT,
    ANALYZE_GENERAL_PROMPT,
    ANALYZE_FUN_PROMPT,
    ANALYZE_ROMANCE_PROMPT,
    ANALYZE_FUN_SYSTEM_MESSAGE
)


class GeminiProvider(LLMProvider):
    """Google Gemini provider for LLM operations."""
    
    def __init__(self, config: Any) -> None:
        """Initialize Gemini provider."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client = None
        self._api_key = config.gemini_api_key
        self._model = config.gemini_model
    
    @property
    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
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
    
    def _get_client(self):
        """Get or create Gemini client."""
        if not self.is_configured:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        if self._client is None:
            try:
                import google.generativeai as genai
                
                # Configure the GenAI library with the API key
                genai.configure(api_key=self._api_key)
                
                # Create client with API key
                self._client = genai.GenerativeModel(self._model)
                
                self._logger.info(f"Initialized Gemini client with model: {self._model}")
                
            except ImportError:
                raise AIProcessorError(
                    "Google GenAI library not installed. Run: pip install google-generativeai"
                )
            except Exception as e:
                raise AIProcessorError(f"Failed to initialize Gemini client: {e}")
        
        return self._client
    
    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Execute a prompt using Google Gemini with retry logic."""
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("Gemini API key not configured or invalid")
        
        # Combine system message and user prompt if needed
        if system_message and system_message.strip():
            full_prompt = f"{system_message}\n\n{user_prompt}"
            self._logger.debug(f"Using system message with prompt")
        else:
            full_prompt = user_prompt
        
        # Log the exact prompt being sent for debugging
        self._logger.debug(f"Sending prompt to Gemini: '{full_prompt[:100]}...'")
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                client = self._get_client()
                
                self._logger.info(
                    f"Attempt {attempt + 1}: Sending prompt to Gemini '{self._model}'. "
                    f"Prompt length: {len(full_prompt)} chars"
                )
                
                # Configure the generation parameters
                generation_config = {
                    "temperature": temperature,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
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
                    self._logger.error(f"LLM response timed out after 5 minutes for model '{self._model}'")
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
                    self._logger.info(
                        f"Gemini '{self._model}' completed successfully. Response: {len(response_text)} chars"
                    )
                    return response_text
                
            except Exception as e:
                self._logger.error(
                    f"Attempt {attempt + 1} failed for Gemini '{self._model}': {e}",
                    exc_info=True
                )
                
                # If this is not the last attempt, retry
                if attempt < max_retries - 1:
                    self._logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    # All attempts failed
                    raise AIProcessorError(f"Failed after {max_retries} attempts: {e}")
        
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
        
        # Build a clean translation prompt without sarcastic commentary
        if source_language.lower() == "auto":
            prompt = (
                f"Detect the language of the following text and then translate it to {target_language_name}.\n"
                f"Provide the Persian phonetic pronunciation for the translated text.\n\n"
                f"Text to translate:\n\"{text}\"\n\n"
                f"Output format:\n"
                f"Translation: [translated text]\n"
                f"Phonetic: ([Persian phonetic pronunciation])\n\n"
                f"Example:\n"
                f"Translation: Hello world\n"
                f"Phonetic: (هِلو وَرلد)"
            )
        else:
            source_language_name = get_language_name(source_language)
            prompt = (
                f"Translate the following text from {source_language_name} to {target_language_name}.\n"
                f"Provide the Persian phonetic pronunciation for the translated text.\n\n"
                f"Text to translate:\n\"{text}\"\n\n"
                f"Output format:\n"
                f"Translation: [translated text]\n"
                f"Phonetic: ([Persian phonetic pronunciation])\n\n"
                f"Example:\n"
                f"Translation: Hello world\n"
                f"Phonetic: (هِلو وَرلد)"
            )
        
        self._logger.info(
            f"Requesting translation for '{text[:50]}...' to {target_language_name} with phonetics."
        )
        
        # Use lower temperature for translation accuracy
        # No max_tokens limit to allow full translation
        raw_response = await self.execute_prompt(
            prompt,
            temperature=0.2,
            system_message=TRANSLATION_SYSTEM_MESSAGE
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
        analysis_type: str = "summary"
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
            # Default summary
            prompt = f"""Please analyze and summarize the following chat messages.
Provide a comprehensive summary including:
1. Main topics discussed
2. Key participants and their contributions
3. Important decisions or conclusions
4. Overall sentiment

Messages:
{messages_text}"""
            system_message = None
        
        self._logger.info(
            f"Sending conversation ({num_messages} messages) for {analysis_type} analysis"
        )
        
        # Use lower temperature for analysis accuracy
        return await self.execute_prompt(
            prompt, 
            max_tokens=100000, 
            temperature=0.4,
            system_message=system_message
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
        
        # Build Persian question-answering prompt
        prompt = QUESTION_ANSWER_PROMPT.format(
            combined_history_text=combined_history,
            user_question=question
        )
        
        self._logger.info(
            f"Answering question '{question[:50]}...' based on {len(formatted_messages)} messages"
        )
        
        return await self.execute_prompt(
            prompt,
            max_tokens=100000,
            temperature=0.5,
            system_message=QUESTION_ANSWER_SYSTEM_MESSAGE
        )
    
    async def close(self) -> None:
        """Clean up Gemini client."""
        self._client = None
