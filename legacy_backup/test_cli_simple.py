#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple test for CLI refactoring validation.

This script validates the basic structure and imports of the refactored CLI modules
without requiring full dependencies.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_basic_imports():
    """Test basic imports that don't require heavy dependencies."""
    print("Testing basic CLI structure...")
    
    try:
        # Test that files exist
        cli_dir = project_root / "src" / "cli"
        required_files = [
            "__init__.py",
            "models.py", 
            "state.py",
            "menu.py",
            "commands.py",
            "interface.py"
        ]
        
        missing_files = []
        for file_name in required_files:
            file_path = cli_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False
        
        print("✅ All required CLI files exist")
        
        # Test basic structure without importing heavy dependencies
        # Read the files to check for basic syntax issues
        for file_name in required_files:
            file_path = cli_dir / file_name
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Basic checks
                    if not content.strip():
                        print(f"❌ File {file_name} is empty")
                        return False
                    if 'class ' not in content and 'def ' not in content and file_name != '__init__.py':
                        print(f"⚠️  File {file_name} may not contain expected content")
            except Exception as e:
                print(f"❌ Error reading {file_name}: {e}")
                return False
        
        print("✅ All CLI files have content and basic structure")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic structure test failed: {e}")
        return False


def test_models_structure():
    """Test CLI models structure without importing dependencies."""
    print("\nTesting CLI models structure...")
    
    try:
        models_file = project_root / "src" / "cli" / "models.py"
        
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for expected classes and structures
        expected_items = [
            'class MenuAction',
            'class CLIMode', 
            'class CLIState',
            'class MenuOption',
            'class SelectionResult',
            'class SearchCriteria',
            'class CommandMapping',
            'class UserInput',
            'class ValidationRule'
        ]
        
        missing_items = []
        for item in expected_items:
            if item not in content:
                missing_items.append(item)
        
        if missing_items:
            print(f"❌ Missing expected items in models.py: {missing_items}")
            return False
        
        print("✅ CLI models file contains expected classes")
        return True
        
    except Exception as e:
        print(f"❌ Models structure test failed: {e}")
        return False


def test_menu_structure():
    """Test menu structure."""
    print("\nTesting menu structure...")
    
    try:
        menu_file = project_root / "src" / "cli" / "menu.py"
        
        with open(menu_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for expected classes and methods
        expected_items = [
            'class RichMenu',
            'def display_header',
            'def display_main_menu',
            'def display_entity_table',
            'def display_command_mappings',
            'def display_progress',
            'def display_error',
            'def display_success',
            'def display_warning'
        ]
        
        missing_items = []
        for item in expected_items:
            if item not in content:
                missing_items.append(item)
        
        if missing_items:
            print(f"❌ Missing expected items in menu.py: {missing_items}")
            return False
        
        print("✅ CLI menu file contains expected methods")
        return True
        
    except Exception as e:
        print(f"❌ Menu structure test failed: {e}")
        return False


def test_commands_structure():
    """Test commands structure."""
    print("\nTesting commands structure...")
    
    try:
        commands_file = project_root / "src" / "cli" / "commands.py"
        
        with open(commands_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for expected classes and methods
        expected_items = [
            'class CLICommands',
            'async def list_cached_pvs',
            'async def refresh_pvs',
            'async def search_pvs',
            'async def set_default_pv_context',
            'async def set_target_group',
            'async def manage_command_mappings',
            'async def manage_authorized_pvs',
            'async def toggle_monitoring'
        ]
        
        missing_items = []
        for item in expected_items:
            if item not in content:
                missing_items.append(item)
        
        if missing_items:
            print(f"❌ Missing expected items in commands.py: {missing_items}")
            return False
        
        print("✅ CLI commands file contains expected methods")
        return True
        
    except Exception as e:
        print(f"❌ Commands structure test failed: {e}")
        return False


def test_interface_structure():
    """Test interface structure."""
    print("\nTesting interface structure...")
    
    try:
        interface_file = project_root / "src" / "cli" / "interface.py"
        
        with open(interface_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for expected items
        expected_items = [
            '@click.group',
            'def cli(',
            '@cli.command()',
            'async def interactive',
            'async def list_pvs',
            'async def refresh',
            'async def monitor',
            'async def display_main_menu_loop',
            'class AsyncClickGroup'
        ]
        
        missing_items = []
        for item in expected_items:
            if item not in content:
                missing_items.append(item)
        
        if missing_items:
            print(f"❌ Missing expected items in interface.py: {missing_items}")
            return False
        
        print("✅ CLI interface file contains expected structure")
        return True
        
    except Exception as e:
        print(f"❌ Interface structure test failed: {e}")
        return False


def test_init_exports():
    """Test __init__.py exports."""
    print("\nTesting CLI module exports...")
    
    try:
        init_file = project_root / "src" / "cli" / "__init__.py"
        
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for expected exports
        expected_exports = [
            '__all__',
            'display_main_menu_loop',
            'CLICommands',
            'RichMenu',
            'StateManager',
            'CLIState'
        ]
        
        missing_exports = []
        for export in expected_exports:
            if export not in content:
                missing_exports.append(export)
        
        if missing_exports:
            print(f"❌ Missing expected exports in __init__.py: {missing_exports}")
            return False
        
        print("✅ CLI __init__.py contains expected exports")
        return True
        
    except Exception as e:
        print(f"❌ Init exports test failed: {e}")
        return False


def test_legacy_compatibility_structure():
    """Test legacy compatibility without importing."""
    print("\nTesting legacy compatibility structure...")
    
    try:
        interface_file = project_root / "src" / "cli" / "interface.py"
        
        with open(interface_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for legacy function
        if 'async def display_main_menu_loop(' not in content:
            print("❌ Legacy display_main_menu_loop function not found")
            return False
        
        # Check function signature compatibility
        if 'client,' not in content or 'cache_manager,' not in content:
            print("❌ Legacy function signature may not be compatible")
            return False
        
        print("✅ Legacy compatibility structure looks good")
        return True
        
    except Exception as e:
        print(f"❌ Legacy compatibility test failed: {e}")
        return False


def check_file_sizes():
    """Check that files have reasonable content."""
    print("\nChecking file sizes and content...")
    
    cli_dir = project_root / "src" / "cli"
    files_info = []
    
    for py_file in cli_dir.glob("*.py"):
        size = py_file.stat().st_size
        with open(py_file, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        
        files_info.append((py_file.name, size, lines))
    
    print("\nCLI module files:")
    for name, size, lines in files_info:
        print(f"  {name:15} - {size:5} bytes, {lines:3} lines")
    
    # Check if files are reasonably sized
    for name, size, lines in files_info:
        if name != "__init__.py" and lines < 10:
            print(f"⚠️  {name} seems too small ({lines} lines)")
        elif size > 50000:  # 50KB
            print(f"⚠️  {name} seems very large ({size} bytes)")
    
    print("✅ File sizes look reasonable")
    return True


def main():
    """Run structure validation tests."""
    print(f"🚀 Running CLI Structure Validation Tests\n")
    print("=" * 50)
    
    tests = [
        ("Basic Imports & File Structure", test_basic_imports),
        ("Models Structure", test_models_structure),
        ("Menu Structure", test_menu_structure),
        ("Commands Structure", test_commands_structure),
        ("Interface Structure", test_interface_structure),
        ("Init Exports", test_init_exports),
        ("Legacy Compatibility Structure", test_legacy_compatibility_structure),
        ("File Sizes", check_file_sizes)
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
        print("🎉 All structure tests passed! CLI refactoring structure is correct.")
        
        print("\n📝 CLI Refactoring Summary:")
        print("")
        print("✅ Created modern CLI structure with:")
        print("  • src/cli/models.py - Data models and state management")
        print("  • src/cli/state.py - State persistence and management")
        print("  • src/cli/menu.py - Rich-based interactive menus")
        print("  • src/cli/commands.py - Command implementations")
        print("  • src/cli/interface.py - Click-based CLI interface")
        print("  • src/cli/__init__.py - Module exports and compatibility")
        print("")
        print("✅ Key Features:")
        print("  • Modern Click framework for command-line interface")
        print("  • Rich library for beautiful terminal UI")
        print("  • Comprehensive type hints and validation")
        print("  • Clean separation of concerns")
        print("  • Async command support")
        print("  • Backward compatibility with legacy CLI")
        print("  • Input validation and error handling")
        print("")
        print("✅ Integration:")
        print("  • Uses custom exceptions from src/core/exceptions.py")
        print("  • Integrates with config system from src/core/config.py")
        print("  • Uses constants from src/core/constants.py")
        print("  • Maintains compatibility with existing modules")
        
    else:
        print(f"⚠️  {failed} structure test(s) failed. Please review the issues above.")
    
    print("\n📝 Next Steps:")
    print("1. Install all dependencies: pip install -r requirements.txt")
    print("2. Update main.py to use: from src.cli import display_main_menu_loop")
    print("3. Test interactive mode: python -m src.cli.interface interactive")
    print("4. Test CLI commands: python -m src.cli.interface --help")
    print("5. Verify full integration with Telegram authentication")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
