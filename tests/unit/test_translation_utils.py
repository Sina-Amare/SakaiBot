"""Unit tests for translation utilities."""

import unittest

from src.utils.translation_utils import parse_translation_command


class TestTranslationUtils(unittest.TestCase):
    """Test translation utility functions."""
    
    def test_parse_translation_command_simple(self):
        """Test parsing simple translation command."""
        target, text, errors = parse_translation_command("en Hello world")
        self.assertEqual(target, "en")
        self.assertEqual(text, "Hello world")
        self.assertEqual(len(errors), 0)
    
    def test_parse_translation_command_with_comma(self):
        """Test parsing translation command with source language."""
        target, text, errors = parse_translation_command("en,fa Hello world")
        self.assertEqual(target, "en")
        self.assertEqual(text, "Hello world")
        self.assertEqual(len(errors), 0)
    
    def test_parse_translation_command_no_text(self):
        """Test parsing translation command without text."""
        target, text, errors = parse_translation_command("en")
        self.assertEqual(target, "en")
        self.assertIsNone(text)
        self.assertEqual(len(errors), 0)
    
    def test_parse_translation_command_empty(self):
        """Test parsing empty translation command."""
        target, text, errors = parse_translation_command("")
        self.assertIsNone(target)
        self.assertIsNone(text)
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()

