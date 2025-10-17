"""Enhanced translation utilities for SakaiBot."""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import iso639

# ISO 639-1 language code mappings with common alternatives
LANGUAGE_CODE_MAPS = {
    'en': ['english', 'en', 'eng', 'en-us', 'en-gb'],
    'es': ['spanish', 'es', 'esp', 'es-es'],
    'fr': ['french', 'fr', 'fra', 'fr-fr'],
    'de': ['german', 'de', 'deu', 'de-de'],
    'it': ['italian', 'it', 'ita', 'it-it'],
    'pt': ['portuguese', 'pt', 'por', 'pt-br', 'pt-pt'],
    'ru': ['russian', 'ru', 'rus', 'ru-ru'],
    'zh': ['chinese', 'zh', 'chi', 'zh-cn', 'zh-tw'],
    'ja': ['japanese', 'ja', 'jpn', 'ja-jp'],
    'ko': ['korean', 'ko', 'kor', 'ko-kr'],
    'ar': ['arabic', 'ar', 'ara', 'ar-sa'],
    'fa': ['persian', 'farsi', 'fa', 'fa-ir', 'per'],
    'hi': ['hindi', 'hi', 'hin', 'hi-in'],
    'tr': ['turkish', 'tr', 'tur', 'tr-tr'],
    'pl': ['polish', 'pl', 'pol', 'pl-pl'],
    'nl': ['dutch', 'nl', 'nld', 'nl-nl'],
    'sv': ['swedish', 'sv', 'swe', 'sv-se'],
    'no': ['norwegian', 'no', 'nor', 'no-no'],
    'da': ['danish', 'da', 'dan', 'da-dk'],
    'fi': ['finnish', 'fi', 'fin', 'fi-fi'],
    'cs': ['czech', 'cs', 'ces', 'cs-cz'],
    'hu': ['hungarian', 'hu', 'hun', 'hu-hu'],
    'ro': ['romanian', 'ro', 'ron', 'ro-ro'],
    'el': ['greek', 'el', 'ell', 'el-gr'],
    'he': ['hebrew', 'he', 'heb', 'he-il'],
    'th': ['thai', 'th', 'tha', 'th-th'],
    'vi': ['vietnamese', 'vi', 'vie', 'vi-vn'],
    'uk': ['ukrainian', 'uk', 'ukr', 'uk-ua'],
}

# Reverse map for quick lookup
REVERSE_LANGUAGE_MAP = {}
for lang_code, aliases in LANGUAGE_CODE_MAPS.items():
    for alias in aliases:
        REVERSE_LANGUAGE_MAP[alias.lower()] = lang_code


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
    
    # Check if it's a valid ISO 639-1 code
    if normalized_code in LANGUAGE_CODE_MAPS:
        return True, normalized_code, None
    
    # Check if it's in our reverse map
    if normalized_code in REVERSE_LANGUAGE_MAP:
        standardized = REVERSE_LANGUAGE_MAP[normalized_code]
        return True, standardized, None
    
    # Try to find partial matches
    suggestions = []
    for valid_code, aliases in LANGUAGE_CODE_MAPS.items():
        for alias in aliases:
            if normalized_code in alias or alias in normalized_code:
                suggestions.append(valid_code)
    
    if suggestions:
        # Remove duplicates and return the first suggestion
        unique_suggestions = list(set(suggestions))
        return False, unique_suggestions[0], f"Did you mean {unique_suggestions[0]}?"
    
    # No match found
    return False, "", f"Unsupported language: {language_code}. Supported languages: {', '.join(LANGUAGE_CODE_MAPS.keys())}"


def parse_enhanced_translate_command(command_text: str) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
    """
    Enhanced translation command parser with improved format support.
    
    Args:
        command_text: Command text after /translate=
    
    Returns:
        Tuple of (target_language, source_language, text_to_translate, error_messages)
    """
    error_messages = []
    
    if not command_text or not command_text.strip():
        error_messages.append("No command provided")
        return None, None, None, error_messages
    
    command_text = command_text.strip()
    
    # Support formats:
    # 1. /translate=<target_lang> <text>
    # 2. /translate=<target_lang>,<source_lang> <text>
    # 3. /translate=<target_lang>=<text>
    # 4. /translate=<target_lang>=<source_lang> <text>
    # 5. /translate=<target_lang>,<source_lang>=<text>
    
    target_language = None
    source_language = "auto"
    text_to_translate = None
    
    # Format 5: /translate=<target_lang>,<source_lang>=<text> (most specific - comma and equals)
    if '=' in command_text and ',' in command_text:
        # Find the first equals sign to split language part from text
        equals_index = command_text.find('=')
        if equals_index > 0:
            language_part = command_text[:equals_index]
            text_to_translate = command_text[equals_index + 1:].strip()
            
            if ',' in language_part:
                target_source = language_part.split(',')
                if len(target_source) == 2:
                    target_language = target_source[0].strip()
                    source_language = target_source[1].strip()
                else:
                    error_messages.append("Invalid language format. Use: target_lang,source_lang")
            else:
                error_messages.append("Invalid command format")
            
            # Validate languages
            if target_language:
                is_valid, std_target, suggestion = validate_language_code(target_language)
                if not is_valid:
                    error_messages.append(f"Invalid target language: {target_language}")
                    if suggestion:
                        error_messages.append(suggestion)
            
            if source_language and source_language.lower() != "auto":
                is_valid, std_source, suggestion = validate_language_code(source_language)
                if not is_valid:
                    error_messages.append(f"Invalid source language: {source_language}")
                    if suggestion:
                        error_messages.append(suggestion)
            
            return target_language, source_language, text_to_translate, error_messages
    
    # Format 3: /translate=<target_lang>=<text> (specific with equals)
    elif '=' in command_text and command_text.count('=') == 1:
        parts = command_text.split('=', 1)
        target_language = parts[0].strip()
        remaining_text = parts[1].strip()
        
        # Check if the remaining text starts with a valid language code followed by space and more text
        # This handles the case: /translate=<target_lang>=<source_lang> <text>
        if ' ' in remaining_text:
            potential_source, potential_text = remaining_text.split(' ', 1)
            is_valid_source, std_source, _ = validate_language_code(potential_source)
            if is_valid_source:
                source_language = std_source
                text_to_translate = potential_text.strip()
            else:
                text_to_translate = remaining_text
        else:
            text_to_translate = remaining_text
        
        # Validate target language
        is_valid, std_target, suggestion = validate_language_code(target_language)
        if not is_valid:
            error_messages.append(f"Invalid target language: {target_language}")
            if suggestion:
                error_messages.append(suggestion)
        
        # Validate source language if it was detected
        if source_language and source_language.lower() != "auto":
            is_valid, std_source, suggestion = validate_language_code(source_language)
            if not is_valid:
                error_messages.append(f"Invalid source language: {source_language}")
                if suggestion:
                    error_messages.append(suggestion)
        
        return target_language, source_language, text_to_translate, error_messages
    
    # Format 2: /translate=<target_lang>,<source_lang> <text> (specific with comma and space)
    elif ' ' in command_text and ',' in command_text:
        space_index = command_text.find(' ')
        if space_index > 0:
            language_part = command_text[:space_index]
            text_to_translate = command_text[space_index + 1:].strip()
            
            if ',' in language_part:
                target_source = language_part.split(',')
                if len(target_source) == 2:
                    target_language = target_source[0].strip()
                    source_language = target_source[1].strip()
                else:
                    error_messages.append("Invalid language format. Use: target_lang,source_lang")
            else:
                target_language = language_part.strip()
                source_language = "auto"
            
            # Validate languages
            if target_language:
                is_valid, std_target, suggestion = validate_language_code(target_language)
                if not is_valid:
                    error_messages.append(f"Invalid target language: {target_language}")
                    if suggestion:
                        error_messages.append(suggestion)
            
            if source_language and source_language.lower() != "auto":
                is_valid, std_source, suggestion = validate_language_code(source_language)
                if not is_valid:
                    error_messages.append(f"Invalid source language: {source_language}")
                    if suggestion:
                        error_messages.append(suggestion)
            
            return target_language, source_language, text_to_translate, error_messages
    
    # Format 1: /translate=<target_lang> <text> (simplest format)
    elif ' ' in command_text:
        parts = command_text.split(' ', 1)
        target_language = parts[0].strip()
        text_to_translate = parts[1].strip()
        
        # Validate target language
        is_valid, std_target, suggestion = validate_language_code(target_language)
        if not is_valid:
            error_messages.append(f"Invalid target language: {target_language}")
            if suggestion:
                error_messages.append(suggestion)
        
        return target_language, source_language, text_to_translate, error_messages
    
    # Unknown format
    error_messages.append("Invalid command format. Use: /translate=<lang> [text] or /translate=<lang>,<source_lang> [text]")
    return None, None, None, error_messages


def format_translation_response(translated_text: str, pronunciation: Optional[str] = None) -> str:
    """
    Unified translation response formatter.
    
    Args:
        translated_text: The translated text
        pronunciation: Optional Persian pronunciation
    
    Returns:
        Formatted response with translation and pronunciation on separate lines
    """
    if not translated_text or not translated_text.strip():
        return "No translation available"
    
    # Clean the text
    translated_text = translated_text.strip()
    
    if pronunciation and pronunciation.strip():
        # Format with translation and pronunciation on separate lines for clarity
        return f"{translated_text}\n pronunciation: ({pronunciation.strip()})"
    else:
        # If no pronunciation, return just the translation
        return translated_text


def extract_translation_from_response(response: str) -> Tuple[str, Optional[str]]:
    """
    Extract translation and pronunciation from AI response.
    
    Args:
        response: AI response text
    
    Returns:
        Tuple of (translation, pronunciation)
    """
    if not response or not response.strip():
        return "", None
    
    response = response.strip()
    
    # Look for specific patterns in AI responses first
    # Pattern: Translation: ... \n Phonetic: (...)
    translation_match = re.search(r'Translation:\s*(.+?)(?:\s*\n|$)', response, re.IGNORECASE)
    phonetic_match = re.search(r'Phonetic:\s*\((.+?)\)', response, re.IGNORECASE)
    
    if translation_match and phonetic_match:
        translation = translation_match.group(1).strip()
        pronunciation = phonetic_match.group(1).strip()
        return translation, pronunciation
    
    # Pattern: Detected Language: ... \n Translation: ... \n Phonetic: (...)
    if not (translation_match and phonetic_match):
        translation_match = re.search(r'Translation:\s*(.+?)(?:\s*\n|$)', response, re.DOTALL | re.IGNORECASE)
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
    # Extract content that might be between comments or other text
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
    # Remove common prefixes like "Some sarcastic comment" or "Detected Language"
    lines = response.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        # Look for the pattern in each line
        match = re.search(r'(.+?)\s*\(\s*(.+?)\s*\)', line)
        if match:
            translation = match.group(1).strip()
            pronunciation = match.group(2).strip()
            return translation, pronunciation
    
    # If no structured format found, try to clean up the response and return as translation
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
            elif '(' in line and ')' in line and line.count('(') == line.count(')'):
                # It might be a translation with pronunciation but with extra text
                # Try to extract the core part
                pass
    
    # As a last resort, return the cleaned response as translation with no pronunciation
    return cleaned_response.strip(), None


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
    return sorted(LANGUAGE_CODE_MAPS.keys())


def get_language_name(language_code: str) -> str:
    """Get language name from code."""
    if language_code in LANGUAGE_CODE_MAPS:
        # Get the first alias which is usually the full name
        return LANGUAGE_CODE_MAPS[language_code][0].title()
    return language_code.title()
