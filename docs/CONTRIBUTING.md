# Contributing to SakaiBot

We welcome contributions to SakaiBot! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Guidelines](#code-guidelines)
4. [Testing](#testing)
5. [Pull Request Process](#pull-request-process)
6. [Issue Reporting](#issue-reporting)
7. [Community Guidelines](#community-guidelines)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A GitHub account

### Fork the Repository

1. Navigate to the [SakaiBot repository](https://github.com/yourusername/SakaiBot)
2. Click the "Fork" button in the top-right corner
3. Clone your fork to your local machine:

```bash
git clone https://github.com/yourusername/SakaiBot.git
cd SakaiBot
```

## Development Setup

### 1. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

### 3. Set Up Configuration

Create a `.env` file for development:

```bash
cp .env.example .env
# Edit .env with your test credentials
```

### 4. Run the Application

```bash
python sakaibot.py
# or
sakaibot
```

## Code Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Write type hints for all function signatures
- Aim for 100 character line length

### Code Structure

- Organize code according to the existing project structure
- Keep functions and classes focused on a single responsibility
- Use meaningful variable and function names
- Write docstrings for all public functions and classes

### Import Organization

Use isort to organize imports in the following order:

1. Standard library imports
2. Related third-party imports
3. Local application/library specific imports

```python
import os
from pathlib import Path

import click
from telethon import TelegramClient

from src.core.config import Config
from src.ai.processor import AIProcessor
```

### Documentation

- Write clear, concise docstrings for all functions and classes
- Document complex logic with inline comments
- Update documentation when adding new features
- Follow the existing documentation style

## Testing

### Running Tests

Before submitting changes, ensure all tests pass:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src

# Run specific test files
pytest tests/test_ai_providers.py
```

### Writing Tests

- Write unit tests for new functionality
- Follow the existing test structure
- Use pytest for test organization
- Mock external dependencies when appropriate
- Test both success and error cases

### Test Coverage

- Aim for high test coverage, especially for critical functionality
- Ensure new features are adequately tested
- Update existing tests when modifying functionality

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

### 2. Make Changes

- Follow the code guidelines
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 3. Commit Changes

- Write clear, descriptive commit messages
- Follow the conventional commit format when possible:
  - `feat: ` for new features
  - `fix: ` for bug fixes
  - `docs: ` for documentation changes
  - `test: ` for test updates
  - `refactor: ` for code restructuring

```bash
git add .
git commit -m "feat: add new AI command for summarization"
```

### 4. Push Changes

```bash
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. Navigate to your fork on GitHub
2. Click "Compare & pull request"
3. Fill out the pull request template:
   - Describe the changes you made
   - Explain why these changes are needed
   - Link to any related issues
   - Include any testing instructions if necessary

## Issue Reporting

### Before Creating an Issue

- Search existing issues to avoid duplicates
- Check the documentation to see if the issue is addressed
- Ensure you're using the latest version

### Creating an Issue

When creating an issue, please include:

- **Title**: Clear, descriptive title
- **Description**: Detailed explanation of the issue
- **Steps to reproduce**: Specific steps to reproduce the issue
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: Python version, OS, etc.
- **Logs**: Any relevant error messages or logs

### Issue Templates

Use the appropriate issue template:

- Bug Report: For reporting bugs
- Feature Request: For suggesting new features
- Enhancement: For improvements to existing features

## Community Guidelines

### Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

### Communication

- Be respectful and considerate
- Provide constructive feedback
- Be patient with new contributors
- Use inclusive language

### Getting Help

- Check the documentation first
- Search existing issues and discussions
- Ask questions in issues or discussions
- Be specific about your problem and what you've tried

## Development Best Practices

### Adding New Features

1. Create an issue to discuss the feature
2. Fork the repository and create a feature branch
3. Implement the feature with appropriate tests
4. Update documentation
5. Submit a pull request

### Bug Fixes

1. Create an issue describing the bug (if it doesn't exist)
2. Fork the repository and create a bugfix branch
3. Write a test that reproduces the bug
4. Implement the fix
5. Verify the test passes
6. Submit a pull request

### Refactoring

- Ensure all tests pass before refactoring
- Make refactoring changes separate from feature additions
- Update tests as needed
- Verify that functionality remains unchanged

## Project Structure

Understanding the project structure will help you contribute effectively:

```
SakaiBot/
├── src/              # Source code
│   ├── ai/          # AI providers and processors
│   ├── cli/         # Command-line interface
│   ├── core/        # Core functionality
│   ├── telegram/    # Telegram integration
│   └── utils/       # Utilities
├── docs/            # Documentation
├── tests/           # Test suite
├── data/            # User data (sessions, settings)
├── cache/           # Cache files
└── logs/            # Application logs
```

## Security Considerations

- Never commit API keys or sensitive information
- Report security vulnerabilities responsibly
- Follow secure coding practices
- Sanitize user inputs appropriately

## Questions?

If you have questions about contributing, feel free to:

- Open a discussion in the repository
- Ask in an existing issue
- Check the documentation

Thank you for contributing to SakaiBot!
