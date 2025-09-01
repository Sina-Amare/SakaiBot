"""
Custom exception hierarchy for SakaiBot.

This module defines all custom exceptions used throughout the application,
providing a clear hierarchy for error handling and debugging.
"""

from typing import Optional, Any, Dict


class SakaiBotError(Exception):
    """Base exception for all SakaiBot errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize SakaiBot exception.
        
        Args:
            message: Error message
            error_code: Optional error code for identification
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.error_code}: {self.message} | Details: {self.details}"
        return f"{self.error_code}: {self.message}"


# Configuration Errors
class ConfigurationError(SakaiBotError):
    """Raised when there's a configuration issue."""
    pass


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing."""
    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration values are invalid."""
    pass


# Telegram Related Errors
class TelegramError(SakaiBotError):
    """Base exception for Telegram-related errors."""
    pass


class AuthenticationError(TelegramError):
    """Raised when Telegram authentication fails."""
    pass


class SessionError(TelegramError):
    """Raised when there's an issue with the Telegram session."""
    pass


class MessageError(TelegramError):
    """Raised when there's an issue with message handling."""
    pass


class PermissionError(TelegramError):
    """Raised when user lacks required permissions."""
    pass


# AI/LLM Related Errors
class AIError(SakaiBotError):
    """Base exception for AI/LLM-related errors."""
    pass


class APIError(AIError):
    """Raised when API calls fail."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_body: Response body from the API
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body
        if status_code:
            self.details["status_code"] = status_code
        if response_body:
            self.details["response_body"] = response_body


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after"] = retry_after


class ModelError(AIError):
    """Raised when there's an issue with the AI model."""
    pass


class TokenLimitError(AIError):
    """Raised when token limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        tokens_used: Optional[int] = None,
        token_limit: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize token limit error.
        
        Args:
            message: Error message
            tokens_used: Number of tokens used
            token_limit: Maximum token limit
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.tokens_used = tokens_used
        self.token_limit = token_limit
        if tokens_used:
            self.details["tokens_used"] = tokens_used
        if token_limit:
            self.details["token_limit"] = token_limit


# Audio Processing Errors
class AudioError(SakaiBotError):
    """Base exception for audio processing errors."""
    pass


class STTError(AudioError):
    """Raised when Speech-to-Text fails."""
    pass


class TTSError(AudioError):
    """Raised when Text-to-Speech fails."""
    pass


class FFmpegError(AudioError):
    """Raised when FFmpeg operations fail."""
    pass


# Cache Related Errors
class CacheError(SakaiBotError):
    """Base exception for cache-related errors."""
    pass


class CacheReadError(CacheError):
    """Raised when reading from cache fails."""
    pass


class CacheWriteError(CacheError):
    """Raised when writing to cache fails."""
    pass


# CLI Related Errors
class CLIError(SakaiBotError):
    """Base exception for CLI-related errors."""
    pass


class InputError(CLIError):
    """Raised when user input is invalid."""
    pass


class MenuError(CLIError):
    """Raised when there's an issue with menu operations."""
    pass


# File System Errors
class FileSystemError(SakaiBotError):
    """Base exception for file system errors."""
    pass


class FileNotFoundError(FileSystemError):
    """Raised when a required file is not found."""
    pass


class FileAccessError(FileSystemError):
    """Raised when file access is denied."""
    pass


# Validation Errors
class ValidationError(SakaiBotError):
    """Base exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Value that failed validation
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = str(value)


class InputValidationError(ValidationError):
    """Raised when input validation fails."""
    pass


class CommandValidationError(ValidationError):
    """Raised when command validation fails."""
    pass


# Network Errors
class NetworkError(SakaiBotError):
    """Base exception for network-related errors."""
    pass


class ConnectionError(NetworkError):
    """Raised when network connection fails."""
    pass


class TimeoutError(NetworkError):
    """Raised when operations timeout."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            self.details["timeout_seconds"] = timeout_seconds


# Retry Errors
class RetryError(SakaiBotError):
    """Raised when retry attempts are exhausted."""
    
    def __init__(
        self,
        message: str,
        attempts: Optional[int] = None,
        max_attempts: Optional[int] = None,
        last_error: Optional[Exception] = None,
        **kwargs
    ):
        """
        Initialize retry error.
        
        Args:
            message: Error message
            attempts: Number of attempts made
            max_attempts: Maximum attempts allowed
            last_error: The last error that occurred
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.attempts = attempts
        self.max_attempts = max_attempts
        self.last_error = last_error
        if attempts:
            self.details["attempts"] = attempts
        if max_attempts:
            self.details["max_attempts"] = max_attempts
        if last_error:
            self.details["last_error"] = str(last_error)