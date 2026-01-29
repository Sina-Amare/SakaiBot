"""Tests for Gemini API Key Manager.

Critical tests for API key rotation and failover logic.
This is the highest priority test file as key exhaustion = bot down.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch  # noqa: F401 - kept for potential future use

from src.ai.api_key_manager import (
    GeminiKeyManager,
    KeyState,
    KeyStatus,
    initialize_gemini_key_manager,
    get_gemini_key_manager,
)


class TestKeyState:
    """Tests for KeyState dataclass."""

    def test_key_state_default_values(self):
        """KeyState initializes with healthy status."""
        state = KeyState(key="test-key")
        assert state.key == "test-key"
        assert state.status == KeyStatus.HEALTHY
        assert state.error_count == 0
        assert state.failed_at is None
        assert state.last_used is None

    def test_key_state_is_available_when_healthy(self):
        """Healthy key is always available."""
        state = KeyState(key="test-key")
        assert state.is_available(cooldown_seconds=60) is True

    def test_key_state_not_available_when_recently_failed(self):
        """Recently failed key is not available."""
        state = KeyState(key="test-key")
        state.status = KeyStatus.RATE_LIMITED
        state.failed_at = datetime.now()
        assert state.is_available(cooldown_seconds=60) is False

    def test_key_state_becomes_available_after_cooldown(self):
        """Key becomes available after cooldown period."""
        state = KeyState(key="test-key")
        state.status = KeyStatus.RATE_LIMITED
        # Set failed_at to 70 seconds ago
        state.failed_at = datetime.now() - timedelta(seconds=70)
        # 60s cooldown should have passed
        assert state.is_available(cooldown_seconds=60) is True

    def test_mark_healthy_resets_error_state(self):
        """mark_healthy resets error count and status."""
        state = KeyState(key="test-key")
        state.status = KeyStatus.ERROR
        state.error_count = 5
        state.mark_healthy()
        assert state.status == KeyStatus.HEALTHY
        assert state.error_count == 0
        assert state.last_used is not None

    def test_mark_failed_increments_error_count(self):
        """mark_failed increments error count and sets status."""
        state = KeyState(key="test-key")
        state.mark_failed(is_rate_limit=True)
        assert state.status == KeyStatus.RATE_LIMITED
        assert state.error_count == 1
        assert state.failed_at is not None

        state.mark_failed(is_rate_limit=False)
        assert state.status == KeyStatus.ERROR
        assert state.error_count == 2


class TestGeminiKeyManager:
    """Tests for GeminiKeyManager."""

    def test_init_with_single_key(self):
        """Manager initializes correctly with single key."""
        manager = GeminiKeyManager(["key1"])
        assert manager.num_keys == 1
        assert manager.current_key == "key1"

    def test_init_with_multiple_keys(self):
        """Manager initializes correctly with multiple keys."""
        manager = GeminiKeyManager(["key1", "key2", "key3"])
        assert manager.num_keys == 3
        assert manager.current_key == "key1"

    def test_init_rejects_empty_keys(self):
        """Manager raises error with empty key list."""
        with pytest.raises(ValueError, match="At least one API key"):
            GeminiKeyManager([])

    def test_init_filters_empty_strings(self):
        """Manager filters out empty string keys."""
        manager = GeminiKeyManager(["key1", "", "key2", "key3"])
        assert manager.num_keys == 3

    def test_get_current_key_returns_first_key(self):
        """get_current_key returns first key initially."""
        manager = GeminiKeyManager(["key1", "key2"])
        assert manager.get_current_key() == "key1"

    def test_mark_success_marks_key_healthy(self):
        """mark_success marks current key as healthy."""
        manager = GeminiKeyManager(["key1"])
        manager.mark_success()
        status = manager.get_status()
        assert status["keys"][0]["status"] == "healthy"

    def test_mark_rate_limited_changes_status(self):
        """mark_key_rate_limited changes key status."""
        manager = GeminiKeyManager(["key1", "key2"])
        result = manager.mark_key_rate_limited()
        assert result is True  # Other keys available
        status = manager.get_status()
        assert status["keys"][0]["status"] == "rate_limited"

    def test_rotate_to_next_key(self):
        """rotate_to_next returns next available key."""
        manager = GeminiKeyManager(["key1", "key2", "key3"])
        manager.mark_key_rate_limited()
        # After rate limiting, manager already finds next available key
        next_key = manager.get_current_key()
        # Should be key2 or key3 (not key1 which is rate limited)
        assert next_key is not None
        assert next_key != "key1"

    def test_rotate_wraps_around(self):
        """Rotation wraps around to first key."""
        manager = GeminiKeyManager(["key1", "key2"], cooldown_seconds=1)
        manager.mark_key_rate_limited()  # key1 rate limited
        manager.rotate_to_next()  # now on key2
        manager.mark_key_rate_limited()  # key2 rate limited

        # Wait for cooldown
        time.sleep(1.1)

        next_key = manager.rotate_to_next()
        assert next_key == "key1"

    def test_all_keys_exhausted_when_all_failed(self):
        """all_keys_exhausted returns True when no keys available."""
        manager = GeminiKeyManager(["key1"], cooldown_seconds=60)
        manager.mark_key_rate_limited()
        assert manager.all_keys_exhausted() is True

    def test_all_keys_not_exhausted_with_healthy_keys(self):
        """all_keys_exhausted returns False when keys available."""
        manager = GeminiKeyManager(["key1", "key2"])
        manager.mark_key_rate_limited()  # Only key1 rate limited
        assert manager.all_keys_exhausted() is False

    def test_get_current_key_finds_available_after_cooldown(self):
        """get_current_key finds available key after cooldown."""
        manager = GeminiKeyManager(["key1"], cooldown_seconds=1)
        manager.mark_key_rate_limited()

        # Key unavailable immediately
        assert manager.get_current_key() is None

        # Wait for cooldown
        time.sleep(1.1)

        # Key available again
        assert manager.get_current_key() == "key1"

    def test_reset_all_keys(self):
        """reset_all_keys restores all keys to healthy."""
        manager = GeminiKeyManager(["key1", "key2", "key3"])
        manager.mark_key_rate_limited()
        manager.rotate_to_next()
        manager.mark_key_error()

        manager.reset_all_keys()

        status = manager.get_status()
        assert status["current_index"] == 0
        for key_info in status["keys"]:
            assert key_info["status"] == "healthy"
            assert key_info["available"] is True

    def test_get_status_returns_correct_structure(self):
        """get_status returns expected structure."""
        manager = GeminiKeyManager(["key1", "key2"])
        status = manager.get_status()

        assert "current_index" in status
        assert "total_keys" in status
        assert "cooldown_seconds" in status
        assert "keys" in status
        assert len(status["keys"]) == 2

        key_info = status["keys"][0]
        assert "index" in key_info
        assert "status" in key_info
        assert "error_count" in key_info
        assert "is_current" in key_info
        assert "available" in key_info
        assert "masked_key" in key_info

    def test_mark_key_exhausted_for_day(self):
        """mark_key_exhausted_for_day sets exhausted_until."""
        manager = GeminiKeyManager(["key1", "key2"])
        result = manager.mark_key_exhausted_for_day()

        assert result is True  # key2 still available
        status = manager.get_status()
        assert status["keys"][0]["status"] == "exhausted"

    def test_mark_key_exhausted_returns_false_when_all_exhausted(self):
        """mark_key_exhausted_for_day returns False when no keys left."""
        manager = GeminiKeyManager(["key1"], cooldown_seconds=60)
        result = manager.mark_key_exhausted_for_day()
        assert result is False


class TestGlobalManager:
    """Tests for global manager functions."""

    def test_initialize_and_get_manager(self):
        """initialize_gemini_key_manager creates accessible instance."""
        manager = initialize_gemini_key_manager(["key1", "key2"])
        assert manager is not None
        assert manager.num_keys == 2

        retrieved = get_gemini_key_manager()
        assert retrieved is manager

    def test_initialize_with_empty_keys_returns_none(self):
        """initialize_gemini_key_manager returns None for empty keys."""
        result = initialize_gemini_key_manager([])
        assert result is None


class TestKeyRotationSequence:
    """Integration tests for key rotation sequences."""

    def test_full_rotation_sequence(self):
        """Test complete rotation through all keys."""
        manager = GeminiKeyManager(
            ["key1", "key2", "key3"], cooldown_seconds=0
        )

        # Start with key1
        assert manager.get_current_key() == "key1"

        # Rate limit key1 - manager auto-finds next available
        manager.mark_key_rate_limited()
        next_key = manager.get_current_key()
        # Should not be key1 which is rate limited
        assert next_key is not None
        assert next_key != "key1"

        # Mark success on current key
        manager.mark_success()
        current_idx = manager.get_status()["current_index"]
        status = manager.get_status()["keys"][current_idx]["status"]
        assert status == "healthy"

    def test_recovery_after_all_keys_cooldown(self):
        """All keys recover after cooldown expires."""
        manager = GeminiKeyManager(["key1", "key2"], cooldown_seconds=1)

        # Exhaust both keys
        manager.mark_key_rate_limited()
        manager.rotate_to_next()
        manager.mark_key_rate_limited()

        assert manager.all_keys_exhausted() is True

        # Wait for cooldown
        time.sleep(1.1)

        # Keys should be available again
        assert manager.all_keys_exhausted() is False
        assert manager.get_current_key() is not None
