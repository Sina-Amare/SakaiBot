"""pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import fixtures
from tests.fixtures.sample_data import (
    SAMPLE_TRANSLATION_COMMANDS,
    SAMPLE_AI_RESPONSES,
    SAMPLE_STT_TEXTS,
    VALID_LANGUAGE_CODES,
    VALID_LANGUAGE_NAMES,
    INVALID_LANGUAGE_CODES
)

# Make fixtures available globally
__all__ = [
    'SAMPLE_TRANSLATION_COMMANDS',
    'SAMPLE_AI_RESPONSES', 
    'SAMPLE_STT_TEXTS',
    'VALID_LANGUAGE_CODES',
    'VALID_LANGUAGE_NAMES',
    'INVALID_LANGUAGE_CODES'
]


def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line(
        "markers", "translation: marks tests as translation related"
    )
    config.addinivalue_line(
        "markers", "tts: marks tests as text-to-speech related"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Example of a pytest fixture
import pytest


@pytest.fixture
def sample_translation_command():
    """Provide a sample translation command."""
    return SAMPLE_TRANSLATION_COMMANDS[0]


@pytest.fixture
def valid_language_codes():
    """Provide valid language codes."""
    return VALID_LANGUAGE_CODES


@pytest.fixture
def invalid_language_codes():
    """Provide invalid language codes."""
    return INVALID_LANGUAGE_CODES
