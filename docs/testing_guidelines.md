# SakaiBot Testing Guidelines

This document outlines the testing practices and structure for the SakaiBot project.

## Test Organization

### Directory Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests between components
├── fixtures/       # Test data and fixtures
├── helpers/        # Test utility functions
└── conftest.py     # pytest configuration and global fixtures
```

### Unit Tests (`tests/unit/`)

Unit tests focus on testing individual components in isolation:

- Fast execution with minimal dependencies
- High code coverage targets (>90%)
- Mock external services when necessary
- Test edge cases and error conditions

### Integration Tests (`tests/integration/`)

Integration tests verify interactions between components:

- May require external services or APIs
- Test end-to-end workflows
- Validate component integration
- Test real-world usage scenarios

### Fixtures (`tests/fixtures/`)

Shared test data and mock objects:

- Common test inputs and expected outputs
- Sample data for various test scenarios
- Mock configurations and responses
- Reusable test data across multiple tests

### Helpers (`tests/helpers/`)

Test utility functions and assertions:

- Common test setup and teardown logic
- Custom assertion functions
- Helper classes for complex test scenarios
- Test data generators and validators

## Running Tests

### Using unittest (Built-in)

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.unit.test_translation

# Run tests with verbose output
python -m unittest tests.unit.test_translation -v
```

### Using pytest (Recommended)

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run tests with specific markers
pytest -m translation
pytest -m tts
pytest -m unit
pytest -m integration

# Run tests with verbose output
pytest -v

# Run tests and generate coverage report
pytest --cov=src --cov-report=html
```

## Test Categories

### Translation Tests

- `tests/unit/test_translation.py` - Unit tests for translation functionality
- `tests/integration/test_translation_integration.py` - Integration tests for translation workflows

### TTS Tests

- `tests/unit/test_tts.py` - Unit tests for text-to-speech functionality
- `tests/integration/test_tts_integration.py` - Integration tests for TTS workflows

### AI Provider Tests

- `tests/unit/test_ai_providers.py` - Unit tests for AI provider interfaces

### CLI Tests

- `tests/unit/test_cli.py` - Unit tests for CLI functionality

### Telegram Handler Tests

- `tests/unit/test_telegram_handlers.py` - Unit tests for Telegram message handlers

## Writing New Tests

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<descriptive_behavior_name>`

### Example Test Structure

```python
import unittest
from unittest.mock import Mock

class TestTranslationComponent(unittest.TestCase):
    """Test translation component functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Initialize test objects
        pass

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up resources
        pass

    def test_valid_translation_command(self):
        """Test parsing of valid translation command."""
        # Arrange
        command = "en Hello world"
        expected_target = "en"
        expected_text = "Hello world"

        # Act
        target, source, text, errors = parse_translation_command(command)

        # Assert
        self.assertEqual(target, expected_target)
        self.assertEqual(text, expected_text)
        self.assertEqual(len(errors), 0)

    def test_invalid_translation_command(self):
        """Test parsing of invalid translation command."""
        # Arrange
        command = "invalid Hello world"

        # Act
        target, source, text, errors = parse_translation_command(command)

        # Assert
        self.assertIsNotNone(target)  # Still returns target even if invalid
        self.assertGreater(len(errors), 0)
```

## Test Data Management

### Using Fixtures

Common test data is stored in `tests/fixtures/` and can be imported in tests:

```python
from tests.fixtures.sample_data import SAMPLE_TRANSLATION_COMMANDS

def test_multiple_commands(self):
    """Test parsing of multiple sample commands."""
    for sample in SAMPLE_TRANSLATION_COMMANDS:
        with self.subTest(command=sample["command"]):
            target, source, text, errors = parse_translation_command(sample["command"])
            self.assertEqual(target, sample["target"])
            self.assertEqual(text, sample["text"])
```

### Custom Assertions

Helper functions in `tests/helpers/test_utils.py` provide common assertions:

```python
from tests.helpers.test_utils import assert_no_errors, assert_parsed_command

def test_command_parsing(self):
    """Test command parsing with helper assertion."""
    assert_parsed_command("en Hello world", self, "en", "auto", "Hello world")
```

## Continuous Integration

Tests are automatically run on:

- Every pull request
- Every commit to main branch
- Scheduled daily runs for integration tests

Coverage reports are generated and uploaded to track test quality over time.

## Best Practices

1. **Keep tests fast** - Use mocks for external dependencies
2. **Write clear test names** - Descriptive names help with debugging
3. **One assertion per test** - Makes failures easier to understand
4. **Use fixtures for shared data** - Reduces duplication
5. **Test edge cases** - Invalid inputs, boundary conditions
6. **Clean up resources** - Use setUp/tearDown methods appropriately
7. **Mock external services** - Integration tests should not depend on network availability

## Contributing

When adding new tests:

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Add new test data to `tests/fixtures/`
4. Use existing helper functions when possible
5. Follow naming conventions
6. Ensure tests pass before submitting PR
