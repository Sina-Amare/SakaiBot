# SakaiBot

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Advanced Telegram userbot with AI capabilities, message automation, and powerful command-line interface.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Overview

SakaiBot is a modern Telegram userbot that integrates AI-powered capabilities for message processing, translation, text-to-speech conversion, and automated message management. Built with Python 3.10+ and designed for extensibility and maintainability.

### Key Capabilities

- 🤖 **AI Integration** - Multiple LLM providers (OpenRouter, Google Gemini)
- 💬 **Smart Commands** - Custom prompts, translations, conversation analysis
- 🎤 **Voice Processing** - Speech-to-text and text-to-speech with high-quality Persian TTS support
- 📨 **Message Management** - Automated categorization and forwarding
- 🔐 **Security** - Multi-level authorization and confirmation flows
- 🎨 **Modern CLI** - Rich terminal interface with colors and progress indicators

## Features

### AI Features
- Multiple LLM provider support (OpenRouter, Google Gemini)
- Custom prompt processing
- Intelligent translation with phonetic support
- Conversation analysis and insights

### Voice Processing
- Speech-to-text (STT) using multiple engines
- Text-to-speech (TTS) with Google Gemini
- High-quality Persian language support
- Automatic language detection
- Multiple voice options

### Telegram Integration
- Full Telegram client integration via Telethon
- Private chat management
- Group message handling
- User verification and authorization
- Message forwarding and categorization

### CLI Interface
- Interactive menu system
- Command-line utilities
- Status monitoring
- Configuration management
- Rich terminal output with progress indicators

## Requirements

- **Python**: 3.10 or higher
- **Telegram API**: Credentials from [my.telegram.org](https://my.telegram.org)
- **AI Provider**: API key from either:
  - [OpenRouter](https://openrouter.ai/) or
  - [Google Gemini](https://deepmind.google/technologies/gemini/)

## Installation

### Prerequisites

Ensure you have Python 3.10+ installed:

```bash
python --version
# Python 3.10.x or higher required
```

### Step 1: Clone the Repository

```bash
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot
```

### Step 2: Create Virtual Environment

**Linux/macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install as a package (recommended)
pip install -e .

# For development, install with dev dependencies
pip install -e ".[dev]"
```

### Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env  # If .env.example exists
# Or create manually
```

Edit `.env` with your credentials (see [Configuration](#configuration)).

## Configuration

Create a `.env` file in the project root with the following variables:

### Required Configuration

```env
# Telegram API Credentials
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+1234567890

# AI Provider (choose one)
LLM_PROVIDER=gemini  # or 'openrouter'
GEMINI_API_KEY=your_gemini_key
# OR
OPENROUTER_API_KEY=your_openrouter_key
```

### Optional Configuration

```env
# TTS-specific API key (uses main GEMINI_API_KEY if not set)
GEMINI_API_KEY_TTS=your_tts_specific_key

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Application paths
DATA_DIR=./data
CACHE_DIR=./cache
LOG_DIR=./logs
```

> **Note**: See the documentation in `docs/` for detailed configuration options.

## Usage

### Command-Line Interface

After installation, the `sakaibot` command is available globally:

```bash
# Check bot status
sakaibot status

# Show help
sakaibot --help
```

### Basic Commands

#### Status Check

```bash
sakaibot status
```

#### Private Chat Management

```bash
# List all private chats
sakaibot pv list

# Search contacts
sakaibot pv search "john"

# Refresh chat list from Telegram
sakaibot pv refresh
```

#### AI Commands

```bash
# Test AI configuration
sakaibot ai test

# Translate text
sakaibot ai translate "Hello" fa

# Custom prompt
sakaibot ai prompt "Explain Python decorators"
```

#### Monitoring

```bash
# Start message monitoring
sakaibot monitor start

# Stop monitoring
sakaibot monitor stop
```

### Telegram Commands

Once monitoring is active, you can use commands in Telegram:

#### Text-to-Speech (TTS)

Convert text to speech using Google Gemini TTS:

```text
/tts سلام، حال شما چطوره؟
```

With voice selection:

```text
/tts voice=Kore Hello, how are you?
```

**Available voices**: Kore, Puck, Fenrir, Zephyr, and more. See [Google Gemini TTS documentation](https://ai.google.dev/gemini-api/docs/speech-generation) for the full list.

#### Translation

```text
/translate Hello fa
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Code Quality

The project uses several tools for code quality:

- **Black**: Code formatter
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pytest**: Testing framework

Run quality checks:

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src

# Run all checks (if using pre-commit)
pre-commit run --all-files
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"    # Skip slow tests
```

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test fixtures
└── helpers/        # Test utilities
```

See `tests/README.md` for detailed testing guidelines.

## Project Structure

```
SakaiBot/
├── src/                    # Source code
│   ├── ai/                 # AI providers and processors
│   │   ├── providers/      # LLM provider implementations
│   │   ├── processor.py    # AI processing logic
│   │   ├── stt.py          # Speech-to-text
│   │   └── tts.py          # Text-to-speech
│   ├── cli/                # Command-line interface
│   │   ├── commands/       # CLI commands
│   │   └── menu_handlers/  # Interactive menu handlers
│   ├── core/               # Core functionality
│   │   ├── config.py       # Configuration management
│   │   └── settings.py     # Settings management
│   ├── telegram/           # Telegram integration
│   │   ├── client.py       # Telegram client wrapper
│   │   └── handlers.py     # Message handlers
│   └── utils/              # Utility modules
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── fixtures/           # Test fixtures
│   └── helpers/            # Test utilities
├── data/                   # User data (sessions, settings)
├── cache/                  # Cache files
├── logs/                   # Application logs
├── docs/                   # Documentation
├── requirements.txt        # Production dependencies
├── pyproject.toml          # Project configuration
├── setup.py                # Package setup
└── README.md               # This file
```

## Contributing

Contributions are welcome! Please follow these guidelines:

### Contribution Process

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Follow the code style (Black formatting)
   - Add tests for new features
   - Update documentation as needed
4. **Commit your changes**
   - Use [Conventional Commits](https://www.conventionalcommits.org/)
   ```bash
   git commit -m "feat: add new feature"
   ```
5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request**
   - Provide a clear description
   - Reference any related issues

### Commit Message Format

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Example:
```
feat(tts): add support for multiple voices
fix(translation): resolve encoding issues with Persian text
docs: update installation instructions
```

### Code Style

- Follow PEP 8 style guidelines
- Use Black for code formatting (line length: 100)
- Run Ruff for linting
- Use type hints where possible

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
Copyright (c) 2025 Sina Amare

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## Support

### Getting Help

- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/Sina-Amare/SakaiBot/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/Sina-Amare/SakaiBot/discussions)

### Documentation

Additional documentation is available in the `docs/` directory (if available):

- Architecture details
- API reference
- Configuration guide
- Testing guidelines
- FAQ

### Acknowledgments

SakaiBot is built with the following excellent libraries:

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [OpenRouter](https://openrouter.ai/) - LLM API gateway
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI models and TTS

---

**Made with ❤️ by [Sina Amare](https://github.com/Sina-Amare)**
