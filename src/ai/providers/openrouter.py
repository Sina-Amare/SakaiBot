"""OpenRouter LLM provider implementation (fallback provider)."""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from openai import AsyncOpenAI
import httpx

from ..llm_interface import LLMProvider
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
        """Initialize OpenRouter provider with model selection support."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client: Optional[AsyncOpenAI] = None
        self._api_key = config.openrouter_api_key
        self._model = config.openrouter_model
        
        # Model configuration - pro for complex tasks, flash for simple
        self._model_pro = getattr(config, 'openrouter_model_pro', 'google/gemini-2.5-pro')
        self._model_flash = getattr(config, 'openrouter_model_flash', 'google/gemini-2.5-flash')
    
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
        task_type: str = "default",
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> str:
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
        
        try:
            client = self._get_client()
            
            # Prompt is already self-contained (system messages merged into prompts)
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
            except httpx.TimeoutException:
                self._logger.error(f"Request timed out after 10 minutes for model '{model}'")
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
                f"OpenRouter model '{model}' processing complete. Response length: {len(response_text)} chars"
            )
            return response_text
        
        except Exception as e:
            self._logger.error(
                f"Error calling OpenRouter API with model '{model}': {e}",
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
            max_tokens=self._calculate_max_tokens("translate"),
            temperature=0.2,
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
        return await self.execute_prompt(
            formatted_prompt, 
            max_tokens=max_tokens, 
            temperature=0.4,
            task_type="analyze",
            use_thinking=use_thinking
        )
    
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
        return await self.execute_prompt(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=0.5,
            task_type="tellme",
            use_thinking=use_thinking,
            use_web_search=use_web_search
        )
    
    async def close(self) -> None:
        """Clean up OpenRouter client."""
        self._client = None
