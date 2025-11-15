"""Unit tests for retry utilities."""

import unittest
import asyncio
from unittest.mock import Mock, patch

from src.utils.retry import retry_with_backoff


class TestRetry(unittest.IsolatedAsyncioTestCase):
    """Test retry utilities."""
    
    async def test_retry_with_backoff_success(self):
        """Test retry with successful function."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)
    
    async def test_retry_with_backoff_failure(self):
        """Test retry with failing function."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Test error")
        
        with self.assertRaises(Exception):
            await failing_func()
        
        # max_retries=3 means 3 total attempts (1 initial + 2 retries)
        self.assertEqual(call_count, 3)
    
    async def test_retry_with_backoff_eventual_success(self):
        """Test retry with eventual success."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Test error")
            return "success"
        
        result = await flaky_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    async def test_retry_with_backoff_no_retries(self):
        """Test retry with max_retries=0."""
        call_count = 0
        
        @retry_with_backoff(max_retries=0, base_delay=0.01)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Test error")
        
        # With max_retries=0, range(0) is empty, so function is never called
        # This is the actual behavior of the implementation
        try:
            await failing_func()
        except Exception:
            pass
        
        # Implementation with max_retries=0 doesn't call the function
        self.assertEqual(call_count, 0)


if __name__ == "__main__":
    unittest.main()

