"""Text-to-Speech processing for SakaiBot."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional

import requests
from pydub import AudioSegment

# Import edge-tts for free TTS functionality
import edge_tts

from ..core.constants import DEFAULT_TTS_VOICE
from ..utils.logging import get_logger


class TextToSpeechProcessor:
    """Handles text-to-speech conversion with free providers."""

    HF_MODEL = os.getenv("HF_TTS_MODEL", "saharmor/fastspeech2-fa")
    HF_MAX_CHARS = int(os.getenv("HF_TTS_MAX_CHARS", "200"))
    GOOGLE_MAX_CHARS = 90

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._last_provider = "none"
        self._hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
        self._last_error: Optional[str] = None
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    async def text_to_speech(
        self,
        text_to_speak: str,
        voice: str = "fa-IR-DilaraNeural",
        output_filename: str = "temp_tts_output.mp3",
        rate: str = "+0%",
        volume: str = "+0%",
    ) -> bool:
        """Convert text to speech."""
        if not text_to_speak:
            self._logger.warning("No text provided to speak")
            return False

        self._last_error = None

        # First try with edge-tts (free and reliable for supported languages)
        if await self._generate_with_edge_tts(text_to_speak, voice, rate, volume, output_filename):
            self._last_provider = "edge-tts"
            return True

        # Try local pyttsx3 as a free offline option (may support Persian depending on system voices)
        if await self._generate_with_pyttsx3(text_to_speak, output_filename):
            self._last_provider = "pyttsx3"
            return True

        # Fallback to existing providers if edge-tts and pyttsx3 fail
        hf_possible = bool(self._hf_token)
        if hf_possible and await self._generate_with_huggingface(text_to_speak, output_filename):
            self._last_provider = "huggingface"
            return True

        if not hf_possible:
            self._logger.info("HuggingFace token not set; skipping HF TTS.")

        if await self._generate_with_google(text_to_speak, output_filename):
            self._last_provider = "google_translate"
            return True

        if not self._last_error:
            self._last_error = "سامانه‌های تبدیل متن به گفتار در دسترس نبودند."
        self._logger.error("All TTS providers failed for the given text.")
        return False

    def _chunk_text(self, text: str, max_chars: int) -> List[str]:
        sanitized = text.replace("\n", " ").strip()
        if len(sanitized) <= max_chars:
            return [sanitized]

        chunks: List[str] = []
        current = ""
        for word in sanitized.split():
            candidate = (current + " " + word).strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = word
        if current:
            chunks.append(current)
        return chunks

    async def _generate_with_edge_tts(self, text: str, voice: str, rate: str, volume: str, output_filename: str) -> bool:
        """Generate speech using edge-tts."""
        self._logger.info("Generating Persian TTS via edge-tts.")
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
            await communicate.save(output_filename)
            return True
        except Exception as e:
            self._logger.error(f"edge-tts generation failed: {e}", exc_info=True)
            self._last_error = f"تولید گفتار با edge-tts با خطا مواجه شد: {str(e)}"
            return False

    async def _generate_with_pyttsx3(self, text: str, output_filename: str) -> bool:
        """Generate speech using pyttsx3 (local TTS engine)."""
        self._logger.info("Generating TTS via pyttsx3 (local).")
        
        try:
            # Import pyttsx3 inside the function to avoid dependency issues if not installed
            import pyttsx3
            
            # Create a temporary WAV file first, then convert to MP3
            temp_wav_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}_pyttsx3.wav"
            
            def _synthesize_with_pyttsx3():
                try:
                    engine = pyttsx3.init()
                    
                    # Set properties for better quality
                    rate = engine.getProperty('rate')
                    engine.setProperty('rate', rate)  # Keep default rate
                    
                    # Get available voices
                    voices = engine.getProperty('voices')
                    
                    # Try to find a suitable voice - may help with Persian if available
                    # On Windows, look for Persian/Microsoft voices if available
                    found_voice = False
                    for voice in voices:
                        if 'persian' in voice.name.lower() or 'farsi' in voice.name.lower():
                            engine.setProperty('voice', voice.id)
                            found_voice = True
                            break
                    
                    # If no Persian voice found, use the default or first available
                    if not found_voice and voices:
                        engine.setProperty('voice', voices[0].id)
                    
                    # Save to WAV file
                    engine.save_to_file(text, str(temp_wav_path))
                    engine.runAndWait()
                except Exception as e:
                    self._logger.error(f"pyttsx3 synthesis error: {e}")
                    return False
                return True
            
            # Run pyttsx3 in a thread since it's synchronous
            success = await asyncio.to_thread(_synthesize_with_pyttsx3)
            
            if not success or not temp_wav_path.exists() or temp_wav_path.stat().st_size == 0:
                self._logger.error("pyttsx3 failed to generate audio")
                self._last_error = "تولید گفتار با pyttsx3 با خطا مواجه شد."
                return False
            
            # Convert WAV to MP3 using pydub
            audio = AudioSegment.from_wav(str(temp_wav_path))
            audio.export(output_filename, format="mp3")
            
            # Clean up temporary WAV file
            temp_wav_path.unlink(missing_ok=True)
            
            # Verify the output file was created and has content
            if Path(output_filename).exists() and Path(output_filename).stat().st_size > 0:
                self._logger.info(f"Successfully generated speech file with pyttsx3: {output_filename}")
                return True
            else:
                self._logger.error("pyttsx3 generated an empty file or file was not created")
                self._last_error = "تولید گفتار با pyttsx3 با خطا مواجه شد. لطفاً متن را بررسی کنید."
                return False
                
        except ImportError:
            self._logger.warning("pyttsx3 not installed, skipping")
            self._last_error = "کتابخانه pyttsx3 نصب نیست. لطفاً با دستور 'pip install pyttsx3' نصب کنید."
            return False
        except Exception as e:
            self._logger.error(f"pyttsx3 generation failed: {e}", exc_info=True)
            self._last_error = f"تولید گفتار با pyttsx3 با خطا مواجه شد: {str(e)}"
            return False

    async def _generate_with_huggingface(self, text: str, output_filename: str) -> bool:
        """Generate speech using Hugging Face Inference API if token provided."""
        if not self._hf_token:
            self._logger.info("HuggingFace token not set; skipping HF TTS.")
            return False

        url = f"https://api-inference.huggingface.co/models/{self.HF_MODEL}"
        headers = {
            "Accept": "audio/wav",
            "Authorization": f"Bearer {self._hf_token}",
        }

        chunks = self._chunk_text(text, self.HF_MAX_CHARS)
        temp_files: List[Path] = []

        params = {"wait_for_model": "true"}

        def _synthesize(chunk: str) -> Optional[bytes]:
            payload = {"inputs": chunk}
            response = requests.post(
                url, headers=headers, json=payload, params=params, timeout=180
            )
            if response.status_code == 200 and response.content:
                content_type = response.headers.get("content-type", "")
                if "audio" in content_type or response.content[:4] == b"RIFF":
                    return response.content

            error_msg = (
                f"HuggingFace request failed ({response.status_code}): "
                f"{response.text[:200] if response.text else 'بدون پاسخ'}"
            )
            self._logger.error(error_msg)
            self._last_error = (
                "API هوگینگ‌فیس پاسخ نداد یا خروجی صوتی برنگرداند. لطفاً کمی صبر کنید "
                "یا از صحت مدل و توکن مطمئن شوید."
            )
            return None

        try:
            for idx, chunk in enumerate(chunks):
                audio_bytes = await asyncio.to_thread(_synthesize, chunk)
                if not audio_bytes:
                    raise RuntimeError("HuggingFace returned no audio data.")
                temp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}_hf_{idx}.wav"
                temp_path.write_bytes(audio_bytes)
                temp_files.append(temp_path)

            if not temp_files:
                raise RuntimeError("HuggingFace did not produce any audio segments.")

            combined = AudioSegment.silent(duration=250)
            for temp_path in temp_files:
                combined += AudioSegment.from_file(temp_path, format="wav")
                combined += AudioSegment.silent(duration=120)

            combined.export(output_filename, format="mp3")
            return True
        except Exception as exc:
            if not self._last_error:
                self._last_error = (
                    "تماس با API هوگینگ‌فیس با خطا روبه‌رو شد. لطفاً توکن را بررسی کنید یا بعداً دوباره امتحان کنید."
                )
            self._logger.error("HuggingFace synthesis failed: %s", exc, exc_info=True)
            return False
        finally:
            for temp_path in temp_files:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    async def _generate_with_google(self, text: str, output_filename: str) -> bool:
        """Generate speech using Google Translate public endpoint."""
        self._logger.info("Generating Persian TTS via Google Translate endpoint.")
        url = "https://translate.googleapis.com/translate_tts"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        chunks = self._chunk_text(text, self.GOOGLE_MAX_CHARS)
        temp_files: List[Path] = []

        error_holder = {"msg": None}

        def _synthesize(chunk: str, idx: int) -> Optional[Path]:
            params = {
                "ie": "UTF-8",
                "client": "tw-ob",
                "tl": "fa",
                "q": chunk,
            }
            response = requests.get(url, params=params, headers=headers, timeout=60)
            if response.status_code != 200 or not response.content:
                msg = (
                    f"Google Translate TTS failed ({response.status_code}). "
                    f"{response.text[:120] if response.text else 'پاسخی دریافت نشد.'}"
                )
                error_holder["msg"] = msg
                self._logger.error(msg)
                return None
            temp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}_google_{idx}.mp3"
            temp_path.write_bytes(response.content)
            return temp_path

        try:
            for idx, chunk in enumerate(chunks):
                temp_path = await asyncio.to_thread(_synthesize, chunk, idx)
                if not temp_path:
                    raise RuntimeError("Google Translate TTS returned no audio data.")
                temp_files.append(temp_path)

            if not temp_files:
                raise RuntimeError("Google Translate TTS did not produce any audio segments.")

            combined = AudioSegment.silent(duration=250)
            for temp_path in temp_files:
                combined += AudioSegment.from_file(temp_path, format="mp3")
                combined += AudioSegment.silent(duration=100)

            combined.export(output_filename, format="mp3")
            return True
        except Exception as exc:
            if error_holder["msg"]:
                if self._last_error:
                    self._last_error = f"{self._last_error} / {error_holder['msg']}"
                else:
                    self._last_error = error_holder["msg"]
            else:
                self._last_error = (
                    "خدمت Google Translate TTS پاسخ نداد. می‌توانید کوتاه‌تر امتحان کنید یا بعداً دوباره تلاش کنید."
                )
            self._logger.error("Google Translate synthesis failed: %s", exc, exc_info=True)
            return False
        finally:
            for temp_path in temp_files:
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    async def generate_speech_file(
        self,
        text: str,
        voice: str = DEFAULT_TTS_VOICE,
        rate: str = "+0%",
        volume: str = "+0%",
    ) -> Optional[str]:
        """Generate a speech file and return the path if successful."""
        temp_path = Path(tempfile.gettempdir()) / f"temp_tts_{uuid.uuid4().hex}.mp3"
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
