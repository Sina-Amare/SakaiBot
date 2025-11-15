"""Unit tests for custom exceptions."""

import unittest

from src.core.exceptions import (
    SakaiBotError,
    ConfigurationError,
    TelegramError,
    AIProcessorError,
    CacheError,
    ValidationError
)


class TestExceptions(unittest.TestCase):
    """Test custom exception classes."""
    
    def test_sakaibot_error_basic(self):
        """Test basic SakaiBotError."""
        error = SakaiBotError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertIsNone(error.details)
    
    def test_sakaibot_error_with_details(self):
        """Test SakaiBotError with details."""
        error = SakaiBotError("Test error", details="Additional details")
        self.assertIn("Test error", str(error))
        self.assertIn("Additional details", str(error))
        self.assertEqual(error.details, "Additional details")
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config error")
        self.assertIsInstance(error, SakaiBotError)
        self.assertEqual(error.message, "Config error")
    
    def test_telegram_error(self):
        """Test TelegramError."""
        error = TelegramError("Telegram error")
        self.assertIsInstance(error, SakaiBotError)
        self.assertEqual(error.message, "Telegram error")
    
    def test_ai_processor_error(self):
        """Test AIProcessorError."""
        error = AIProcessorError("AI error")
        self.assertIsInstance(error, SakaiBotError)
        self.assertEqual(error.message, "AI error")
    
    def test_cache_error(self):
        """Test CacheError."""
        error = CacheError("Cache error")
        self.assertIsInstance(error, SakaiBotError)
        self.assertEqual(error.message, "Cache error")
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation error")
        self.assertIsInstance(error, SakaiBotError)
        self.assertEqual(error.message, "Validation error")


if __name__ == "__main__":
    unittest.main()

