"""Integration tests for translation functionality."""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.translation_utils import (
    validate_language_code,
    parse_translation_command,
    format_translation_response,
    extract_translation_from_response
)


class TestTranslationIntegration(unittest.TestCase):
    """Test integrated translation functionality."""
    
    def test_complete_translation_workflow(self):
        """Test complete translation workflow from command to response."""
        # Test command parsing
        command = "en=Hello world"
        target, text, errors = parse_translation_command(command)
        
        self.assertEqual(target, "en")
        self.assertEqual(text, "Hello world")
        self.assertEqual(len(errors), 0)
        
        # Test language validation
        is_valid, std_target, suggestion = validate_language_code(target)
        self.assertTrue(is_valid)
        self.assertEqual(std_target, "en")
        
        # Test response formatting with mock translation
        translation = "سلام دنیا"
        pronunciation = "salaam donyaa"
        formatted_response = format_translation_response(translation, pronunciation, "fa")
        self.assertIn("سلام دنیا", formatted_response)
        self.assertIn("salaam donyaa", formatted_response)
    
    def test_structured_response_extraction(self):
        """Test extraction from structured AI responses."""
        # Simulate AI response with structured format
        ai_response = """Translation: Hello world
Phonetic: (هلو ورلد)"""
        
        translation, pronunciation = extract_translation_from_response(ai_response)
        self.assertEqual(translation, "Hello world")
        self.assertEqual(pronunciation, "هلو ورلد")
        
        # Test formatting the extracted response
        formatted_response = format_translation_response(translation, pronunciation, "en")
        self.assertIn("Hello world", formatted_response)
        self.assertIn("هلو ورلد", formatted_response)
    
    def test_end_to_end_persian_translation(self):
        """Test end-to-end Persian translation workflow."""
        # Test Persian command parsing - translate Persian text to English
        command = "en=سلام دنیا"  # Translate to English from Persian: سلام دنیا
        target, text, errors = parse_translation_command(command)
        
        self.assertEqual(target, "en")
        self.assertEqual(text, "سلام دنیا")
        self.assertEqual(len(errors), 0)
        
        # Test language validation
        is_valid, std_target, suggestion = validate_language_code(target)
        self.assertTrue(is_valid)
        self.assertEqual(std_target, "en")
        
        # Simulate AI response
        ai_response = """Translation: Hello world
Phonetic: (helo vorld)"""
        
        translation, pronunciation = extract_translation_from_response(ai_response)
        formatted_response = format_translation_response(translation, pronunciation, "en")
        self.assertIn("Hello world", formatted_response)
        self.assertIn("helo vorld", formatted_response)


if __name__ == '__main__':
    unittest.main()
