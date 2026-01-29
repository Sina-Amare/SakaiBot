"""Shared test fixtures for SakaiBot."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    config = Mock()
    config.gemini_api_keys = ["test-key-1", "test-key-2", "test-key-3"]
    config.gemini_model_pro = "gemini-2.5-pro"
    config.gemini_model_flash = "gemini-2.5-flash"
    config.openrouter_api_key = "test-openrouter-key"
    config.llm_provider = "gemini"
    config.telegram_api_id = 12345678
    config.telegram_api_hash = "test_api_hash"
    config.telegram_phone_number = "+1234567890"
    config.max_analyze_messages = 10000
    config.flux_worker_url = "https://test-flux.workers.dev"
    config.sdxl_worker_url = "https://test-sdxl.workers.dev"
    config.sdxl_api_key = "test-sdxl-key"
    config.ffmpeg_path = None
    config.environment = "development"
    config.debug = True
    return config


@pytest.fixture
def mock_ai_processor(mock_config):
    """Mock AI processor."""
    processor = Mock()
    processor.execute_custom_prompt = AsyncMock(return_value="Test AI response")
    processor.translate_text = AsyncMock(return_value="Test translation")
    processor.analyze_messages = AsyncMock(return_value="Test analysis")
    processor.answer_question = AsyncMock(return_value="Test answer")
    return processor


@pytest.fixture
def mock_telegram_client():
    """Mock Telegram client."""
    client = MagicMock()
    client.get_me = AsyncMock(return_value=Mock(id=123456789, first_name="TestBot"))
    client.send_message = AsyncMock(return_value=Mock(id=1))
    client.edit_message = AsyncMock()
    client.delete_messages = AsyncMock()
    client.get_entity = AsyncMock()
    return client


@pytest.fixture
def mock_message():
    """Mock Telegram message."""
    message = Mock()
    message.id = 1
    message.text = "/prompt=Hello world"
    message.chat_id = -100123456789
    message.sender_id = 123456789
    message.reply_to_msg_id = None
    message.date = datetime.utcnow()
    message.edit = AsyncMock()
    message.delete = AsyncMock()
    return message


@pytest.fixture
def sample_api_keys():
    """Sample API keys for testing."""
    return ["key1", "key2", "key3"]
