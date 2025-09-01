"""Text-to-Speech (TTS) functionality.

This module provides text-to-speech capabilities using various providers
with voice customization and audio quality optimization.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import edge_tts

from src.core.config import get_settings
from src.core.constants import (
    DEFAULT_TTS_VOICE_FA, DEFAULT_TTS_VOICE_EN, TTS_VOICES
)
from src.core.exceptions import (
    TTSError, ValidationError, FileSystemError
)
from .models import TTSRequest, TTSResponse, TTSProvider


logger = logging.getLogger(__name__)


class VoiceManager:
    """Manages TTS voices and voice selection."""
    
    @staticmethod
    def get_available_voices() -> Dict[str, List[str]]:
        """Get available TTS voices by language.
        
        Returns:
            Dict[str, List[str]]: Mapping of language codes to voice lists
        """
        return TTS_VOICES.copy()
    
    @staticmethod
    def get_default_voice(language: str = "fa") -> str:
        """Get default voice for language.
        
        Args:
            language: Language code
            
        Returns:
            str: Default voice name
        """
        voice_mapping = {
            "fa": DEFAULT_TTS_VOICE_FA,
            "en": DEFAULT_TTS_VOICE_EN,
            "ar": "ar-SA-HamedNeural",
            "es": "es-ES-ElviraNeural",
            "fr": "fr-FR-DeniseNeural",
            "de": "de-DE-KatjaNeural",
            "it": "it-IT-ElsaNeural",
            "pt": "pt-BR-FranciscaNeural",
            "ru": "ru-RU-SvetlanaNeural",
            "zh": "zh-CN-XiaoxiaoNeural",
            "ja": "ja-JP-NanamiNeural",
            "ko": "ko-KR-SunHiNeural",
            "hi": "hi-IN-SwaraNeural",
            "tr": "tr-TR-EmelNeural"
        }
        
        return voice_mapping.get(language, DEFAULT_TTS_VOICE_EN)
    
    @staticmethod
    def validate_voice(voice: str, language: Optional[str] = None) -> bool:
        """Validate if voice is available.
        
        Args:
            voice: Voice name to validate
            language: Optional language code to check against
            
        Returns:
            bool: True if voice is valid
        """
        if language:
            available_voices = TTS_VOICES.get(language, [])
            return voice in available_voices
        
        # Check across all languages
        all_voices = [voice for voices in TTS_VOICES.values() for voice in voices]
        return voice in all_voices
    
    @staticmethod
    def get_voice_language(voice: str) -> Optional[str]:
        """Get language code for a voice.
        
        Args:
            voice: Voice name
            
        Returns:
            Optional[str]: Language code or None if not found
        """
        for lang_code, voices in TTS_VOICES.items():
            if voice in voices:
                return lang_code
        return None


class EdgeTTSProcessor:
    """Text-to-Speech processor using Microsoft Edge TTS."""
    
    def __init__(self):
        """Initialize Edge TTS processor."""
        self.voice_manager = VoiceManager()
    
    def validate_request(self, request: TTSRequest) -> None:
        """Validate TTS request.
        
        Args:
            request: TTS request to validate
            
        Raises:
            ValidationError: If request is invalid
        """
        if not request.text.strip():
            raise ValidationError(
                "Text cannot be empty",
                field="text",
                value=request.text
            )
        
        if len(request.text) > 10000:  # Reasonable limit
            raise ValidationError(
                "Text too long for TTS",
                field="text",
                value=len(request.text)
            )
        
        # Validate voice
        if not self.voice_manager.validate_voice(request.voice):
            raise ValidationError(
                f"Invalid voice: {request.voice}",
                field="voice",
                value=request.voice
            )
        
        # Validate output directory
        output_dir = request.output_path.parent
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise FileSystemError(
                    f"Cannot create output directory: {output_dir}",
                    details={"path": str(output_dir)}
                ) from e
    
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech from text using Edge TTS.
        
        Args:
            request: TTS request parameters
            
        Returns:
            TTSResponse: Synthesis result with metadata
            
        Raises:
            TTSError: If synthesis fails
        """
        start_time = time.time()
        
        try:
            # Validate request
            self.validate_request(request)
            
            logger.info(
                f"Synthesizing speech with voice '{request.voice}': "
                f"'{request.text[:100]}...'"
            )
            
            # Create Edge TTS communicate object
            communicate = edge_tts.Communicate(
                text=request.text,
                voice=request.voice,
                rate=request.rate,
                volume=request.volume
            )
            
            # Generate speech and save to file
            await communicate.save(str(request.output_path))
            
            processing_time = time.time() - start_time
            
            # Validate output file
            if not request.output_path.exists() or request.output_path.stat().st_size == 0:
                raise TTSError(
                    f"Output file was not created or is empty: {request.output_path}",
                    details={"output_path": str(request.output_path)}
                )
            
            # Get file metadata
            file_size = request.output_path.stat().st_size
            duration = self._estimate_audio_duration(request.text)
            
            logger.info(
                f"TTS synthesis completed in {processing_time:.2f}s. "
                f"Output: {request.output_path} ({file_size} bytes)"
            )
            
            return TTSResponse(
                success=True,
                output_path=request.output_path,
                processing_time=processing_time,
                voice_used=request.voice,
                duration=duration,
                file_size=file_size,
                provider=TTSProvider.EDGE_TTS,
                metadata={
                    "rate": request.rate,
                    "volume": request.volume,
                    "text_length": len(request.text)
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"TTS synthesis failed after {processing_time:.2f}s: {e}",
                exc_info=True
            )
            
            if isinstance(e, (TTSError, ValidationError, FileSystemError)):
                raise
            
            raise TTSError(
                f"Edge TTS synthesis failed: {e}",
                details={"processing_time": processing_time}
            ) from e
    
    def _estimate_audio_duration(self, text: str) -> float:
        """Estimate audio duration based on text length.
        
        Args:
            text: Text to estimate duration for
            
        Returns:
            float: Estimated duration in seconds
        """
        # Rough estimate: ~200 words per minute for Persian, ~180 for English
        words = len(text.split())
        
        # Detect if text is primarily Persian (contains Persian characters)
        persian_char_count = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
        is_persian = persian_char_count > len(text) * 0.3
        
        wpm = 200 if is_persian else 180
        duration = (words / wpm) * 60  # Convert to seconds
        
        return max(1.0, duration)  # Minimum 1 second


class TTSProcessor:
    """Text-to-Speech processor with multiple provider support."""
    
    def __init__(self):
        """Initialize TTS processor."""
        self.settings = get_settings()
        self.edge_processor = EdgeTTSProcessor()
    
    async def synthesize_speech(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech from text.
        
        Args:
            request: TTS request parameters
            
        Returns:
            TTSResponse: Synthesis result with metadata
            
        Raises:
            TTSError: If synthesis fails
        """
        logger.info(
            f"Starting TTS synthesis using provider {request.provider.value}"
        )
        
        try:
            if request.provider == TTSProvider.EDGE_TTS:
                return await self.edge_processor.synthesize(request)
            elif request.provider == TTSProvider.GTTS:
                return await self._synthesize_gtts(request)
            elif request.provider == TTSProvider.ELEVENLABS:
                return await self._synthesize_elevenlabs(request)
            elif request.provider == TTSProvider.OPENAI:
                return await self._synthesize_openai(request)
            else:
                raise TTSError(
                    f"Unsupported TTS provider: {request.provider}",
                    details={"provider": request.provider.value}
                )
                
        except Exception as e:
            if isinstance(e, TTSError):
                raise
            
            raise TTSError(
                f"TTS synthesis failed: {e}",
                details={"provider": request.provider.value}
            ) from e
    
    async def _synthesize_gtts(self, request: TTSRequest) -> TTSResponse:
        """Synthesize using Google TTS (placeholder).
        
        Args:
            request: TTS request
            
        Returns:
            TTSResponse: Synthesis result
            
        Raises:
            TTSError: If synthesis fails
        """
        # This is a placeholder for gTTS implementation
        raise TTSError(
            "Google TTS not yet implemented",
            details={"provider": "gtts"}
        )
    
    async def _synthesize_elevenlabs(self, request: TTSRequest) -> TTSResponse:
        """Synthesize using ElevenLabs (placeholder).
        
        Args:
            request: TTS request
            
        Returns:
            TTSResponse: Synthesis result
            
        Raises:
            TTSError: If synthesis fails
        """
        # This is a placeholder for ElevenLabs implementation
        raise TTSError(
            "ElevenLabs TTS not yet implemented",
            details={"provider": "elevenlabs"}
        )
    
    async def _synthesize_openai(self, request: TTSRequest) -> TTSResponse:
        """Synthesize using OpenAI TTS (placeholder).
        
        Args:
            request: TTS request
            
        Returns:
            TTSResponse: Synthesis result
            
        Raises:
            TTSError: If synthesis fails
        """
        # This is a placeholder for OpenAI TTS implementation
        raise TTSError(
            "OpenAI TTS not yet implemented",
            details={"provider": "openai"}
        )


# Legacy compatibility function
async def text_to_speech_edge(
    text_to_speak: str,
    voice: str = DEFAULT_TTS_VOICE_FA,
    output_filename: str = "temp_tts_output.mp3",
    rate: str = "+0%",
    volume: str = "+0%"
) -> bool:
    """Legacy wrapper for Edge TTS functionality.
    
    Args:
        text_to_speak: Text to synthesize
        voice: Voice to use
        output_filename: Output file path
        rate: Speech rate adjustment
        volume: Volume adjustment
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        processor = TTSProcessor()
        
        request = TTSRequest(
            text=text_to_speak,
            voice=voice,
            output_path=Path(output_filename),
            provider=TTSProvider.EDGE_TTS,
            rate=rate,
            volume=volume
        )
        
        response = await processor.synthesize_speech(request)
        return response.success
        
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}", exc_info=True)
        return False


# Utility functions
def get_optimal_tts_settings(language: str = "fa") -> Dict[str, Any]:
    """Get optimal TTS settings for language.
    
    Args:
        language: Target language code
        
    Returns:
        Dict[str, Any]: Optimal TTS configuration
    """
    voice_manager = VoiceManager()
    default_voice = voice_manager.get_default_voice(language)
    
    return {
        "voice": default_voice,
        "rate": "+0%",
        "volume": "+0%",
        "format": "mp3",
        "quality": "high"
    }


def estimate_synthesis_time(text_length: int) -> float:
    """Estimate TTS synthesis time.
    
    Args:
        text_length: Length of text to synthesize
        
    Returns:
        float: Estimated processing time in seconds
    """
    # Rough estimate: ~1-2 seconds per 100 characters
    base_time = max(1.0, text_length / 100)
    return min(base_time * 2, 30.0)  # Cap at 30 seconds


def validate_voice_settings(voice: str, rate: str, volume: str) -> None:
    """Validate voice configuration parameters.
    
    Args:
        voice: Voice name
        rate: Rate adjustment string
        volume: Volume adjustment string
        
    Raises:
        ValidationError: If parameters are invalid
    """
    import re
    
    # Validate voice
    voice_manager = VoiceManager()
    if not voice_manager.validate_voice(voice):
        raise ValidationError(
            f"Invalid voice: {voice}",
            field="voice",
            value=voice
        )
    
    # Validate rate and volume format
    adjustment_pattern = r'^[+-]?\d+%$'
    
    if not re.match(adjustment_pattern, rate):
        raise ValidationError(
            f"Invalid rate format: {rate}",
            field="rate",
            value=rate
        )
    
    if not re.match(adjustment_pattern, volume):
        raise ValidationError(
            f"Invalid volume format: {volume}",
            field="volume",
            value=volume
        )
    
    # Validate adjustment ranges
    rate_value = int(rate.rstrip('%'))
    volume_value = int(volume.rstrip('%'))
    
    if not -50 <= rate_value <= 100:
        raise ValidationError(
            f"Rate adjustment out of range: {rate_value}%",
            field="rate",
            value=rate_value
        )
    
    if not -50 <= volume_value <= 100:
        raise ValidationError(
            f"Volume adjustment out of range: {volume_value}%",
            field="volume",
            value=volume_value
        )


async def get_available_edge_voices() -> List[Dict[str, Any]]:
    """Get list of available Edge TTS voices.
    
    Returns:
        List[Dict[str, Any]]: List of voice information dictionaries
    """
    try:
        voices = await edge_tts.list_voices()
        return [
            {
                "name": voice["ShortName"],
                "display_name": voice["FriendlyName"],
                "language": voice["Locale"],
                "gender": voice["Gender"],
                "language_name": voice["LocaleName"]
            }
            for voice in voices
        ]
    except Exception as e:
        logger.error(f"Failed to get Edge TTS voices: {e}")
        return []


def split_text_for_tts(text: str, max_length: int = 1000) -> List[str]:
    """Split long text into chunks suitable for TTS.
    
    Args:
        text: Text to split
        max_length: Maximum length per chunk
        
    Returns:
        List[str]: List of text chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences first
    import re
    sentences = re.split(r'[.!?]+', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # If adding this sentence would exceed max_length, start new chunk
        if len(current_chunk) + len(sentence) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                # Single sentence is too long, split by words
                word_chunks = _split_by_words(sentence, max_length)
                chunks.extend(word_chunks)
        else:
            current_chunk = f"{current_chunk} {sentence}".strip()
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def _split_by_words(text: str, max_length: int) -> List[str]:
    """Split text by words when sentences are too long.
    
    Args:
        text: Text to split
        max_length: Maximum length per chunk
        
    Returns:
        List[str]: List of word-based chunks
    """
    words = text.split()
    chunks = []
    current_chunk = ""
    
    for word in words:
        if len(current_chunk) + len(word) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = word
            else:
                # Single word is too long, just add it
                chunks.append(word)
        else:
            current_chunk = f"{current_chunk} {word}".strip()
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
