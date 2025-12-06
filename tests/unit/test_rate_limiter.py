"""Tests for Rate Limiter.

Tests for the rate limiting functionality that protects against abuse.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from src.utils.rate_limiter import RateLimiter, get_ai_rate_limiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter for testing."""
        return RateLimiter(max_requests=5, window_seconds=60)

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, rate_limiter):
        """Requests within limit are allowed."""
        user_id = 12345
        for _ in range(5):
            result = await rate_limiter.check_rate_limit(user_id)
            assert result is True

    @pytest.mark.asyncio
    async def test_blocks_requests_exceeding_limit(self, rate_limiter):
        """Requests exceeding limit are blocked."""
        user_id = 12345
        # Use up all allowed requests
        for _ in range(5):
            await rate_limiter.check_rate_limit(user_id)

        # Next request should be blocked
        result = await rate_limiter.check_rate_limit(user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_different_users_have_separate_limits(self, rate_limiter):
        """Each user has their own rate limit bucket."""
        user1 = 12345
        user2 = 67890

        # Exhaust user1's limit
        for _ in range(5):
            await rate_limiter.check_rate_limit(user1)

        # user1 should be blocked
        assert await rate_limiter.check_rate_limit(user1) is False

        # user2 should still be allowed
        assert await rate_limiter.check_rate_limit(user2) is True

    @pytest.mark.asyncio
    async def test_remaining_requests_decreases(self, rate_limiter):
        """Remaining requests count decreases with each request."""
        user_id = 12345

        initial = await rate_limiter.get_remaining_requests(user_id)
        assert initial == 5

        await rate_limiter.check_rate_limit(user_id)
        remaining = await rate_limiter.get_remaining_requests(user_id)
        assert remaining == 4

    @pytest.mark.asyncio
    async def test_requests_allowed_after_window_expires(self):
        """Requests are allowed again after time window expires."""
        rate_limiter = RateLimiter(max_requests=2, window_seconds=1)
        user_id = 12345

        # Use up all requests
        await rate_limiter.check_rate_limit(user_id)
        await rate_limiter.check_rate_limit(user_id)

        # Should be blocked
        assert await rate_limiter.check_rate_limit(user_id) is False

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be allowed again
        assert await rate_limiter.check_rate_limit(user_id) is True

    def test_reset_user_limit(self, rate_limiter):
        """reset_user_limit clears user's bucket."""
        user_id = 12345

        # Make some requests
        asyncio.run(rate_limiter.check_rate_limit(user_id))
        asyncio.run(rate_limiter.check_rate_limit(user_id))

        # Reset
        rate_limiter.reset_user_limit(user_id)

        # Should have full remaining requests
        remaining = asyncio.run(rate_limiter.get_remaining_requests(user_id))
        assert remaining == 5

    def test_cleanup_old_entries(self, rate_limiter):
        """cleanup_old_entries removes stale buckets."""
        # Add some entries manually with old timestamps
        old_time = datetime.utcnow() - timedelta(seconds=200)
        rate_limiter._buckets[12345].append(old_time)
        rate_limiter._buckets[67890].append(old_time)

        # Cleanup
        rate_limiter.cleanup_old_entries()

        # Old entries should be removed
        assert 12345 not in rate_limiter._buckets
        assert 67890 not in rate_limiter._buckets


class TestGetAiRateLimiter:
    """Tests for global AI rate limiter."""

    def test_returns_singleton(self):
        """get_ai_rate_limiter returns the same instance."""
        limiter1 = get_ai_rate_limiter()
        limiter2 = get_ai_rate_limiter()
        assert limiter1 is limiter2

    def test_has_correct_defaults(self):
        """AI rate limiter has correct default values."""
        limiter = get_ai_rate_limiter()
        # Default is 10 requests per 60 seconds
        assert limiter._max_requests == 10
        assert limiter._window_seconds == 60


class TestRateLimiterEdgeCases:
    """Edge case tests for rate limiter."""

    @pytest.mark.asyncio
    async def test_zero_max_requests_blocks_all(self):
        """Zero max requests blocks everything."""
        limiter = RateLimiter(max_requests=0, window_seconds=60)
        result = await limiter.check_rate_limit(12345)
        assert result is False

    @pytest.mark.asyncio
    async def test_large_user_id(self):
        """Large user IDs are handled correctly."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        large_id = 9999999999999
        result = await limiter.check_rate_limit(large_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_negative_user_id(self):
        """Negative user IDs (chat IDs) are handled correctly."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        negative_id = -100123456789  # Typical channel ID
        result = await limiter.check_rate_limit(negative_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Concurrent requests are handled correctly."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        user_id = 12345

        # Make 10 concurrent requests
        tasks = [
            limiter.check_rate_limit(user_id)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

        # Next should fail
        assert await limiter.check_rate_limit(user_id) is False
