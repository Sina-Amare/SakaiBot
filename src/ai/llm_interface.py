"""Abstract interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .response_metadata import AIResponseMetadata


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def __init__(self, config: Any) -> None:
        """Initialize the LLM provider with configuration."""
        pass
    
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the current model name."""
        pass
    
    @abstractmethod
    async def execute_prompt(
        self,
        user_prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.7,
        task_type: str = "default",
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> AIResponseMetadata:
        """
        Execute a prompt and return the response with metadata.
        
        Args:
            user_prompt: The user's prompt
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation
            task_type: Type of task (for model selection)
            use_thinking: Enable deep thinking/reasoning mode
            use_web_search: Enable web search grounding
            
        Returns:
            AIResponseMetadata with response text and execution status
            
        Raises:
            AIProcessorError: If generation fails
        """
        pass
    
    @abstractmethod
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_language: Target language
            source_language: Source language (auto-detect if "auto")
            
        Returns:
            Translated text
            
        Raises:
            AIProcessorError: If translation fails
        """
        pass
    
    @abstractmethod
    async def analyze_messages(
        self,
        messages: List[Dict[str, Any]],
        analysis_type: str = "summary",
        output_language: str = "english",
        use_thinking: bool = False
    ) -> str:
        """
        Analyze a list of messages.
        
        Args:
            messages: List of message dictionaries
            analysis_type: Type of analysis to perform
            output_language: Output language for analysis
            use_thinking: Enable deep thinking mode
            
        Returns:
            Analysis result
            
        Raises:
            AIProcessorError: If analysis fails
        """
        pass
    
    @abstractmethod
    async def answer_question_from_history(
        self,
        messages: List[Dict[str, Any]],
        question: str,
        use_thinking: bool = False,
        use_web_search: bool = False
    ) -> str:
        """
        Answer a question based on chat history.
        
        Args:
            messages: List of message dictionaries
            question: User's question
            use_thinking: Enable deep thinking mode
            use_web_search: Enable web search grounding
            
        Returns:
            Answer to the question
            
        Raises:
            AIProcessorError: If answering fails
        """
        pass
    
    async def close(self) -> None:
        """Clean up any resources. Override if needed."""
        pass