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


def split_message(text: str, max_length: int = 4096, reserve_length: int = 0) -> list[str]:
    """Split long text into chunks that fit within max_length.
    
    Intelligently splits at sentence/paragraph boundaries when possible.
    Falls back to word boundaries, then character boundaries if needed.
    
    Args:
        text: The text to split
        max_length: Maximum length for each chunk (default: 4096 for Telegram)
        reserve_length: Additional bytes to reserve (e.g., for prefixes/suffixes)
    
    Returns:
        List of text chunks, each within max_length
    """
    if not text:
        return [""]
    
    # Calculate actual max length per chunk
    actual_max = max_length - reserve_length
    if actual_max <= 0:
        actual_max = max_length
    
    # If text fits in one message, return as is
    if len(text) <= actual_max:
        return [text]
    
    chunks = []
    remaining = text
    
    while len(remaining) > actual_max:
        # Try to split at paragraph boundary first (double newline)
        if '\n\n' in remaining[:actual_max + 100]:  # Look ahead a bit
            # Find the last paragraph break within limit
            para_split = remaining.rfind('\n\n', 0, actual_max)
            if para_split > actual_max * 0.5:  # Only use if not too small
                chunks.append(remaining[:para_split].strip())
                remaining = remaining[para_split + 2:].strip()
                continue
        
        # Try to split at sentence boundary (., !, ?, ؟, !)
        sentence_enders = ['. ', '! ', '? ', '؟ ', '!\n', '?\n', '.\n', '؟\n']
        best_split = -1
        
        for ender in sentence_enders:
            # Look for sentence endings within the limit
            pos = remaining.rfind(ender, 0, actual_max + 50)
            if pos > best_split and pos > actual_max * 0.5:
                best_split = pos + len(ender) - 1  # Include the space/newline
        
        if best_split > 0:
            chunks.append(remaining[:best_split].strip())
            remaining = remaining[best_split:].strip()
            continue
        
        # Try to split at word boundary
        last_space = remaining.rfind(' ', 0, actual_max)
        if last_space > actual_max * 0.5:  # Only use if not too small
            chunks.append(remaining[:last_space].strip())
            remaining = remaining[last_space + 1:].strip()
            continue
        
        # Fallback: split at character boundary (avoid breaking in middle if possible)
        # Try to find a safe break point near the limit
        split_pos = actual_max
        # Look for any whitespace near the boundary
        for i in range(actual_max - 100, actual_max):
            if i < len(remaining) and remaining[i] in (' ', '\n', '\t'):
                split_pos = i + 1
                break
        
        chunks.append(remaining[:split_pos].strip())
        remaining = remaining[split_pos:].strip()
    
    # Add remaining text if any
    if remaining:
        chunks.append(remaining)
    
    return chunks if chunks else [text]