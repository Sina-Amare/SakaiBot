"""Unit tests for input validators."""

import unittest

from src.utils.validators import InputValidator


class TestInputValidator(unittest.TestCase):
    """Test InputValidator class."""
    
    def test_validate_prompt_valid(self):
        """Test validating valid prompts."""
        prompt = "This is a valid prompt"
        result = InputValidator.validate_prompt(prompt)
        self.assertEqual(result, prompt.strip())
    
    def test_validate_prompt_empty(self):
        """Test validating empty prompt."""
        with self.assertRaises(ValueError):
            InputValidator.validate_prompt("")
    
    def test_validate_prompt_too_long(self):
        """Test validating too long prompt."""
        long_prompt = "a" * 3000
        with self.assertRaises(ValueError):
            InputValidator.validate_prompt(long_prompt, max_length=2000)
    
    def test_validate_prompt_too_short(self):
        """Test validating too short prompt."""
        with self.assertRaises(ValueError):
            InputValidator.validate_prompt("", min_length=1)
    
    def test_validate_prompt_sanitization(self):
        """Test prompt sanitization."""
        prompt = "Test   prompt\nwith\twhitespace"
        result = InputValidator.validate_prompt(prompt)
        self.assertNotIn("\n", result)
        self.assertNotIn("\t", result)
    
    def test_validate_language_code_valid(self):
        """Test validating valid language codes."""
        self.assertTrue(InputValidator.validate_language_code("en"))
        self.assertTrue(InputValidator.validate_language_code("fa"))
        self.assertTrue(InputValidator.validate_language_code("ES"))
        self.assertTrue(InputValidator.validate_language_code("Fr"))
    
    def test_validate_language_code_invalid(self):
        """Test validating invalid language codes."""
        self.assertFalse(InputValidator.validate_language_code(""))
        self.assertFalse(InputValidator.validate_language_code("eng"))
        self.assertFalse(InputValidator.validate_language_code("1"))
        self.assertFalse(InputValidator.validate_language_code("EN-US"))
        self.assertFalse(InputValidator.validate_language_code(None))
    
    def test_validate_number_valid(self):
        """Test validating valid numbers."""
        self.assertTrue(InputValidator.validate_number("10"))
        self.assertTrue(InputValidator.validate_number("1"))
        self.assertTrue(InputValidator.validate_number("10000"))
        self.assertTrue(InputValidator.validate_number("500", min_val=1, max_val=1000))
    
    def test_validate_number_invalid(self):
        """Test validating invalid numbers."""
        self.assertFalse(InputValidator.validate_number(""))
        self.assertFalse(InputValidator.validate_number("abc"))
        self.assertFalse(InputValidator.validate_number("0"))
        self.assertFalse(InputValidator.validate_number("10001"))
        self.assertFalse(InputValidator.validate_number("10", min_val=20, max_val=100))
    
    def test_sanitize_command_input(self):
        """Test command input sanitization."""
        input_str = "test command"
        result = InputValidator.sanitize_command_input(input_str)
        self.assertEqual(result, input_str)
        
        # Test with control characters
        input_str = "test\x00command"
        result = InputValidator.sanitize_command_input(input_str)
        self.assertNotIn("\x00", result)
        
        # Test with None
        result = InputValidator.sanitize_command_input(None)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()

