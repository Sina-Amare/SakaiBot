"""AI processing functionality with multiple LLM provider support."""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

from .llm_interface import LLMProvider
from .providers import OpenRouterProvider, GeminiProvider
from ..core.config import Config
from ..core.exceptions import AIProcessorError
from ..utils.logging import get_logger


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
                self._logger.warning(
                    f"{self._provider.provider_name} is not properly configured. "
                    "AI features will be disabled."
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
    
    async def execute_custom_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Execute a custom prompt using the configured LLM provider."""
        if not self.is_configured:
            raise AIProcessorError(
                f"AI processor not configured. Provider: {self._config.llm_provider}"
            )
        
        self._logger.info(
            f"Executing prompt with {self.provider_name} using model {self.model_name}"
        )
        
        return await self._provider.execute_prompt(
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_message=system_message
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
        analysis_mode: str = "general"
    ) -> str:
        """Analyze a collection of messages."""
        if not self.is_configured:
            raise AIProcessorError(
                f"AI processor not configured. Provider: {self._config.llm_provider}"
            )
        
        if not messages:
            raise AIProcessorError("No messages provided for analysis")
        
        self._logger.info(
            f"Analyzing {len(messages)} messages with {self.provider_name}"
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
            analysis_type=analysis_mode
        )
    
    async def close(self) -> None:
        """Clean up provider resources."""
        if self._provider:
            await self._provider.close()
            self._provider = None
    
    # Backward compatibility methods
    async def execute_tellme_mode(self, prompt: str) -> str:
        """Execute tellme mode (backward compatibility)."""
        system_message = (
            "You are a helpful AI assistant. Provide comprehensive, detailed, "
            "and informative responses to questions."
        )
        return await self.execute_custom_prompt(
            user_prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            system_message=system_message
        )
    
    async def analyze_conversation_messages(
        self, 
        messages_data: List[Dict[str, Any]],
        analysis_mode: str = "general"
    ) -> str:
        """Analyze conversation messages (compatibility wrapper)."""
        # Convert to expected format for analyze_messages
        messages = []
        participant_mapping = {}
        
        for msg in messages_data:
            from_id = msg.get('from_id', 0)
            sender_name = msg.get('sender_name', f'User_{from_id}')
            participant_mapping[from_id] = sender_name
            
            messages.append({
                'date': msg.get('timestamp'),
                'from_id': from_id,
                'text': msg.get('text', '')
            })
        
        return await self.analyze_messages(
            messages=messages,
            participant_mapping=participant_mapping,
            analysis_mode=analysis_mode
        )
    
    async def answer_question_from_chat_history(
        self,
        messages_data: List[Dict[str, Any]],
        user_question: str
    ) -> str:
        """Answer a question based on chat history (compatibility wrapper)."""
        # Format the conversation and question
        conversation_text = "Conversation History:\n"
        for msg in messages_data:
            sender = msg.get('sender', 'Unknown')
            text = msg.get('text', '')
            conversation_text += f"{sender}: {text}\n"
        
        full_prompt = (
            f"{conversation_text}\n\n"
            f"Based on the above conversation, please answer this question:\n"
            f"{user_question}"
        )
        
        return await self.execute_tellme_mode(full_prompt)