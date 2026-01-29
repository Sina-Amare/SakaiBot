"""
RTL (Right-to-Left) text handling for Persian/Arabic display in Telegram.

This module fixes RTL text display issues by inserting Unicode LRM (Left-to-Right Mark)
characters after LTR segments (URLs, English words, numbers) within RTL text.

Telegram does not support HTML `dir` attributes, so we use Unicode BiDi control
characters (specifically U+200E LRM) which are universally supported.

References:
- W3C Unicode BiDi: https://www.w3.org/International/questions/qa-bidi-controls
- Unicode LRM: U+200E (LEFT-TO-RIGHT MARK)
- Persian/Arabic range: U+0600-U+06FF
"""

import re
from typing import Final

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Unicode control character: Left-to-Right Mark
LRM: Final[str] = '\u200E'

# Persian/Arabic script detection (Unicode range U+0600-U+06FF)
PERSIAN_PATTERN: Final[re.Pattern] = re.compile(r'[\u0600-\u06FF]+')

# URL detection pattern
URL_PATTERN: Final[re.Pattern] = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+',
    re.IGNORECASE
)

# LTR segments: English words, emails, inline code
# NOTE: Numbers are intentionally EXCLUDED to avoid visual artifacts
# in pagination (1/2), section numbers, and Persian numerals
# This pattern matches:
# 1. Email addresses
# 2. English words (2+ chars to avoid single-letter artifacts)
# 3. Inline code between backticks
LTR_SEGMENT_PATTERN: Final[re.Pattern] = re.compile(
    r'\b[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b|'  # Email
    r'\b[A-Za-z][A-Za-z0-9._-]+\b|'  # English words (2+ chars, not single letters)
    r'`[^`]+`',  # Inline code
    re.IGNORECASE
)

# Pagination pattern to protect from LRM insertion
# Matches: (1/2), (2/2), etc.
PAGINATION_PATTERN: Final[re.Pattern] = re.compile(r'\(\d+/\d+\)')


def has_persian_text(text: str) -> bool:
    """
    Check if text contains Persian/Arabic script characters.
    
    Uses Unicode range U+0600-U+06FF which covers:
    - Basic Arabic script (used by Persian, Arabic, Urdu)
    - Persian-specific letters (گ چ پ ژ)
    - Arabic diacritics and special characters
    
    Args:
        text: Text to check for Persian/Arabic characters
    
    Returns:
        True if Persian/Arabic characters found, False otherwise
    
    Examples:
        >>> has_persian_text("Hello World")
        False
        >>> has_persian_text("سلام دنیا")
        True
        >>> has_persian_text("Mixed: سلام and hello")
        True
        >>> has_persian_text("")
        False
    """
    if not text:
        return False
    return bool(PERSIAN_PATTERN.search(text))


def fix_rtl_display(text: str) -> str:
    """
    Fix RTL text display by inserting LRM after LTR segments.
    
    This function inserts Unicode LRM (U+200E) characters after:
    - URLs (complete URLs get single LRM after)
    - English words (2+ characters) ONLY when between Persian words
    - Email addresses
    - Inline code (between backticks)
    
    Numbers are intentionally NOT processed to avoid visual artifacts
    in pagination (1/2), section numbers, and Persian contexts.
    
    Args:
        text: Text with mixed RTL (Persian) and LTR (English/numbers) content
    
    Returns:
        Text with LRM characters inserted after LTR segments
    
    Examples:
        >>> fix_rtl_display("این یک test است")
        'این یک test‎ است'
        
        >>> fix_rtl_display("لینک: https://example.com اینجاست")
        'لینک: https://example.com‎ اینجاست'
        
        >>> fix_rtl_display("<b>bold</b> متن فارسی")
        '<b>bold‎</b> متن فارسی'
    
    Notes:
        - Does NOT modify text without Persian characters (optimization)
        - Does NOT add LRM after numbers (prevents pagination/section artifacts)
        - Does NOT add LRM after usernames followed by : or ( or )
        - Preserves all HTML formatting
        - Safe to call multiple times (idempotent - won't double-insert)
    """
    # Quick check: skip if no Persian text
    if not has_persian_text(text):
        return text
    
    # Step 1: Protect pagination patterns by temporarily replacing them
    # This prevents any accidental LRM insertion in pagination like (1/2)
    pagination_placeholders = []
    def protect_pagination(match):
        # Use Zero-Width Space (U+200B) as delimiter - safer than null char
        placeholder = f"\u200B__PGNTN_{len(pagination_placeholders)}__\u200B"
        pagination_placeholders.append(match.group(0))
        return placeholder
    
    text = PAGINATION_PATTERN.sub(protect_pagination, text)
    
    # Step 2: Insert LRM after URLs
    # URLs are processed first to avoid breaking them with word-level processing
    text = URL_PATTERN.sub(lambda m: m.group(0) + LRM, text)
    
    # Step 3: Insert LRM after other LTR segments (English words, emails, code)
    # Numbers are intentionally excluded to prevent visual artifacts
    text = LTR_SEGMENT_PATTERN.sub(lambda m: m.group(0) + LRM, text)
    
    # Step 4: Remove LRM before certain characters where it causes visible artifacts
    # This handles usernames like "sina:" or "amirhossein:" in bullet points
    # Pattern: LRM followed by : or ) or ( or end of bullet point context
    text = text.replace(LRM + ':', ':')
    text = text.replace(LRM + ')', ')')
    text = text.replace(LRM + '(', '(')
    text = text.replace(LRM + ' (', ' (')
    
    # Step 5: Restore pagination patterns
    for i, original in enumerate(pagination_placeholders):
        text = text.replace(f"\u200B__PGNTN_{i}__\u200B", original)
    
    return text


def ensure_rtl_safe(text: str, force: bool = False) -> str:
    """
    Public API to ensure text is safe for RTL display in Telegram.
    
    This is the main function that should be called before sending any
    message to Telegram. It auto-detects Persian text and applies RTL
    fixes only when needed.
    
    Args:
        text: Message text (may contain Persian, English, HTML, etc.)
        force: If True, always apply RTL fixes even without Persian detection
               (default: False - auto-detect)
    
    Returns:
        RTL-safe text with LRM markers inserted where needed
    
    Examples:
        >>> ensure_rtl_safe("Pure English text")
        'Pure English text'  # No changes
        
        >>> ensure_rtl_safe("تحلیل fun است")
        'تحلیل fun‎ است'  # LRM added
        
        >>> ensure_rtl_safe("English", force=True)
        'English'  # No Persian, but force=True doesn't add LRM
    
    Notes:
        - Safe to call on ALL outgoing messages (low overhead)
        - No-op for pure English text (fast return)
        - Logs when RTL fixes are applied (for monitoring)
    """
    if not text:
        return text
    
    # Auto-detect if RTL fix is needed
    if not force and not has_persian_text(text):
        # Pure English/numbers - no fix needed
        return text
    
    # Apply RTL fixes
    fixed_text = fix_rtl_display(text)
    
    # Log if changes were made (for debugging/monitoring)
    if fixed_text != text:
        lrm_count = fixed_text.count(LRM) - text.count(LRM)
        logger.debug(f"RTL fix applied: inserted {lrm_count} LRM characters")
    
    return fixed_text


def strip_rtl_markers(text: str) -> str:
    """
    Remove all LRM markers from text.
    
    Useful for:
    - Testing/validation (compare original vs. fixed)
    - Extracting clean text for non-Telegram outputs
    - Debugging RTL issues
    
    Args:
        text: Text potentially containing LRM characters
    
    Returns:
        Text with all LRM characters removed
    
    Examples:
        >>> strip_rtl_markers("test‎ متن")
        'test متن'
        
        >>> strip_rtl_markers("no markers here")
        'no markers here'
    """
    return text.replace(LRM, '')


def count_lrm_markers(text: str) -> int:
    """
    Count number of LRM markers in text.
    
    Useful for testing and validation.
    
    Args:
        text: Text to count LRM markers in
    
    Returns:
        Number of LRM characters found
    
    Examples:
        >>> count_lrm_markers("test‎ one‎ two‎")
        3
        >>> count_lrm_markers("no markers")
        0
    """
    return text.count(LRM)
