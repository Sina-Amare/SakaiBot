"""Unit tests for settings management."""

import unittest
import json
import tempfile
import os
from unittest.mock import patch

from src.core.settings import SettingsManager


class TestSettingsManager(unittest.TestCase):
    """Test SettingsManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_file = os.path.join(self.temp_dir, "settings.json")
        self.manager = SettingsManager(settings_file=self.settings_file)
    
    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.settings_file):
            os.remove(self.settings_file)
        os.rmdir(self.temp_dir)
    
    def test_load_settings_default(self):
        """Test loading default settings."""
        settings = self.manager.load_settings()
        self.assertIsInstance(settings, dict)
        self.assertIn("active_command_to_topic_map", settings)
        self.assertIn("directly_authorized_pvs", settings)
    
    def test_save_and_load_settings(self):
        """Test saving and loading settings."""
        settings = {
            "active_command_to_topic_map": {"test": "value"},
            "directly_authorized_pvs": [123, 456]
        }
        self.manager.save_settings(settings)
        
        loaded = self.manager.load_settings()
        self.assertEqual(loaded, settings)
    
    def test_get_default_settings(self):
        """Test getting default settings."""
        defaults = self.manager.get_default_settings()
        self.assertIsInstance(defaults, dict)
        self.assertIn("active_command_to_topic_map", defaults)
    
    def test_validate_settings_valid(self):
        """Test validating valid settings."""
        settings = {
            "active_command_to_topic_map": {},
            "directly_authorized_pvs": []
        }
        self.assertTrue(self.manager.validate_settings(settings))
    
    def test_validate_settings_invalid(self):
        """Test validating invalid settings."""
        settings = {
            "active_command_to_topic_map": "not a dict"
        }
        self.assertFalse(self.manager.validate_settings(settings))
    
    def test_validate_settings_missing_keys(self):
        """Test validating settings with missing keys."""
        settings = {}
        self.assertFalse(self.manager.validate_settings(settings))


if __name__ == "__main__":
    unittest.main()

