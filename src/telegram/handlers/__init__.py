"""Telegram event handlers package."""

# Export specialized handlers
from .base import BaseHandler
from .stt_handler import STTHandler
from .tts_handler import TTSHandler
from .ai_handler import AIHandler
from .categorization_handler import CategorizationHandler

__all__ = [
    'BaseHandler',
    'STTHandler',
    'TTSHandler',
    'AIHandler',
    'CategorizationHandler'
]

# Note: EventHandlers is in src.telegram.handlers (the parent module file, not this package)
# Import it directly from there to avoid circular imports

