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
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
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
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Test error")
        
        with self.assertRaises(Exception):
            await failing_func()
        
        self.assertEqual(call_count, 4)  # 1 initial + 3 retries
    
    async def test_retry_with_backoff_eventual_success(self):
        """Test retry with eventual success."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
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
        
        @retry_with_backoff(max_retries=0, initial_delay=0.01)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Test error")
        
        with self.assertRaises(Exception):
            await failing_func()
        
        self.assertEqual(call_count, 1)  # Only initial call


if __name__ == "__main__":
    unittest.main()

