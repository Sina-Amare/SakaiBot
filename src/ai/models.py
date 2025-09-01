"""Data models for AI processing functionality.

This module defines Pydantic models for request/response data structures
used throughout the AI processing pipeline.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field, validator


class AIProvider(str, Enum):
    """Enumeration of supported AI providers."""
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class TTSProvider(str, Enum):
    """Enumeration of supported TTS providers."""
    EDGE_TTS = "edge_tts"
    GTTS = "gtts"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"


class STTProvider(str, Enum):
    """Enumeration of supported STT providers."""
    GOOGLE = "google"
    ASSEMBLYAI = "assemblyai"
    OPENAI = "openai"
    AZURE = "azure"


class MessageData(BaseModel):
    """Model for chat message data used in analysis."""
    
    sender: str = Field(..., description="Message sender name or ID")
    text: Optional[str] = Field(None, description="Message text content")
    timestamp: Union[datetime, int, float] = Field(..., description="Message timestamp")
    message_id: Optional[int] = Field(None, description="Unique message identifier")
    chat_id: Optional[int] = Field(None, description="Chat identifier")
    reply_to: Optional[int] = Field(None, description="ID of message this replies to")
    media_type: Optional[str] = Field(None, description="Type of media if present")
    
    @validator("text")
    def validate_text(cls, v: Optional[str]) -> Optional[str]:
        """Ensure text is not empty string."""
        if v is not None and not v.strip():
            return None
        return v


class AIRequest(BaseModel):
    """Base model for AI API requests."""
    
    model_config = {'protected_namespaces': ()}
    
    prompt: str = Field(..., min_length=1, description="The prompt text")
    model_name: str = Field(..., description="Model name to use")
    max_tokens: int = Field(default=1500, ge=1, le=8192, description="Maximum tokens")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    system_message: Optional[str] = Field(None, description="System message")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    
    @validator("prompt")
    def validate_prompt(cls, v: str) -> str:
        """Ensure prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()


class TranslationRequest(AIRequest):
    """Model for translation requests."""
    
    text_to_translate: str = Field(..., min_length=1, description="Text to translate")
    target_language: str = Field(..., description="Target language")
    source_language: str = Field(default="auto", description="Source language (auto-detect if 'auto')")
    include_phonetics: bool = Field(default=True, description="Include phonetic pronunciation")
    
    @validator("text_to_translate")
    def validate_translation_text(cls, v: str) -> str:
        """Ensure translation text is not empty."""
        if not v.strip():
            raise ValueError("Text to translate cannot be empty")
        return v.strip()


class AnalysisRequest(BaseModel):
    """Model for conversation analysis requests."""
    
    model_config = {'protected_namespaces': ()}
    
    messages: List[MessageData] = Field(..., min_items=1, description="Messages to analyze")
    api_key: str = Field(..., description="API key")
    model_name: str = Field(..., description="Model name")
    analysis_type: str = Field(default="detailed", description="Type of analysis")
    language: str = Field(default="fa", description="Analysis output language")
    
    @validator("messages")
    def validate_messages(cls, v: List[MessageData]) -> List[MessageData]:
        """Ensure there are messages with text content."""
        text_messages = [msg for msg in v if msg.text and msg.text.strip()]
        if not text_messages:
            raise ValueError("At least one message with text content is required")
        return v


class QuestionAnswerRequest(BaseModel):
    """Model for question answering from chat history."""
    
    model_config = {'protected_namespaces': ()}
    
    question: str = Field(..., min_length=1, description="Question to answer")
    messages: List[MessageData] = Field(..., min_items=1, description="Chat history")
    api_key: str = Field(..., description="API key")
    model_name: str = Field(..., description="Model name")
    response_language: str = Field(default="fa", description="Response language")
    
    @validator("question")
    def validate_question(cls, v: str) -> str:
        """Ensure question is not empty."""
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class STTRequest(BaseModel):
    """Model for Speech-to-Text requests."""
    
    audio_path: Path = Field(..., description="Path to audio file")
    language: str = Field(default="fa-IR", description="Recognition language")
    provider: STTProvider = Field(default=STTProvider.GOOGLE, description="STT provider")
    
    @validator("audio_path")
    def validate_audio_path(cls, v: Path) -> Path:
        """Ensure audio file exists."""
        if not v.exists():
            raise ValueError(f"Audio file not found: {v}")
        return v


class TTSRequest(BaseModel):
    """Model for Text-to-Speech requests."""
    
    text: str = Field(..., min_length=1, description="Text to synthesize")
    voice: str = Field(default="fa-IR-DilaraNeural", description="Voice to use")
    output_path: Path = Field(..., description="Output file path")
    provider: TTSProvider = Field(default=TTSProvider.EDGE_TTS, description="TTS provider")
    rate: str = Field(default="+0%", description="Speech rate adjustment")
    volume: str = Field(default="+0%", description="Volume adjustment")
    
    @validator("text")
    def validate_text(cls, v: str) -> str:
        """Ensure text is not empty."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()
    
    @validator("rate", "volume")
    def validate_adjustment(cls, v: str) -> str:
        """Validate rate and volume adjustments."""
        import re
        if not re.match(r'^[+-]?\d+%$', v):
            raise ValueError(f"Invalid adjustment format: {v}. Expected format: '+10%' or '-5%'")
        return v


class AIResponse(BaseModel):
    """Model for AI API responses."""
    
    content: str = Field(..., description="Response content")
    model: str = Field(..., description="Model used")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    provider: AIProvider = Field(..., description="AI provider")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TranslationResponse(AIResponse):
    """Model for translation responses."""
    
    source_language: Optional[str] = Field(None, description="Detected source language")
    target_language: str = Field(..., description="Target language")
    phonetics: Optional[str] = Field(None, description="Phonetic pronunciation")


class AnalysisResponse(AIResponse):
    """Model for conversation analysis responses."""
    
    summary: str = Field(..., description="Executive summary")
    topics: List[str] = Field(default_factory=list, description="Key topics discussed")
    sentiment: str = Field(..., description="Overall sentiment")
    decisions: List[str] = Field(default_factory=list, description="Decisions made")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Chat statistics")


class AudioProcessingResult(BaseModel):
    """Model for audio processing results."""
    
    success: bool = Field(..., description="Whether processing succeeded")
    output_path: Optional[Path] = Field(None, description="Path to output file")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class STTResponse(AudioProcessingResult):
    """Model for Speech-to-Text responses."""
    
    transcription: Optional[str] = Field(None, description="Transcribed text")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    language: Optional[str] = Field(None, description="Detected language")
    provider: STTProvider = Field(..., description="STT provider used")


class TTSResponse(AudioProcessingResult):
    """Model for Text-to-Speech responses."""
    
    voice_used: str = Field(..., description="Voice that was used")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    file_size: Optional[int] = Field(None, description="Output file size in bytes")
    provider: TTSProvider = Field(..., description="TTS provider used")


class RetryConfig(BaseModel):
    """Configuration for retry logic."""
    
    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts")
    base_delay: float = Field(default=1.0, ge=0.1, description="Base delay between retries")
    max_delay: float = Field(default=60.0, ge=1.0, description="Maximum delay between retries")
    exponential_backoff: bool = Field(default=True, description="Use exponential backoff")
    jitter: bool = Field(default=True, description="Add random jitter to delays")
    
    @validator("max_delay")
    def validate_max_delay(cls, v: float, values: Dict[str, Any]) -> float:
        """Ensure max_delay is greater than base_delay."""
        base_delay = values.get("base_delay", 1.0)
        if v <= base_delay:
            raise ValueError("max_delay must be greater than base_delay")
        return v
