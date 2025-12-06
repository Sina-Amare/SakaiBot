"""Tests for Circuit Breaker.

Tests for the circuit breaker pattern that protects external API calls.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_ai_circuit_breaker,
    get_telegram_circuit_breaker,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,
            expected_exception=Exception
        )

    def test_initial_state_is_closed(self, circuit_breaker):
        """Circuit breaker starts in closed state."""
        assert circuit_breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_passes_through(self, circuit_breaker):
        """Successful calls pass through circuit breaker."""
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failed_calls_increment_counter(self, circuit_breaker):
        """Failed calls increment failure counter."""
        async def failing_func():
            raise Exception("fail")

        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

        stats = circuit_breaker.get_stats()
        assert stats["failure_count"] == 1
        assert stats["state"] == "closed"

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Circuit opens after failure threshold is reached."""
        async def failing_func():
            raise Exception("fail")

        # Fail 3 times (threshold)
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Open circuit rejects calls immediately."""
        async def failing_func():
            raise Exception("fail")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        # Next call should be rejected by circuit
        async def should_not_run():
            return "this should not execute"

        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await circuit_breaker.call(should_not_run)

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """Circuit transitions to half-open after timeout."""
        async def failing_func():
            raise Exception("fail")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Try a call - should transition to half-open first
        async def success_func():
            return "success"

        # The call should succeed and transition state
        result = await circuit_breaker.call(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_half_open_closes_after_successes(self, circuit_breaker):
        """Half-open circuit closes after success threshold."""
        async def failing_func():
            raise Exception("fail")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        # Wait for timeout to transition to half-open
        await asyncio.sleep(1.1)

        # Succeed twice (success_threshold = 2)
        await circuit_breaker.call(success_func)
        await circuit_breaker.call(success_func)

        assert circuit_breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_returns_to_open(self):
        """Half-open failure returns to open state."""
        cb = CircuitBreaker(
            failure_threshold=1,
            success_threshold=2,
            timeout=0.1
        )

        async def failing_func():
            raise Exception("fail")

        # Open the circuit
        with pytest.raises(Exception):
            await cb.call(failing_func)

        assert cb.get_state() == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Fail again - should go back to open
        with pytest.raises(Exception):
            await cb.call(failing_func)

        assert cb.get_state() == CircuitState.OPEN

    def test_get_stats_returns_correct_structure(self, circuit_breaker):
        """get_stats returns expected structure."""
        stats = circuit_breaker.get_stats()

        assert "state" in stats
        assert "failure_count" in stats
        assert "success_count" in stats
        assert "last_failure_time" in stats
        assert "recent_failures" in stats

    @pytest.mark.asyncio
    async def test_sync_function_support(self, circuit_breaker):
        """Circuit breaker works with sync functions."""
        def sync_func():
            return "sync result"

        result = await circuit_breaker.call(sync_func)
        assert result == "sync result"

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, circuit_breaker):
        """Successful call resets failure count in closed state."""
        async def failing_func():
            raise Exception("fail")

        async def success_func():
            return "success"

        # Fail twice (below threshold)
        for _ in range(2):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_func)

        stats = circuit_breaker.get_stats()
        assert stats["failure_count"] == 2

        # Success should reset
        await circuit_breaker.call(success_func)

        stats = circuit_breaker.get_stats()
        assert stats["failure_count"] == 0


class TestGlobalCircuitBreakers:
    """Tests for global circuit breaker instances."""

    def test_telegram_circuit_breaker_singleton(self):
        """get_telegram_circuit_breaker returns singleton."""
        cb1 = get_telegram_circuit_breaker()
        cb2 = get_telegram_circuit_breaker()
        assert cb1 is cb2

    def test_ai_circuit_breaker_singleton(self):
        """get_ai_circuit_breaker returns singleton."""
        cb1 = get_ai_circuit_breaker()
        cb2 = get_ai_circuit_breaker()
        assert cb1 is cb2

    def test_telegram_and_ai_are_separate(self):
        """Telegram and AI circuit breakers are separate instances."""
        telegram_cb = get_telegram_circuit_breaker()
        ai_cb = get_ai_circuit_breaker()
        assert telegram_cb is not ai_cb
