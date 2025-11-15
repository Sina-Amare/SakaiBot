"""Unit tests for Telegram utilities."""

import unittest
from unittest.mock import Mock

from src.telegram.utils import TelegramUtils


class TestTelegramUtils(unittest.TestCase):
    """Test TelegramUtils class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utils = TelegramUtils()
    
    def test_initialization(self):
        """Test TelegramUtils initialization."""
        self.assertIsNotNone(self.utils)


if __name__ == "__main__":
    unittest.main()

