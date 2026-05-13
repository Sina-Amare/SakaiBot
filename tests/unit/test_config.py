"""Tests for application configuration behavior."""

from src.core.config import Config


def _base_config(**overrides):
    values = {
        "_env_file": None,
        "telegram_api_id": 123456,
        "telegram_api_hash": "0123456789abcdef",
        "telegram_phone_number": "+1234567890",
        "debug": False,
        "openrouter_api_key": None,
        "openrouter_api_key_1": None,
        "openrouter_api_key_2": None,
        "openrouter_api_key_3": None,
        "openrouter_api_key_4": None,
    }
    values.update(overrides)
    return Config(**values)


def test_openrouter_numbered_key_enables_ai():
    """Numbered OpenRouter keys should enable AI without the legacy key."""
    config = _base_config(
        llm_provider="openrouter",
        openrouter_api_key_1="sk-or-v1-primary123456",
    )

    assert config.openrouter_api_keys == ["sk-or-v1-primary123456"]
    assert config.is_ai_enabled is True


def test_openrouter_legacy_key_still_enables_ai():
    """The legacy OpenRouter key remains supported for compatibility."""
    config = _base_config(
        llm_provider="openrouter",
        openrouter_api_key="sk-or-v1-legacy123456",
    )

    assert config.openrouter_api_keys == ["sk-or-v1-legacy123456"]
    assert config.is_ai_enabled is True
