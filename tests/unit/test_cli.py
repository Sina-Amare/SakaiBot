"""Unit tests for CLI functionality."""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import CLI state with mocked config
from src.cli.state import CLIState


class TestCLIState(unittest.TestCase):
    """Test CLI state management functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock config
        mock_config = Mock()
        mock_config.is_ai_enabled = True
        self.cli_state = CLIState(mock_config)
    
    def test_initial_state(self):
        """Test initial CLI state."""
        # Note: CLIState doesn't have is_authenticated, current_group_id, or current_context properties
        # These were likely from a different version or misunderstanding
        # We'll test the actual properties that exist
        self.assertTrue(hasattr(self.cli_state, 'config'))
        self.assertIsNone(self.cli_state.selected_target_group)
        self.assertEqual(self.cli_state.directly_authorized_pvs, [])
        self.assertFalse(self.cli_state.is_monitoring_active)


if __name__ == "__main__":
    unittest.main()

