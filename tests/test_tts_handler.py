
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.telegram.handlers import EventHandlers
from src.ai.processor import AIProcessor
from src.ai.stt import SpeechToTextProcessor
from src.ai.tts import TextToSpeechProcessor
from src.core.config import Config

class TestTtsHandler(unittest.TestCase):

    def setUp(self):
        self.config = Config(
            telegram_api_id=12345,
            telegram_api_hash="1234567890abcdef",
            telegram_phone_number="+1234567890",
            telegram_session_name="test_session",
            llm_provider="gemini",
        )
        self.ai_processor = AIProcessor(self.config)
        self.stt_processor = SpeechToTextProcessor()
        self.tts_processor = TextToSpeechProcessor()
        self.event_handlers = EventHandlers(self.ai_processor, self.stt_processor, self.tts_processor)

    @patch.object(EventHandlers, '_process_tts_command', new_callable=AsyncMock)
    def test_handle_tts_command_with_reply(self, mock_process_tts_command):
        """Test that the TTS command handler correctly processes a reply."""
        async def run_test():
            # Arrange
            client = AsyncMock()
            replied_message = MagicMock()
            replied_message.text = "این یک پیام برای تست است"
            message = MagicMock()
            message.is_reply = True
            message.text = "/tts"
            message.get_reply_message = AsyncMock(return_value=replied_message)

            # Act
            await self.event_handlers._handle_tts_command(message, client, 123, "test_user")

            # Assert
            mock_process_tts_command.assert_called_once()
            args, _ = mock_process_tts_command.call_args
            self.assertEqual(args[3], "این یک پیام برای تست است")

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
