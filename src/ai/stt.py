"""Speech-to-Text (STT) functionality.

This module provides speech recognition capabilities using various providers
with proper error handling and audio format support.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional, Union, Dict, Any

import speech_recognition as sr
from pydub import AudioSegment

from src.core.config import get_settings
from src.core.constants import (
    AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, SUPPORTED_AUDIO_FORMATS,
    MAX_AUDIO_FILE_SIZE
)
from src.core.exceptions import (
    STTError, FFmpegError, ValidationError, FileSystemError
)
from .models import STTRequest, STTResponse, STTProvider


logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles audio file processing and format conversion."""
    
    def __init__(self):
        """Initialize audio processor."""
        self.settings = get_settings()
    
    def validate_audio_file(self, file_path: Path) -> None:
        """Validate audio file exists and is supported format.
        
        Args:
            file_path: Path to audio file
            
        Raises:
            ValidationError: If file is invalid
            FileSystemError: If file doesn't exist or is inaccessible
        """
        if not file_path.exists():
            raise FileSystemError(
                f"Audio file not found: {file_path}",
                details={"path": str(file_path)}
            )
        
        if not file_path.is_file():
            raise FileSystemError(
                f"Path is not a file: {file_path}",
                details={"path": str(file_path)}
            )
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > MAX_AUDIO_FILE_SIZE:
            raise ValidationError(
                f"Audio file too large: {file_size} bytes",
                field="file_size",
                value=file_size
            )
        
        # Check file extension
        extension = file_path.suffix.lower().lstrip('.')
        if extension not in SUPPORTED_AUDIO_FORMATS:
            raise ValidationError(
                f"Unsupported audio format: {extension}",
                field="format",
                value=extension,
                details={"supported_formats": list(SUPPORTED_AUDIO_FORMATS)}
            )
    
    async def convert_to_wav(
        self,
        input_path: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """Convert audio file to WAV format.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output WAV file (auto-generated if None)
            
        Returns:
            Path: Path to converted WAV file
            
        Raises:
            FFmpegError: If conversion fails
            ValidationError: If input file is invalid
        """
        self.validate_audio_file(input_path)
        
        if output_path is None:
            output_path = input_path.with_suffix('.wav')
        
        # If already WAV format, just copy/validate
        if input_path.suffix.lower() == '.wav':
            if input_path != output_path:
                import shutil
                shutil.copy2(input_path, output_path)
            return output_path
        
        logger.info(f"Converting audio from {input_path} to {output_path}")
        
        try:
            # Setup FFmpeg path if configured
            original_path = os.environ.get("PATH", "")
            ffmpeg_added = False
            
            if self.settings.paths.ffmpeg_executable:
                ffmpeg_dir = self.settings.paths.ffmpeg_executable.parent
                os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{original_path}"
                ffmpeg_added = True
            
            try:
                # Convert using pydub (which uses FFmpeg)
                loop = asyncio.get_event_loop()
                audio = await loop.run_in_executor(
                    None,
                    lambda: AudioSegment.from_file(str(input_path))
                )
                
                # Convert to standard format
                audio = audio.set_frame_rate(AUDIO_SAMPLE_RATE)
                audio = audio.set_channels(AUDIO_CHANNELS)
                
                # Export as WAV
                await loop.run_in_executor(
                    None,
                    lambda: audio.export(str(output_path), format="wav")
                )
                
                logger.info(f"Audio conversion completed: {output_path}")
                return output_path
                
            finally:
                # Restore original PATH
                if ffmpeg_added:
                    os.environ["PATH"] = original_path
        
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}", exc_info=True)
            raise FFmpegError(
                f"Failed to convert audio file: {e}",
                details={
                    "input_path": str(input_path),
                    "output_path": str(output_path)
                }
            ) from e


class STTProcessor:
    """Speech-to-Text processor with multiple provider support."""
    
    def __init__(self):
        """Initialize STT processor."""
        self.settings = get_settings()
        self.audio_processor = AudioProcessor()
    
    async def transcribe_audio(self, request: STTRequest) -> STTResponse:
        """Transcribe audio file to text.
        
        Args:
            request: STT request parameters
            
        Returns:
            STTResponse: Transcription result with metadata
            
        Raises:
            STTError: If transcription fails
        """
        start_time = time.time()
        
        try:
            logger.info(
                f"Starting STT transcription for {request.audio_path} "
                f"using provider {request.provider.value}"
            )
            
            # Validate and convert audio if needed
            wav_path = await self._prepare_audio(request.audio_path)
            
            # Perform transcription based on provider
            if request.provider == STTProvider.GOOGLE:
                result = await self._transcribe_google(wav_path, request.language)
            elif request.provider == STTProvider.ASSEMBLYAI:
                result = await self._transcribe_assemblyai(wav_path, request.language)
            elif request.provider == STTProvider.OPENAI:
                result = await self._transcribe_openai(wav_path, request.language)
            else:
                raise STTError(
                    f"Unsupported STT provider: {request.provider}",
                    details={"provider": request.provider.value}
                )
            
            processing_time = time.time() - start_time
            
            # Clean up temporary WAV file if it was created
            if wav_path != request.audio_path and wav_path.exists():
                try:
                    wav_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {wav_path}: {e}")
            
            logger.info(
                f"STT transcription completed in {processing_time:.2f}s: "
                f"'{result.transcription[:100] if result.transcription else 'None'}...'"
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"STT transcription failed after {processing_time:.2f}s: {e}",
                exc_info=True
            )
            
            if isinstance(e, (STTError, ValidationError, FileSystemError)):
                raise
            
            raise STTError(
                f"Transcription failed: {e}",
                details={"processing_time": processing_time}
            ) from e
    
    async def _prepare_audio(self, audio_path: Path) -> Path:
        """Prepare audio file for transcription.
        
        Args:
            audio_path: Original audio file path
            
        Returns:
            Path: Path to WAV file ready for transcription
            
        Raises:
            ValidationError: If audio file is invalid
            FFmpegError: If conversion fails
        """
        # Validate the audio file
        self.audio_processor.validate_audio_file(audio_path)
        
        # Convert to WAV if not already
        if audio_path.suffix.lower() != '.wav':
            wav_path = audio_path.with_suffix('.wav')
            return await self.audio_processor.convert_to_wav(audio_path, wav_path)
        
        return audio_path
    
    async def _transcribe_google(
        self,
        wav_path: Path,
        language: str
    ) -> STTResponse:
        """Transcribe using Google Speech Recognition.
        
        Args:
            wav_path: Path to WAV audio file
            language: Recognition language code
            
        Returns:
            STTResponse: Transcription result
            
        Raises:
            STTError: If transcription fails
        """
        recognizer = sr.Recognizer()
        
        try:
            # Load audio file
            with sr.AudioFile(str(wav_path)) as source:
                audio_data = recognizer.record(source)
            
            logger.debug(f"Audio data loaded from {wav_path}, attempting Google STT")
            
            # Perform recognition
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(
                None,
                lambda: recognizer.recognize_google(audio_data, language=language)
            )
            
            return STTResponse(
                success=True,
                transcription=transcription,
                confidence=None,  # Google API doesn't return confidence
                language=language,
                provider=STTProvider.GOOGLE,
                processing_time=0,  # Will be set by caller
                metadata={"audio_file": str(wav_path)}
            )
            
        except sr.WaitTimeoutError as e:
            raise STTError(
                "No speech detected (timeout)",
                details={"provider": "google", "language": language}
            ) from e
        
        except sr.UnknownValueError as e:
            raise STTError(
                "Speech was unintelligible",
                details={"provider": "google", "language": language}
            ) from e
        
        except sr.RequestError as e:
            raise STTError(
                f"Google Speech API request failed: {e}",
                details={"provider": "google", "language": language}
            ) from e
        
        except Exception as e:
            raise STTError(
                f"Google STT transcription failed: {e}",
                details={"provider": "google", "language": language}
            ) from e
    
    async def _transcribe_assemblyai(
        self,
        wav_path: Path,
        language: str
    ) -> STTResponse:
        """Transcribe using AssemblyAI (placeholder).
        
        Args:
            wav_path: Path to WAV audio file
            language: Recognition language code
            
        Returns:
            STTResponse: Transcription result
            
        Raises:
            STTError: If transcription fails
        """
        # This is a placeholder for AssemblyAI implementation
        raise STTError(
            "AssemblyAI STT not yet implemented",
            details={"provider": "assemblyai"}
        )
    
    async def _transcribe_openai(
        self,
        wav_path: Path,
        language: str
    ) -> STTResponse:
        """Transcribe using OpenAI Whisper (placeholder).
        
        Args:
            wav_path: Path to WAV audio file
            language: Recognition language code
            
        Returns:
            STTResponse: Transcription result
            
        Raises:
            STTError: If transcription fails
        """
        # This is a placeholder for OpenAI Whisper implementation
        raise STTError(
            "OpenAI Whisper STT not yet implemented",
            details={"provider": "openai"}
        )


# Legacy compatibility function
async def transcribe_voice_to_text(audio_wav_path: str) -> str:
    """Legacy wrapper for STT functionality.
    
    Args:
        audio_wav_path: Path to WAV audio file
        
    Returns:
        str: Transcribed text or error message
    """
    try:
        processor = STTProcessor()
        
        request = STTRequest(
            audio_path=Path(audio_wav_path),
            language="fa-IR",  # Default to Persian
            provider=STTProvider.GOOGLE
        )
        
        response = await processor.transcribe_audio(request)
        
        if response.success and response.transcription:
            return response.transcription
        else:
            return response.error_message or "STT Error: Transcription failed"
            
    except Exception as e:
        error_msg = f"STT Error: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# Utility functions
def get_supported_languages() -> Dict[str, str]:
    """Get supported STT languages.
    
    Returns:
        Dict[str, str]: Mapping of language codes to names
    """
    return {
        "fa-IR": "Persian (Iran)",
        "en-US": "English (US)",
        "en-GB": "English (UK)",
        "ar-SA": "Arabic (Saudi Arabia)",
        "de-DE": "German (Germany)",
        "es-ES": "Spanish (Spain)",
        "fr-FR": "French (France)",
        "it-IT": "Italian (Italy)",
        "pt-BR": "Portuguese (Brazil)",
        "ru-RU": "Russian (Russia)",
        "zh-CN": "Chinese (Simplified)",
        "ja-JP": "Japanese (Japan)",
        "ko-KR": "Korean (South Korea)",
    }


def estimate_transcription_time(file_size_bytes: int) -> float:
    """Estimate transcription processing time.
    
    Args:
        file_size_bytes: Audio file size in bytes
        
    Returns:
        float: Estimated processing time in seconds
    """
    # Very rough estimate: ~2-5 seconds per MB for Google STT
    size_mb = file_size_bytes / (1024 * 1024)
    return max(2.0, size_mb * 3.5)


def get_optimal_audio_settings() -> Dict[str, Any]:
    """Get optimal audio settings for STT.
    
    Returns:
        Dict[str, Any]: Optimal audio configuration
    """
    return {
        "sample_rate": AUDIO_SAMPLE_RATE,
        "channels": AUDIO_CHANNELS,
        "format": "wav",
        "bit_depth": 16,
        "encoding": "pcm"
    }
