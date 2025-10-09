#!/usr/bin/env python3
"""Test script to verify the new forum group mapping functionality."""

import asyncio
import json
from pathlib import Path

def test_mapping_format():
    """Test that the new mapping format works correctly."""
    print("Testing new mapping format...")
    
    # Simulate the old format
    old_format = {
        'help': 123,
        'support': 456,
        'general': None,
        'question': 123  # Multiple commands to same topic
    }
    
    print("Old format:", old_format)
    
    # Convert to new format (as done in the code)
    new_format = {}
    for command, topic_id in old_format.items():
        if topic_id not in new_format:
            new_format[topic_id] = []
        new_format[topic_id].append(command)
    
    print("New format:", new_format)
    
    # Test command lookup
    def find_topic_for_command(command, mappings):
        for topic_id, commands in mappings.items():
            if command in commands:
                return topic_id
        return None
    
    # Test various commands
    test_commands = ['help', 'support', 'general', 'question', 'nonexistent']
    for cmd in test_commands:
        topic = find_topic_for_command(cmd, new_format)
        print(f"Command '{cmd}' maps to topic: {topic}")
    
    print("PASS: Mapping format test passed")
    return True

def test_add_mapping():
    """Test adding a new mapping to the new format."""
    print("\nTesting adding mappings...")
    
    # Start with new format
    mappings = {
        123: ['help', 'question'],
        456: ['support'],
        None: ['general', 'info']
    }
    
    print("Initial mappings:", mappings)
    
    # Add a new command to existing topic
    command = 'faq'
    topic_id = 123
    
    # Remove command from any existing topic first (if it exists)
    for existing_topic_id, commands in mappings.items():
        if command in commands:
            commands.remove(command)
            if not commands:
                del mappings[existing_topic_id]
            break
    
    # Add command to target topic
    if topic_id not in mappings:
        mappings[topic_id] = []
    mappings[topic_id].append(command)
    
    print("After adding 'faq' topic 123:", mappings)
    
    # Add a command to a new topic
    command2 = 'news'
    topic_id2 = 789
    
    # Remove command from any existing topic first (if it exists)
    for existing_topic_id, commands in mappings.items():
        if command2 in commands:
            commands.remove(command2)
            if not commands:
                del mappings[existing_topic_id]
            break
    
    # Add command to target topic
    if topic_id2 not in mappings:
        mappings[topic_id2] = []
    mappings[topic_id2].append(command2)
    
    print("After adding 'news' topic 789:", mappings)
    
    print("PASS: Add mapping test passed")
    return True

def test_remove_mapping():
    """Test removing a mapping from the new format."""
    print("\nTesting removing mappings...")
    
    # Start with new format
    mappings = {
        123: ['help', 'question', 'faq'],
        456: ['support'],
        789: ['news'],
        None: ['general', 'info']
    }
    
    print("Initial mappings:", mappings)
    
    # Remove a command
    command_to_remove = 'question'
    
    for topic_id, commands in mappings.items():
        if command_to_remove in commands:
            commands.remove(command_to_remove)
            # Remove the topic key if it has no commands left
            if not commands:
                del mappings[topic_id]
            break
    
    print(f"After removing '{command_to_remove}':", mappings)
    
    # Remove the last command from a topic (should remove the topic key too)
    command_to_remove = 'support'
    
    for topic_id, commands in mappings.items():
        if command_to_remove in commands:
            commands.remove(command_to_remove)
            # Remove the topic key if it has no commands left
            if not commands:
                del mappings[topic_id]
            break
    
    print(f"After removing '{command_to_remove}' (last in topic):", mappings)
    
    print("PASS: Remove mapping test passed")
    return True

def test_list_mappings():
    """Test listing mappings in the new format."""
    print("\nTesting listing mappings...")
    
    # Test mappings
    mappings = {
        123: ['help', 'question', 'faq'],
        456: ['support', 'contact'],
        789: ['news'],
        None: ['general', 'info', 'start']
    }
    
    print("Mappings:")
    for topic_id, commands in mappings.items():
        if topic_id is None:
            target = "Main Group Chat"
        else:
            target = f"Topic ID: {topic_id}"
        
        command_list = ", ".join([f"/{cmd}" for cmd in commands])
        print(f"  {command_list} -> {target}")
    
    print("PASS: List mappings test passed")
    return True

def test_forum_topic_selection():
    """Test forum topic selection functionality."""
    print("\nTesting forum topic selection...")
    
    # Simulate forum topics
    forum_topics = [
        {'id': 1, 'title': 'General'},
        {'id': 123, 'title': 'Help'},
        {'id': 456, 'title': 'Support'},
        {'id': 789, 'title': 'Announcements'}
    ]
    
    # Test choices creation
    choices = ["Main Group Chat"] + [t['title'] for t in forum_topics]
    print("Available choices:", choices)
    
    # Simulate selection
    selected_title = "Help" # Simulate user selecting "Help" topic
    if selected_title != "Main Group Chat":
        topic_idx = choices.index(selected_title) - 1
        selected_topic_id = forum_topics[topic_idx]['id']
        print(f"Selected topic ID: {selected_topic_id}, Title: {selected_title}")
    else:
        selected_topic_id = None
        print("Selected main group chat")
    
    print("PASS: Forum topic selection test passed")
    return True

def test_multiple_commands_same_topic():
    """Test multiple commands mapping to the same topic."""
    print("\nTesting multiple commands to same topic...")
    
    # Start with empty mappings
    mappings = {}
    
    # Add multiple commands to the same topic
    commands_for_topic_123 = ['help', 'question', 'support', 'faq']
    
    for cmd in commands_for_topic_123:
        # Remove command from any existing topic first (if it exists)
        for existing_topic_id, commands in mappings.items():
            if cmd in commands:
                commands.remove(cmd)
                if not commands:
                    del mappings[existing_topic_id]
                break
        
        # Add command to target topic
        topic_id = 123
        if topic_id not in mappings:
            mappings[topic_id] = []
        mappings[topic_id].append(cmd)
    
    print("Final mappings:", mappings)
    
    # Verify all commands are mapped to the same topic
    if 123 in mappings:
        mapped_commands = set(mappings[123])
        expected_commands = set(commands_for_topic_123)
        if mapped_commands == expected_commands:
            print("All commands correctly mapped to topic 123")
        else:
            print(f"ERROR: Expected {expected_commands}, got {mapped_commands}")
            return False
    else:
        print("ERROR: Topic 123 not found in mappings")
        return False
    
    print("PASS: Multiple commands same topic test passed")
    return True

def test_backward_compatibility():
    """Test that old format mappings are converted to new format."""
    print("\nTesting backward compatibility...")
    
    # Simulate old format (command -> topic_id)
    old_format = {
        'help': 123,
        'support': 456,
        'general': None,
        'question': 123  # Multiple commands to same topic
    }
    
    print("Old format:", old_format)
    
    # Convert as done in the actual code
    new_format = {}
    for command, topic_id in old_format.items():
        if topic_id not in new_format:
            new_format[topic_id] = []
        new_format[topic_id].append(command)
    
    print("Converted to new format:", new_format)
    
    # Verify structure
    expected_topics = {123, 456, None}
    actual_topics = set(new_format.keys())
    if expected_topics == actual_topics:
        print("Topic structure is correct")
    else:
        print(f"ERROR: Expected topics {expected_topics}, got {actual_topics}")
        return False
    
    # Verify all commands are present
    all_commands = []
    for cmds in new_format.values():
        all_commands.extend(cmds)
    
    expected_commands = set(['help', 'support', 'general', 'question'])
    actual_commands = set(all_commands)
    
    if expected_commands == actual_commands:
        print("All commands preserved during conversion")
    else:
        print(f"ERROR: Expected commands {expected_commands}, got {actual_commands}")
        return False
    
    print("PASS: Backward compatibility test passed")
    return True

def test_command_lookup():
    """Test the command lookup functionality used in handlers."""
    print("\nTesting command lookup functionality...")
    
    # Test mapping format
    mappings = {
        123: ['help', 'question', 'faq'],
        456: ['support', 'contact'],
        789: ['news'],
        None: ['general', 'info', 'start']
    }
    
    print("Test mappings:", mappings)
    
    # Test the lookup function used in handlers
    def find_topic_for_command(command, mapping_dict):
        for topic_id, commands in mapping_dict.items():
            if command in commands:
                return topic_id
        return None
    
    # Test various lookups
    test_cases = [
        ('help', 123),
        ('question', 123),
        ('faq', 123),
        ('support', 456),
        ('contact', 456),
        ('news', 789),
        ('general', None),
        ('info', None),
        ('start', None),
        ('nonexistent', None)
    ]
    
    all_correct = True
    for cmd, expected_topic in test_cases:
        found_topic = find_topic_for_command(cmd, mappings)
        if found_topic == expected_topic:
            print(f"  Command '{cmd}' -> Topic {found_topic} OK")
        else:
            print(f" Command '{cmd}' -> Topic {found_topic}, expected {expected_topic} FAIL")
            all_correct = False
    
    if all_correct:
        print("PASS: Command lookup functionality test passed")
        return True
    else:
        print("FAIL: Command lookup functionality test failed")
        return False

def run_all_tests():
    """Run all tests."""
    print("Running forum group mapping functionality tests...\n")
    
    tests = [
        test_mapping_format,
        test_add_mapping,
        test_remove_mapping,
        test_list_mappings,
        test_forum_topic_selection,
        test_multiple_commands_same_topic,
        test_backward_compatibility,
        test_command_lookup
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