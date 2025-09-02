"""Text-to-Speech processing for SakaiBot."""

import os
from pathlib import Path
from typing import Optional

import edge_tts

from ..core.constants import DEFAULT_TTS_VOICE
from ..core.exceptions import AIProcessorError
from ..utils.logging import get_logger


class TextToSpeechProcessor:
    """Handles text-to-speech conversion using Edge TTS."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
    
    async def text_to_speech(
        self,
        text_to_speak: str,
        voice: str = DEFAULT_TTS_VOICE,
        output_filename: str = "temp_tts_output.mp3",
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> bool:
        """Convert text to speech using Microsoft Edge TTS.
        
        Args:
            text_to_speak: The text to convert to speech
            voice: Voice to use (e.g., "fa-IR-DilaraNeural", "fa-IR-FaridNeural")
            output_filename: Path to save the output MP3 file
            rate: Speech rate adjustment (e.g., "+10%", "-5%")
            volume: Volume adjustment (e.g., "+20%", "-10%")
            
        Returns:
            True if successful, False otherwise
        """
        if not text_to_speak:
            self._logger.warning("No text provided to speak")
            return False
        
        self._logger.info(
            f"Converting text to speech - Voice: {voice}, Rate: {rate}, "
            f"Volume: {volume}, Output: {output_filename}, "
            f"Text: '{text_to_speak[:100]}...'"
        )
        
        try:
            communicate = edge_tts.Communicate(
                text=text_to_speak,
                voice=voice,
                rate=rate,
                volume=volume
            )
            
            await communicate.save(output_filename)
            
            output_path = Path(output_filename)
            if output_path.exists() and output_path.stat().st_size > 0:
                self._logger.info(f"Successfully saved speech to '{output_filename}'")
                return True
            else:
                self._logger.error(
                    f"Output file '{output_filename}' was not created or is empty"
                )
                return False
        
        except Exception as e:
            self._logger.error(
                f"Failed to convert text to speech using edge-tts: {e}",
                exc_info=True
            )
            return False
    
    async def generate_speech_file(
        self,
        text: str,
        voice: str = DEFAULT_TTS_VOICE,
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> Optional[str]:
        """Generate a speech file and return the path if successful."""
        import tempfile
        import time
        
        # Create unique temporary filename
        timestamp = int(time.time())
        temp_filename = f"temp_tts_{timestamp}.mp3"
        
        try:
            success = await self.text_to_speech(
                text_to_speak=text,
                voice=voice,
                output_filename=temp_filename,
                rate=rate,
                volume=volume
            )
            
            if success:
                return temp_filename
            else:
                return None
        
        except Exception as e:
            self._logger.error(f"Error generating speech file: {e}")
            return None
