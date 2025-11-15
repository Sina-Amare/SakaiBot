"""Security utilities for masking sensitive data."""

import re
from typing import Optional


def mask_api_key(api_key: Optional[str], visible_chars: int = 4) -> str:
    """
    Mask an API key, showing only the first and last few characters.
    
    Args:
        api_key: API key to mask
        visible_chars: Number of characters to show at start and end
        
    Returns:
        Masked API key string
    """
    if not api_key:
        return "None"
    
    if len(api_key) <= visible_chars * 2:
        # Too short to mask meaningfully
        return "*" * len(api_key)
    
    start = api_key[:visible_chars]
    end = api_key[-visible_chars:]
    masked = "*" * (len(api_key) - visible_chars * 2)
    
    return f"{start}{masked}{end}"


def mask_sensitive_data(text: str) -> str:
    """
    Mask sensitive data in text (API keys, tokens, etc.).
    
    Args:
        text: Text that may contain sensitive data
        
    Returns:
        Text with sensitive data masked
    """
    # Pattern for API keys (common formats)
    patterns = [
        (r'sk-[a-zA-Z0-9]{20,}', 'sk-****'),  # OpenAI-style keys
        (r'AIza[a-zA-Z0-9_-]{35}', 'AIza****'),  # Google API keys
        (r'[a-zA-Z0-9_-]{32,}', lambda m: mask_api_key(m.group(0))),  # Generic long tokens
    ]
    
    masked_text = text
    for pattern, replacement in patterns:
        if callable(replacement):
            masked_text = re.sub(pattern, replacement, masked_text)
        else:
            masked_text = re.sub(pattern, replacement, masked_text)
    
    return masked_text


def sanitize_log_message(message: str) -> str:
    """
    Sanitize log message to remove sensitive data.
    
    Args:
        message: Log message
        
    Returns:
        Sanitized log message
    """
    return mask_sensitive_data(message)

