"""Custom exceptions for SakaiBot."""

from typing import Optional


class SakaiBotError(Exception):
    """Base exception for SakaiBot."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ConfigurationError(SakaiBotError):
    """Raised when there are configuration-related issues."""
    pass


class TelegramError(SakaiBotError):
    """Raised when there are Telegram API-related issues."""
    pass


class AIProcessorError(SakaiBotError):
    """Raised when there are AI processing-related issues."""
    pass


class CacheError(SakaiBotError):
    """Raised when there are cache-related issues."""
    pass


class ValidationError(SakaiBotError):
    """Raised when validation fails."""
    pass
