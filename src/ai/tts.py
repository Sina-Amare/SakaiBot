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


class TextToSpeechProcessor:
    """Handles text-to-speech conversion via Google GenAI TTS (Gemini)."""

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def _resolve_voice(self, requested_voice: Optional[str]) -> str:
        # Pass through requested voice if provided; otherwise default to a known prebuilt voice
        # Note: Google GenAI voices like 'Kore' are language/model dependent.
        if requested_voice and requested_voice.strip():
            return requested_voice.strip()
        return "Kore"

    def _write_wav(self, filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
        import wave
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    async def _synthesize_with_gemini(self, text: str, voice_name: str) -> Optional[bytes]:
        self._logger.info("Generating TTS via Google GenAI (Gemini) TTS.")
        # Try TTS-specific key first, fallback to general Gemini key
        # Also try common typos/variations
        api_key = (
            os.getenv("GEMINI_API_KEY_TTS") or 
            os.getenv("GEMINI_API__KEY_TTS") or  # Handle double underscore typo
            os.getenv("GEMINI_API_KEY")
        )
        
        # Debug logging
        has_tts_key = bool(os.getenv("GEMINI_API_KEY_TTS") or os.getenv("GEMINI_API__KEY_TTS"))
        has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
        self._logger.debug(f"TTS key check: TTS-specific={has_tts_key}, General={has_gemini_key}")
        
        if not api_key:
            self._last_error = "کلید GEMINI_API_KEY_TTS یا GEMINI_API_KEY تنظیم نشده است."
            self._logger.error("No Gemini API key found for TTS. Check .env file.")
            return None

        def _call_genai() -> Optional[bytes]:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash-preview-tts",
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name,
                                )
                            )
                        ),
                    ),
                )
                # Extract inline audio bytes (PCM)
                part = response.candidates[0].content.parts[0]
                inline = getattr(part, "inline_data", None)
                if not inline or not getattr(inline, "data", None):
                    return None
                return inline.data
            except Exception as e:
                self._logger.error(f"GenAI TTS call failed: {e}", exc_info=True)
                return None

        return await asyncio.to_thread(_call_genai)

    async def text_to_speech(
        self,
        text_to_speak: str,
        voice: str = "fa-IR-DilaraNeural",
        output_filename: str = "temp_tts_output.wav",
        rate: str = "+0%",
        volume: str = "+0%",
    ) -> bool:
        """Convert text to speech using Google GenAI TTS (writes WAV)."""
        if not text_to_speak:
            self._logger.warning("No text provided to speak")
            return False

        self._last_error = None

        try:
            voice_name = self._resolve_voice(voice)
            audio_bytes = await self._synthesize_with_gemini(text_to_speak, voice_name)
            if not audio_bytes:
                if not self._last_error:
                    self._last_error = "تولید گفتار با سرویس گوگل انجام نشد."
                return False

            # Write WAV file
            self._write_wav(output_filename, audio_bytes)
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
