"""Centralized logging configuration for SakaiBot."""

import logging
import sys
import uuid
import json
from pathlib import Path
from typing import Optional, Dict, Any
from contextvars import ContextVar

from ..core.constants import LOG_FORMAT, MONITOR_LOG_FILE

# Context variable for correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class AutoFlushFileHandler(logging.FileHandler):
    """File handler that automatically flushes after each log record."""
    
    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def setup_logging(
    level: int = logging.INFO,
    log_file: str = MONITOR_LOG_FILE,
    enable_console: bool = False
) -> None:
    """Set up centralized logging configuration."""
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Create file handler with auto-flush
    file_handler = AutoFlushFileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    
    # Optionally add console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root_logger.addHandler(console_handler)
        
        # Configure stdout encoding for Windows
        if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except Exception:
                pass
    
    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a configured logger for a specific module."""
    logger = logging.getLogger(name)
    
    if level is not None:
        logger.setLevel(level)
    
    # Prevent propagation if handlers are already configured
    if logger.handlers:
        logger.propagate = False
    
    # Add correlation ID filter
    if not any(isinstance(f, CorrelationIDFilter) for f in logger.filters):
        logger.addFilter(CorrelationIDFilter())
    
    return logger


class CorrelationIDFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record."""
        correlation_id = _correlation_id.get()
        # Set correlation_id attribute, defaulting to '-' if not set
        record.correlation_id = correlation_id if correlation_id else '-'
        return True


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for current context.
    
    Args:
        correlation_id: Optional correlation ID. If None, generates a new one.
        
    Returns:
        The correlation ID
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    _correlation_id.set(None)


def setup_module_logger(
    module_name: str,
    level: int = logging.INFO,
    log_file: str = MONITOR_LOG_FILE
) -> logging.Logger:
    """Set up a logger for a specific module."""
    logger = logging.getLogger(module_name)
    
    # Configure only if not already configured
    if not logger.handlers:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        formatter = logging.Formatter(LOG_FORMAT)
        
        file_handler = AutoFlushFileHandler(log_file, encoding='utf-8', mode='a')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        
        logger.setLevel(level)
        logger.addHandler(file_handler)
        logger.propagate = False
    
    return logger
