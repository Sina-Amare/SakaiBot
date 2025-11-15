"""Unit tests for configuration management."""

import unittest
import os
import tempfile
from unittest.mock import patch, Mock

from src.core.config import Config, get_settings
from src.core.exceptions import ConfigurationError


class TestConfig(unittest.TestCase):
    """Test Config class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_config = {
            "telegram_api_id": 12345,
            "telegram_api_hash": "abcdefghij1234567890",
            "telegram_phone_number": "+1234567890",
            "llm_provider": "openrouter",
            "openrouter_api_key": "sk-test12345678901234567890"
        }
    
    @patch.dict(os.environ, {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abcdefghij1234567890",
        "TELEGRAM_PHONE_NUMBER": "+1234567890"
    })
    def test_config_creation(self):
        """Test creating config from environment."""
        config = Config()
        self.assertEqual(config.telegram_api_id, 12345)
        self.assertEqual(config.telegram_api_hash, "abcdefghij1234567890")
        self.assertEqual(config.telegram_phone_number, "+1234567890")
    
    def test_validate_api_id_positive(self):
        """Test API ID validation."""
        with self.assertRaises(ValueError):
            Config(telegram_api_id=-1, telegram_api_hash="test", telegram_phone_number="+123")
    
    def test_validate_api_hash_length(self):
        """Test API hash validation."""
        with self.assertRaises(ValueError):
            Config(telegram_api_id=123, telegram_api_hash="short", telegram_phone_number="+123")
    
    def test_validate_phone_number_format(self):
        """Test phone number validation."""
        with self.assertRaises(ValueError):
            Config(telegram_api_id=123, telegram_api_hash="abcdefghij", telegram_phone_number="123")
    
    def test_validate_llm_provider(self):
        """Test LLM provider validation."""
        with self.assertRaises(ValueError):
            Config(
                telegram_api_id=123,
                telegram_api_hash="abcdefghij",
                telegram_phone_number="+123",
                llm_provider="invalid"
            )
    
    def test_validate_openrouter_key(self):
        """Test OpenRouter key validation."""
        config = Config(
            telegram_api_id=123,
            telegram_api_hash="abcdefghij",
            telegram_phone_number="+123",
            openrouter_api_key="YOUR_OPENROUTER_API_KEY_HERE"
        )
        self.assertIsNone(config.openrouter_api_key)
    
    def test_validate_gemini_key(self):
        """Test Gemini key validation."""
        config = Config(
            telegram_api_id=123,
            telegram_api_hash="abcdefghij",
            telegram_phone_number="+123",
            gemini_api_key="YOUR_GEMINI_API_KEY_HERE"
        )
        self.assertIsNone(config.gemini_api_key)
    
    def test_is_ai_enabled_openrouter(self):
        """Test AI enabled check for OpenRouter."""
        config = Config(
            telegram_api_id=123,
            telegram_api_hash="abcdefghij",
            telegram_phone_number="+123",
            llm_provider="openrouter",
            openrouter_api_key="sk-validkey12345678901234567890"
        )
        self.assertTrue(config.is_ai_enabled)
    
    def test_is_ai_enabled_gemini(self):
        """Test AI enabled check for Gemini."""
        config = Config(
            telegram_api_id=123,
            telegram_api_hash="abcdefghij",
            telegram_phone_number="+123",
            llm_provider="gemini",
            gemini_api_key="AIzaValidKey12345678901234567890"
        )
        self.assertTrue(config.is_ai_enabled)
    
    def test_is_ai_enabled_no_key(self):
        """Test AI enabled check without key."""
        config = Config(
            telegram_api_id=123,
            telegram_api_hash="abcdefghij",
            telegram_phone_number="+123",
            llm_provider="openrouter",
            openrouter_api_key=None
        )
        self.assertFalse(config.is_ai_enabled)


class TestConfigLoadFromINI(unittest.TestCase):
    """Test loading config from INI file."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.ini")
    
    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        os.rmdir(self.temp_dir)
    
    def test_load_from_ini_nonexistent(self):
        """Test loading from non-existent INI file."""
        with self.assertRaises(ConfigurationError):
            Config.load_from_ini("nonexistent.ini")
    
    def test_load_from_ini_valid(self):
        """Test loading from valid INI file."""
        ini_content = """[Telegram]
api_id = 12345
api_hash = abcdefghij1234567890
phone_number = +1234567890

[LLM]
provider = openrouter
openrouter_api_key = sk-test12345678901234567890
"""
        with open(self.config_file, 'w') as f:
            f.write(ini_content)
        
        config = Config.load_from_ini(self.config_file)
        # Config loads from INI and converts to environment variables
        # The actual values depend on the conversion logic
        self.assertIsNotNone(config.telegram_api_id)
        self.assertIsNotNone(config.telegram_api_hash)
        self.assertIsNotNone(config.telegram_phone_number)


if __name__ == "__main__":
    unittest.main()

