"""Text-to-Speech processing for SakaiBot."""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

# Ensure .env is loaded before reading environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, rely on Pydantic Settings or system env

from ..core.constants import DEFAULT_TTS_VOICE
from ..utils.logging import get_logger
from .providers.tts_gemini import synthesize_speech as gemini_synthesize_speech


class TextToSpeechProcessor:
    """Handles text-to-speech conversion with multiple provider support."""

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def _resolve_voice(self, requested_voice: Optional[str]) -> str:
        """Resolve voice name to a valid Google GenAI voice.
        
        Valid voices: achernar, achird, algenib, algieba, alnilam, aoede, autonoe, 
        callirrhoe, charon, despina, enceladus, erinome, fenrir, gacrux, iapetus, 
        kore, laomedeia, leda, orus, puck, pulcherrima, rasalgethi, sadachbia, 
        sadaltager, schedar, sulafat, umbriel, vindemiatrix, zephyr, zubenelgenubi
        
        Masculine voices: Orus, Charon, Fenrir, Puck, Gacrux, Alnilam, Schedar, 
        Rasalgethi, Iapetus, Achernar, Zephyr
        """
        if not requested_voice or not requested_voice.strip():
            return "Orus"  # Default masculine voice
        
        voice = requested_voice.strip()
        
        # Map old Microsoft/Edge TTS voice names to Google GenAI voices
        # If it's already a valid Google voice, pass it through
        if voice.lower() in [
            'achernar', 'achird', 'algenib', 'algieba', 'alnilam', 'aoede', 
            'autonoe', 'callirrhoe', 'charon', 'despina', 'enceladus', 'erinome', 
            'fenrir', 'gacrux', 'iapetus', 'kore', 'laomedeia', 'leda', 'orus', 
            'puck', 'pulcherrima', 'rasalgethi', 'sadachbia', 'sadaltager', 
            'schedar', 'sulafat', 'umbriel', 'vindemiatrix', 'zephyr', 'zubenelgenubi'
        ]:
            return voice.lower()
        
        # Old voice names - default to Orus (masculine)
        return "Orus"

    async def _synthesize_with_gemini(self, text: str, voice_name: str, output_file: str) -> bool:
        """Synthesize speech using Gemini TTS provider."""
        self._logger.info("Generating TTS via Google GenAI (Gemini) TTS.")
        
        def _call_gemini() -> bool:
            success, error_msg = gemini_synthesize_speech(text, output_file, voice_name)
            if not success and error_msg:
                self._logger.error(f"Gemini TTS error: {error_msg}")
                self._last_error = error_msg
            return success
        
        return await asyncio.to_thread(_call_gemini)

    async def text_to_speech(
        self,
        text_to_speak: str,
        voice: Optional[str] = None,
        output_filename: str = "temp_tts_output.wav",
        rate: str = "+0%",
        volume: str = "+0%",
    ) -> bool:
        """Convert text to speech using Gemini TTS provider."""
        if not text_to_speak:
            self._logger.warning("No text provided to speak")
            return False

        self._last_error = None

        try:
            voice_name = self._resolve_voice(voice)
            success = await self._synthesize_with_gemini(text_to_speak, voice_name, output_filename)
            
            if not success:
                if not self._last_error:
                    self._last_error = "تولید گفتار با سرویس گوگل انجام نشد."
                return False

            return True
        except Exception as e:
            self._logger.error(f"TTS error: {e}", exc_info=True)
            self._last_error = str(e)
            return False

    async def generate_speech_file(
        self,
        text: str,
        voice: str = DEFAULT_TTS_VOICE,
        rate: str = "+0%",
        volume: str = "+0%",
    ) -> Optional[str]:
        """Generate a speech WAV file and return the path if successful."""
        temp_path = Path(tempfile.gettempdir()) / f"temp_tts_{uuid.uuid4().hex}.wav"
        try:
            success = await self.text_to_speech(
                text_to_speak=text,
                voice=voice,
                output_filename=str(temp_path),
                rate=rate,
                volume=volume,
            )
            if success:
                return str(temp_path)
            temp_path.unlink(missing_ok=True)
            return None
        except Exception as exc:
            self._logger.error("Error generating speech file: %s", exc)
            temp_path.unlink(missing_ok=True)
            return None
