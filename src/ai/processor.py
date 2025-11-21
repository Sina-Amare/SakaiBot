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
    """
    A high-level facade for handling AI processing operations.

    This class abstracts the underlying LLM provider (e.g., Gemini, OpenRouter)
    and provides a consistent interface for tasks like executing prompts,
    translating text, and analyzing conversations. It is responsible for
    initializing the correct provider based on the application's configuration.

    Attributes:
        _config (Config): The application configuration object.
        _logger: The logger instance for this class.
        _provider (Optional[LLMProvider]): The initialized LLM provider instance.
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes the AIProcessor with the given configuration.

        Args:
            config (Config): The application's configuration settings.
        """
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._provider: Optional[LLMProvider] = None
        
        # Initialize the appropriate provider
        self._initialize_provider()

    def _initialize_provider(self) -> None:
        """
        Initializes the LLM provider based on the configuration.

        Dynamically selects and instantiates the appropriate provider
        (e.g., OpenRouterProvider, GeminiProvider) based on the `llm_provider`
        setting in the config.

        Raises:
            AIProcessorError: If the configured provider is unknown or fails to initialize.
        """
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
        """
        Executes a custom prompt using the configured LLM provider.

        Args:
            user_prompt (str): The prompt text from the user.
            max_tokens (int): The maximum number of tokens for the response.
            temperature (float): The creativity of the response.
            system_message (Optional[str]): An optional system-level instruction.

        Returns:
            str: The response from the LLM provider.

        Raises:
            AIProcessorError: If the AI provider is not configured.
        """
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
        """
        Translates text and includes phonetic pronunciation for certain languages.

        Args:
            text_to_translate (str): The text to be translated.
            target_language (str): The target language code (e.g., 'en', 'fa').
            source_language (str): The source language code ('auto' for detection).

        Returns:
            str: The translated text, possibly with phonetic guidance.

        Raises:
            AIProcessorError: If the AI provider is not configured.
        """
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
        """
        Analyzes a list of messages to provide a summary or specific insights.

        Args:
            messages (List[Dict[str, Any]]): A list of message objects.
            participant_mapping (Optional[Dict[int, str]]): A map of user IDs to names.
            max_messages (int): The maximum number of messages to analyze.
            analysis_mode (str): The mode of analysis (e.g., 'general', 'fun').

        Returns:
            str: The analysis result from the LLM provider.

        Raises:
            AIProcessorError: If the AI provider is not configured or no messages are provided.
        """
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

    # --- Backward Compatibility Methods ---

    async def execute_tellme_mode(self, prompt: str) -> str:
        """
        Executes a prompt in 'tellme' mode for backward compatibility.

        This method uses a predefined system message to elicit detailed and
        informative responses from the AI.

        Args:
            prompt (str): The user's prompt.

        Returns:
            str: The AI's response.
        """
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
        """
        Analyzes conversation messages. (Compatibility Wrapper)

        This method adapts the newer `analyze_messages` interface to the older
        data format used by some handlers.

        Args:
            messages_data (List[Dict[str, Any]]): The list of message data.
            analysis_mode (str): The mode for the analysis.

        Returns:
            str: The analysis result.
        """
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
        """
        Answers a user's question based on a provided chat history. (Compatibility Wrapper)

        Args:
            messages_data (List[Dict[str, Any]]): A list of message data.
            user_question (str): The question to answer.

        Returns:
            str: The AI's answer based on the conversation context.
        """
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