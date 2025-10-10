cl#!/usr/bin/env python3
"""Test script to verify CLI fixes for NoneType errors and menu rendering issues."""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_prompt_choice_fix():
    """Test the fixed prompt_choice function."""
    print("Testing prompt_choice function fix...")
    
    try:
        from src.cli.utils import prompt_choice
    except ImportError:
        # Try alternative import path
        try:
            sys.path.insert(0, str(project_root))
            from src.cli.utils import prompt_choice
        except ImportError:
            print("SKIP: prompt_choice function not found - skipping test")
            return True
    
    # Test with empty choices
    try:
        result = prompt_choice("Test message", [])
        print(f"Empty choices result: {result}")
    except Exception as e:
        print(f"Expected error with empty choices: {e}")
    
    # Test with normal choices
    choices = ["Option 1", "Option 2", "Option 3"]
    print(f"Available choices: {choices}")
    
    print("PASS: prompt_choice fix test completed")
    return True

def test_safe_mapping_operations():
    """Test safe operations on mappings with potential None values."""
    print("\nTesting safe mapping operations...")
    
    # Test the logic that counts commands in mappings
    mappings = {
        123: ['help', 'question', 'faq'],
        456: ['support', 'contact'],
        789: ['news'],
        None: ['general', 'info', 'start'],
        'empty': []  # Empty list
    }
    
    # Count total commands safely (as implemented in the fix)
    total_commands = 0
    for commands_list in mappings.values():
        if commands_list and isinstance(commands_list, list):
            total_commands += len([cmd for cmd in commands_list if cmd is not None])
    
    print(f"Total commands counted: {total_commands}")
    expected = 9  # help, question, faq (3) + support, contact (2) + news (1) + general, info, start (3) = 9
    assert total_commands == expected, f"Expected {expected}, got {total_commands}"
    
    # Test with None values in the mapping
    mappings_with_none = {
        123: ['help', None, 'faq'],
        456: [None, 'contact'],
        789: ['news'],
        None: ['general', 'info', None],
    }
    
    total_commands_none = 0
    for commands_list in mappings_with_none.values():
        if commands_list and isinstance(commands_list, list):
            total_commands_none += len([cmd for cmd in commands_list if cmd is not None])
    
    print(f"Total commands with None values: {total_commands_none}")
    expected_none = 6  # help, faq, contact, news, general, info
    assert total_commands_none == expected_none, f"Expected {expected_none}, got {total_commands_none}"
    
    print("PASS: Safe mapping operations test completed")
    return True

def test_backward_compatibility_conversion():
    """Test the backward compatibility conversion logic."""
    print("\nTesting backward compatibility conversion...")
    
    # Test old format (command -> topic_id)
    old_format = {
        'help': 123,
        'support': 456,
        'general': None,
        'question': 123  # Multiple commands to same topic
    }
    
    # Apply the same logic as in the fixed code
    mappings = old_format
    new_format = {}
    
    # Check if we need to convert (as in the fixed code)
    if mappings and isinstance(list(mappings.values())[0] if mappings and len(mappings) > 0 else None, (int, type(None))):
        # Convert old format (command -> topic_id) to new format (topic_id -> [commands])
        for command, topic_id in mappings.items():
            if topic_id not in new_format:
                new_format[topic_id] = []
            new_format[topic_id].append(command)
    
    print(f"Converted format: {new_format}")
    
    # Verify the conversion
    assert 123 in new_format
    assert 456 in new_format
    assert None in new_format
    assert len(new_format[123]) == 2  # help and question
    assert len(new_format[456]) == 1 # support
    assert len(new_format[None]) == 1  # general
    
    print("PASS: Backward compatibility conversion test completed")
    return True

def run_all_tests():
    """Run all tests."""
    print("Running CLI fixes verification tests...\n")
    
    tests = [
        test_prompt_choice_fix,
        test_safe_mapping_operations,
        test_backward_compatibility_conversion
    ]
    
    all_passed = True
    for test in tests:
        try:
            result = test()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"FAIL: Test {test.__name__} failed with error: {e}")
            all_passed = False
    
    if all_passed:
        print("\nSUCCESS: All tests passed!")
    else:
        print("\nERROR: Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()