"""Telegram event handlers package."""

# Import EventHandlers from the main handlers module for backward compatibility
# After refactoring, this will import from the new structure
from ..handlers import EventHandlers

__all__ = ['EventHandlers']

