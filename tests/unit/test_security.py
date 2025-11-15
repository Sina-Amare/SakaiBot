"""Unit tests for security utilities."""

import unittest

from src.utils.security import (
    mask_api_key,
    mask_sensitive_data,
    sanitize_log_message
)


class TestSecurityUtils(unittest.TestCase):
    """Test security utility functions."""
    
    def test_mask_api_key_short(self):
        """Test masking short API key."""
        key = "short"
        masked = mask_api_key(key)
        self.assertEqual(masked, "*****")
    
    def test_mask_api_key_normal(self):
        """Test masking normal API key."""
        key = "sk-123456789012345678901234567890"
        masked = mask_api_key(key, visible_chars=4)
        self.assertIn("sk-1", masked)
        self.assertIn("7890", masked)
        self.assertIn("****", masked)
        self.assertNotIn("2345678901234567890123456", masked)
    
    def test_mask_api_key_none(self):
        """Test masking None API key."""
        masked = mask_api_key(None)
        self.assertEqual(masked, "None")
    
    def test_mask_sensitive_data_openai_key(self):
        """Test masking OpenAI-style API key."""
        text = "API key: sk-123456789012345678901234567890"
        masked = mask_sensitive_data(text)
        self.assertNotIn("123456789012345678901234567890", masked)
        self.assertIn("sk-", masked)
    
    def test_mask_sensitive_data_google_key(self):
        """Test masking Google API key."""
        text = "API key: AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
        masked = mask_sensitive_data(text)
        self.assertNotIn("SyAbCdEfGhIjKlMnOpQrStUvWxYz1234567890", masked)
        self.assertIn("AIza", masked)
    
    def test_sanitize_log_message(self):
        """Test sanitizing log message."""
        message = "Error with API key: sk-123456789012345678901234567890"
        sanitized = sanitize_log_message(message)
        self.assertNotIn("123456789012345678901234567890", sanitized)
        self.assertIn("sk-", sanitized)
    
    def test_mask_api_key_custom_visible(self):
        """Test masking with custom visible characters."""
        key = "12345678901234567890"
        masked = mask_api_key(key, visible_chars=2)
        self.assertEqual(len(masked), len(key))
        self.assertTrue(masked.startswith("12"))
        self.assertTrue(masked.endswith("90"))
        self.assertIn("****", masked)


if __name__ == "__main__":
    unittest.main()

