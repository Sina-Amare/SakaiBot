"""
Centralized logging configuration for SakaiBot.

This module provides a clean, configurable logging setup with support for
file rotation, structured logging, and proper log levels.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from queue import Queue
from typing import Optional, Dict, Any
import json
from datetime import datetime

from src.core.constants import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_MAX_FILE_SIZE,
    LOG_BACKUP_COUNT,
    LOG_ENCODING,
    LogLevel,
    DEFAULT_LOGS_DIR
)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs for production
    and human-readable format for development.
    """
    
    def __init__(self, json_format: bool = False):
        """
        Initialize the formatter.
        
        Args:
            json_format: If True, output JSON formatted logs
        """
        super().__init__(LOG_FORMAT, LOG_DATE_FORMAT)
        self.json_format = json_format
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log string
        """
        if self.json_format:
            log_obj = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            
            # Add extra fields if present
            for key, value in record.__dict__.items():
                if key not in ["name", "msg", "args", "created", "filename", 
                              "funcName", "levelname", "levelno", "lineno",
                              "module", "msecs", "message", "pathname", "process",
                              "processName", "relativeCreated", "thread", "threadName",
                              "exc_info", "exc_text", "stack_info"]:
                    log_obj[key] = value
            
            return json.dumps(log_obj, ensure_ascii=False)
        else:
            return super().format(record)


class LoggerManager:
    """Manages application-wide logging configuration."""
    
    _instance: Optional["LoggerManager"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "LoggerManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logger manager."""
        if not self._initialized:
            self.loggers: Dict[str, logging.Logger] = {}
            self.handlers: Dict[str, logging.Handler] = {}
            self.queue: Optional[Queue] = None
            self.queue_listener: Optional[QueueListener] = None
            self._initialized = True
    
    def setup(
        self,
        log_level: str = "INFO",
        log_dir: Optional[Path] = None,
        json_format: bool = False,
        enable_console: bool = True,
        enable_file: bool = True,
        async_logging: bool = True
    ) -> None:
        """
        Set up the logging configuration.
        
        Args:
            log_level: Default logging level
            log_dir: Directory for log files
            json_format: Use JSON formatted logs
            enable_console: Enable console output
            enable_file: Enable file output
            async_logging: Use async logging with queue
        """
        # Convert string level to logging constant
        level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Set up log directory
        if log_dir is None:
            log_dir = Path(DEFAULT_LOGS_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        console_formatter = StructuredFormatter(json_format=False)
        file_formatter = StructuredFormatter(json_format=json_format)
        
        # Set up handlers
        handlers = []
        
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(level)
            handlers.append(console_handler)
            self.handlers["console"] = console_handler
        
        if enable_file:
            log_file = log_dir / "sakaibot.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=LOG_MAX_FILE_SIZE,
                backupCount=LOG_BACKUP_COUNT,
                encoding=LOG_ENCODING
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(level)
            handlers.append(file_handler)
            self.handlers["file"] = file_handler
            
            # Add separate error log
            error_log_file = log_dir / "errors.log"
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=LOG_MAX_FILE_SIZE,
                backupCount=LOG_BACKUP_COUNT,
                encoding=LOG_ENCODING
            )
            error_handler.setFormatter(file_formatter)
            error_handler.setLevel(logging.ERROR)
            handlers.append(error_handler)
            self.handlers["error"] = error_handler
        
        # Set up async logging if enabled
        if async_logging and handlers:
            self.queue = Queue(-1)  # Unlimited queue size
            queue_handler = QueueHandler(self.queue)
            self.queue_listener = QueueListener(self.queue, *handlers, respect_handler_level=True)
            self.queue_listener.start()
            
            # Replace handlers with queue handler
            handlers = [queue_handler]
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()
        for handler in handlers:
            root_logger.addHandler(handler)
        
        # Suppress noisy third-party loggers
        logging.getLogger("telethon").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger with the given name.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]
    
    def set_level(self, logger_name: str, level: str) -> None:
        """
        Set the logging level for a specific logger.
        
        Args:
            logger_name: Name of the logger
            level: Logging level as string
        """
        logger = self.get_logger(logger_name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    def add_context(self, **kwargs) -> Dict[str, Any]:
        """
        Add context to log messages using LoggerAdapter.
        
        Args:
            **kwargs: Context key-value pairs
            
        Returns:
            Context dictionary
        """
        return kwargs
    
    def shutdown(self) -> None:
        """Properly shutdown logging, especially async queue listener."""
        if self.queue_listener:
            self.queue_listener.stop()
            self.queue_listener = None
        
        # Flush and close all handlers
        for handler in self.handlers.values():
            handler.flush()
            handler.close()
        
        # Clear handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        self.handlers.clear()
        self.loggers.clear()


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter for adding context to log messages.
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process the log message and kwargs.
        
        Args:
            msg: Log message
            kwargs: Keyword arguments
            
        Returns:
            Processed message and kwargs
        """
        # Add extra context to the log record
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


# Singleton instance
_logger_manager = LoggerManager()


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    json_format: bool = False,
    enable_console: bool = True,
    enable_file: bool = True,
    async_logging: bool = True
) -> None:
    """
    Set up application logging.
    
    Args:
        log_level: Default logging level
        log_dir: Directory for log files
        json_format: Use JSON formatted logs
        enable_console: Enable console output
        enable_file: Enable file output
        async_logging: Use async logging with queue
    """
    _logger_manager.setup(
        log_level=log_level,
        log_dir=log_dir,
        json_format=json_format,
        enable_console=enable_console,
        enable_file=enable_file,
        async_logging=async_logging
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return _logger_manager.get_logger(name)


def get_logger_with_context(name: str, **context) -> LoggerAdapter:
    """
    Get a logger with additional context.
    
    Args:
        name: Logger name
        **context: Context key-value pairs
        
    Returns:
        Logger adapter with context
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)


def shutdown_logging() -> None:
    """Properly shutdown the logging system."""
    _logger_manager.shutdown()


# Convenience functions for module-level logging
def log_debug(message: str, **kwargs) -> None:
    """Log a debug message."""
    get_logger("sakaibot").debug(message, **kwargs)


def log_info(message: str, **kwargs) -> None:
    """Log an info message."""
    get_logger("sakaibot").info(message, **kwargs)


def log_warning(message: str, **kwargs) -> None:
    """Log a warning message."""
    get_logger("sakaibot").warning(message, **kwargs)


def log_error(message: str, exc_info: bool = False, **kwargs) -> None:
    """Log an error message."""
    get_logger("sakaibot").error(message, exc_info=exc_info, **kwargs)


def log_critical(message: str, exc_info: bool = False, **kwargs) -> None:
    """Log a critical message."""
    get_logger("sakaibot").critical(message, exc_info=exc_info, **kwargs)