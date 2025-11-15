"""Unit tests for rate limiter."""

import unittest
import asyncio

from src.utils.rate_limiter import RateLimiter, get_ai_rate_limiter


class TestRateLimiter(unittest.IsolatedAsyncioTestCase):
    """Test RateLimiter class."""
    
    async def test_check_rate_limit_allows(self):
        """Test that rate limit allows requests within limit."""
        limiter = RateLimiter(capacity=5, fill_rate=1.0, window_seconds=60)
        
        user_id = 123
        
        # First 5 requests should be allowed
        for i in range(5):
            allowed = await limiter.check_rate_limit(user_id)
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
    
    async def test_check_rate_limit_blocks(self):
        """Test that rate limit blocks requests over limit."""
        limiter = RateLimiter(capacity=2, fill_rate=0.1, window_seconds=60)
        
        user_id = 123
        
        # First 2 should be allowed
        self.assertTrue(await limiter.check_rate_limit(user_id))
        self.assertTrue(await limiter.check_rate_limit(user_id))
        
        # Third should be blocked
        self.assertFalse(await limiter.check_rate_limit(user_id))
    
    async def test_get_remaining_requests(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(capacity=10, fill_rate=1.0, window_seconds=60)
        
        user_id = 123
        
        # Use some requests
        await limiter.check_rate_limit(user_id)
        await limiter.check_rate_limit(user_id)
        
        remaining = await limiter.get_remaining_requests(user_id)
        self.assertGreaterEqual(remaining, 0)
        self.assertLessEqual(remaining, 10)
    
    async def test_rate_limit_per_user(self):
        """Test that rate limits are per user."""
        limiter = RateLimiter(capacity=2, fill_rate=0.1, window_seconds=60)
        
        user1 = 123
        user2 = 456
        
        # User 1 uses limit
        self.assertTrue(await limiter.check_rate_limit(user1))
        self.assertTrue(await limiter.check_rate_limit(user1))
        self.assertFalse(await limiter.check_rate_limit(user1))
        
        # User 2 should still have requests
        self.assertTrue(await limiter.check_rate_limit(user2))
        self.assertTrue(await limiter.check_rate_limit(user2))
    
    def test_get_ai_rate_limiter_singleton(self):
        """Test singleton pattern."""
        limiter1 = get_ai_rate_limiter()
        limiter2 = get_ai_rate_limiter()
        self.assertIs(limiter1, limiter2)


if __name__ == "__main__":
    unittest.main()

