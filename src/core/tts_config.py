"""TTS Configuration for SakaiBot."""

import os
from typing import List, Optional

# Ensure .env is loaded before reading environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, rely on system env


def _get_google_api_key() -> Optional[str]:
    """Get Google API key with priority: GEMINI_API_KEY_TTS -> GEMINI_API_KEY -> GOOGLE_API_KEY."""
    # Priority 1: TTS-specific key
    key = os.getenv("GEMINI_API_KEY_TTS")
    if key and len(key) > 10 and "YOUR_GEMINI_API_KEY_HERE" not in key:
        return key
    
    # Priority 2: General Gemini key
    key = os.getenv("GEMINI_API_KEY")
    if key and len(key) > 10 and "YOUR_GEMINI_API_KEY_HERE" not in key:
        return key
    
    # Priority 3: Legacy Google API key name
    key = os.getenv("GOOGLE_API_KEY")
    if key and len(key) > 10 and "YOUR_GEMINI_API_KEY_HERE" not in key:
        return key
    
    return None


# TTS API Configuration
GOOGLE_API_KEY: Optional[str] = _get_google_api_key()

# Retry Configuration
MAX_RETRIES: int = 3
RETRY_DELAYS: List[float] = [1.0, 2.0, 4.0]  # Exponential backoff: 1s, 2s, 4s

# API Settings
API_TIMEOUT: int = 30

# TTS Model Configuration
TTS_MODEL: str = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE: str = "Orus"  # Masculine voice

# Audio Settings
DEFAULT_SAMPLE_RATE: int = 24000
DEFAULT_CHANNELS: int = 1
DEFAULT_SAMPLE_WIDTH: int = 2
