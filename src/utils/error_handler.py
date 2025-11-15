"""Comprehensive error handling with recovery strategies and user-friendly messages."""

from typing import Optional, Callable, Any, TypeVar, Union
from functools import wraps
import asyncio

from ..core.exceptions import (
    SakaiBotError,
    ConfigurationError,
    TelegramError,
    AIProcessorError,
    ValidationError
)
from .logging import get_logger

T = TypeVar('T')
logger = get_logger(__name__)

# Persian error messages for users
ERROR_MESSAGES = {
    ConfigurationError: "⚠️ خطای پیکربندی: لطفاً تنظیمات را بررسی کنید.",
    TelegramError: "⚠️ خطای تلگرام: مشکلی در ارتباط با تلگرام رخ داد. لطفاً دوباره تلاش کنید.",
    AIProcessorError: "⚠️ خطای هوش مصنوعی: مشکلی در پردازش درخواست شما رخ داد. لطفاً دوباره تلاش کنید.",
    ValidationError: "⚠️ خطای اعتبارسنجی: ورودی نامعتبر است. لطفاً دوباره بررسی کنید.",
    Exception: "⚠️ خطای غیرمنتظره: مشکلی رخ داد. لطفاً بعداً دوباره تلاش کنید."
}


class ErrorHandler:
    """Handles errors with recovery strategies and user-friendly messages."""
    
    @staticmethod
    def get_user_message(error: Exception) -> str:
        """
        Get user-friendly Persian error message.
        
        Args:
            error: Exception instance
            
        Returns:
            Persian error message
        """
        error_type = type(error)
        
        # Check for specific error types
        for exc_type, message in ERROR_MESSAGES.items():
            if issubclass(error_type, exc_type):
                # Add details if available
                if hasattr(error, 'details') and error.details:
                    return f"{message}\n\nجزئیات: {error.details}"
                return message
        
        # Default message
        return ERROR_MESSAGES[Exception]
    
    @staticmethod
    def should_retry(error: Exception, attempt: int, max_retries: int) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error: Exception instance
            attempt: Current attempt number
            max_retries: Maximum retry attempts
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= max_retries:
            return False
        
        # Don't retry on configuration or validation errors
        if isinstance(error, (ConfigurationError, ValidationError)):
            return False
        
        # Retry on network/API errors
        if isinstance(error, (TelegramError, AIProcessorError)):
            return True
        
        # Retry on connection errors
        error_str = str(error).lower()
        retryable_keywords = [
            'timeout', 'connection', 'network', 'temporary',
            'rate limit', 'too many requests', 'service unavailable'
        ]
        
        if any(keyword in error_str for keyword in retryable_keywords):
            return True
        
        return False
    
    @staticmethod
    def log_error(error: Exception, context: Optional[str] = None) -> None:
        """
        Log error with context.
        
        Args:
            error: Exception instance
            context: Additional context string
        """
        context_str = f" [{context}]" if context else ""
        logger.error(
            f"Error{context_str}: {type(error).__name__}: {error}",
            exc_info=True
        )


def handle_errors(
    default_return: Any = None,
    log_error: bool = True,
    reraise: bool = False
) -> Callable:
    """
    Decorator for error handling with recovery.
    
    Args:
        default_return: Value to return on error (if not reraise)
        log_error: Whether to log the error
        reraise: Whether to re-raise the exception
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except SakaiBotError as e:
                if log_error:
                    ErrorHandler.log_error(e, context=func.__name__)
                if reraise:
                    raise
                return default_return
            except Exception as e:
                if log_error:
                    ErrorHandler.log_error(e, context=func.__name__)
                if reraise:
                    raise
                return default_return
        
        return wrapper
    return decorator


async def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default_return: Any = None,
    max_retries: int = 0,
    retry_delay: float = 1.0,
    **kwargs: Any
) -> T:
    """
    Safely execute a function with error handling and optional retries.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        default_return: Value to return on error
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        **kwargs: Keyword arguments
        
    Returns:
        Function result or default_return on error
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries and ErrorHandler.should_retry(e, attempt, max_retries):
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                ErrorHandler.log_error(e, context=func.__name__)
                break
    
    return default_return

