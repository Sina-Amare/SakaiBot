"""Base handler class with common utilities."""

import os
from pathlib import Path
from typing import Tuple, Optional

from ...utils.logging import get_logger


class BaseHandler:
    """Base class for all Telegram event handlers with common utilities."""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize base handler.
        
        Args:
            ffmpeg_path: Optional path to FFmpeg executable
        """
        self._ffmpeg_path = ffmpeg_path
        self._logger = get_logger(self.__class__.__name__)
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for TTS processing.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Simple text normalization without hazm dependency
        # Replace common Persian characters and clean up text
        normalized = text.replace("\u200c", " ")  # Replace zero-width non-joiner with space
        normalized = " ".join(normalized.split())  # Normalize whitespace
        return normalized
    
    async def _setup_ffmpeg_path(self) -> Tuple[bool, str]:
        """
        Setup FFmpeg path for audio processing.
        
        Returns:
            Tuple of (path_modified, original_path)
        """
        import platform
        from pydub import AudioSegment
        
        original_path = os.environ.get("PATH", "")
        path_modified = False
        
        if self._ffmpeg_path and Path(self._ffmpeg_path).is_file():
            ffmpeg_dir = str(Path(self._ffmpeg_path).parent)
            if ffmpeg_dir not in original_path.split(os.pathsep):
                self._logger.info(f"Adding '{ffmpeg_dir}' to PATH for pydub")
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + original_path
                path_modified = True
            else:
                self._logger.info(f"FFmpeg directory '{ffmpeg_dir}' already in PATH")
            
            # Explicitly set ffmpeg path for pydub on Windows
            if platform.system() == "Windows":
                AudioSegment.converter = self._ffmpeg_path
                AudioSegment.ffmpeg = self._ffmpeg_path
                self._logger.info(f"Set pydub converter path to: {self._ffmpeg_path}")
        else:
            self._logger.info("FFmpeg path not configured. pydub will try to find ffmpeg in system PATH")
        
        return path_modified, original_path
    
    async def _restore_ffmpeg_path(self, path_modified: bool, original_path: str) -> None:
        """
        Restore original PATH if it was modified.
        
        Args:
            path_modified: Whether PATH was modified
            original_path: Original PATH value
        """
        if path_modified:
            os.environ["PATH"] = original_path
            self._logger.info("Restored original PATH")

