"""Unit tests for CLI state."""

import unittest
from unittest.mock import Mock

from src.cli.state import CLIState


class TestCLIState(unittest.TestCase):
    """Test CLIState class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_config.is_ai_enabled = True
        self.state = CLIState(self.mock_config)
    
    def test_initial_state(self):
        """Test initial CLI state."""
        self.assertIsNone(self.state.selected_target_group)
        self.assertEqual(self.state.directly_authorized_pvs, [])
        self.assertFalse(self.state.is_monitoring_active)
        self.assertFalse(self.state.settings_saved_on_cli_exit)
    
    def test_to_settings_dict(self):
        """Test converting state to settings dictionary."""
        self.state._raw_selected_target_group = "test_group"
        self.state._active_command_to_topic_map = {"cmd": "topic"}
        self.state.directly_authorized_pvs = [123, 456]
        self.state.is_monitoring_active = True
        
        settings = self.state.to_settings_dict()
        
        self.assertEqual(settings["selected_target_group"], "test_group")
        self.assertEqual(settings["active_command_to_topic_map"], {"cmd": "topic"})
        self.assertEqual(settings["directly_authorized_pvs"], [123, 456])
        self.assertTrue(settings["is_monitoring_active"])


if __name__ == "__main__":
    unittest.main()

