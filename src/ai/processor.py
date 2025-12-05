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
    """Handles AI processing operations using configured LLM provider."""
    
    def __init__(self, config: Config) -> None:
        """Initialize AI processor with configured provider."""
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._provider: Optional[LLMProvider] = None
        
        # Initialize the appropriate provider
        self._initialize_provider()
    
    def _initialize_provider(self) -> None:
        """Initialize the LLM provider based on configuration."""
        provider_type = self._config.llm_provider.lower()
        
        try:
            if provider_type == "openrouter":
                self._provider = OpenRouterProvider(self._config)
                self._logger.info("Initialized OpenRouter provider")
            elif provider_type == "gemini":
                self._provider = GeminiProvider(self._config)
                self._logger.info("Initialized Google Gemini provider")
            else:
                raise AIProcessorError(f"Unknown LLM provider: {provider_type}")
            
            if not self._provider.is_configured:
                api_key_field = "openrouter_api_key" if provider_type == "openrouter" else "gemini_api_key"
                api_key = getattr(self._config, api_key_field, None)
                masked_key = mask_api_key(api_key) if api_key else "None"
                self._logger.warning(
                    f"{self._provider.provider_name} is not properly configured "
                    f"(API key: {masked_key}). AI features will be disabled."
                )
        except Exception as e:
            self._logger.error(f"Failed to initialize LLM provider: {e}")
            raise AIProcessorError(f"Could not initialize {provider_type} provider: {e}")
    
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
        """Execute a custom prompt using the configured LLM provider.
        
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
        
        return await self._provider.execute_prompt(
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            task_type=task_type,
            use_thinking=use_thinking,
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
            max_tokens=2000,
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
    ) -> str:
        """Answer a question based on chat history (compatibility wrapper)."""
        if not self.is_configured:
            raise AIProcessorError(
                f"AI processor not configured. Provider: {self._config.llm_provider}"
            )
        
        # Use provider's answer_question_from_history method which handles formatting
        # Convert messages_data format to expected format
        formatted_messages = []
        for msg in messages_data:
            formatted_messages.append({
                'sender_name': msg.get('sender', 'Unknown'),
                'text': msg.get('text', ''),
                'timestamp': msg.get('timestamp')
            })
        
        return await self._provider.answer_question_from_history(
            messages=formatted_messages,
            question=user_question,
            use_thinking=use_thinking,
            use_web_search=use_web_search
        )