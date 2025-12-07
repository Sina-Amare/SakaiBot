"""
API Key Manager with auto-rotation on rate limits.

Manages multiple API keys (for Gemini, OpenRouter, etc.) with automatic
rotation when a key hits rate limits or errors. Provides seamless failover
without requiring bot restart.

Key Features:
- Sequential key rotation (1→2→3→4)
- Automatic rotation on 429 errors
- Daily quota tracking with Pacific midnight reset
- Thread-safe operations
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum

import pytz

from ..utils.logging import get_logger


logger = get_logger(__name__)


class KeyStatus(Enum):
    """Status of an API key."""
    HEALTHY = "healthy"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    EXHAUSTED = "exhausted"


@dataclass
class KeyState:
    """State information for a single API key."""
    key: str
    status: KeyStatus = KeyStatus.HEALTHY
    failed_at: Optional[datetime] = None
    error_count: int = 0
    last_used: Optional[datetime] = None
    # When not None, key is considered exhausted until this UTC timestamp
    exhausted_until: Optional[datetime] = None

    def is_available(self, cooldown_seconds: int) -> bool:
        """Check if key is available for use.

        A key is available when:
        - It is not marked as exhausted for the current quota day, and
        - Either it is healthy, or its transient cooldown has passed.
        """
        # Daily exhaustion check (Gemini RPD reset at midnight Pacific)
        if self.exhausted_until is not None:
            now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
            if now_utc < self.exhausted_until:
                return False
            # Exhaustion window has passed; clear it
            self.exhausted_until = None

        if self.status == KeyStatus.HEALTHY:
            return True

        if self.failed_at is None:
            return True

        # Check if cooldown period has passed for transient failures
        cooldown_end = self.failed_at + timedelta(seconds=cooldown_seconds)
        if datetime.now() > cooldown_end:
            return True

        return False

    def mark_healthy(self):
        """Mark key as healthy after successful use.

        Note: This does NOT clear exhausted_until, because daily
        exhaustion is governed by provider-level quotas and resets
        only at the next Pacific midnight.
        """
        self.status = KeyStatus.HEALTHY
        self.error_count = 0
        self.last_used = datetime.now()

    def mark_failed(self, is_rate_limit: bool = False):
        """Mark key as failed due to a transient error or short-term rate limit.

        Daily quota exhaustion is handled separately via exhausted_until.
        """
        self.failed_at = datetime.now()
        self.error_count += 1
        self.status = KeyStatus.RATE_LIMITED if is_rate_limit else KeyStatus.ERROR


class APIKeyManager:
    """
    Manages multiple API keys with auto-rotation.
    
    Provides automatic failover when a key hits rate limits (429 errors)
    or other errors. Keys are rotated seamlessly without requiring
    application restart.
    
    Usage:
        manager = APIKeyManager(["key1", "key2", "key3"], provider_name="Gemini")
        
        # Get current key
        key = manager.get_current_key()
        
        # On rate limit error
        manager.mark_key_rate_limited()
        next_key = manager.rotate_to_next()
        
        # On success
        manager.mark_success()
    """
    
    # Default cooldown period for rate-limited keys (seconds)
    DEFAULT_COOLDOWN = 60
    
    def __init__(
        self,
        api_keys: List[str],
        cooldown_seconds: int = DEFAULT_COOLDOWN,
        provider_name: str = "API"
    ):
        """
        Initialize key manager.
        
        Args:
            api_keys: List of API keys
            cooldown_seconds: Seconds to wait before retrying a failed key
            provider_name: Name of provider for logging (e.g., 'Gemini', 'OpenRouter')
        """
        if not api_keys:
            raise ValueError("At least one API key must be provided")
        
        self._keys: List[KeyState] = [
            KeyState(key=key) for key in api_keys if key
        ]
        
        if not self._keys:
            raise ValueError("No valid API keys provided")
        
        self._current_index = 0
        self._cooldown_seconds = cooldown_seconds
        self._provider_name = provider_name
        self._lock = asyncio.Lock()
        self._logger = logger
        
        self._logger.info(
            f"Initialized {provider_name} KeyManager with {len(self._keys)} keys, "
            f"cooldown: {cooldown_seconds}s"
        )
    
    @property
    def num_keys(self) -> int:
        """Get total number of keys."""
        return len(self._keys)
    
    @property
    def current_key(self) -> str:
        """Get current API key (without rotation logic)."""
        return self._keys[self._current_index].key
    
    def get_current_key(self) -> Optional[str]:
        """
        Get the current healthy API key.
        
        Returns:
            Current API key if available, None if all keys exhausted
        """
        # First check if current key is available
        current = self._keys[self._current_index]
        if current.is_available(self._cooldown_seconds):
            return current.key
        
        # Try to find an available key
        return self._find_available_key()
    
    def _find_available_key(self) -> Optional[str]:
        """Find the first available key starting from current index."""
        original_index = self._current_index
        
        for i in range(len(self._keys)):
            check_index = (original_index + i) % len(self._keys)
            key_state = self._keys[check_index]
            
            if key_state.is_available(self._cooldown_seconds):
                if check_index != self._current_index:
                    self._current_index = check_index
                    self._logger.info(
                        f"Switched to key {check_index + 1}/{len(self._keys)} "
                        f"(previous key in cooldown)"
                    )
                return key_state.key
        
        # All keys exhausted
        self._logger.warning("All API keys are currently in cooldown")
        return None
    
    def mark_success(self):
        """Mark current key as successfully used."""
        current = self._keys[self._current_index]
        current.mark_healthy()
    
    def mark_key_rate_limited(self) -> bool:
        """
        Mark current key as rate limited.
        
        Returns:
            True if there are other keys to try, False if all exhausted
        """
        current = self._keys[self._current_index]
        current.mark_failed(is_rate_limit=True)
        
        masked_key = f"{current.key[:8]}...{current.key[-4:]}"
        self._logger.warning(
            f"Key {self._current_index + 1}/{len(self._keys)} rate limited: {masked_key}"
        )
        
        # Check if there are other available keys
        return self._find_available_key() is not None
    
    def mark_key_error(self) -> bool:
        """
        Mark current key as having an error.
        
        Returns:
            True if there are other keys to try, False if all exhausted
        """
        current = self._keys[self._current_index]
        current.mark_failed(is_rate_limit=False)
        
        masked_key = f"{current.key[:8]}...{current.key[-4:]}"
        self._logger.warning(
            f"Key {self._current_index + 1}/{len(self._keys)} error: {masked_key}"
        )
        
        # Check if there are other available keys
        return self._find_available_key() is not None
    
    def rotate_to_next(self) -> Optional[str]:
        """
        Rotate to the next available key.
        
        Returns:
            Next available API key, or None if all exhausted
        """
        # Move to next index
        original_index = self._current_index
        self._current_index = (self._current_index + 1) % len(self._keys)
        
        # Find an available key
        result = self._find_available_key()
        
        if result:
            self._logger.info(
                f"Rotated from key {original_index + 1} to {self._current_index + 1}"
            )
        else:
            self._logger.warning("Failed to rotate - all keys exhausted")
        
        return result
    
    def reset_for_model_switch(self) -> None:
        """
        Reset key exhaustion status when switching models.
        
        This is needed because Gemini Pro and Flash have SEPARATE quotas.
        When Pro is exhausted, the same API keys can still work for Flash.
        """
        for key_state in self._keys:
            # Clear the exhausted_until flag so keys can be tried again
            key_state.exhausted_until = None
            # Reset error count
            key_state.error_count = 0
            # Reset status to healthy
            key_state.status = KeyStatus.HEALTHY
        
        # Reset to first key
        self._current_index = 0
        
        self._logger.info(
            f"{self._provider_name}: Reset all {len(self._keys)} keys for model switch"
        )
    
    def get_status(self) -> Dict[str, any]:
        """Get status of all keys for debugging."""
        return {
            "current_index": self._current_index,
            "total_keys": len(self._keys),
            "cooldown_seconds": self._cooldown_seconds,
            "keys": [
                {
                    "index": i,
                    "status": k.status.value,
                    "error_count": k.error_count,
                    "is_current": i == self._current_index,
                    "available": k.is_available(self._cooldown_seconds),
                    "masked_key": f"{k.key[:8]}...{k.key[-4:]}" if len(k.key) > 12 else "***"
                }
                for i, k in enumerate(self._keys)
            ]
        }
    
    def _compute_next_pacific_midnight_utc(self) -> datetime:
        """
        Compute the next midnight in America/Los_Angeles, returned in UTC.

        According to Gemini docs, Requests Per Day (RPD) quotas reset at
        midnight Pacific time:
        https://ai.google.dev/gemini-api/docs/rate-limits#free-tier
        """
        pacific_tz = pytz.timezone("America/Los_Angeles")
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        now_pacific = now_utc.astimezone(pacific_tz)

        today_midnight_pacific = now_pacific.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if now_pacific >= today_midnight_pacific:
            next_midnight_pacific = today_midnight_pacific + timedelta(days=1)
        else:
            # If we are somehow before today's midnight, use today's midnight
            next_midnight_pacific = today_midnight_pacific

        return next_midnight_pacific.astimezone(pytz.utc)

    def mark_key_exhausted_for_day(self) -> bool:
        """
        Mark current key as exhausted for the rest of the quota day.

        Daily exhaustion is distinct from short-term rate limiting. The
        key will not be considered available again until after the next
        Pacific midnight.

        Returns:
            True if there are other keys to try, False if all exhausted.
        """
        current = self._keys[self._current_index]
        current.status = KeyStatus.EXHAUSTED
        current.failed_at = datetime.now()
        current.error_count += 1
        current.exhausted_until = self._compute_next_pacific_midnight_utc()

        masked_key = f"{current.key[:8]}...{current.key[-4:]}" if len(current.key) > 12 else "***"
        self._logger.warning(
            "Key %s/%s exhausted for the day until %s UTC: %s",
            self._current_index + 1,
            len(self._keys),
            current.exhausted_until.isoformat(),
            masked_key,
        )

        # Move to next available key (if any)
        return self._find_available_key() is not None

    def all_keys_exhausted(self) -> bool:
        """Check if all keys are currently unavailable.

        Unavailability can be due to:
        - Transient cooldown after errors/rate limits, or
        - Daily exhaustion until the next Pacific midnight.
        """
        return all(
            not k.is_available(self._cooldown_seconds)
            for k in self._keys
        )

    def reset_all_keys(self):
        """Reset all keys to healthy state (for testing/recovery)."""
        for key in self._keys:
            key.status = KeyStatus.HEALTHY
            key.failed_at = None
            key.error_count = 0
        self._current_index = 0
        self._logger.info("All keys reset to healthy state")


# Global manager instance (lazy initialization)
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> Optional[APIKeyManager]:
    """Get the global API key manager instance."""
    return _api_key_manager


def initialize_api_key_manager(
    api_keys: List[str],
    cooldown_seconds: int = 60,
    provider_name: str = "API"
) -> Optional[APIKeyManager]:
    """
    Initialize the global API key manager.

    Args:
        api_keys: List of API keys
        cooldown_seconds: Cooldown period for failed keys
        provider_name: Provider name for logging

    Returns:
        Initialized APIKeyManager instance
    """
    global _api_key_manager

    if not api_keys:
        logger.warning(f"No {provider_name} API keys provided for key manager")
        return None

    _api_key_manager = APIKeyManager(api_keys, cooldown_seconds, provider_name)
    return _api_key_manager


# Backward compatibility aliases
GeminiKeyManager = APIKeyManager


def get_gemini_key_manager() -> Optional[APIKeyManager]:
    """Backward compat: Get the global key manager."""
    return _api_key_manager


def initialize_gemini_key_manager(
    api_keys: List[str],
    cooldown_seconds: int = 60
) -> Optional[APIKeyManager]:
    """Backward compat: Initialize key manager for Gemini."""
    return initialize_api_key_manager(api_keys, cooldown_seconds, "Gemini")

