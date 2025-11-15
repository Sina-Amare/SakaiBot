"""Unit tests for cache manager."""

import unittest
import json
import tempfile
import os
from pathlib import Path

from src.utils.cache import CacheManager


class TestCacheManager(unittest.TestCase):
    """Test CacheManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "test_cache.json")
        self.manager = CacheManager(cache_file=self.cache_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        os.rmdir(self.temp_dir)
    
    def test_save_and_load_cache(self):
        """Test saving and loading cache."""
        data = {"key1": "value1", "key2": "value2"}
        self.manager.save_cache(data)
        
        loaded = self.manager.load_cache()
        self.assertEqual(loaded, data)
    
    def test_load_cache_nonexistent(self):
        """Test loading non-existent cache."""
        manager = CacheManager(cache_file="nonexistent_file.json")
        result = manager.load_cache()
        self.assertEqual(result, {})
    
    def test_save_cache_creates_directory(self):
        """Test that save_cache creates directory if needed."""
        nested_dir = os.path.join(self.temp_dir, "nested", "path")
        cache_file = os.path.join(nested_dir, "cache.json")
        manager = CacheManager(cache_file=cache_file)
        
        data = {"test": "data"}
        manager.save_cache(data)
        
        self.assertTrue(os.path.exists(cache_file))
        loaded = manager.load_cache()
        self.assertEqual(loaded, data)
    
    def test_cache_persistence(self):
        """Test that cache persists across instances."""
        data = {"persistent": "data"}
        self.manager.save_cache(data)
        
        # Create new instance
        new_manager = CacheManager(cache_file=self.cache_file)
        loaded = new_manager.load_cache()
        self.assertEqual(loaded, data)


if __name__ == "__main__":
    unittest.main()

