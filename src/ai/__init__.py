"""AI processing package for SakaiBot.

This package provides modular AI functionality including:
- LLM interactions through various providers
- Speech-to-Text (STT) processing
- Text-to-Speech (TTS) synthesis
- Prompt template management
- Data models for AI operations

Usage:
    from src.ai import AIProcessor, STTProcessor, TTSProcessor
    from src.ai.models import AIRequest, TranslationRequest
    from src.ai.prompts import TranslationPrompts, AnalysisPrompts
"""

from .processor import (
    AIProcessor,
    # Legacy compatibility functions
    execute_custom_prompt,
    translate_text_with_phonetics,
    analyze_conversation_messages,
    answer_question_from_chat_history
)
from .stt import (
    STTProcessor,
    AudioProcessor,
    # Legacy compatibility function
    transcribe_voice_to_text,
    get_supported_languages as get_stt_languages,
    get_optimal_audio_settings
)
from .tts import (
    TTSProcessor,
    EdgeTTSProcessor,
    VoiceManager,
    # Legacy compatibility function
    text_to_speech_edge,
    get_optimal_tts_settings,
    split_text_for_tts,
    validate_voice_settings
)
from .models import (
    # Request models
    AIRequest,
    TranslationRequest,
    AnalysisRequest,
    QuestionAnswerRequest,
    STTRequest,
    TTSRequest,
    
    # Response models
    AIResponse,
    TranslationResponse,
    AnalysisResponse,
    STTResponse,
    TTSResponse,
    AudioProcessingResult,
    
    # Data models
    MessageData,
    RetryConfig,
    
    # Enums
    AIProvider,
    STTProvider,
    TTSProvider
)
from .prompts import (
    PromptTemplate,
    TranslationPrompts,
    AnalysisPrompts,
    QuestionAnswerPrompts,
    CommonPrompts,
    SystemMessages,
    get_system_message,
    calculate_max_tokens
)

# Package metadata
__version__ = "2.0.0"
__author__ = "SakaiBot Team"
__description__ = "Modular AI processing package for SakaiBot"

# Main processor instances (lazy initialization)
_ai_processor = None
_stt_processor = None
_tts_processor = None


def get_ai_processor() -> AIProcessor:
    """Get or create AI processor instance.
    
    Returns:
        AIProcessor: Shared AI processor instance
    """
    global _ai_processor
    if _ai_processor is None:
        _ai_processor = AIProcessor()
    return _ai_processor


def get_stt_processor() -> STTProcessor:
    """Get or create STT processor instance.
    
    Returns:
        STTProcessor: Shared STT processor instance
    """
    global _stt_processor
    if _stt_processor is None:
        _stt_processor = STTProcessor()
    return _stt_processor


def get_tts_processor() -> TTSProcessor:
    """Get or create TTS processor instance.
    
    Returns:
        TTSProcessor: Shared TTS processor instance
    """
    global _tts_processor
    if _tts_processor is None:
        _tts_processor = TTSProcessor()
    return _tts_processor


# Convenience functions for common operations
async def quick_prompt(prompt: str, model: Optional[str] = None) -> str:
    """Quick AI prompt execution with default settings.
    
    Args:
        prompt: Text prompt
        model: Model name (uses default if None)
        
    Returns:
        str: AI response
        
    Raises:
        AIError: If prompt execution fails
    """
    from src.core.config import get_settings
    
    settings = get_settings()
    processor = get_ai_processor()
    
    request = AIRequest(
        prompt=prompt,
        model_name=model or settings.openrouter.model_name
    )
    
    response = await processor.execute_prompt(request)
    return response.content


async def quick_translate(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """Quick translation with default settings.
    
    Args:
        text: Text to translate
        target_lang: Target language
        source_lang: Source language (auto-detect if "auto")
        
    Returns:
        str: Translation result
        
    Raises:
        AIError: If translation fails
    """
    from src.core.config import get_settings
    
    settings = get_settings()
    processor = get_ai_processor()
    
    request = TranslationRequest(
        prompt="",  # Will be generated
        model_name=settings.openrouter.model_name,
        text_to_translate=text,
        target_language=target_lang,
        source_language=source_lang
    )
    
    response = await processor.translate_text(request)
    return response.content


async def quick_transcribe(audio_path: Union[str, Path]) -> str:
    """Quick audio transcription with default settings.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        str: Transcribed text
        
    Raises:
        STTError: If transcription fails
    """
    processor = get_stt_processor()
    
    request = STTRequest(
        audio_path=Path(audio_path),
        language="fa-IR"
    )
    
    response = await processor.transcribe_audio(request)
    
    if response.success and response.transcription:
        return response.transcription
    else:
        raise STTError(response.error_message or "Transcription failed")


async def quick_synthesize(text: str, output_path: Union[str, Path], voice: Optional[str] = None) -> bool:
    """Quick speech synthesis with default settings.
    
    Args:
        text: Text to synthesize
        output_path: Output file path
        voice: Voice to use (uses default if None)
        
    Returns:
        bool: True if successful
        
    Raises:
        TTSError: If synthesis fails
    """
    processor = get_tts_processor()
    voice_manager = VoiceManager()
    
    request = TTSRequest(
        text=text,
        voice=voice or voice_manager.get_default_voice("fa"),
        output_path=Path(output_path)
    )
    
    response = await processor.synthesize_speech(request)
    return response.success


# Export all public APIs
__all__ = [
    # Main processors
    "AIProcessor",
    "STTProcessor",
    "TTSProcessor",
    "AudioProcessor",
    "EdgeTTSProcessor",
    "VoiceManager",
    
    # Models
    "AIRequest",
    "TranslationRequest",
    "AnalysisRequest",
    "QuestionAnswerRequest",
    "STTRequest",
    "TTSRequest",
    "AIResponse",
    "TranslationResponse",
    "AnalysisResponse",
    "STTResponse",
    "TTSResponse",
    "MessageData",
    "RetryConfig",
    "AIProvider",
    "STTProvider",
    "TTSProvider",
    
    # Prompts
    "PromptTemplate",
    "TranslationPrompts",
    "AnalysisPrompts",
    "QuestionAnswerPrompts",
    "CommonPrompts",
    "SystemMessages",
    "get_system_message",
    "calculate_max_tokens",
    
    # Factory functions
    "get_ai_processor",
    "get_stt_processor",
    "get_tts_processor",
    
    # Convenience functions
    "quick_prompt",
    "quick_translate",
    "quick_transcribe",
    "quick_synthesize",
    
    # Legacy compatibility
    "execute_custom_prompt",
    "translate_text_with_phonetics",
    "analyze_conversation_messages",
    "answer_question_from_chat_history",
    "transcribe_voice_to_text",
    "text_to_speech_edge",
    
    # Utilities
    "get_stt_languages",
    "get_optimal_audio_settings",
    "get_optimal_tts_settings",
    "split_text_for_tts",
    "validate_voice_settings"
]
