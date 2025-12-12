# Development Guide

Guide for contributing to and developing SakaiBot.

## Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Quality Tools

| Tool   | Purpose         | Command                |
| ------ | --------------- | ---------------------- |
| Black  | Code formatting | `black src tests`      |
| Ruff   | Linting         | `ruff check src tests` |
| MyPy   | Type checking   | `mypy src`             |
| Pytest | Testing         | `pytest`               |

### Running All Checks

```bash
# Via pre-commit (recommended)
pre-commit run --all-files

# Or individually
black src tests
ruff check src tests
mypy src
pytest
```

## Testing

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_api_key_manager.py
│   ├── test_circuit_breaker.py
│   ├── test_rate_limiter.py
│   ├── test_rtl_fixer.py
│   └── test_validators.py
├── integration/            # Integration tests
└── conftest.py             # Pytest fixtures
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Verbose output
pytest -v

# Specific file
pytest tests/unit/test_api_key_manager.py
```

### Writing Tests

```python
import pytest
from src.ai.api_key_manager import APIKeyManager

class TestAPIKeyManager:
    def test_rotation_on_rate_limit(self):
        manager = APIKeyManager(["key1", "key2"])

        # First key should be current
        assert manager.get_current_key() == "key1"

        # Mark as rate limited
        manager.mark_key_rate_limited()

        # Should rotate to second key
        assert manager.get_current_key() == "key2"
```

## Code Style

### Formatting

- **Line length**: 100 characters
- **Formatter**: Black
- **Import sorting**: Ruff (isort rules)

### Type Hints

```python
from typing import Optional, List, Dict

def process_messages(
    messages: List[Dict[str, str]],
    max_count: int = 100
) -> Optional[str]:
    """Process messages and return summary."""
    ...
```

### Docstrings

```python
def analyze_conversation(
    messages: List[Dict[str, Any]],
    mode: str = "general"
) -> str:
    """
    Analyze conversation messages.

    Args:
        messages: List of message dictionaries
        mode: Analysis mode ('general', 'fun', 'romance')

    Returns:
        Analysis result text

    Raises:
        AIProcessorError: If analysis fails
    """
    ...
```

## Project Configuration

### pyproject.toml

Key sections:

```toml
[tool.black]
line-length = 100
target-version = ['py310', 'py311', 'py312']

[tool.ruff]
line-length = 100
select = ["E", "W", "F", "I", "B", "C4", "UP"]

[tool.mypy]
python_version = "3.10"
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["unit", "integration", "slow"]
```

## Commit Guidelines

Use [Conventional Commits](https://conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type       | Description                  |
| ---------- | ---------------------------- |
| `feat`     | New feature                  |
| `fix`      | Bug fix                      |
| `docs`     | Documentation                |
| `style`    | Formatting (no logic change) |
| `refactor` | Code restructure             |
| `test`     | Test additions               |
| `chore`    | Maintenance                  |

### Examples

```
feat(ai): add web search grounding to /prompt command
fix(tts): resolve audio encoding issue with Persian text
docs: update command reference for /analyze flags
refactor(handlers): extract common validation logic
test(api_key): add rotation edge case tests
```

## Branch Strategy

```
main              # Production-ready code
├── feat/xxx      # Feature branches
├── fix/xxx       # Bug fix branches
└── chore/xxx     # Maintenance branches
```

## Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Run quality checks
4. Push and create PR
5. Wait for review
6. Merge via squash

## Adding New Commands

### 1. Create Handler

```python
# src/telegram/handlers/my_handler.py

class MyHandler(BaseHandler):
    async def process_command(self, ...):
        ...
```

### 2. Register in Event Handlers

```python
# src/telegram/event_handlers.py

async def handle_my_command(event):
    handler = MyHandler(...)
    await handler.process_command(event, ...)
```

### 3. Add to Help System

```python
# src/telegram/commands/self_commands.py

# Add to /help output
```

### 4. Write Tests

```python
# tests/unit/test_my_handler.py
```

## Adding New LLM Provider

1. Implement `LLMProvider` interface
2. Add to `ai/providers/`
3. Update `AIProcessor` initialization
4. Add configuration options
5. Write tests
