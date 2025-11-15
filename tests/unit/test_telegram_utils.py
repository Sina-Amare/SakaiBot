"""Unit tests for Telegram utilities."""

import unittest
from unittest.mock import Mock

from src.telegram.utils import TelegramUtils


class TestTelegramUtils(unittest.TestCase):
    """Test TelegramUtils class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.utils = TelegramUtils(self.mock_client)
    
    def test_initialization(self):
        """Test TelegramUtils initialization."""
        self.assertEqual(self.utils.client, self.mock_client)


if __name__ == "__main__":
    unittest.main()

