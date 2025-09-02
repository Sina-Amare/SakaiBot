"""Speech-to-Text processing for SakaiBot."""

import os
from pathlib import Path
from typing import Optional

import speech_recognition as sr

from ..core.exceptions import AIProcessorError
from ..utils.logging import get_logger


class SpeechToTextProcessor:
    """Handles speech-to-text conversion using Google Web Speech API."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._recognizer = sr.Recognizer()
    
    async def transcribe_voice_to_text(
        self,
        audio_wav_path: str,
        language: str = "fa-IR"
    ) -> str:
        """Transcribe voice audio file to text."""
        audio_path = Path(audio_wav_path)
        
        if not audio_path.exists():
            self._logger.error(f"Audio file not found at {audio_wav_path}")
            raise AIProcessorError("Audio file not found")
        
        try:
            with sr.AudioFile(str(audio_path)) as source:
                audio_data = self._recognizer.record(source)
            
            self._logger.info(f"Audio file '{audio_wav_path}' loaded successfully. Attempting transcription...")
            
            # Use Google Web Speech API for transcription
            text = self._recognizer.recognize_google(audio_data, language=language)
            
            self._logger.info(f"Transcription successful: '{text[:100]}...'")
            return text
        
        except sr.WaitTimeoutError:
            self._logger.error("No speech detected (timeout)")
            raise AIProcessorError("No speech detected or timeout")
        
        except sr.UnknownValueError:
            self._logger.info("Google Web Speech API could not understand audio")
            raise AIProcessorError("Speech was unintelligible")
        
        except sr.RequestError as e:
            self._logger.error(f"Could not request results from Google Web Speech API: {e}")
            raise AIProcessorError(f"API request failed: {e}. Check internet connection")
        
        except Exception as e:
            self._logger.error(f"Unexpected error during transcription: {e}", exc_info=True)
            raise AIProcessorError(f"Transcription failed: {e}")
