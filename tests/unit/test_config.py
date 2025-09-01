"""Unit tests for configuration module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config import (
    Environment,
    TelegramConfig,
    OpenRouterConfig,
    UserBotConfig,
    PathConfig,
    LoggingConfig
)


class TestEnvironment:
    """Test Environment enum."""
    
    def test_environment_values(self):
        """Test that all environment values are defined."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"
        assert Environment.TESTING == "testing"


class TestTelegramConfig:
    """Test TelegramConfig."""
    
    @patch.dict('os.environ', {
        'TELEGRAM_API_ID': '12345',
        'TELEGRAM_API_HASH': 'test_hash',
        'TELEGRAM_PHONE_NUMBER': '+1234567890'
    })
    def test_telegram_config_from_env(self):
        """Test loading Telegram config from environment."""
        config = TelegramConfig()
        assert config.api_id == 12345
        assert config.api_hash.get_secret_value() == 'test_hash'
        assert config.phone_number == '+1234567890'
        assert config.session_name == 'sakaibot_session'
    
    def test_telegram_config_defaults(self):
        """Test default values."""
        with patch.dict('os.environ', {
            'TELEGRAM_API_ID': '12345',
            'TELEGRAM_API_HASH': 'test_hash',
            'TELEGRAM_PHONE_NUMBER': '+1234567890'
        }):
            config = TelegramConfig()
            assert config.session_name == 'sakaibot_session'


class TestOpenRouterConfig:
    """Test OpenRouterConfig."""
    
    @patch.dict('os.environ', {
        'OPENROUTER_API_KEY': 'test_key',
        'OPENROUTER_MODEL_NAME': 'test_model'
    })
    def test_openrouter_config_from_env(self):
        """Test loading OpenRouter config from environment."""
        config = OpenRouterConfig()
        assert config.api_key.get_secret_value() == 'test_key'
        assert config.model_name == 'test_model'
        assert config.base_url == 'https://openrouter.ai/api/v1'
    
    def test_temperature_validation(self):
        """Test temperature validation."""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test'}):
            config = OpenRouterConfig()
            assert 0.0 <= config.temperature <= 2.0
    
    @patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test'})
    def test_defaults(self):
        """Test default values."""
        config = OpenRouterConfig()
        assert config.max_tokens == 1500
        assert config.temperature == 0.7
        assert config.timeout == 30
        assert config.max_retries == 3


class TestUserBotConfig:
    """Test UserBotConfig."""
    
    def test_userbot_defaults(self):
        """Test default values."""
        config = UserBotConfig()
        assert config.max_analyze_messages == 5000
        assert config.max_message_length == 4096
        assert config.confirmation_keyword == 'confirm'
        assert config.default_tts_voice == 'fa-IR-DilaraNeural'
    
    @patch.dict('os.environ', {
        'USERBOT_MAX_ANALYZE_MESSAGES': '1000',
        'USERBOT_CONFIRMATION_KEYWORD': 'ok'
    })
    def test_userbot_from_env(self):
        """Test loading from environment."""
        config = UserBotConfig()
        assert config.max_analyze_messages == 1000
        assert config.confirmation_keyword == 'ok'


class TestPathConfig:
    """Test PathConfig."""
    
    def test_path_defaults(self):
        """Test default paths."""
        config = PathConfig()
        assert config.cache_dir == Path('cache')
        assert config.logs_dir == Path('logs')
        assert config.session_dir == Path('.')
    
    def test_directory_creation(self):
        """Test that directories are created."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            config = PathConfig()
            # Directories should be created
            assert mock_mkdir.called


class TestLoggingConfig:
    """Test LoggingConfig."""
    
    def test_logging_defaults(self):
        """Test default logging configuration."""
        config = LoggingConfig()
        assert config.level == 'INFO'
        assert config.file_name == 'sakaibot.log'
        assert config.max_file_size == 10485760  # 10MB
        assert config.backup_count == 5
    
    @patch.dict('os.environ', {'LOGGING_LEVEL': 'DEBUG'})
    def test_logging_from_env(self):
        """Test loading from environment."""
        config = LoggingConfig()
        assert config.level == 'DEBUG'
    
    @patch.dict('os.environ', {'LOGGING_LEVEL': 'invalid'})
    def test_invalid_log_level(self):
        """Test invalid log level raises error."""
        with pytest.raises(ValueError):
            config = LoggingConfig()