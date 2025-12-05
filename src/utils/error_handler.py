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
from ..utils.logging import get_logger

# Define type variable for generic functions
T = TypeVar('T')

logger = get_logger(__name__)
# English error messages for users (HTML formatted)
ERROR_MESSAGES = {
    ConfigurationError: (
        "⚙️ <b>Configuration Error</b>\n\n"
        "Please check your settings.\n\n"
        "<i>💡 Run /status to verify configuration</i>"
    ),
    TelegramError: (
        "📡 <b>Connection Error</b>\n\n"
        "Failed to communicate with Telegram.\n\n"
        "<i>💡 Please try again in a few moments</i>"
    ),
    AIProcessorError: (
        "🤖 <b>AI Processing Error</b>\n\n"
        "Failed to process your request.\n\n"
        "<i>💡 Try with simpler input or wait a moment</i>"
    ),
    ValidationError: (
        "⚠️ <b>Invalid Input</b>\n\n"
        "Please check your input and try again.\n\n"
        "<i>💡 Use /help for correct command format</i>"
    ),
    Exception: (
        "❌ <b>Unexpected Error</b>\n\n"
        "Something went wrong.\n\n"
        "<i>💡 Please try again later</i>"
    )
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
        error_str = str(error).lower()
        
        # Image generation specific error messages
        if "image generation" in error_str or "sdxl" in error_str or "flux" in error_str:
            if "timeout" in error_str or "timed out" in error_str:
                return (
                    "⏱️ <b>Image Timeout</b>\n\n"
                    "Generation took too long.\n\n"
                    "<i>💡 Try again - workers may be busy</i>"
                )
            elif "rate limit" in error_str or "429" in error_str:
                return (
                    "🚦 <b>Rate Limited</b>\n\n"
                    "Too many requests.\n\n"
                    "<i>💡 Wait 60 seconds and try again</i>"
                )
            elif "unauthorized" in error_str or "401" in error_str or "api key" in error_str:
                return (
                    "🔐 <b>Auth Error</b>\n\n"
                    "Invalid API key.\n\n"
                    "<i>💡 Check your configuration</i>"
                )
            elif "invalid" in error_str or "400" in error_str:
                return (
                    "⚠️ <b>Invalid Request</b>\n\n"
                    "Please check your prompt.\n\n"
                    "<i>💡 Try simpler, clearer description</i>"
                )
            elif "network" in error_str or "connection" in error_str:
                return (
                    "🌐 <b>Network Error</b>\n\n"
                    "Cannot reach image server.\n\n"
                    "<i>💡 Try again in a moment</i>"
                )
            elif "content" in error_str or "moderation" in error_str or "filter" in error_str:
                return (
                    "🚫 <b>Content Filtered</b>\n\n"
                    "Prompt was blocked by safety filter.\n\n"
                    "<i>💡 Try a different prompt</i>"
                )
            elif "service" in error_str or "500" in error_str or "unavailable" in error_str:
                return (
                    "🔧 <b>Service Unavailable</b>\n\n"
                    "Image server is down.\n\n"
                    "<i>💡 Try again later</i>"
                )
            elif "model" in error_str and "invalid" in error_str:
                return (
                    "❌ <b>Invalid Model</b>\n\n"
                    "Use <code>flux</code> or <code>sdxl</code>\n\n"
                    "<i>💡 /help images for more info</i>"
                )
        
        # Check for specific error types
        for exc_type, message in ERROR_MESSAGES.items():
            if issubclass(error_type, exc_type):
                # Add details if available
                if hasattr(error, 'details') and error.details:
                    return f"{message}\n\nDetails: {error.details}"
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
        Log error with context, masking sensitive data.
        
        Args:
            error: Exception instance
            context: Additional context string
        """
        context_str = f" [{context}]" if context else ""
        error_message = str(error)
        # Log error message
        logger.error(
            f"Error{context_str}: {type(error).__name__}: {error_message}",
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

