"""Unit tests for helper utilities."""

import unittest
from datetime import timedelta

from src.utils.helpers import (
    safe_filename,
    format_duration,
    truncate_text,
    split_message,
    clean_temp_files
)


class TestHelpers(unittest.TestCase):
    """Test helper utility functions."""
    
    def test_safe_filename(self):
        """Test safe filename conversion."""
        self.assertEqual(safe_filename("test.txt"), "test.txt")
        self.assertEqual(safe_filename("test<>file.txt"), "test__file.txt")
        self.assertEqual(safe_filename("test/file.txt"), "test_file.txt")
        self.assertEqual(safe_filename("  test.txt  "), "test.txt")
        self.assertEqual(safe_filename(""), "unnamed")
        self.assertEqual(safe_filename("."), "unnamed")
        long_name = "a" * 300
        result = safe_filename(long_name)
        self.assertLessEqual(len(result), 255)
    
    def test_format_duration(self):
        """Test duration formatting."""
        self.assertEqual(format_duration(0), "0s")
        self.assertEqual(format_duration(30), "30s")
        self.assertEqual(format_duration(90), "1m 30s")
        self.assertEqual(format_duration(3661), "1h 1m")  # Hours format doesn't include seconds
        self.assertEqual(format_duration(86400), "24h 0m")  # 24 hours
        self.assertEqual(format_duration(90061), "25h 1m")  # 25 hours 1 minute
    
    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a long text"
        # With max_length=10 and suffix="...", we get 10-3=7 chars + "..." = "This is..."
        self.assertEqual(truncate_text(text, 10), "This is...")
        self.assertEqual(truncate_text(text, 100), text)
        self.assertEqual(truncate_text("", 10), "")
        self.assertEqual(truncate_text("short", 10), "short")
    
    def test_split_message(self):
        """Test message splitting."""
        short_text = "Short message"
        result = split_message(short_text, max_length=100)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], short_text)
        
        long_text = "a" * 5000
        result = split_message(long_text, max_length=1000)
        self.assertGreater(len(result), 1)
        for chunk in result:
            self.assertLessEqual(len(chunk), 1000)
    
    def test_split_message_with_reserve(self):
        """Test message splitting with reserved length."""
        text = "a" * 5000
        result = split_message(text, max_length=1000, reserve_length=100)
        for chunk in result:
            self.assertLessEqual(len(chunk), 900)  # 1000 - 100
    
    def test_clean_temp_files(self):
        """Test temp file cleaning."""
        # Test with None (should not raise)
        clean_temp_files(None)
        
        # Test with multiple None
        clean_temp_files(None, None, None)
        
        # Test with non-existent files (should not raise)
        clean_temp_files("nonexistent_file_12345.txt")


if __name__ == "__main__":
    unittest.main()

