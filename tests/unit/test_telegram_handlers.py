"""Unit tests for Telegram handlers."""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.telegram.handlers import EventHandlers


class TestTelegramHandlers(unittest.TestCase):
    """Test Telegram handler functionality."""
    
    def test_event_handlers_initialization(self):
        """Test EventHandlers initialization."""
        # Create mock processors for initialization
        mock_ai_processor = Mock()
        mock_stt_processor = Mock()
        mock_tts_processor = Mock()
        
        handler = EventHandlers(
            ai_processor=mock_ai_processor,
            stt_processor=mock_stt_processor,
            tts_processor=mock_tts_processor
        )
        self.assertIsInstance(handler, EventHandlers)


if __name__ == "__main__":
    unittest.main()
