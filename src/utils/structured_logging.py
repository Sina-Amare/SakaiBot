"""
Structured logging for production and Docker environments.

Provides:
- JSON-formatted logs for log aggregation (ELK, Loki, etc.)
- Automatic log rotation (size and time based)
- Docker-native logging (stdout/stderr)
- Sensitive data redaction (API keys, passwords, tokens)
- Correlation ID tracking across requests
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Set

from .security import mask_api_key


class SensitiveDataFilter(logging.Filter):
    """Filter that redacts sensitive data from log messages."""

    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        # API keys (various formats)
        (r'(api[_-]?key["\s:=]+)["\']?([a-zA-Z0-9_-]{20,})["\']?', r'\1***REDACTED***'),
        (r'(AIza[a-zA-Z0-9_-]{35})', r'***GEMINI_KEY***'),
        (r'(sk-[a-zA-Z0-9]{20,})', r'***OPENROUTER_KEY***'),
        # Bearer tokens
        (r'(Bearer\s+)([a-zA-Z0-9_-]{20,})', r'\1***TOKEN***'),
        # Session strings
        (r'(session["\s:=]+)["\']?([a-zA-Z0-9_-]{20,})["\']?', r'\1***SESSION***'),
        # Phone numbers (international format)
        (r'(\+\d{1,3})\d{6,}(\d{2})', r'\1******\2'),
    ]

    def __init__(self):
        super().__init__()
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.SENSITIVE_PATTERNS
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from the log message."""
        if record.msg:
            msg = str(record.msg)
            for pattern, replacement in self._compiled_patterns:
                msg = pattern.sub(replacement, msg)
            record.msg = msg

        # Also check args if present
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self._compiled_patterns:
                        arg = pattern.sub(replacement, arg)
                new_args.append(arg)
            record.args = tuple(new_args)

        return True


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production environments.

    Outputs logs in JSON format for easy parsing by log aggregation tools.
    Automatically redacts sensitive data like API keys.
    """

    SENSITIVE_KEYS: Set[str] = {
        'api_key', 'apikey', 'api-key',
        'password', 'passwd', 'pwd',
        'secret', 'token', 'bearer',
        'session', 'credential', 'auth',
        'phone', 'phone_number'
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._sanitize_message(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        correlation_id = getattr(record, 'correlation_id', None)
        if correlation_id and correlation_id != '-':
            log_data["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields (excluding standard LogRecord attributes)
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'message', 'correlation_id', 'taskName'
        }

        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                # Redact sensitive fields
                if self._is_sensitive_key(key):
                    value = self._redact_value(value)
                log_data[key] = value

        return json.dumps(log_data, default=str, ensure_ascii=False)

    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key name indicates sensitive data."""
        key_lower = key.lower()
        return any(s in key_lower for s in self.SENSITIVE_KEYS)

    def _redact_value(self, value) -> str:
        """Redact a sensitive value."""
        if value is None:
            return None
        str_val = str(value)
        if len(str_val) > 8:
            return f"{str_val[:4]}***{str_val[-4:]}"
        return "***"

    def _sanitize_message(self, message: str) -> str:
        """Sanitize message by masking any API keys."""
        return mask_api_key(message)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter with correlation ID support.

    Used for development and console output.
    """

    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(correlation_id)s | '
                '%(name)s:%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record: logging.LogRecord) -> str:
        # Ensure correlation_id exists
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = '-'
        return super().format(record)


def is_docker_environment() -> bool:
    """Detect if running inside a Docker container."""
    # Check for Docker-specific environment variable
    if os.environ.get('SAKAIBOT_DOCKER', '').lower() in ('1', 'true', 'yes'):
        return True

    # Check for .dockerenv file
    if Path('/.dockerenv').exists():
        return True

    # Check cgroup (Linux containers)
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except (FileNotFoundError, PermissionError):
        pass

    return False


def setup_production_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    json_format: bool = True,
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 7,
    docker_mode: Optional[bool] = None
) -> logging.Logger:
    """
    Setup production-grade logging with rotation and optional JSON format.

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (recommended for production)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        docker_mode: Force Docker mode (auto-detect if None)

    Returns:
        Configured root logger
    """
    # Auto-detect Docker if not specified
    if docker_mode is None:
        docker_mode = is_docker_environment()

    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    # Choose formatter
    if json_format or docker_mode:
        formatter = JSONFormatter()
    else:
        formatter = HumanReadableFormatter()

    if docker_mode:
        # Docker mode: log to stdout (INFO and below) and stderr (ERROR+)
        # This allows Docker's log driver to capture everything

        # Stdout handler for INFO and below
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.addFilter(sensitive_filter)
        stdout_handler.addFilter(lambda r: r.levelno < logging.ERROR)
        root_logger.addHandler(stdout_handler)

        # Stderr handler for ERROR and above
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        stderr_handler.addFilter(sensitive_filter)
        stderr_handler.setLevel(logging.ERROR)
        root_logger.addHandler(stderr_handler)

        # Still write to file for persistence
        file_handler = RotatingFileHandler(
            log_path / "sakaibot.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)

    else:
        # Standard file-based logging with rotation

        # Main log file
        file_handler = RotatingFileHandler(
            log_path / "sakaibot.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)

        # Error-only log file
        error_handler = RotatingFileHandler(
            log_path / "sakaibot.error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.addFilter(sensitive_filter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

        # Console handler (human-readable)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(HumanReadableFormatter())
        console_handler.addFilter(sensitive_filter)
        root_logger.addHandler(console_handler)

    # Configure Windows console encoding
    if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging initialized",
        extra={
            "docker_mode": docker_mode,
            "json_format": json_format,
            "log_level": log_level,
            "log_dir": str(log_path.absolute())
        }
    )

    return root_logger


def get_structured_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for structured logging.

    This is a convenience function that returns a logger with the
    sensitive data filter already applied.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Ensure filter is applied
    if not any(isinstance(f, SensitiveDataFilter) for f in logger.filters):
        logger.addFilter(SensitiveDataFilter())

    return logger
