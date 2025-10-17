"""Test utility functions and helpers."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def assert_no_errors(errors_list, test_case):
    """Assert that no errors occurred."""
    test_case.assertEqual(len(errors_list), 0, f"Expected no errors but got: {errors_list}")


def assert_has_errors(errors_list, test_case, expected_count=None):
    """Assert that errors occurred."""
    if expected_count is not None:
        test_case.assertEqual(len(errors_list), expected_count, 
                              f"Expected {expected_count} errors but got {len(errors_list)}: {errors_list}")
    else:
        test_case.assertGreater(len(errors_list), 0, 
                                f"Expected errors but got none: {errors_list}")


def assert_valid_language_code(code, test_case, expected_valid=True, expected_std=None):
    """Assert language code validation results."""
    from src.utils.translation_utils import validate_language_code
    is_valid, std_code, suggestion = validate_language_code(code)
    
    test_case.assertEqual(is_valid, expected_valid, 
                          f"Expected validity {expected_valid} for code '{code}' but got {is_valid}")
    
    if expected_std is not None:
        test_case.assertEqual(std_code, expected_std,
                            f"Expected standard code '{expected_std}' for code '{code}' but got '{std_code}'")


def assert_parsed_command(command, test_case, expected_target, expected_source, expected_text):
    """Assert parsed command results."""
    from src.utils.translation_utils import parse_enhanced_translate_command
    target, source, text, errors = parse_enhanced_translate_command(command)
    
    test_case.assertEqual(target, expected_target,
                         f"Expected target '{expected_target}' for command '{command}' but got '{target}'")
    test_case.assertEqual(source, expected_source,
                         f"Expected source '{expected_source}' for command '{command}' but got '{source}'")
    test_case.assertEqual(text, expected_text,
                         f"Expected text '{expected_text}' for command '{command}' but got '{text}'")
    assert_no_errors(errors, test_case)


def assert_formatted_response(translation, pronunciation, test_case, expected_response):
    """Assert formatted response results."""
    from src.utils.translation_utils import format_translation_response
    response = format_translation_response(translation, pronunciation)
    
    test_case.assertEqual(response, expected_response,
                         f"Expected response '{expected_response}' but got '{response}'")


def assert_extracted_translation(response, test_case, expected_translation, expected_pronunciation=None):
    """Assert extracted translation results."""
    from src.utils.translation_utils import extract_translation_from_response
    translation, pronunciation = extract_translation_from_response(response)
    
    test_case.assertEqual(translation, expected_translation,
                         f"Expected translation '{expected_translation}' but got '{translation}'")
    
    if expected_pronunciation is not None:
        test_case.assertEqual(pronunciation, expected_pronunciation,
                             f"Expected pronunciation '{expected_pronunciation}' but got '{pronunciation}'")
