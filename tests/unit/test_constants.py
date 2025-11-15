"""Unit tests for constants."""

import unittest

from src.core.constants import (
    APP_NAME,
    APP_VERSION,
    MAX_MESSAGE_LENGTH,
    DEFAULT_TTS_VOICE,
    CONFIRMATION_KEYWORD,
    LOG_FORMAT,
    MONITOR_LOG_FILE
)


class TestConstants(unittest.TestCase):
    """Test constants module."""
    
    def test_app_constants(self):
        """Test application constants."""
        self.assertEqual(APP_NAME, "SakaiBot")
        self.assertEqual(APP_VERSION, "2.0.0")
        self.assertIsInstance(MAX_MESSAGE_LENGTH, int)
        self.assertEqual(MAX_MESSAGE_LENGTH, 4096)
    
    def test_tts_constants(self):
        """Test TTS constants."""
        self.assertIsInstance(DEFAULT_TTS_VOICE, str)
        self.assertEqual(CONFIRMATION_KEYWORD, "confirm")
    
    def test_logging_constants(self):
        """Test logging constants."""
        self.assertIsInstance(LOG_FORMAT, str)
        self.assertIsInstance(MONITOR_LOG_FILE, str)
        self.assertIn("logs", MONITOR_LOG_FILE)


if __name__ == "__main__":
    unittest.main()

