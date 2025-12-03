"""Shared pytest fixtures for SakaiBot tests.

These fixtures avoid using real API keys or external services. They
provide:

- A mocked logger to silence log output in tests
- Sample fake Gemini API keys
"""

from typing import List
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_logger() -> MagicMock:
    """Return a mocked logger to avoid noisy log output in tests."""
    logger = MagicMock()
    # Provide standard logging methods
    for method in ("debug", "info", "warning", "error", "exception"):
        setattr(logger, method, MagicMock())
    return logger


@pytest.fixture
def sample_api_keys() -> List[str]:
    """Return a list of fake Gemini API keys for testing."""
    return [
        "AIzaFAKEKEY0000000001",
        "AIzaFAKEKEY0000000002",
        "AIzaFAKEKEY0000000003",
    ]


