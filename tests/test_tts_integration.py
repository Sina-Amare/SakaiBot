
import asyncio
import unittest
from telethon import TelegramClient
from telethon.sessions import StringSession

from src.core.config import Config

class TestTtsIntegration(unittest.TestCase):

    def setUp(self):
        self.config = Config(
            telegram_api_id=12345,
            telegram_api_hash="1234567890abcdef",
            telegram_phone_number="+1234567890",
            telegram_session_name="test_session",
            llm_provider="gemini",
        )
        self.client = TelegramClient(StringSession(), self.config.telegram_api_id, self.config.telegram_api_hash)

    async def test_tts_command(self):
        """Test the /tts command in an integration test."""
        async with self.client as client:
            # Send a message to a test chat
            await client.send_message('me', '/tts سلام')
            # Wait for the bot to respond
            await asyncio.sleep(5)
            # Get the last message
            messages = await client.get_messages('me', limit=1)
            self.assertTrue(messages[0].voice)

    async def test_tts_reply(self):
        """Test the /tts command as a reply in an integration test."""
        async with self.client as client:
            # Send a message to a test chat
            message_to_reply = await client.send_message('me', 'این یک پیام برای تست است')
            # Reply to the message with the /tts command
            await client.send_message('me', '/tts', reply_to=message_to_reply.id)
            # Wait for the bot to respond
            await asyncio.sleep(5)
            # Get the last message
            messages = await client.get_messages('me', limit=1)
            self.assertTrue(messages[0].voice)

if __name__ == '__main__':
    unittest.main()
