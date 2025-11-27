"""Telegram event handlers package."""

# Export specialized handlers (these are in this package)
from .base import BaseHandler
from .stt_handler import STTHandler
from .tts_handler import TTSHandler
from .ai_handler import AIHandler
from .categorization_handler import CategorizationHandler
from .image_handler import ImageHandler

__all__ = [
    'BaseHandler',
    'STTHandler',
    'TTSHandler',
    'AIHandler',
    'ImageHandler',
    'CategorizationHandler',
]

# Note: EventHandlers is now in event_handlers.py (sibling file), not in this package
# Import it from the parent telegram module if needed:
# from src.telegram import EventHandlers
