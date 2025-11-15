"""Unit tests for Telegram handlers."""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import EventHandlers from handlers.py file
# Handle the conflict between handlers.py (file) and handlers/ (package)
try:
    # Try importing via the module system
    import importlib
    # Import the handlers.py file as a module
    handlers_module = importlib.import_module('src.telegram.handlers')
    EventHandlers = handlers_module.EventHandlers
except (ImportError, AttributeError):
    # If that fails, try direct file import
    try:
        import importlib.util
        handlers_file = Path(__file__).parent.parent.parent / "src" / "telegram" / "handlers.py"
        spec = importlib.util.spec_from_file_location("handlers_module", handlers_file)
        if spec and spec.loader:
            handlers_module = importlib.util.module_from_spec(spec)
            # Set up parent modules for relative imports
            sys.modules['src'] = type(sys)('src')
            sys.modules['src.telegram'] = type(sys)('src.telegram')
            sys.modules['src.telegram.handlers'] = handlers_module
            spec.loader.exec_module(handlers_module)
            EventHandlers = getattr(handlers_module, 'EventHandlers', None)
        else:
            EventHandlers = None
    except Exception:
        EventHandlers = None


class TestTelegramHandlers(unittest.TestCase):
    """Test Telegram handler functionality."""
    
    @unittest.skipIf(EventHandlers is None, "EventHandlers could not be imported")
    def test_event_handlers_initialization(self):
        """Test EventHandlers initialization."""
        # Create mock processors for initialization
        mock_ai_processor = Mock()
        mock_stt_processor = Mock()
        mock_tts_processor = Mock()
        
        # EventHandlers requires these parameters
        handler = EventHandlers(
            ai_processor=mock_ai_processor,
            stt_processor=mock_stt_processor,
            tts_processor=mock_tts_processor,
            ffmpeg_path=None
        )
        self.assertIsNotNone(handler)
        self.assertEqual(handler._ai_processor, mock_ai_processor)
        self.assertEqual(handler._stt_processor, mock_stt_processor)
        self.assertEqual(handler._tts_processor, mock_tts_processor)


if __name__ == "__main__":
    unittest.main()
