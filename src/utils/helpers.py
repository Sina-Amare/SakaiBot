"""Helper utilities for SakaiBot."""

import re
import os
from pathlib import Path
from typing import Optional, Union
from datetime import datetime, timedelta


def safe_filename(filename: str, max_length: int = 255) -> str:
    """Convert a string to a safe filename."""
    # Remove invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(' .')
    
    # Truncate if too long
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length]
    
    # Ensure it's not empty
    if not safe_name:
        safe_name = "unnamed"
    
    return safe_name


def format_duration(seconds: Union[int, float]) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists, create if it doesn't."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def clean_temp_files(*file_paths: Union[str, Path], max_attempts: int = 3) -> None:
    """Clean up temporary files with retry logic."""
    for file_path in file_paths:
        if not file_path:
            continue
            
        path = Path(file_path)
        if not path.exists():
            continue
            
        for attempt in range(max_attempts):
            try:
                path.unlink()
                break
            except PermissionError:
                if attempt < max_attempts - 1:
                    import time
                    time.sleep(0.1)
                    continue
                # Log the error but don't raise
                import logging
                logging.getLogger(__name__).warning(
                    f"Could not remove temp file {path} after {max_attempts} attempts"
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Error removing temp file {path}: {e}"
                )
                break


def parse_command_with_params(command_text: str, command_prefix: str) -> tuple[dict[str, str], str]:
    """Parse command text to extract parameters and remaining text."""
    if not command_text.lower().startswith(command_prefix.lower()):
        return {}, command_text
    
    remaining_text = command_text[len(command_prefix):].strip()
    
    # Pattern to match key=value parameters
    param_pattern = re.compile(r"(\w+)=([^\s\"']+|\"[^\"]*\"|'[^']*')\s*")
    params = {}
    
    # Find all parameters at the beginning
    while True:
        match = param_pattern.match(remaining_text)
        if not match:
            break
        
        param_name = match.group(1).lower()
        param_value = match.group(2).strip("\"'")
        params[param_name] = param_value
        
        # Remove the matched parameter from remaining text
        remaining_text = remaining_text[match.end():].strip()
    
    return params, remaining_text
