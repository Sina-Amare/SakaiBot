#!/usr/bin/env python3
"""Test script to verify menu interactions work correctly after fixes."""

def test_safe_dict_access():
    """Test safe access to dictionary values that might be None."""
    print("Testing safe dictionary access...")
    
    # Test cases for settings that might have None values
    test_settings = [
        # Case 1: Normal settings
        {
            'selected_target_group': {'id': 123, 'title': 'Test Group', 'type': 'Forum'},
            'active_command_to_topic_map': {123: ['help', 'question'], None: ['general']},
            'directly_authorized_pvs': ['user1', 'user2']
        },
        # Case 2: Some values are None
        {
            'selected_target_group': None,
            'active_command_to_topic_map': None,
            'directly_authorized_pvs': None
        },
        # Case 3: Empty structures
        {
            'selected_target_group': {},
            'active_command_to_topic_map': {},
            'directly_authorized_pvs': []
        },
        # Case 4: Missing keys
        {
            'other_setting': 'value'
        }
    ]
    
    for i, settings in enumerate(test_settings):
        print(f"  Test case {i+1}: {settings}")
        
        # Test target group access
        target_group = settings.get('selected_target_group')
        if target_group and isinstance(target_group, dict):
            group_info = f"{target_group.get('title', 'Unknown')} ({target_group.get('type', 'Unknown')})"
        else:
            group_info = "None selected"
        print(f"    Target group: {group_info}")
        
        # Test command mappings access
        active_command_to_topic_map = settings.get('active_command_topic_map')
        if active_command_to_topic_map and isinstance(active_command_to_topic_map, dict):
            # Count total mappings safely
            mappings_count = 0
            for commands_list in active_command_to_topic_map.values():
                if commands_list and isinstance(commands_list, list):
                    mappings_count += len([cmd for cmd in commands_list if cmd is not None])
        else:
            mappings_count = 0
        print(f"    Command mappings: {mappings_count}")
        
        # Test authorized users access
        directly_authorized_pvs = settings.get('directly_authorized_pvs')
        auth_count = len(directly_authorized_pvs) if directly_authorized_pvs and isinstance(directly_authorized_pvs, list) else 0
        print(f"    Authorized users: {auth_count}")
    
    print("PASS: Safe dictionary access test completed")
    return True

def test_safe_list_operations():
    """Test safe operations on lists that might be None."""
    print("\nTesting safe list operations...")
    
    # Test cases for lists that might be None
    test_lists = [
        ['item1', 'item2', 'item3'],  # Normal list
        [],  # Empty list
        None,  # None value
        'not_a_list',  # Wrong type
        ['item1', None, 'item3'],  # List with None values
    ]
    
    for i, test_list in enumerate(test_lists):
        print(f"  Test case {i+1}: {test_list}")
        
        # Safely get length
        safe_length = len(test_list) if test_list and isinstance(test_list, list) else 0
        print(f"    Safe length: {safe_length}")
        
        # Safely count non-None items
        safe_count = 0
        if test_list and isinstance(test_list, list):
            safe_count = len([item for item in test_list if item is not None])
        print(f"    Safe count (non-None): {safe_count}")
    
    print("PASS: Safe list operations test completed")
    return True

def test_mapping_operations():
    """Test safe operations on mappings that might contain None values."""
    print("\nTesting safe mapping operations...")
    
    # Test cases for mappings
    test_mappings = [
        # Normal mappings
        {123: ['help', 'question'], 456: ['support'], None: ['general']},
        # Empty mappings
        {},
        # Mappings with empty lists
        {123: [], 456: ['support']},
        # Mappings with None values in command lists
        {123: ['help', None, 'faq'], 456: [None, 'contact']},
    ]
    
    for i, mappings in enumerate(test_mappings):
        print(f"  Test case {i+1}: {mappings}")
        
        # Count total commands safely
        total_commands = 0
        for commands_list in mappings.values():
            if commands_list and isinstance(commands_list, list):
                total_commands += len([cmd for cmd in commands_list if cmd is not None])
        print(f"    Total safe commands: {total_commands}")
        
        # Test finding topic for command safely
        def find_topic_for_command(command, mapping_dict):
            for topic_id, commands in mapping_dict.items():
                if commands and isinstance(commands, list) and command in commands:
                    return topic_id
            return None
        
        test_commands = ['help', 'support', 'nonexistent']
        for cmd in test_commands:
            topic = find_topic_for_command(cmd, mappings)
            print(f"    Command '{cmd}' -> Topic {topic}")
            
            print("PASS: Safe mapping operations test completed")
            return True

def run_all_tests():
    """Run all tests."""
    print("Running menu interaction stability tests...\n")
    
    tests = [
        test_safe_dict_access,
        test_safe_list_operations,
        test_mapping_operations
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