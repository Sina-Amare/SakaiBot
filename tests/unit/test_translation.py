"""Unit tests for translation functionality."""

import unittest
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import directly from the file to avoid package structure issues
import importlib.util
spec = importlib.util.spec_from_file_location("translation_utils", str(src_path / "utils" / "translation_utils.py"))
translation_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translation_utils)

# Use the imported functions
validate_language_code = translation_utils.validate_language_code
parse_enhanced_translate_command = translation_utils.parse_enhanced_translate_command
format_translation_response = translation_utils.format_translation_response
extract_translation_from_response = translation_utils.extract_translation_from_response
TranslationHistory = translation_utils.TranslationHistory
get_supported_languages = translation_utils.get_supported_languages
get_language_name = translation_utils.get_language_name


class TestLanguageCodeValidation(unittest.TestCase):
    """Test language code validation functionality."""
    
    def test_valid_iso_codes(self):
        """Test valid ISO 639-1 language codes."""
        valid_cases = [
            ("en", True, "en"),
            ("es", True, "es"),
            ("fr", True, "fr"),
            ("fa", True, "fa"),
            ("zh", True, "zh")
        ]
        
        for code, expected_valid, expected_std in valid_cases:
            with self.subTest(code=code):
                is_valid, std_code, suggestion = validate_language_code(code)
                self.assertTrue(is_valid)
                self.assertEqual(std_code, expected_std)
                self.assertIsNone(suggestion)
    
    def test_valid_language_names(self):
        """Test valid language names."""
        valid_cases = [
            ("english", True, "en"),
            ("spanish", True, "es"),
            ("farsi", True, "fa"),
            ("persian", True, "fa")
        ]
        
        for code, expected_valid, expected_std in valid_cases:
            with self.subTest(code=code):
                is_valid, std_code, suggestion = validate_language_code(code)
                self.assertTrue(is_valid)
                self.assertEqual(std_code, expected_std)
                self.assertIsNone(suggestion)
    
    def test_invalid_codes(self):
        """Test invalid language codes."""
        invalid_cases = ["", "invalid", "xyz", "123"]
        
        for code in invalid_cases:
            with self.subTest(code=code):
                is_valid, std_code, suggestion = validate_language_code(code)
                self.assertFalse(is_valid)
                self.assertEqual(std_code, "")
                self.assertIsNotNone(suggestion)
    
    def test_suggestion_mechanism(self):
        """Test that similar codes get suggestions."""
        # Test partial match
        is_valid, std_code, suggestion = validate_language_code("engli")
        self.assertFalse(is_valid)
        self.assertEqual(std_code, "en")
        self.assertIn("Did you mean en", suggestion)
        
        # Test case insensitive
        is_valid, std_code, suggestion = validate_language_code("EN")
        self.assertTrue(is_valid)
        self.assertEqual(std_code, "en")
        self.assertIsNone(suggestion)


class TestEnhancedCommandParsing(unittest.TestCase):
    """Test enhanced translation command parsing."""
    
    def test_format_1_lang_text(self):
        """Test format: /translate=<lang> <text>"""
        test_cases = [
            ("en Hello world", "en", "auto", "Hello world"),
            ("fa سلام دنیا", "fa", "auto", "سلام دنیا")
        ]
        
        for command, expected_target, expected_source, expected_text in test_cases:
            with self.subTest(command=command):
                target, source, text, errors = parse_enhanced_translate_command(command)
                self.assertEqual(target, expected_target)
                self.assertEqual(source, expected_source)
                self.assertEqual(text, expected_text)
                self.assertEqual(len(errors), 0)
    
    def test_format_2_lang_lang_text(self):
        """Test format: /translate=<target_lang>,<source_lang> <text>"""
        test_cases = [
            ("en,fa Hello world", "en", "fa", "Hello world"),
            ("fa,en سلام دنیا", "fa", "en", "سلام دنیا")
        ]
        
        for command, expected_target, expected_source, expected_text in test_cases:
            with self.subTest(command=command):
                target, source, text, errors = parse_enhanced_translate_command(command)
                self.assertEqual(target, expected_target)
                self.assertEqual(source, expected_source)
                self.assertEqual(text, expected_text)
                self.assertEqual(len(errors), 0)
    
    def test_format_3_lang_equals_text(self):
        """Test format: /translate=<lang>=<text>"""
        test_cases = [
            ("en=Hello world", "en", "auto", "Hello world"),
            ("es=Hola mundo", "es", "auto", "Hola mundo"),
            ("fa=سلام دنیا", "fa", "auto", "سلام دنیا")
        ]
        
        for command, expected_target, expected_source, expected_text in test_cases:
            with self.subTest(command=command):
                target, source, text, errors = parse_enhanced_translate_command(command)
                self.assertEqual(target, expected_target)
                self.assertEqual(source, expected_source)
                self.assertEqual(text, expected_text)
                self.assertEqual(len(errors), 0)
    
    def test_format_4_lang_lang_equals_text(self):
        """Test format: /translate=<target_lang>,<source_lang>=<text>"""
        test_cases = [
            ("en,fa=Hello world", "en", "fa", "Hello world"),
            ("fa,en=سلام دنیا", "fa", "en", "سلام دنیا")
        ]
        
        for command, expected_target, expected_source, expected_text in test_cases:
            with self.subTest(command=command):
                target, source, text, errors = parse_enhanced_translate_command(command)
                self.assertEqual(target, expected_target)
                self.assertEqual(source, expected_source)
                self.assertEqual(text, expected_text)
                self.assertEqual(len(errors), 0)
    
    def test_format_4_lang_equals_lang_text(self):
        """Test format: /translate=<target_lang>=<source_lang> <text> (Format 4 from documentation)"""
        test_cases = [
            ("en=fa سلام دنیا", "en", "fa", "سلام دنیا"),
            ("fa=en Hello world", "fa", "en", "Hello world"),
            ("de=es Hola mundo", "de", "es", "Hola mundo"),
            ("fr=zh 你好世界", "fr", "zh", "你好世界")
        ]
        
        for command, expected_target, expected_source, expected_text in test_cases:
            with self.subTest(command=command):
                target, source, text, errors = parse_enhanced_translate_command(command)
                self.assertEqual(target, expected_target)
                self.assertEqual(source, expected_source)
                self.assertEqual(text, expected_text)
                self.assertEqual(len(errors), 0)
    
    def test_invalid_formats(self):
        """Test invalid command formats."""
        invalid_cases = [
            "",  # Empty
            "en",  # Missing text
            "en,fa",  # Missing text
        ]
        
        for command in invalid_cases:
            with self.subTest(command=command):
                target, source, text, errors = parse_enhanced_translate_command(command)
                self.assertIsNone(target)
                self.assertIsNone(source)
                self.assertIsNone(text)
                self.assertGreater(len(errors), 0)
    
    def test_language_validation_in_parsing(self):
        """Test that invalid language codes are caught during parsing."""
        # Invalid target language
        target, source, text, errors = parse_enhanced_translate_command("invalid Hello world")
        self.assertEqual(target, "invalid")
        self.assertEqual(source, "auto")
        self.assertEqual(text, "Hello world")
        self.assertGreater(len(errors), 0)
        self.assertIn("Invalid target language", errors[0])


class TestResponseFormatting(unittest.TestCase):
    """Test translation response formatting."""
    
    def test_format_with_pronunciation(self):
        """Test formatting with pronunciation."""
        response = format_translation_response("Hello world", "هِلو ورلد")
        self.assertEqual(response, "Hello world\n pronunciation: (هِلو ورلد)")
    
    def test_format_without_pronunciation(self):
        """Test formatting without pronunciation."""
        response = format_translation_response("Hello world", None)
        self.assertEqual(response, "Hello world")
        
        response = format_translation_response("Hello world", "")
        self.assertEqual(response, "Hello world")
    
    def test_format_empty_text(self):
        """Test formatting with empty text."""
        response = format_translation_response("", "pronunciation")
        self.assertEqual(response, "No translation available")
        
        response = format_translation_response(None, "pronunciation")
        self.assertEqual(response, "No translation available")


class TestResponseExtraction(unittest.TestCase):
    """Test translation extraction from AI responses."""
    
    def test_extract_with_parentheses(self):
        """Test extraction from format: translation (pronunciation)"""
        response = "Hello world (هِلو ورلد)"
        translation, pronunciation = extract_translation_from_response(response)
        self.assertEqual(translation, "Hello world")
        self.assertEqual(pronunciation, "هِلو ورلد")
    
    def test_extract_with_patterns(self):
        """Test extraction from structured AI response."""
        response = """Translation: Hello world
Phonetic: (هِلو ورلد)"""
        translation, pronunciation = extract_translation_from_response(response)
        self.assertEqual(translation, "Hello world")
        self.assertEqual(pronunciation, "هِلو ورلد")
    
    def test_extract_no_structure(self):
        """Test extraction when no structure is found."""
        response = "Just some translation text without structure"
        translation, pronunciation = extract_translation_from_response(response)
        self.assertEqual(translation, response)
        self.assertIsNone(pronunciation)
    
    def test_extract_empty_response(self):
        """Test extraction from empty response."""
        translation, pronunciation = extract_translation_from_response("")
        self.assertEqual(translation, "")
        self.assertIsNone(pronunciation)


class TestTranslationHistory(unittest.TestCase):
    """Test translation history functionality."""
    
    def setUp(self):
        self.history = TranslationHistory(max_items=5)
    
    def test_add_translation(self):
        """Test adding translations to history."""
        self.history.add_translation(
            source_text="Hello",
            target_language="fa",
            translated_text="سلام",
            pronunciation="سلام"
        )
        
        history_items = self.history.get_history()
        self.assertEqual(len(history_items), 1)
        self.assertEqual(history_items[0]["source_text"], "Hello")
        self.assertEqual(history_items[0]["target_language"], "fa")
        self.assertEqual(history_items[0]["translated_text"], "سلام")
        self.assertEqual(history_items[0]["pronunciation"], "سلام")
    
    def test_history_limit(self):
        """Test that history respects max items limit."""
        # Add more items than the limit
        for i in range(10):
            self.history.add_translation(
                source_text=f"Text {i}",
                target_language="en",
                translated_text=f"Translation {i}"
            )
        
        history_items = self.history.get_history()
        self.assertEqual(len(history_items), 5)  # Should keep only the last 5
        self.assertEqual(history_items[0]["source_text"], "Text 5")
        self.assertEqual(history_items[-1]["source_text"], "Text 9")
    
    def test_clear_history(self):
        """Test clearing the history."""
        self.history.add_translation("Hello", "fa", "سلام")
        self.assertEqual(len(self.history.get_history()), 1)
        
        self.history.clear_history()
        self.assertEqual(len(self.history.get_history()), 0)
    
    def test_to_from_dict(self):
        """Test serialization and deserialization."""
        # Add some data
        self.history.add_translation("Hello", "fa", "سلام")
        
        # Convert to dict
        history_dict = self.history.to_dict()
        
        # Create new history from dict
        new_history = TranslationHistory.from_dict(history_dict)
        
        # Verify data is preserved
        history_items = new_history.get_history()
        self.assertEqual(len(history_items), 1)
        self.assertEqual(history_items[0]["source_text"], "Hello")
    
    def test_get_history_with_limit(self):
        """Test getting history with a specific limit."""
        # Add some data
        for i in range(5):
            self.history.add_translation(f"Text {i}", "en", f"Translation {i}")
        
        # Get last 3 items
        limited_history = self.history.get_history(limit=3)
        self.assertEqual(len(limited_history), 3)
        self.assertEqual(limited_history[0]["source_text"], "Text 2")
        self.assertEqual(limited_history[-1]["source_text"], "Text 4")


class TestLanguageUtilities(unittest.TestCase):
    """Test language utility functions."""
    
    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        languages = get_supported_languages()
        self.assertIsInstance(languages, list)
        self.assertGreater(len(languages), 0)
        self.assertIn("en", languages)
        self.assertIn("fa", languages)
    
    def test_get_language_name(self):
        """Test getting language names from codes."""
        self.assertEqual(get_language_name("en"), "English")
        self.assertEqual(get_language_name("fa"), "Persian")
        self.assertEqual(get_language_name("es"), "Spanish")
        self.assertEqual(get_language_name("invalid"), "Invalid")


if __name__ == '__main__':
    unittest.main()
