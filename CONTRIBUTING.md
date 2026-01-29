# Contributing to SakaiBot

Thank you for your interest in contributing to SakaiBot! This guide will help you get started.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment.

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists in [Issues](https://github.com/Sina-Amare/SakaiBot/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version)

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with:
   - Clear description of the feature
   - Use case and motivation
   - Proposed implementation (if any)

### Pull Requests

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/SakaiBot.git
   ```
3. **Create branch**:
   ```bash
   git checkout -b feat/my-feature
   ```
4. **Make changes**:
   - Follow code style guidelines
   - Add tests for new features
   - Update documentation
5. **Commit** using [Conventional Commits](https://conventionalcommits.org/):
   ```bash
   git commit -m "feat(ai): add new analysis mode"
   ```
6. **Push** to your fork:
   ```bash
   git push origin feat/my-feature
   ```
7. **Open Pull Request** on GitHub

## Development Setup

```bash
# Clone repository
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Style

- **Formatter**: Black (line length 100)
- **Linter**: Ruff
- **Type Checker**: MyPy
- **Docstrings**: Google style

Run quality checks:

```bash
pre-commit run --all-files
```

## Commit Messages

Use [Conventional Commits](https://conventionalcommits.org/):

| Type       | Description      |
| ---------- | ---------------- |
| `feat`     | New feature      |
| `fix`      | Bug fix          |
| `docs`     | Documentation    |
| `style`    | Formatting       |
| `refactor` | Code restructure |
| `test`     | Tests            |
| `chore`    | Maintenance      |

Examples:

```
feat(ai): add web search to /prompt command
fix(tts): resolve encoding issue
docs: update installation guide
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src

# Specific tests
pytest tests/unit/
```

## Documentation

Update relevant documentation when making changes:

- `README.md` - Overview and quick start
- `docs/COMMANDS.md` - Command reference
- `docs/CONFIGURATION.md` - Config options
- Inline docstrings for functions

## Review Process

1. All PRs require at least one review
2. CI checks must pass
3. Code must be documented
4. Tests must be included for new features

## Questions?

- Open a [Discussion](https://github.com/Sina-Amare/SakaiBot/discussions)
- Check existing issues for similar questions

---

Thank you for contributing! 🎉
