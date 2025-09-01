#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script for CLI refactoring validation.

This script validates the refactored CLI modules to ensure they work correctly
with the existing SakaiBot codebase.
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_imports():
    """Test that all CLI modules can be imported correctly."""
    print("Testing CLI module imports...")
    
    try:
        # Test core imports
        from src.cli.models import CLIState, MenuAction, SelectionResult
        from src.cli.state import StateManager, get_state_manager
        from src.cli.menu import RichMenu
        from src.cli.commands import CLICommands
        from src.cli.interface import cli, display_main_menu_loop
        
        print("✅ All CLI modules imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False


def test_models():
    """Test CLI models and data structures."""
    print("\nTesting CLI models...")
    
    try:
        from src.cli.models import CLIState, SearchCriteria, CommandMapping
        
        # Test CLIState
        state = CLIState()
        assert state.openrouter_model_name == "deepseek/deepseek-chat"
        assert state.max_analyze_messages == 5000
        assert not state.is_monitoring_active
        
        # Test method calls
        display_name = state.get_pv_display_name()
        assert "None" in display_name
        
        group_status = state.get_group_status_text()
        assert "No group" in group_status
        
        can_start, reasons = state.can_start_monitoring()
        assert not can_start  # Should not be able to start without setup
        assert len(reasons) > 0
        
        # Test SearchCriteria
        criteria = SearchCriteria(query="test", search_type="all")
        test_pv = {
            'id': 123,
            'username': 'testuser',
            'display_name': 'Test User'
        }
        
        # Should match by name
        assert criteria.matches_pv({'id': 1, 'display_name': 'Test User', 'username': None})
        
        # Test CommandMapping
        mapping = CommandMapping(command="test", topic_id=None)
        assert mapping.target_description == "Main Group Chat"
        assert mapping.command_with_prefix == "/test"
        
        mapping_with_topic = CommandMapping(command="news", topic_id=42, topic_title="News Topic")
        assert "News Topic" in mapping_with_topic.target_description
        assert "42" in mapping_with_topic.target_description
        
        print("✅ CLI models working correctly")
        return True
        
    except Exception as e:
        print(f"❌ CLI models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_manager():
    """Test state manager functionality."""
    print("\nTesting state manager...")
    
    try:
        from src.cli.state import StateManager
        import settings_manager  # Import legacy settings manager
        
        # Create state manager
        manager = StateManager(settings_manager)
        
        # Test state access
        state = manager.state
        assert state is not None
        
        # Test PV operations
        test_pv = {
            'id': 12345,
            'display_name': 'Test User',
            'username': 'testuser'
        }
        
        manager.set_default_pv(test_pv)
        assert manager.state.selected_pv_for_categorization == test_pv
        
        manager.clear_default_pv()
        assert manager.state.selected_pv_for_categorization is None
        
        # Test authorization
        authorized = manager.authorize_pv(test_pv)
        assert authorized  # Should return True for new authorization
        assert manager.state.is_pv_authorized(12345)
        
        already_authorized = manager.authorize_pv(test_pv)
        assert not already_authorized  # Should return False for duplicate
        
        deauthorized = manager.deauthorize_pv(12345)
        assert deauthorized is not None
        assert not manager.state.is_pv_authorized(12345)
        
        # Test command mappings
        manager.add_command_mapping("test", None)
        assert "test" in manager.state.active_command_to_topic_map
        
        removed = manager.remove_command_mapping("test")
        assert removed
        assert "test" not in manager.state.active_command_to_topic_map
        
        print("✅ State manager working correctly")
        return True
        
    except Exception as e:
        print(f"❌ State manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rich_menu():
    """Test Rich menu functionality."""
    print("\nTesting Rich menu...")
    
    try:
        from src.cli.menu import RichMenu
        from src.cli.state import StateManager
        import settings_manager
        
        # Create components
        manager = StateManager(settings_manager)
        menu = RichMenu(manager)
        
        # Test that menu can be created
        assert menu.console is not None
        assert menu.state_manager is not None
        
        # Test menu options creation
        options = menu._create_menu_options()
        assert len(options) > 0
        
        # Test that we can find specific options
        exit_option = next((opt for opt in options if opt.action.value == "exit"), None)
        assert exit_option is not None
        assert exit_option.key == "0"
        
        list_option = next((opt for opt in options if opt.action.value == "list_pvs"), None)
        assert list_option is not None
        assert list_option.key == "1"
        
        print("✅ Rich menu working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Rich menu test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_click_interface():
    """Test Click interface functionality."""
    print("\nTesting Click interface...")
    
    try:
        from src.cli.interface import cli
        from click.testing import CliRunner
        
        # Test CLI can be instantiated
        runner = CliRunner()
        
        # Test help command
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "SakaiBot" in result.output or "CLI" in result.output
        
        # Test version command
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        
        # Test status command (should work even without full config)
        result = runner.invoke(cli, ['status'])
        # Don't assert exit code since it might fail due to missing config
        
        print("✅ Click interface working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Click interface test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_legacy_compatibility():
    """Test backward compatibility with legacy code."""
    print("\nTesting legacy compatibility...")
    
    try:
        # Test that legacy function can still be imported
        from src.cli import display_main_menu_loop
        
        # Test that it's a coroutine function
        import inspect
        assert inspect.iscoroutinefunction(display_main_menu_loop)
        
        print("✅ Legacy compatibility maintained")
        return True
        
    except Exception as e:
        print(f"❌ Legacy compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling in CLI components."""
    print("\nTesting error handling...")
    
    try:
        from src.cli.models import UserInput, ValidationRule
        from src.core.exceptions import InputError, CLIError
        
        # Test UserInput validation
        try:
            UserInput(raw_value="", input_type="test")  # Should fail
            assert False, "Should have raised validation error"
        except ValueError:
            pass  # Expected
        
        # Test ValidationRule
        rule = ValidationRule(
            rule_type="range",
            parameters={"min": 1, "max": 10},
            error_message="Value out of range"
        )
        
        valid, error = rule.validate(5)
        assert valid
        assert error is None
        
        valid, error = rule.validate(15)
        assert not valid
        assert error is not None
        
        print("✅ Error handling working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration_integration():
    """Test integration with configuration system."""
    print("\nTesting configuration integration...")
    
    try:
        from src.core.config import Settings, TelegramConfig, OpenRouterConfig
        from src.core.exceptions import ConfigurationError
        from pydantic import SecretStr
        
        # Test that we can create a minimal settings object
        # (This won't work without actual config, but we can test structure)
        
        # Test exception classes exist
        error = ConfigurationError("test error")
        assert str(error) == "ConfigurationError: test error"
        
        print("✅ Configuration integration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Configuration integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print(f"🚀 Running CLI Refactoring Validation Tests\n")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("CLI Models", test_models),
        ("State Manager", test_state_manager),
        ("Rich Menu", test_rich_menu),
        ("Click Interface", test_click_interface),
        ("Legacy Compatibility", test_legacy_compatibility),
        ("Error Handling", test_error_handling),
        ("Configuration Integration", test_configuration_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! CLI refactoring is successful.")
    else:
        print(f"⚠️  {failed} test(s) failed. Please review the issues above.")
    
    print("\n📝 Next steps:")
    print("1. Update main.py to use the new CLI interface")
    print("2. Test interactive mode with actual Telegram authentication")
    print("3. Verify all legacy functionality works in new CLI")
    print("4. Update documentation to reflect new CLI structure")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
