"""Gemini TTS Provider for SakaiBot."""

import os
import base64
import time
from typing import Optional, Tuple
import wave

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from ...utils.logging import get_logger
from ...core.tts_config import (
    GOOGLE_API_KEY, 
    MAX_RETRIES, 
    RETRY_DELAYS, 
    TTS_MODEL, 
    DEFAULT_VOICE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_CHANNELS,
    DEFAULT_SAMPLE_WIDTH
)


def _decode_audio_inline(part) -> Optional[bytes]:
    """Decode audio data from inline_data part (handles base64 and raw bytes)."""
    try:
        if getattr(part, "inline_data", None):
            mime = getattr(part.inline_data, "mime_type", None)
            data = getattr(part.inline_data, "data", None)
            if not data:
                return None
            # Prefer WAV if provided; otherwise try base64 decode
            if mime in ("audio/wav", "audio/x-wav"):
                return data
            try:
                return base64.b64decode(data)
            except Exception:
                return data
    except Exception:
        return None
    return None


def synthesize_speech(
    text: str, 
    output_file: str = "output.wav", 
    voice_name: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Synthesize speech using Gemini AI Studio TTS.
    
    Args:
        text: Text to convert to speech
        output_file: Path to save the audio file
        voice_name: Voice name to use (default: Kore)
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    logger = get_logger("GeminiTTS")
    
    if not text:
        return False, "Empty text provided for synthesis"

    if not GOOGLE_API_KEY:
        # Check which keys are actually set (for debugging)
        keys_checked = []
        if os.getenv("GEMINI_API_KEY_TTS"):
            keys_checked.append("GEMINI_API_KEY_TTS (found but invalid/empty)")
        if os.getenv("GEMINI_API_KEY"):
            keys_checked.append("GEMINI_API_KEY (found but invalid/empty)")
        if os.getenv("GOOGLE_API_KEY"):
            keys_checked.append("GOOGLE_API_KEY (found but invalid/empty)")
        
        error_msg = (
            "Google API key not configured for Gemini AI Studio TTS. "
            "Checked (in order): GEMINI_API_KEY_TTS, GEMINI_API_KEY, GOOGLE_API_KEY. "
            f"{'Found keys (but invalid): ' + ', '.join(keys_checked) if keys_checked else 'No keys found in environment.'}"
        )
        logger.error(error_msg)
        return False, error_msg

    if genai is None or types is None:
        return False, "google-genai library not installed. Install with: pip install google-genai"

    selected_voice = voice_name or DEFAULT_VOICE
    
    # Log which key was used (for debugging)
    if os.getenv("GEMINI_API_KEY_TTS") == GOOGLE_API_KEY:
        logger.debug("Using GEMINI_API_KEY_TTS for TTS")
    elif os.getenv("GEMINI_API_KEY") == GOOGLE_API_KEY:
        logger.debug("Using GEMINI_API_KEY for TTS")
    elif os.getenv("GOOGLE_API_KEY") == GOOGLE_API_KEY:
        logger.debug("Using GOOGLE_API_KEY for TTS")

    for attempt in range(MAX_RETRIES):
        try:
            # Initialize client with API key
            client = genai.Client(api_key=GOOGLE_API_KEY)
            
            # Configure generation with speech settings
            cfg = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=selected_voice
                        )
                    )
                ),
            )

            # Generate content with TTS
            response = client.models.generate_content(
                model=TTS_MODEL,
                contents=text,
                config=cfg,
            )

            # Extract audio data from response
            candidates = getattr(response, "candidates", None) or []
            if not candidates:
                raise RuntimeError("No candidates returned from Gemini TTS")

            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None) or []

            audio_part = None
            for p in parts:
                inline = getattr(p, "inline_data", None)
                if inline is not None:
                    audio_part = inline
                    break

            if audio_part is None:
                raise RuntimeError("No inline audio data part in response")

            raw_data = getattr(audio_part, "data", None)
            mime_type = getattr(audio_part, "mime_type", None) or ""
            if raw_data is None:
                raise RuntimeError("Audio inline_data.data is missing")

            # Handle both bytes and base64-encoded strings
            if isinstance(raw_data, (bytes, bytearray)):
                audio_bytes = bytes(raw_data)
            else:
                try:
                    audio_bytes = base64.b64decode(raw_data)
                except Exception:
                    audio_bytes = raw_data

            # Write audio file - if WAV, write directly; otherwise wrap PCM in WAV
            if mime_type.lower() in {"audio/wav", "audio/x-wav", "audio/wave"}:
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)
            else:
                # PCM or other format - wrap in WAV container
                with wave.open(output_file, "wb") as wf:
                    wf.setnchannels(DEFAULT_CHANNELS)
                    wf.setsampwidth(DEFAULT_SAMPLE_WIDTH)
                    wf.setframerate(DEFAULT_SAMPLE_RATE)
                    wf.writeframes(audio_bytes)

            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"Audio saved to {output_file} (Gemini AI Studio TTS)")
                return True, None
            else:
                raise RuntimeError("Written audio file is empty")

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                logger.error(f"Gemini AI Studio TTS error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"Gemini AI Studio TTS failed after {MAX_RETRIES} attempts: {e}")
                return False, str(e)

    return False, "Failed after all retry attempts"
