"""Input validation and sanitization utilities."""

import re
from typing import Optional, Set

from .logging import get_logger
from ..core.constants import SUPPORTED_IMAGE_MODELS, MAX_IMAGE_PROMPT_LENGTH

logger = get_logger(__name__)

# Common language codes (ISO 639-1)
VALID_LANGUAGE_CODES: Set[str] = {
    'fa', 'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar',
    'hi', 'tr', 'pl', 'nl', 'sv', 'da', 'fi', 'no', 'cs', 'hu', 'ro', 'bg',
    'hr', 'sk', 'sl', 'et', 'lv', 'lt', 'el', 'he', 'th', 'vi', 'id', 'ms',
    'tl', 'uk', 'be', 'mk', 'sr', 'sq', 'is', 'ga', 'mt', 'cy'
}

# Maximum lengths
MAX_PROMPT_LENGTH = 10000
MAX_COMMAND_LENGTH = 5000


class InputValidator:
    """Validates and sanitizes user inputs."""
    
    @staticmethod
    def validate_prompt(text: str, max_length: int = MAX_PROMPT_LENGTH) -> str:
        """
        Validate and sanitize prompt text.
        
        Args:
            text: Input text to validate
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValueError: If text is invalid
        """
        if not text or not isinstance(text, str):
            raise ValueError("Prompt text is required and must be a string")
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Limit length
        if len(sanitized) > max_length:
            raise ValueError(f"Prompt too long (max {max_length} characters, got {len(sanitized)})")
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        if not sanitized:
            raise ValueError("Prompt cannot be empty after sanitization")
        
        return sanitized
    
    @staticmethod
    def validate_language_code(code: str) -> bool:
        """
        Validate language code.
        
        Args:
            code: Language code to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not code or not isinstance(code, str):
            return False
        
        # Normalize to lowercase
        code = code.lower().strip()
        
        # Check if it's a valid language code
        return code in VALID_LANGUAGE_CODES
    
    @staticmethod
    def sanitize_command_input(text: str) -> str:
        """
        Sanitize command input to prevent injection attacks.
        
        Args:
            text: Command input text
            
        Returns:
            Sanitized text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>',  # Script tags
            r'javascript:',     # JavaScript protocol
            r'on\w+\s*=',       # Event handlers
            r'\$\(',            # Command substitution
            r'`[^`]*`',         # Backticks (command execution)
            r'\$\{[^}]*\}',     # Variable substitution
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Limit length
        if len(sanitized) > MAX_COMMAND_LENGTH:
            sanitized = sanitized[:MAX_COMMAND_LENGTH]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_command_args(args: str) -> Optional[str]:
        """
        Validate command arguments.
        
        Args:
            args: Command arguments string
            
        Returns:
            Sanitized arguments or None if invalid
        """
        if not args:
            return None
        
        # Check for injection attempts
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'on\w+\s*=',
            r'\$\(',
            r'`[^`]*`',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, args, re.IGNORECASE):
                logger.warning(f"Potentially dangerous pattern detected in command args: {pattern}")
                return None
        
        # Sanitize and return
        return InputValidator.sanitize_command_input(args)
    
    @staticmethod
    def validate_file_path(path: str) -> bool:
        """
        Validate file paths to prevent directory traversal.
        
        Args:
            path: File path to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not path or not isinstance(path, str):
            return False
        
        # Check for directory traversal attempts
        if '..' in path or path.startswith('/'):
            return False
        
        # Check for suspicious patterns
        if re.search(r'[;&|`$]', path):
            return False
        
        # Check for absolute paths on Windows
        if re.match(r'^[A-Za-z]:\\', path):
            return False
        
        return True
    
    @staticmethod
    def validate_number(value: str, min_val: int = 1, max_val: int = 10000) -> Optional[int]:
        """
        Validate and parse a number string.
        
        Args:
            value: String value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Parsed integer or None if invalid
        """
        if not value or not isinstance(value, str):
            return None
        
        try:
            num = int(value.strip())
            if min_val <= num <= max_val:
                return num
            return None
        except ValueError:
            return None
    
    @staticmethod
    def validate_image_model(model: str) -> bool:
        """
        Validate image generation model name.
        
        Args:
            model: Model name to validate (e.g., "flux", "sdxl")
            
        Returns:
            True if valid, False otherwise
        """
        if not model or not isinstance(model, str):
            return False
        
        # Normalize to lowercase
        model = model.lower().strip()
        
        # Check if it's a supported model
        return model in SUPPORTED_IMAGE_MODELS
    
    @staticmethod
    def validate_image_prompt(prompt: str) -> str:
        """
        Validate and sanitize image generation prompt.
        
        Args:
            prompt: Prompt text to validate
            
        Returns:
            Sanitized prompt
            
        Raises:
            ValueError: If prompt is invalid
        """
        if not prompt or not isinstance(prompt, str):
            raise ValueError("Image prompt is required and must be a string")
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', prompt)
        
        # Limit length
        if len(sanitized) > MAX_IMAGE_PROMPT_LENGTH:
            raise ValueError(
                f"Image prompt too long (max {MAX_IMAGE_PROMPT_LENGTH} characters, got {len(sanitized)})"
            )
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        if not sanitized:
            raise ValueError("Image prompt cannot be empty after sanitization")
        
        # Basic content filtering - check for obviously harmful content
        # This is a simple check; more sophisticated filtering can be added
        harmful_patterns = [
            r'\b(kill|murder|violence|hate|attack)\b',  # Basic harmful keywords
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"Potentially harmful content detected in image prompt: {pattern}")
                # Don't block, just log - let the worker handle moderation
        
        return sanitized

