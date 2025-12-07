"""AI processing functionality with multiple LLM provider support."""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import pytz

from .llm_interface import LLMProvider
from .response_metadata import AIResponseMetadata
from .providers import OpenRouterProvider, GeminiProvider
from ..core.config import Config
from ..core.exceptions import AIProcessorError, ConfigurationError
from ..utils.logging import get_logger
from ..utils.security import mask_api_key


class AIProcessor:
    """Handles AI processing operations with Gemini primary and OpenRouter fallback."""
    
    def __init__(self, config: Config) -> None:
        """Initialize AI processor with primary and fallback providers."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._provider: Optional[LLMProvider] = None
        self._primary_provider: Optional[LLMProvider] = None
        self._fallback_provider: Optional[LLMProvider] = None
        self._using_fallback: bool = False
        
        # Initialize providers with fallback support
        self._initialize_provider()
    
    def _initialize_provider(self) -> None:
        """Initialize primary (Gemini) and fallback (OpenRouter) providers."""
        provider_type = self._config.llm_provider.lower()
        
        try:
            if provider_type == "openrouter":
                # OpenRouter as primary, no fallback
                self._provider = OpenRouterProvider(self._config)
                self._primary_provider = self._provider
                self._logger.info("Initialized OpenRouter as primary provider")
            elif provider_type == "gemini":
                # Gemini as primary, OpenRouter as fallback
                self._primary_provider = GeminiProvider(self._config)
                self._provider = self._primary_provider
                self._logger.info("Initialized Google Gemini as primary provider")
                
                # Initialize fallback provider (OpenRouter)
                try:
                    self._fallback_provider = OpenRouterProvider(self._config)
                    if self._fallback_provider.is_configured:
                        self._logger.info(
                            "Initialized OpenRouter as fallback provider"
                        )
                    else:
                        self._fallback_provider = None
                        self._logger.info(
                            "OpenRouter fallback not configured, will use Gemini only"
                        )
                except Exception as e:
                    self._logger.warning(f"Failed to init fallback provider: {e}")
                    self._fallback_provider = None
            else:
                raise AIProcessorError(f"Unknown LLM provider: {provider_type}")
            
            if not self._provider.is_configured:
                api_key_field = (
                    "openrouter_api_key" if provider_type == "openrouter" 
                    else "gemini_api_key"
                )
                api_key = getattr(self._config, api_key_field, None)
                masked_key = mask_api_key(api_key) if api_key else "None"
                self._logger.warning(
                    f"{self._provider.provider_name} is not properly configured "
                    f"(API key: {masked_key}). AI features will be disabled."
                )
        except Exception as e:
            self._logger.error(f"Failed to initialize LLM provider: {e}")
            raise AIProcessorError(
                f"Could not initialize {provider_type} provider: {e}"
            )
    
    def _is_keys_exhausted_error(self, error: Exception) -> bool:
        """Check if error indicates all API keys are exhausted."""
        error_msg = str(error).lower()
        exhausted_indicators = [
            "all api keys exhausted",
            "all keys exhausted",
            "no available api keys",
            "rate limit",
            "quota exceeded",
            "429",
        ]
        return any(indicator in error_msg for indicator in exhausted_indicators)
    
    async def _execute_with_fallback(
        self,
        operation_name: str,
        primary_func,
        fallback_func,
        use_thinking: bool = False,
        **kwargs
    ) -> AIResponseMetadata:
        """
        Execute an operation with fallback support.
        
        Tries primary provider first, falls back to secondary on key exhaustion.
        """
        try:
            # Try primary provider
            result = await primary_func(**kwargs, use_thinking=use_thinking)
            self._using_fallback = False
            return result
        except (AIProcessorError, Exception) as e:
            if not self._is_keys_exhausted_error(e):
                # Not a key exhaustion error, re-raise
                raise
            
            if self._fallback_provider is None:
                self._logger.error(
                    f"{operation_name}: All Gemini keys exhausted, no fallback"
                )
                raise AIProcessorError(
                    "All Gemini API keys exhausted and no fallback configured"
                )
            
            # Switch to fallback provider
            self._logger.warning(
                f"{operation_name}: Gemini keys exhausted, falling back to OpenRouter"
            )
            self._using_fallback = True
            
            # Execute with fallback provider (thinking disabled)
            try:
                # OpenRouter doesn't support native thinking, so disable it
                result = await fallback_func(**kwargs, use_thinking=False)
                
                # Update metadata to reflect fallback
                result.provider_fallback_applied = True
                result.provider_fallback_reason = "All Gemini keys exhausted"
                
                # If thinking was requested but not available
                if use_thinking:
                    result.thinking_requested = True
                    result.thinking_applied = False
                    result.fallback_reason = "OpenRouter fallback (no native thinking)"
                
                return result
            except Exception as fallback_error:
                self._logger.error(
                    f"{operation_name}: Fallback also failed: {fallback_error}"
                )
                raise AIProcessorError(
                    f"Both Gemini and OpenRouter failed: {fallback_error}"
                )
    
    @property
    def is_configured(self) -> bool:
        """Check if AI processor is properly configured."""
        return self._provider is not None and self._provider.is_configured
    
    @property
    def provider_name(self) -> str:
        """Get the current provider name."""
        if self._provider:
            return self._provider.provider_name
        return "None"
    
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        if self._provider:
            return self._provider.model_name
        return "None"
    
    def get_model_for_task(self, task_type: str) -> str:
        """
        Get the model name that will be used for a specific task.
        
        Args:
            task_type: Task type (e.g., "analyze", "prompt", "tellme", "translate")
            
        Returns:
            Model name that will be used for this task
        """
        if not self._provider:
            return "None"
        
        # Check if provider has get_model_for_task method
        if hasattr(self._provider, 'get_model_for_task'):
            return self._provider.get_model_for_task(task_type)
        
        # Fallback to default model_name
        return self._provider.model_name
    
    async def execute_custom_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        task_type: str = "prompt",
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> AIResponseMetadata:
        """Execute a custom prompt with automatic Gemini→OpenRouter fallback.
        
        Returns AIResponseMetadata with response text and execution status.
        """
        if not self.is_configured:
            raise AIProcessorError(
                f"AI processor not configured. Provider: {self._config.llm_provider}"
            )
        
        self._logger.info(
            f"Executing {task_type} prompt with {self.provider_name} "
            f"(thinking={use_thinking}, web_search={use_web_search})"
        )
        
        # If no fallback provider, use primary directly
        if self._fallback_provider is None:
            return await self._provider.execute_prompt(
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                task_type=task_type,
                use_thinking=use_thinking,
                use_web_search=use_web_search
            )
        
        # Use fallback mechanism
        return await self._execute_with_fallback(
            operation_name="execute_custom_prompt",
            primary_func=self._primary_provider.execute_prompt,
            fallback_func=self._fallback_provider.execute_prompt,
            use_thinking=use_thinking,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            task_type=task_type,
            use_web_search=use_web_search
        )
    
    async def translate_text_with_phonetics(
        self,
        text_to_translate: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """Translate text with Persian phonetic pronunciation."""
        if not self.is_configured:
            raise AIProcessorError(
                f"AI processor not configured. Provider: {self._config.llm_provider}"
            )
        
        self._logger.info(
            f"Translating text with {self.provider_name} to {target_language}"
        )
        
        return await self._provider.translate_text(
            text=text_to_translate,
            target_language=target_language,
            source_language=source_language
        )
    
    async def analyze_messages(
        self,
        messages: List[Dict[str, Any]],
        participant_mapping: Optional[Dict[int, str]] = None,
        max_messages: int = 10000,
        analysis_mode: str = "general",
        output_language: str = "english",
        use_thinking: bool = False
    ) -> str:
        """Analyze a collection of messages."""
        if not self.is_configured:
            raise AIProcessorError(
                f"AI processor not configured. Provider: {self._config.llm_provider}"
            )
        
        if not messages:
            raise AIProcessorError("No messages provided for analysis")
        
        self._logger.info(
            f"Analyzing {len(messages)} messages with {self.provider_name}, output={output_language}"
        )
        
        # Prepare messages for analysis
        processed_messages = []
        for msg in messages[:max_messages]:
            processed_msg = {
                'timestamp': msg.get('date'),
                'sender_name': participant_mapping.get(
                    msg.get('from_id'), 
                    f"User_{msg.get('from_id', 'Unknown')}"
                ) if participant_mapping else f"User_{msg.get('from_id', 'Unknown')}",
                'text': msg.get('text', '[No text]')
            }
            processed_messages.append(processed_msg)
        
        return await self._provider.analyze_messages(
            messages=processed_messages,
            analysis_type=analysis_mode,
            output_language=output_language,
            use_thinking=use_thinking
        )
    
    async def close(self) -> None:
        """Clean up provider resources."""
        if self._provider:
            await self._provider.close()
            self._provider = None
    
    # Backward compatibility methods
    async def execute_tellme_mode(self, prompt: str) -> str:
        """Execute tellme mode (backward compatibility)."""
        result = await self.execute_custom_prompt(
            user_prompt=prompt,
            max_tokens=32000,  # Full token budget for complete answers
            temperature=0.7,
            task_type="tellme"
        )
        return result.response_text
    
    async def analyze_conversation_messages(
        self, 
        messages_data: List[Dict[str, Any]],
        analysis_mode: str = "general",
        output_language: str = "english",
        use_thinking: bool = False
    ) -> str:
        """Analyze conversation messages (compatibility wrapper)."""
        # Convert to expected format for analyze_messages
        messages = []
        participant_mapping = {}
        
        for idx, msg in enumerate(messages_data):
            # Support both 'sender' (from ai_handler) and 'sender_name' keys
            sender_name = msg.get('sender') or msg.get('sender_name') or f'User_{idx}'
            # Use index as fallback ID since ai_handler doesn't provide from_id
            from_id = msg.get('from_id', idx)
            participant_mapping[from_id] = sender_name
            
            messages.append({
                'date': msg.get('timestamp'),
                'from_id': from_id,
                'text': msg.get('text', '')
            })
        
        return await self.analyze_messages(
            messages=messages,
            participant_mapping=participant_mapping,
            analysis_mode=analysis_mode,
            output_language=output_language,
            use_thinking=use_thinking
        )
    
    async def answer_question_from_chat_history(
        self,
        messages_data: List[Dict[str, Any]],
        user_question: str,
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> "AIResponseMetadata":
        """Answer a question based on chat history with fallback support.
        
        Returns AIResponseMetadata to preserve thinking_summary for display.
        """
        if not self.is_configured:
            raise AIProcessorError(
                f"AI processor not configured. Provider: {self._config.llm_provider}"
            )
        
        # Convert messages_data format to expected format
        formatted_messages = []
        for msg in messages_data:
            formatted_messages.append({
                'sender_name': msg.get('sender', 'Unknown'),
                'text': msg.get('text', ''),
                'timestamp': msg.get('timestamp')
            })
        
        # If no fallback provider, use primary directly
        if self._fallback_provider is None:
            return await self._provider.answer_question_from_history(
                messages=formatted_messages,
                question=user_question,
                use_thinking=use_thinking,
                use_web_search=use_web_search
            )
        
        # Use fallback mechanism
        return await self._execute_with_fallback(
            operation_name="answer_question",
            primary_func=self._primary_provider.answer_question_from_history,
            fallback_func=self._fallback_provider.answer_question_from_history,
            use_thinking=use_thinking,
            messages=formatted_messages,
            question=user_question,
            use_web_search=use_web_search
        )