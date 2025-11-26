"""OpenRouter LLM provider implementation."""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from openai import AsyncOpenAI
import httpx

from ..llm_interface import LLMProvider
from ...core.constants import OPENROUTER_HEADERS
from ...core.exceptions import AIProcessorError
from ...utils.logging import get_logger
from ..prompts import (
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


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider for LLM operations."""
    
    def __init__(self, config: Any) -> None:
        """Initialize OpenRouter provider."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client: Optional[AsyncOpenAI] = None
        self._api_key = config.openrouter_api_key
        self._model = config.openrouter_model
    
    @property
    def is_configured(self) -> bool:
        """Check if OpenRouter is properly configured."""
        return bool(
            self._api_key
            and "YOUR_OPENROUTER_API_KEY_HERE" not in (self._api_key or "")
            and len(self._api_key or "") > 10
        )
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "OpenRouter"
    
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self._model
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client for OpenRouter."""
        if not self.is_configured:
            raise AIProcessorError("OpenRouter API key not configured or invalid")
        
        if self._client is None:
            # Create client without any proxy configuration
            # This avoids the httpx AsyncClient proxy error
            import httpx
            
            # Create httpx client without proxy support
            http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(600.0, connect=30.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                follow_redirects=True
            )
            
            self._client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self._api_key,
                http_client=http_client,
                max_retries=3
            )
            
            self._logger.info(f"Initialized OpenRouter client with custom httpx configuration")
        
        return self._client
    
    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Execute a prompt using OpenRouter."""
        if not user_prompt:
            raise AIProcessorError("Prompt cannot be empty")
        
        if not self.is_configured:
            raise AIProcessorError("OpenRouter API key not configured or invalid")
        
        try:
            client = self._get_client()
            
            messages = []
            if system_message and system_message.strip():
                self._logger.debug(f"Using system message: '{system_message}'")
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": user_prompt})
            
            self._logger.info(
                f"Sending prompt to OpenRouter model '{self._model}'. "
                f"System message: {'Yes' if system_message else 'No'}. "
                f"Prompt preview: '{user_prompt[:100]}...'"
            )
            
            # Add timeout for large requests
            try:
                completion = await client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    extra_headers=OPENROUTER_HEADERS,
                    timeout=600.0  # 10 minute timeout for large requests
                )
            except httpx.TimeoutException:
                self._logger.error(f"Request timed out after 10 minutes for model '{self._model}'")
                raise AIProcessorError("Request timed out. Try with fewer messages or a different model.")
            except httpx.HTTPStatusError as e:
                self._logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise AIProcessorError(f"API returned error {e.response.status_code}: {e.response.text[:200]}")
            
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
                        self._logger.warning(f"Response blocked by content filter: {choice.finish_reason}")
                        raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")

                if response_text:
                    self._logger.info(f"Got response text: {len(response_text)} chars")
                else:
                    self._logger.warning("Message content is None or empty")
            else:
                self._logger.warning("No choices in completion response")
                # Check if the completion has other attributes that might indicate filtering
                if hasattr(completion, 'usage') and completion.usage is None:
                    # This might indicate a safety block
                    self._logger.warning("Completion usage is None, possibly due to safety filtering")
                    raise AIProcessorError("Content was filtered by AI provider due to safety policies. Try with different text.")
            
            if not response_text:
                self._logger.error(f"Could not extract text from completion. Type: {type(completion)}")
                if completion and hasattr(completion, 'model'):
                    self._logger.error(f"Model used: {completion.model}")
                raise AIProcessorError(
                    "OpenRouter did not return any content for the request. The response may have been filtered or the model is unavailable."
                )
            
            self._logger.info(
                f"OpenRouter model '{self._model}' processing complete. Response length: {len(response_text)} chars"
            )
            return response_text
        
        except Exception as e:
            self._logger.error(
                f"Error calling OpenRouter API with model '{self._model}': {e}",
                exc_info=True
            )
            raise AIProcessorError(f"Could not get response from OpenRouter: {e}")
    
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
        """Clean up OpenRouter client."""
        self._client = None
