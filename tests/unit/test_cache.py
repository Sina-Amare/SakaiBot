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
        self.manager = CacheManager()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up cache files if they exist
        from src.core.constants import PV_CACHE_FILE, GROUP_CACHE_FILE
        for cache_file in [PV_CACHE_FILE, GROUP_CACHE_FILE]:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except:
                    pass
    
    def test_save_and_load_pv_cache(self):
        """Test saving and loading PV cache."""
        data = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        self.manager.save_pv_cache(data)
        
        loaded, _ = self.manager.load_pv_cache()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["id"], 1)
    
    def test_load_pv_cache_nonexistent(self):
        """Test loading non-existent PV cache."""
        result, timestamp = self.manager.load_pv_cache()
        # Should return None or empty list if file doesn't exist
        self.assertIn(result, [None, []])
    
    def test_save_group_cache(self):
        """Test saving group cache."""
        data = [{"id": 1, "title": "test_group"}]
        self.manager.save_group_cache(data)
        
        loaded, _ = self.manager.load_group_cache()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["id"], 1)
    
    def test_cache_persistence(self):
        """Test that cache persists across instances."""
        data = [{"id": 1, "name": "test"}]
        self.manager.save_pv_cache(data)
        
        # Create new instance
        new_manager = CacheManager()
        loaded, _ = new_manager.load_pv_cache()
        self.assertIsNotNone(loaded)
        self.assertGreater(len(loaded), 0)


if __name__ == "__main__":
    unittest.main()

