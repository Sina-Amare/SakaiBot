"""Extended unit tests for helper utilities."""

import unittest
from pathlib import Path
import tempfile
import os

from src.utils.helpers import (
    format_file_size,
    ensure_directory,
    parse_command_with_params
)


class TestHelpersExtended(unittest.TestCase):
    """Extended tests for helper utility functions."""
    
    def test_format_file_size(self):
        """Test file size formatting."""
        self.assertEqual(format_file_size(0), "0.0 B")
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_file_size(1024 * 1024 * 1024), "1.0 GB")
        self.assertIn("TB", format_file_size(1024 * 1024 * 1024 * 1024))
    
    def test_ensure_directory(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test" / "nested" / "dir"
            result = ensure_directory(test_path)
            self.assertTrue(result.exists())
            self.assertTrue(result.is_dir())
            self.assertEqual(result, test_path)
    
    def test_parse_command_with_params(self):
        """Test command parsing with parameters."""
        # Test with parameters
        params, remaining = parse_command_with_params(
            "/command key1=value1 key2=value2 rest of text",
            "/command"
        )
        self.assertIn("key1", params)
        self.assertEqual(params["key1"], "value1")
        self.assertIn("key2", params)
        self.assertEqual(params["key2"], "value2")
        self.assertIn("rest", remaining.lower())
        
        # Test without parameters
        params, remaining = parse_command_with_params(
            "/command just text",
            "/command"
        )
        self.assertEqual(len(params), 0)
        self.assertIn("just text", remaining)
        
        # Test with wrong prefix
        params, remaining = parse_command_with_params(
            "/other text",
            "/command"
        )
        self.assertEqual(len(params), 0)
        self.assertEqual(remaining, "/other text")


if __name__ == "__main__":
    unittest.main()

