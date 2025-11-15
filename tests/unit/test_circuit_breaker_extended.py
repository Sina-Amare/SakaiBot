"""Extended unit tests for circuit breaker."""

import unittest
import asyncio
from unittest.mock import AsyncMock, patch

from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_telegram_circuit_breaker,
    get_ai_circuit_breaker
)


class TestCircuitBreakerExtended(unittest.IsolatedAsyncioTestCase):
    """Extended tests for CircuitBreaker class."""
    
    async def test_circuit_closed_success(self):
        """Test circuit in closed state with successful calls."""
        breaker = CircuitBreaker(failure_threshold=5, success_threshold=2, timeout=60.0)
        
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(breaker.get_state(), CircuitState.CLOSED)
    
    async def test_circuit_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3, success_threshold=2, timeout=60.0)
        
        async def failing_func():
            raise Exception("Test error")
        
        # Cause failures to open circuit
        for i in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        # Circuit should be open
        self.assertEqual(breaker.get_state(), CircuitState.OPEN)
        
        # Next call should be rejected immediately
        with self.assertRaises(Exception) as context:
            await breaker.call(failing_func)
        self.assertIn("Circuit breaker is OPEN", str(context.exception))
    
    async def test_circuit_half_open_recovery(self):
        """Test circuit recovery through half-open state."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            success_threshold=2,
            timeout=0.1  # Short timeout for testing
        )
        
        async def failing_func():
            raise Exception("Test error")
        
        # Open circuit
        for i in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass
        
        self.assertEqual(breaker.get_state(), CircuitBreakerState.OPEN)
        
        # Wait for timeout
        await asyncio.sleep(0.15)
        
        # Try successful call (should transition to half-open)
        async def success_func():
            return "success"
        
        # First call after timeout should work (half-open)
        result = await breaker.call(success_func)
        self.assertEqual(result, "success")
        
        # Second success should close circuit
        result = await breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(breaker.get_state(), CircuitState.CLOSED)
    
    def test_get_stats(self):
        """Test getting circuit breaker statistics."""
        breaker = CircuitBreaker()
        stats = breaker.get_stats()
        
        self.assertIn("state", stats)
        self.assertIn("failure_count", stats)
        self.assertIn("success_count", stats)
        self.assertEqual(stats["state"], CircuitState.CLOSED.value)
    
    def test_get_telegram_circuit_breaker_singleton(self):
        """Test singleton pattern for Telegram circuit breaker."""
        breaker1 = get_telegram_circuit_breaker()
        breaker2 = get_telegram_circuit_breaker()
        self.assertIs(breaker1, breaker2)
    
    def test_get_ai_circuit_breaker_singleton(self):
        """Test singleton pattern for AI circuit breaker."""
        breaker1 = get_ai_circuit_breaker()
        breaker2 = get_ai_circuit_breaker()
        self.assertIs(breaker1, breaker2)


if __name__ == "__main__":
    unittest.main()

