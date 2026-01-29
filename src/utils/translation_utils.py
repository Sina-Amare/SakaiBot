"""Enhanced translation utilities for SakaiBot."""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Language code to full name mapping
LANGUAGE_CODE_TO_NAME = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'fa': 'Persian',
    'hi': 'Hindi',
    'tr': 'Turkish',
    'pl': 'Polish',
    'nl': 'Dutch',
    'sv': 'Swedish',
    'no': 'Norwegian',
    'da': 'Danish',
    'fi': 'Finnish',
    'cs': 'Czech',
    'hu': 'Hungarian',
    'ro': 'Romanian',
    'el': 'Greek',
    'he': 'Hebrew',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'uk': 'Ukrainian',
}


def get_language_name(language_code: str) -> str:
    """Get language name from code."""
    return LANGUAGE_CODE_TO_NAME.get(language_code.lower(), language_code.title())


def validate_language_code(language_code: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate a language code and return standardized code with suggestions.
    
    Args:
        language_code: Input language code (can be ISO 639-1, name, or alias)
    
    Returns:
        Tuple of (is_valid, standardized_code, suggestion_if_invalid)
    """
    if not language_code or not language_code.strip():
        return False, "", "Please provide a language code"
    
    normalized_code = language_code.lower().strip()
    
    # Check if it's a valid language code in our mapping
    if normalized_code in LANGUAGE_CODE_TO_NAME:
        return True, normalized_code, None
    
    # Check if it's a language name (case-insensitive)
    for code, name in LANGUAGE_CODE_TO_NAME.items():
        if name.lower() == normalized_code:
            return True, code, None
    
    # Try to find partial matches
    suggestions = []
    for valid_code, valid_name in LANGUAGE_CODE_TO_NAME.items():
        if normalized_code in valid_code or normalized_code in valid_name.lower():
            suggestions.append(valid_code)
    
    if suggestions:
        # Return the first suggestion
        return False, suggestions[0], f"Did you mean {suggestions[0]}?"
    
    # No match found
    return False, "", f"Unsupported language: {language_code}. Supported languages: {', '.join(LANGUAGE_CODE_TO_NAME.keys())}"


def parse_translation_command(command_text: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Parse translation command for the two core use cases only:
    1. Direct Translation: /translate=<language>=<text>
    2. Reply Translation: /translate=<language> (text comes from replied message)
    
    Args:
        command_text: Command text after /translate=
    
    Returns:
        Tuple of (target_language, text_to_translate, error_messages)
    """
    error_messages = []
    
    if not command_text or not command_text.strip():
        error_messages.append("No command provided")
        return None, None, error_messages
    
    command_text = command_text.strip()
    
    # Format 1: /translate=<language>=<text>
    if '=' in command_text and command_text.count('=') >= 1:
        parts = command_text.split('=', 1)
        target_language = parts[0].strip()
        text_to_translate = parts[1].strip()
        
        # Validate target language
        is_valid, std_target, suggestion = validate_language_code(target_language)
        if not is_valid:
            error_messages.append(f"Invalid target language: {target_language}")
            if suggestion:
                error_messages.append(suggestion)
            return None, None, error_messages
        
        if not text_to_translate:
            error_messages.append("No text provided to translate")
            return None, None, error_messages
        
        return std_target, text_to_translate, error_messages
    
    # Format 2: /translate=<language> (for reply translation)
    else:
        target_language = command_text.strip()
        is_valid, std_target, suggestion = validate_language_code(target_language)
        if not is_valid:
            error_messages.append(f"Invalid target language: {target_language}")
            if suggestion:
                error_messages.append(suggestion)
            return None, None, error_messages
        
        # For reply translation, text will be provided separately
        return std_target, None, error_messages


def format_translation_response(translation: str, pronunciation: str, target_language: str) -> str:
    """
    Format translation response with the exact required structure.
    
    Args:
        translation: The translated text
        pronunciation: The Persian phonetic pronunciation
        target_language: The target language code (will be converted to full name)
    
    Returns:
        Formatted response with translation and pronunciation in required format
    """
    if not translation or not translation.strip():
        return "No translation available"
    
    # Get the full language name
    language_name = get_language_name(target_language)
    
    # Skip pronunciation for Persian translations (Persian speakers don't need
    # Persian phonetics for Persian text - only for non-Persian translations)
    target_lower = target_language.lower()
    if target_lower in ('fa', 'farsi', 'persian'):
        formatted_response = f"Translation ({language_name}):\n{translation}\n-----------------------------"
    else:
        # Include pronunciation for non-Persian translations
        formatted_response = f"Translation ({language_name}):\n{translation}\nPronunciation:\n{pronunciation}\n-----------------------------"
    
    return formatted_response


def extract_translation_from_response(response: str) -> Tuple[str, str]:
    """
    Extract translation and pronunciation from AI response.
    
    Args:
        response: AI response text
    
    Returns:
        Tuple of (translation, pronunciation)
    """
    if not response or not response.strip():
        return "", ""
    
    response = response.strip()
    
    # Look for structured patterns in AI responses first
    # Pattern: Translation: ... \n Phonetic: (...)
    translation_match = re.search(r'Translation:\s*(.+?)(?:\s*\n|$)', response, re.IGNORECASE | re.DOTALL)
    phonetic_match = re.search(r'Phonetic:\s*\((.+?)\)', response, re.IGNORECASE)
    
    if translation_match and phonetic_match:
        translation = translation_match.group(1).strip()
        pronunciation = phonetic_match.group(1).strip()
        return translation, pronunciation
    
    # Pattern: Any text with "translation:" followed by "phonetic:"
    if not (translation_match and phonetic_match):
        # Extract text between "Translation:" and "Phonetic:" or end of line
        translation_match = re.search(r'Translation:\s*(.+?)(?:\n.*?Phonetic:|\Z)', response, re.DOTALL | re.IGNORECASE)
        phonetic_match = re.search(r'Phonetic:\s*\((.*?)\)', response, re.IGNORECASE)
        
        if translation_match and phonetic_match:
            translation = translation_match.group(1).strip()
            pronunciation = phonetic_match.group(1).strip()
            # Remove any trailing text after the phonetic
            translation = re.sub(r'\s*\n.*$', '', translation, flags=re.DOTALL).strip()
            return translation, pronunciation

    # Look for pattern: "translation (pronunciation)" in the cleaned content
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        match = re.search(r'(.+?)\s*\(\s*(.+?)\s*\)', line)
        if match:
            translation = match.group(1).strip()
            pronunciation = match.group(2).strip()
            # Make sure we're not picking up other parenthetical content
            if len(translation) > 0 and len(pronunciation) > 0:
                return translation, pronunciation

    # If we still haven't found a good match, try to find the main content
    # Remove common prefixes like [NOTES] or other markers
    cleaned_response = re.sub(r'^\[.*?\].*?\n?', '', response, flags=re.MULTILINE)
    cleaned_response = re.sub(r'^.*?:.*?\n?', '', cleaned_response, flags=re.MULTILINE)  # Remove lines like "Detected Language: ..."

    # Find the most likely translation line
    lines = cleaned_response.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('[') and not re.match(r'^\w+:\s', line, re.IGNORECASE):
            # Check if this line contains the pattern
            match = re.search(r'(.+?)\s*\(\s*(.+?)\s*\)', line)
            if match:
                translation = match.group(1).strip()
                pronunciation = match.group(2).strip()
                return translation, pronunciation

    # If no structured format found, return the cleaned response as translation with empty pronunciation
    return cleaned_response.strip(), ""


class TranslationHistory:
    """Simple translation history manager."""
    
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.history: List[Dict[str, str]] = []
    
    def add_translation(
        self, 
        source_text: str, 
        target_language: str, 
        translated_text: str,
        pronunciation: Optional[str] = None
    ) -> None:
        """Add a translation to history."""
        history_item = {
            'timestamp': datetime.now().isoformat(),
            'source_text': source_text,
            'target_language': target_language,
            'translated_text': translated_text,
            'pronunciation': pronunciation
        }
        
        self.history.append(history_item)
        
        # Keep only the most recent items
        if len(self.history) > self.max_items:
            self.history = self.history[-self.max_items:]
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get translation history."""
        if limit:
            return self.history[-limit:]
        return self.history.copy()
    
    def clear_history(self) -> None:
        """Clear translation history."""
        self.history.clear()
    
    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        """Convert history to dictionary for serialization."""
        return {'translation_history': self.history}
    
    @classmethod
    def from_dict(cls, data: Dict[str, List[Dict[str, str]]]) -> 'TranslationHistory':
        """Create TranslationHistory from dictionary."""
        history = cls()
        history.history = data.get('translation_history', [])
        return history


def get_supported_languages() -> List[str]:
    """Get list of supported language codes."""
    return sorted(LANGUAGE_CODE_TO_NAME.keys())
