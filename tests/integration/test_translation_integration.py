"""Integration tests for translation functionality."""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.unit.test_translation import (
    validate_language_code,
    parse_enhanced_translate_command,
    format_translation_response,
    extract_translation_from_response
)


class TestTranslationIntegration(unittest.TestCase):
    """Test integrated translation functionality."""
    
    def test_complete_translation_workflow(self):
        """Test complete translation workflow from command to response."""
        # Test command parsing
        command = "en,fa Hello world"
        target, source, text, errors = parse_enhanced_translate_command(command)
        
        self.assertEqual(target, "en")
        self.assertEqual(source, "fa")
        self.assertEqual(text, "Hello world")
        self.assertEqual(len(errors), 0)
        
        # Test language validation
        is_valid, std_target, suggestion = validate_language_code(target)
        self.assertTrue(is_valid)
        self.assertEqual(std_target, "en")
        
        is_valid, std_source, suggestion = validate_language_code(source)
        self.assertTrue(is_valid)
        self.assertEqual(std_source, "fa")
        
        # Test response formatting with mock translation
        translation = "سلام دنیا"
        pronunciation = "سلام دنیا"
        formatted_response = format_translation_response(translation, pronunciation)
        self.assertEqual(formatted_response, "سلام دنیا\n pronunciation: (سلام دنیا)")
    
    def test_structured_response_extraction(self):
        """Test extraction from structured AI responses."""
        # Simulate AI response with structured format
        ai_response = """Translation: Hello world
Phonetic: (هلو ورلد)"""
        
        translation, pronunciation = extract_translation_from_response(ai_response)
        self.assertEqual(translation, "Hello world")
        self.assertEqual(pronunciation, "هلو ورلد")
        
        # Test formatting the extracted response
        formatted_response = format_translation_response(translation, pronunciation)
        self.assertEqual(formatted_response, "Hello world\n pronunciation: (هلو ورلد)")
    
    def test_end_to_end_persian_translation(self):
        """Test end-to-end Persian translation workflow."""
        # Test Persian command parsing - translate Persian text to English
        command = "en=fa سلام دنیا"  # Translate to English from Persian: سلام دنیا
        target, source, text, errors = parse_enhanced_translate_command(command)
        
        self.assertEqual(target, "en")
        self.assertEqual(source, "fa")
        self.assertEqual(text, "سلام دنیا")
        self.assertEqual(len(errors), 0)
        
        # Test language validation
        is_valid, std_target, suggestion = validate_language_code(target)
        self.assertTrue(is_valid)
        self.assertEqual(std_target, "en")
        
        is_valid, std_source, suggestion = validate_language_code(source)
        self.assertTrue(is_valid)
        self.assertEqual(std_source, "fa")
        
        # Simulate AI response
        ai_response = """Translation: Hello world
Phonetic: (هلو ورلد)"""
        
        translation, pronunciation = extract_translation_from_response(ai_response)
        formatted_response = format_translation_response(translation, pronunciation)
        self.assertEqual(formatted_response, "Hello world\n pronunciation: (هلو ورلد)")


if __name__ == '__main__':
    unittest.main()
