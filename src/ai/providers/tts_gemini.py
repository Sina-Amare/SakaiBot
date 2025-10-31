"""Gemini TTS Provider for SakaiBot.

Uses the official Google Gemini TTS API pattern from:
https://ai.google.dev/gemini-api/docs/speech-generation
"""

import os
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


def wave_file(filename: str, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    """Set up the wave file to save the output."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


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
            # Initialize client with API key (exact pattern from official docs)
            client = genai.Client(api_key=GOOGLE_API_KEY)
            
            # Generate content with TTS (exact pattern from official docs)
            response = client.models.generate_content(
                model=TTS_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=selected_voice,
                            )
                        )
                    ),
                )
            )

            # Extract audio data (exact pattern from official snippet)
            # response.candidates[0].content.parts[0].inline_data.data
            if not hasattr(response, 'candidates') or not response.candidates:
                raise RuntimeError("No candidates returned from Gemini TTS")
            
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content:
                raise RuntimeError("No content in candidate response")
            
            if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
                raise RuntimeError("No parts in content")
            
            part = candidate.content.parts[0]
            
            if not hasattr(part, 'inline_data') or not part.inline_data:
                raise RuntimeError("No inline_data in part")
            
            if not hasattr(part.inline_data, 'data') or not part.inline_data.data:
                raise RuntimeError("No data in inline_data")
            
            # Get audio data (this is already PCM bytes ready for WAV)
            data = part.inline_data.data

            # Save to WAV file using the exact pattern from official docs
            wave_file(output_file, data)

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
