"""Unit tests for error handling utilities."""

import unittest
from unittest.mock import Mock, patch

from src.core.exceptions import (
    ConfigurationError,
    TelegramError,
    AIProcessorError,
    ValidationError
)
from src.utils.error_handler import ErrorHandler, handle_errors, safe_execute


class TestErrorHandler(unittest.TestCase):
    """Test ErrorHandler class."""
    
    def test_get_user_message_configuration_error(self):
        """Test user message for ConfigurationError."""
        error = ConfigurationError("Invalid config")
        message = ErrorHandler.get_user_message(error)
        self.assertIn("پیکربندی", message)
        self.assertIn("⚠️", message)
    
    def test_get_user_message_telegram_error(self):
        """Test user message for TelegramError."""
        error = TelegramError("Connection failed")
        message = ErrorHandler.get_user_message(error)
        self.assertIn("تلگرام", message)
    
    def test_get_user_message_ai_error(self):
        """Test user message for AIProcessorError."""
        error = AIProcessorError("API error")
        message = ErrorHandler.get_user_message(error)
        self.assertIn("هوش مصنوعی", message)
    
    def test_get_user_message_generic_error(self):
        """Test user message for generic Exception."""
        error = Exception("Something went wrong")
        message = ErrorHandler.get_user_message(error)
        self.assertIn("⚠️", message)
    
    def test_should_retry_configuration_error(self):
        """Test that ConfigurationError should not be retried."""
        error = ConfigurationError("Invalid config")
        self.assertFalse(ErrorHandler.should_retry(error, attempt=1, max_retries=3))
    
    def test_should_retry_telegram_error(self):
        """Test that TelegramError should be retried."""
        error = TelegramError("Connection failed")
        self.assertTrue(ErrorHandler.should_retry(error, attempt=1, max_retries=3))
    
    def test_should_retry_timeout_error(self):
        """Test that timeout errors should be retried."""
        error = Exception("Request timeout")
        self.assertTrue(ErrorHandler.should_retry(error, attempt=1, max_retries=3))
    
    def test_should_retry_max_attempts(self):
        """Test that retry is false when max attempts reached."""
        error = TelegramError("Connection failed")
        self.assertFalse(ErrorHandler.should_retry(error, attempt=3, max_retries=3))
    
    @patch('src.utils.error_handler.logger')
    def test_log_error(self, mock_logger):
        """Test error logging."""
        error = Exception("Test error")
        ErrorHandler.log_error(error, context="test_context")
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        self.assertIn("test_context", call_args)
        self.assertIn("Exception", call_args)


class TestHandleErrorsDecorator(unittest.IsolatedAsyncioTestCase):
    """Test handle_errors decorator."""
    
    @handle_errors(default_return="default")
    async def failing_function(self):
        """Function that raises an exception."""
        raise Exception("Test error")
    
    @handle_errors(default_return="default", reraise=True)
    async def failing_function_reraise(self):
        """Function that raises an exception with reraise."""
        raise Exception("Test error")
    
    async def test_handle_errors_returns_default(self):
        """Test that decorator returns default on error."""
        result = await self.failing_function()
        self.assertEqual(result, "default")
    
    async def test_handle_errors_reraise(self):
        """Test that decorator re-raises when reraise=True."""
        with self.assertRaises(Exception):
            await self.failing_function_reraise()


class TestSafeExecute(unittest.IsolatedAsyncioTestCase):
    """Test safe_execute function."""
    
    async def test_safe_execute_success(self):
        """Test safe_execute with successful function."""
        async def success_func():
            return "success"
        
        result = await safe_execute(success_func, default_return="default")
        self.assertEqual(result, "success")
    
    async def test_safe_execute_failure(self):
        """Test safe_execute with failing function."""
        async def failing_func():
            raise Exception("Error")
        
        result = await safe_execute(failing_func, default_return="default", max_retries=0)
        self.assertEqual(result, "default")
    
    async def test_safe_execute_with_retries(self):
        """Test safe_execute with retries."""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return "success"
        
        result = await safe_execute(flaky_func, default_return="default", max_retries=2, retry_delay=0.1)
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()

