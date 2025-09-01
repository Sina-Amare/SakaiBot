"""Core AI processor for LLM interactions.

This module handles all large language model interactions through various providers,
with proper error handling, retry logic, and response validation.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Union

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from src.core.config import get_settings
from src.core.constants import (
    DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, API_TIMEOUT_SECONDS,
    API_MAX_RETRIES, API_RETRY_DELAY_BASE, API_RETRY_DELAY_MAX
)
from src.core.exceptions import (
    AIError, APIError, RateLimitError, TokenLimitError, RetryError,
    ConfigurationError, ValidationError
)
from .models import (
    AIRequest, AIResponse, TranslationRequest, TranslationResponse,
    AnalysisRequest, AnalysisResponse, QuestionAnswerRequest, RetryConfig,
    AIProvider, MessageData
)
from .prompts import (
    TranslationPrompts, AnalysisPrompts, QuestionAnswerPrompts,
    get_system_message, calculate_max_tokens
)


logger = logging.getLogger(__name__)


class RetryManager:
    """Manages retry logic with exponential backoff and jitter."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry manager.
        
        Args:
            config: Retry configuration, uses defaults if None
        """
        self.config = config or RetryConfig()
    
    async def execute_with_retry(
        self,
        operation,
        *args,
        **kwargs
    ) -> Any:
        """Execute operation with retry logic.
        
        Args:
            operation: Async function to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Any: Operation result
            
        Raises:
            RetryError: If all retry attempts failed
        """
        last_error = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await operation(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"Operation succeeded on attempt {attempt}")
                return result
                
            except RateLimitError as e:
                last_error = e
                if attempt == self.config.max_attempts:
                    break
                
                # Use retry_after if provided, otherwise use exponential backoff
                delay = e.retry_after if e.retry_after else self._calculate_delay(attempt)
                logger.warning(
                    f"Rate limit hit on attempt {attempt}, retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
                
            except (APIError, ConnectionError) as e:
                last_error = e
                if attempt == self.config.max_attempts:
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"API error on attempt {attempt}, retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Don't retry on unexpected errors
                logger.error(f"Unexpected error on attempt {attempt}: {e}")
                raise
        
        raise RetryError(
            f"Operation failed after {self.config.max_attempts} attempts",
            attempts=self.config.max_attempts,
            max_attempts=self.config.max_attempts,
            last_error=last_error
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            float: Delay in seconds
        """
        if self.config.exponential_backoff:
            delay = min(self.config.base_delay * (2 ** (attempt - 1)), self.config.max_delay)
        else:
            delay = self.config.base_delay
        
        # Add jitter if enabled
        if self.config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
        
        return delay


class AIProcessor:
    """Core AI processor for LLM interactions."""
    
    def __init__(self, settings: Optional[Any] = None):
        """Initialize AI processor.
        
        Args:
            settings: Application settings, loads from config if None
        """
        self.settings = settings or get_settings()
        self.retry_manager = RetryManager()
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> AsyncOpenAI:
        """Get or create OpenAI client.
        
        Returns:
            AsyncOpenAI: Configured client instance
            
        Raises:
            ConfigurationError: If API key is missing or invalid
        """
        if self._client is None:
            api_key = self.settings.openrouter.api_key.get_secret_value()
            
            if not api_key or "YOUR_OPENROUTER_API_KEY_HERE" in api_key or len(api_key) < 10:
                raise ConfigurationError(
                    "OpenRouter API key is not configured or seems invalid",
                    details={"key_length": len(api_key) if api_key else 0}
                )
            
            self._client = AsyncOpenAI(
                base_url=self.settings.openrouter.base_url,
                api_key=api_key,
                timeout=self.settings.openrouter.timeout
            )
        
        return self._client
    
    def _validate_request(self, request: AIRequest) -> None:
        """Validate AI request parameters.
        
        Args:
            request: AI request to validate
            
        Raises:
            ValidationError: If request is invalid
        """
        if not request.model_name:
            raise ValidationError("Model name is required", field="model_name")
        
        if not request.prompt.strip():
            raise ValidationError("Prompt cannot be empty", field="prompt")
        
        if request.max_tokens > 8192:
            raise ValidationError(
                "Max tokens exceeds limit",
                field="max_tokens",
                value=request.max_tokens
            )
    
    async def _make_api_call(self, request: AIRequest) -> ChatCompletion:
        """Make API call to OpenRouter.
        
        Args:
            request: Validated AI request
            
        Returns:
            ChatCompletion: API response
            
        Raises:
            APIError: If API call fails
            RateLimitError: If rate limited
            TokenLimitError: If token limit exceeded
        """
        try:
            messages = []
            
            # Add system message if provided
            if request.system_message and request.system_message.strip():
                messages.append({"role": "system", "content": request.system_message})
            
            # Add user prompt
            messages.append({"role": "user", "content": request.prompt})
            
            logger.debug(
                f"Making API call to model '{request.model_name}' with {len(messages)} messages"
            )
            
            response = await self.client.chat.completions.create(
                model=request.model_name,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                extra_headers={
                    "HTTP-Referer": "http://localhost/sakaibot",
                    "X-Title": "SakaiBot"
                }
            )
            
            return response
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific error types
            if "rate limit" in error_msg or "too many requests" in error_msg:
                retry_after = self._extract_retry_after(str(e))
                raise RateLimitError(
                    f"Rate limit exceeded for model '{request.model_name}'",
                    retry_after=retry_after
                ) from e
            
            if "token" in error_msg and ("limit" in error_msg or "exceed" in error_msg):
                raise TokenLimitError(
                    f"Token limit exceeded for model '{request.model_name}'",
                    tokens_used=request.max_tokens
                ) from e
            
            # Generic API error
            raise APIError(
                f"API call failed for model '{request.model_name}': {e}",
                details={"model": request.model_name, "error_type": type(e).__name__}
            ) from e
    
    def _extract_retry_after(self, error_message: str) -> Optional[int]:
        """Extract retry-after value from error message.
        
        Args:
            error_message: Error message to parse
            
        Returns:
            Optional[int]: Retry-after value in seconds, if found
        """
        import re
        match = re.search(r'retry[_\s-]?after[_\s-]?(\d+)', error_message.lower())
        return int(match.group(1)) if match else None
    
    async def execute_prompt(self, request: AIRequest) -> AIResponse:
        """Execute a custom prompt with the LLM.
        
        Args:
            request: AI request parameters
            
        Returns:
            AIResponse: AI response with metadata
            
        Raises:
            AIError: If processing fails
        """
        start_time = time.time()
        
        try:
            # Validate request
            self._validate_request(request)
            
            logger.info(
                f"Executing prompt with model '{request.model_name}'. "
                f"Prompt preview: '{request.prompt[:100]}...'"
            )
            
            # Execute with retry logic
            response = await self.retry_manager.execute_with_retry(
                self._make_api_call, request
            )
            
            # Extract response content
            content = response.choices[0].message.content.strip()
            tokens_used = getattr(response.usage, 'total_tokens', None) if response.usage else None
            processing_time = time.time() - start_time
            
            logger.info(
                f"Prompt executed successfully in {processing_time:.2f}s. "
                f"Tokens used: {tokens_used}"
            )
            
            return AIResponse(
                content=content,
                model=request.model_name,
                tokens_used=tokens_used,
                processing_time=processing_time,
                provider=AIProvider.OPENROUTER,
                metadata={
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "system_message_used": bool(request.system_message)
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Prompt execution failed after {processing_time:.2f}s: {e}",
                exc_info=True
            )
            
            if isinstance(e, (AIError, ValidationError, ConfigurationError)):
                raise
            
            raise AIError(
                f"Unexpected error during prompt execution: {e}",
                details={"processing_time": processing_time}
            ) from e
    
    async def translate_text(
        self,
        request: TranslationRequest
    ) -> TranslationResponse:
        """Translate text with optional phonetic pronunciation.
        
        Args:
            request: Translation request parameters
            
        Returns:
            TranslationResponse: Translation with metadata
            
        Raises:
            AIError: If translation fails
        """
        try:
            # Generate translation prompt
            prompt = TranslationPrompts.get_translation_prompt(
                text_to_translate=request.text_to_translate,
                target_language=request.target_language,
                source_language=request.source_language,
                include_phonetics=request.include_phonetics
            )
            
            # Calculate appropriate token limit
            max_tokens = calculate_max_tokens(request.text_to_translate, base_tokens=150)
            
            # Create AI request
            ai_request = AIRequest(
                prompt=prompt,
                model_name=request.model_name,
                max_tokens=max_tokens,
                temperature=0.2,  # Lower temperature for more consistent translations
                system_message=TranslationPrompts.SYSTEM_MESSAGE
            )
            
            logger.info(
                f"Translating text from '{request.source_language}' to "
                f"'{request.target_language}': '{request.text_to_translate[:50]}...'"
            )
            
            # Execute translation
            response = await self.execute_prompt(ai_request)
            
            # Parse phonetics if included
            phonetics = None
            if request.include_phonetics and "(" in response.content:
                try:
                    # Extract text in parentheses as phonetics
                    import re
                    phonetic_match = re.search(r'\(([^)]+)\)', response.content)
                    if phonetic_match:
                        phonetics = phonetic_match.group(1)
                except Exception:
                    pass  # Phonetics extraction is optional
            
            logger.info(f"Translation completed successfully")
            
            return TranslationResponse(
                content=response.content,
                model=response.model,
                tokens_used=response.tokens_used,
                processing_time=response.processing_time,
                provider=response.provider,
                metadata=response.metadata,
                source_language=request.source_language,
                target_language=request.target_language,
                phonetics=phonetics
            )
            
        except Exception as e:
            logger.error(f"Translation failed: {e}", exc_info=True)
            
            if isinstance(e, (AIError, ValidationError)):
                raise
            
            raise AIError(f"Translation failed: {e}") from e
    
    async def analyze_conversation(
        self,
        request: AnalysisRequest
    ) -> AnalysisResponse:
        """Analyze conversation messages.
        
        Args:
            request: Analysis request parameters
            
        Returns:
            AnalysisResponse: Analysis results with metadata
            
        Raises:
            AIError: If analysis fails
        """
        try:
            # Format messages for analysis
            formatted_messages = self._format_messages_for_analysis(request.messages)
            
            # Calculate statistics
            stats = self._calculate_message_stats(request.messages)
            
            # Generate analysis prompt
            prompt = AnalysisPrompts.get_analysis_prompt(
                messages_text=formatted_messages,
                num_messages=stats["num_messages"],
                num_senders=stats["num_senders"],
                duration_minutes=stats["duration_minutes"]
            )
            
            # Create AI request
            ai_request = AIRequest(
                prompt=prompt,
                model_name=request.model_name,
                max_tokens=2000,
                temperature=0.4,  # Balanced for analysis
                system_message=AnalysisPrompts.SYSTEM_MESSAGE
            )
            
            logger.info(
                f"Analyzing conversation with {stats['num_messages']} messages "
                f"from {stats['num_senders']} senders"
            )
            
            # Execute analysis
            response = await self.execute_prompt(ai_request)
            
            # Parse structured response (basic extraction)
            summary = self._extract_summary(response.content)
            topics = self._extract_topics(response.content)
            sentiment = self._extract_sentiment(response.content)
            decisions = self._extract_decisions(response.content)
            
            logger.info("Conversation analysis completed successfully")
            
            return AnalysisResponse(
                content=response.content,
                model=response.model,
                tokens_used=response.tokens_used,
                processing_time=response.processing_time,
                provider=response.provider,
                metadata=response.metadata,
                summary=summary,
                topics=topics,
                sentiment=sentiment,
                decisions=decisions,
                statistics=stats
            )
            
        except Exception as e:
            logger.error(f"Conversation analysis failed: {e}", exc_info=True)
            
            if isinstance(e, (AIError, ValidationError)):
                raise
            
            raise AIError(f"Conversation analysis failed: {e}") from e
    
    async def answer_question_from_history(
        self,
        request: QuestionAnswerRequest
    ) -> AIResponse:
        """Answer question based on chat history.
        
        Args:
            request: Question answering request
            
        Returns:
            AIResponse: Answer with metadata
            
        Raises:
            AIError: If question answering fails
        """
        try:
            # Format chat history
            formatted_history = self._format_messages_for_analysis(request.messages)
            
            # Generate QA prompt
            prompt = QuestionAnswerPrompts.get_qa_prompt(
                chat_history=formatted_history,
                user_question=request.question
            )
            
            # Create AI request
            ai_request = AIRequest(
                prompt=prompt,
                model_name=request.model_name,
                max_tokens=1000,
                temperature=0.5,
                system_message=QuestionAnswerPrompts.SYSTEM_MESSAGE
            )
            
            logger.info(
                f"Answering question '{request.question[:50]}...' from "
                f"{len(request.messages)} messages"
            )
            
            # Execute question answering
            response = await self.execute_prompt(ai_request)
            
            logger.info("Question answered successfully")
            
            return response
            
        except Exception as e:
            logger.error(f"Question answering failed: {e}", exc_info=True)
            
            if isinstance(e, (AIError, ValidationError)):
                raise
            
            raise AIError(f"Question answering failed: {e}") from e
    
    def _format_messages_for_analysis(self, messages: list[MessageData]) -> str:
        """Format messages for AI analysis.
        
        Args:
            messages: List of message data
            
        Returns:
            str: Formatted messages text
        """
        formatted = []
        
        for msg in messages:
            if msg.text and msg.text.strip():
                formatted.append(f"{msg.sender}: {msg.text}")
        
        return "\n".join(formatted)
    
    def _calculate_message_stats(self, messages: list[MessageData]) -> Dict[str, Any]:
        """Calculate statistics from messages.
        
        Args:
            messages: List of message data
            
        Returns:
            Dict[str, Any]: Message statistics
        """
        from datetime import datetime
        import pytz
        
        text_messages = [msg for msg in messages if msg.text and msg.text.strip()]
        senders = set(msg.sender for msg in text_messages)
        timestamps = []
        
        for msg in text_messages:
            if isinstance(msg.timestamp, datetime):
                if msg.timestamp.tzinfo is None:
                    ts_aware = pytz.utc.localize(msg.timestamp)
                else:
                    ts_aware = msg.timestamp.astimezone(pytz.utc)
                timestamps.append(ts_aware)
            elif isinstance(msg.timestamp, (int, float)):
                ts_aware = datetime.fromtimestamp(msg.timestamp, tz=pytz.utc)
                timestamps.append(ts_aware)
        
        duration_minutes = 0
        if len(timestamps) >= 2:
            min_time = min(timestamps)
            max_time = max(timestamps)
            duration_minutes = int((max_time - min_time).total_seconds() / 60)
        
        return {
            "num_messages": len(text_messages),
            "num_senders": len(senders),
            "duration_minutes": duration_minutes,
            "total_messages": len(messages),
            "senders": list(senders),
            "time_span": {
                "start": min(timestamps) if timestamps else None,
                "end": max(timestamps) if timestamps else None
            }
        }
    
    def _extract_summary(self, content: str) -> str:
        """Extract executive summary from analysis content.
        
        Args:
            content: Full analysis content
            
        Returns:
            str: Extracted summary or first paragraph
        """
        # Try to extract the executive summary section
        import re
        
        # Look for Persian executive summary
        summary_match = re.search(
            r'خلاصه اجرایی.*?:(.*?)(?=\n\d+\.|$)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if summary_match:
            return summary_match.group(1).strip()
        
        # Fallback: return first paragraph
        paragraphs = content.split('\n\n')
        return paragraphs[0].strip() if paragraphs else content[:200] + "..."
    
    def _extract_topics(self, content: str) -> list[str]:
        """Extract key topics from analysis content.
        
        Args:
            content: Full analysis content
            
        Returns:
            list[str]: Extracted topics
        """
        topics = []
        
        # Try to extract topics section
        import re
        
        topics_match = re.search(
            r'موضوعات اصلی.*?:(.*?)(?=\n\d+\.|$)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if topics_match:
            topics_text = topics_match.group(1)
            # Extract numbered or bulleted items
            topic_items = re.findall(r'[\d\-\*]\s*(.+?)(?=\n|$)', topics_text)
            topics.extend([topic.strip() for topic in topic_items if topic.strip()])
        
        return topics[:10]  # Limit to 10 topics
    
    def _extract_sentiment(self, content: str) -> str:
        """Extract sentiment from analysis content.
        
        Args:
            content: Full analysis content
            
        Returns:
            str: Extracted sentiment or "neutral"
        """
        # Try to extract sentiment section
        import re
        
        sentiment_match = re.search(
            r'لحن.*?و.*?احساسات.*?:(.*?)(?=\n\d+\.|$)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if sentiment_match:
            sentiment_text = sentiment_match.group(1).strip()
            # Extract first sentence
            first_sentence = sentiment_text.split('.')[0].strip()
            return first_sentence if first_sentence else "neutral"
        
        return "neutral"
    
    def _extract_decisions(self, content: str) -> list[str]:
        """Extract decisions and actions from analysis content.
        
        Args:
            content: Full analysis content
            
        Returns:
            list[str]: Extracted decisions
        """
        decisions = []
        
        # Try to extract decisions section
        import re
        
        decisions_match = re.search(
            r'اقدامات.*?تصمیمات.*?:(.*?)(?=\n\d+\.|$)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if decisions_match:
            decisions_text = decisions_match.group(1)
            # Extract bulleted items
            decision_items = re.findall(r'[\-\*]\s*(.+?)(?=\n|$)', decisions_text)
            decisions.extend([decision.strip() for decision in decision_items if decision.strip()])
        
        return decisions[:10]  # Limit to 10 decisions


# Legacy compatibility functions for existing code
async def execute_custom_prompt(
    api_key: str,
    model_name: str,
    user_text_prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    system_message: Optional[str] = None
) -> str:
    """Legacy wrapper for execute_prompt function.
    
    Args:
        api_key: OpenRouter API key
        model_name: Model to use
        user_text_prompt: User prompt
        max_tokens: Maximum tokens for response
        temperature: Sampling temperature
        system_message: Optional system message
        
    Returns:
        str: AI response content or error message
    """
    try:
        # Create temporary settings with provided API key
        from src.core.config import OpenRouterConfig
        from pydantic import SecretStr
        
        openrouter_config = OpenRouterConfig(
            api_key=SecretStr(api_key),
            model_name=model_name
        )
        
        # Use current settings but override OpenRouter config
        current_settings = get_settings()
        current_settings.openrouter = openrouter_config
        
        processor = AIProcessor(current_settings)
        
        request = AIRequest(
            prompt=user_text_prompt,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            system_message=system_message
        )
        
        response = await processor.execute_prompt(request)
        return response.content
        
    except Exception as e:
        error_msg = f"AI Error: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def translate_text_with_phonetics(
    api_key: str,
    model_name: str,
    text_to_translate: str,
    target_language: str,
    source_language: str = "auto"
) -> str:
    """Legacy wrapper for translate_text function.
    
    Args:
        api_key: OpenRouter API key
        model_name: Model to use
        text_to_translate: Text to translate
        target_language: Target language
        source_language: Source language (auto-detect if "auto")
        
    Returns:
        str: Translation with phonetics or error message
    """
    try:
        from src.core.config import OpenRouterConfig
        from pydantic import SecretStr
        
        openrouter_config = OpenRouterConfig(
            api_key=SecretStr(api_key),
            model_name=model_name
        )
        
        current_settings = get_settings()
        current_settings.openrouter = openrouter_config
        
        processor = AIProcessor(current_settings)
        
        request = TranslationRequest(
            prompt="",  # Will be generated
            model_name=model_name,
            text_to_translate=text_to_translate,
            target_language=target_language,
            source_language=source_language,
            include_phonetics=True
        )
        
        response = await processor.translate_text(request)
        return response.content
        
    except Exception as e:
        error_msg = f"AI Error: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def analyze_conversation_messages(
    api_key: str,
    model_name: str,
    messages_data: list
) -> str:
    """Legacy wrapper for analyze_conversation function.
    
    Args:
        api_key: OpenRouter API key
        model_name: Model to use
        messages_data: List of message dictionaries
        
    Returns:
        str: Analysis result or error message
    """
    try:
        from src.core.config import OpenRouterConfig
        from pydantic import SecretStr
        
        openrouter_config = OpenRouterConfig(
            api_key=SecretStr(api_key),
            model_name=model_name
        )
        
        current_settings = get_settings()
        current_settings.openrouter = openrouter_config
        
        processor = AIProcessor(current_settings)
        
        # Convert legacy message format to MessageData
        messages = []
        for msg_data in messages_data:
            try:
                message = MessageData(**msg_data)
                messages.append(message)
            except Exception as e:
                logger.warning(f"Skipping invalid message data: {e}")
                continue
        
        if not messages:
            return "No valid messages found for analysis."
        
        request = AnalysisRequest(
            messages=messages,
            api_key=api_key,
            model_name=model_name
        )
        
        response = await processor.analyze_conversation(request)
        return response.content
        
    except Exception as e:
        error_msg = f"AI Error: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


async def answer_question_from_chat_history(
    api_key: str,
    model_name: str,
    messages_data: list,
    user_question: str
) -> str:
    """Legacy wrapper for answer_question_from_history function.
    
    Args:
        api_key: OpenRouter API key
        model_name: Model to use
        messages_data: List of message dictionaries
        user_question: User's question
        
    Returns:
        str: Answer or error message
    """
    try:
        from src.core.config import OpenRouterConfig
        from pydantic import SecretStr
        
        openrouter_config = OpenRouterConfig(
            api_key=SecretStr(api_key),
            model_name=model_name
        )
        
        current_settings = get_settings()
        current_settings.openrouter = openrouter_config
        
        processor = AIProcessor(current_settings)
        
        # Convert legacy message format to MessageData
        messages = []
        for msg_data in messages_data:
            try:
                message = MessageData(**msg_data)
                messages.append(message)
            except Exception as e:
                logger.warning(f"Skipping invalid message data: {e}")
                continue
        
        if not messages:
            return "No valid messages found to answer question from."
        
        request = QuestionAnswerRequest(
            question=user_question,
            messages=messages,
            api_key=api_key,
            model_name=model_name
        )
        
        response = await processor.answer_question_from_history(request)
        return response.content
        
    except Exception as e:
        error_msg = f"AI Error: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg
