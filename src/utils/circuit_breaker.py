"""Circuit breaker pattern for external API calls."""

import asyncio
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from collections import deque

from .logging import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for protecting external API calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures to open circuit
            success_threshold: Number of successes to close circuit (half-open -> closed)
            timeout: Time in seconds before attempting to close circuit
            expected_exception: Exception type to catch
        """
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout = timeout
        self._expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._failure_history = deque(maxlen=100)  # Keep last 100 failures
        
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        async with self._lock:
            # Check if circuit should transition
            await self._check_state_transition()
            
            # If circuit is open, reject immediately
            if self._state == CircuitState.OPEN:
                raise Exception(
                    f"Circuit breaker is OPEN. Service unavailable. "
                    f"Last failure: {self._last_failure_time}"
                )
        
        # Execute function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - update state
            async with self._lock:
                await self._on_success()
            
            return result
        
        except self._expected_exception as e:
            # Failure - update state
            async with self._lock:
                await self._on_failure(e)
            raise
    
    async def _check_state_transition(self) -> None:
        """Check and perform state transitions."""
        now = datetime.utcnow()
        
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time and \
               (now - self._last_failure_time).total_seconds() >= self._timeout:
                logger.info("Circuit breaker transitioning from OPEN to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
    
    async def _on_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._success_threshold:
                logger.info("Circuit breaker transitioning from HALF_OPEN to CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    async def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        self._failure_history.append({
            'time': self._last_failure_time,
            'error': str(error)
        })
        
        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            logger.warning("Circuit breaker transitioning from HALF_OPEN to OPEN")
            self._state = CircuitState.OPEN
            self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Check if threshold reached
            if self._failure_count >= self._failure_threshold:
                logger.warning(
                    f"Circuit breaker transitioning from CLOSED to OPEN "
                    f"({self._failure_count} failures)"
                )
                self._state = CircuitState.OPEN
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            'state': self._state.value,
            'failure_count': self._failure_count,
            'success_count': self._success_count,
            'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None,
            'recent_failures': len(self._failure_history)
        }


# Global circuit breakers for different services
_telegram_circuit_breaker: Optional[CircuitBreaker] = None
_ai_circuit_breaker: Optional[CircuitBreaker] = None


def get_telegram_circuit_breaker() -> CircuitBreaker:
    """Get global Telegram API circuit breaker."""
    global _telegram_circuit_breaker
    if _telegram_circuit_breaker is None:
        _telegram_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=60.0,
            expected_exception=Exception
        )
    return _telegram_circuit_breaker


def get_ai_circuit_breaker() -> CircuitBreaker:
    """Get global AI API circuit breaker."""
    global _ai_circuit_breaker
    if _ai_circuit_breaker is None:
        _ai_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=60.0,
            expected_exception=Exception
        )
    return _ai_circuit_breaker

