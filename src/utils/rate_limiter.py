"""Rate limiting utility for API calls and commands."""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional

from .logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter for per-user rate limiting."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._buckets: Dict[int, deque] = defaultdict(deque)
        self._logger = get_logger(self.__class__.__name__)
    
    async def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User identifier (Telegram user ID)
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = datetime.utcnow()
        bucket = self._buckets[user_id]
        
        # Remove old requests outside the time window
        cutoff_time = now - timedelta(seconds=self._window_seconds)
        while bucket and bucket[0] < cutoff_time:
            bucket.popleft()
        
        # Check if limit exceeded
        if len(bucket) >= self._max_requests:
            self._logger.warning(
                f"Rate limit exceeded for user {user_id}: "
                f"{len(bucket)}/{self._max_requests} requests in last {self._window_seconds}s"
            )
            return False
        
        # Add current request timestamp
        bucket.append(now)
        return True
    
    async def get_remaining_requests(self, user_id: int) -> int:
        """
        Get number of remaining requests for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of remaining requests in the current window
        """
        now = datetime.utcnow()
        bucket = self._buckets[user_id]
        
        # Clean up old requests
        cutoff_time = now - timedelta(seconds=self._window_seconds)
        while bucket and bucket[0] < cutoff_time:
            bucket.popleft()
        
        return max(0, self._max_requests - len(bucket))
    
    def reset_user_limit(self, user_id: int) -> None:
        """
        Reset rate limit for a specific user.
        
        Args:
            user_id: User identifier
        """
        if user_id in self._buckets:
            del self._buckets[user_id]
            self._logger.debug(f"Rate limit reset for user {user_id}")
    
    def cleanup_old_entries(self) -> None:
        """Clean up old entries for users who haven't made requests recently."""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self._window_seconds * 2)
        
        users_to_remove = []
        for user_id, bucket in self._buckets.items():
            if not bucket or (bucket and bucket[-1] < cutoff_time):
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self._buckets[user_id]
        
        if users_to_remove:
            self._logger.debug(f"Cleaned up {len(users_to_remove)} old rate limit entries")


# Global rate limiter instance for AI commands
_ai_rate_limiter: Optional[RateLimiter] = None


def get_ai_rate_limiter() -> RateLimiter:
    """
    Get the global AI rate limiter instance.
    
    Returns:
        Global RateLimiter instance for AI commands
    """
    global _ai_rate_limiter
    if _ai_rate_limiter is None:
        # Default: 10 requests per 60 seconds
        _ai_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
    return _ai_rate_limiter

