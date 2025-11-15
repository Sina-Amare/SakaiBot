"""Unit tests for translation utilities."""

import unittest

from src.utils.translation_utils import parse_translation_command


class TestTranslationUtils(unittest.TestCase):
    """Test translation utility functions."""
    
    def test_parse_translation_command_simple(self):
        """Test parsing simple translation command."""
        # Format: language=text
        target, text, errors = parse_translation_command("en=Hello world")
        self.assertEqual(target, "en")
        self.assertEqual(text, "Hello world")
        self.assertEqual(len(errors), 0)
    
    def test_parse_translation_command_reply_format(self):
        """Test parsing translation command for reply format."""
        # Format: just language (for reply translation)
        target, text, errors = parse_translation_command("en")
        self.assertEqual(target, "en")
        self.assertIsNone(text)  # Text comes from replied message
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

