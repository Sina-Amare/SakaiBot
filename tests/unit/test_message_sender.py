"""Unit tests for message sender."""

import unittest
from unittest.mock import AsyncMock, Mock, patch

from src.utils.message_sender import MessageSender


class TestMessageSender(unittest.IsolatedAsyncioTestCase):
    """Test MessageSender class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = AsyncMock()
        self.sender = MessageSender(self.mock_client)
    
    async def test_send_message_safe_success(self):
        """Test successful message sending."""
        self.mock_client.send_message.return_value = Mock(id=123)
        
        result = await self.sender.send_message_safe(
            chat_id=456,
            text="Test message",
            reply_to=789
        )
        
        self.assertIsNotNone(result)
        self.mock_client.send_message.assert_called_once()
    
    async def test_send_message_safe_retry(self):
        """Test message sending with retry."""
        # First call fails, second succeeds
        self.mock_client.send_message.side_effect = [
            Exception("Network error"),
            Mock(id=123)
        ]
        
        result = await self.sender.send_message_safe(
            chat_id=456,
            text="Test message",
            max_retries=2
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(self.mock_client.send_message.call_count, 2)
    
    async def test_edit_message_safe_success(self):
        """Test successful message editing."""
        mock_message = Mock(id=123)
        self.mock_client.edit_message.return_value = mock_message
        
        result = await self.sender.edit_message_safe(mock_message, "Updated text")
        
        self.assertIsNotNone(result)
        self.mock_client.edit_message.assert_called_once()
    
    async def test_edit_message_safe_failure(self):
        """Test message editing with failure."""
        mock_message = Mock(id=123)
        self.mock_client.edit_message.side_effect = Exception("Edit failed")
        
        # Should not raise, should return None
        result = await self.sender.edit_message_safe(mock_message, "Updated text")
        self.assertIsNone(result)
    
    async def test_send_long_message_single_chunk(self):
        """Test sending short message (single chunk)."""
        self.mock_client.send_message.return_value = Mock(id=123)
        
        text = "Short message"
        messages = await self.sender.send_long_message(
            chat_id=456,
            text=text
        )
        
        self.assertEqual(len(messages), 1)
        self.mock_client.send_message.assert_called_once()
    
    async def test_send_long_message_multiple_chunks(self):
        """Test sending long message (multiple chunks)."""
        self.mock_client.send_message.return_value = Mock(id=123)
        
        # Create a long message
        text = "a" * 5000
        messages = await self.sender.send_long_message(
            chat_id=456,
            text=text
        )
        
        self.assertGreater(len(messages), 1)
        self.assertGreaterEqual(self.mock_client.send_message.call_count, 2)
    
    async def test_send_long_message_with_edit(self):
        """Test sending long message with edit option."""
        mock_message = Mock(id=123)
        self.mock_client.edit_message.return_value = mock_message
        self.mock_client.send_message.return_value = Mock(id=124)
        
        text = "a" * 5000
        messages = await self.sender.send_long_message(
            chat_id=456,
            text=text,
            edit_message=mock_message
        )
        
        self.assertGreater(len(messages), 1)
        self.mock_client.edit_message.assert_called_once()
        self.assertGreaterEqual(self.mock_client.send_message.call_count, 1)


if __name__ == "__main__":
    unittest.main()

