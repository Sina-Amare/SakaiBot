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
- 🎨 **Image Generation** - Text-to-image with Flux and SDXL models via Cloudflare Workers
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
- Image generation with prompt enhancement (Flux and SDXL)

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

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your credentials. See [Configuration](#configuration) for detailed instructions and [First-Time Setup](#first-time-setup) below.

## Configuration

Create a `.env` file in the project root. You can copy from the example:

```bash
cp .env.example .env
```

Then edit `.env` with your actual credentials.

### Required Configuration

```env
# Telegram API Credentials (get from https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE_NUMBER=+1234567890

# LLM Provider Selection (required - choose 'gemini' or 'openrouter')
LLM_PROVIDER=gemini

# AI Provider API Key (required - set the one matching your LLM_PROVIDER)
# For Gemini:
GEMINI_API_KEY=your_gemini_api_key_here
# OR for OpenRouter:
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### Optional Configuration

```env
# Telegram Session Settings
TELEGRAM_SESSION_NAME=sakaibot_session  # Default: sakaibot_session
                                          # Session files are stored in data/

# Google Gemini Configuration (if LLM_PROVIDER=gemini)
GEMINI_API_KEY_TTS=your_tts_specific_key  # Optional: TTS-specific key (priority over GEMINI_API_KEY)
GEMINI_MODEL=gemini-2.5-flash              # Default: gemini-2.5-flash

# OpenRouter Configuration (if LLM_PROVIDER=openrouter)
OPENROUTER_MODEL=google/gemini-2.5-flash  # Default: google/gemini-2.5-flash

# UserBot Configuration
USERBOT_MAX_ANALYZE_MESSAGES=10000  # Default: 10000, Range: 1-10000
                                     # Maximum number of messages to analyze in one operation

# Paths Configuration
PATHS_FFMPEG_EXECUTABLE=/usr/local/bin/ffmpeg  # Optional: Path to FFmpeg executable
                                                # Required for audio processing features
                                                # Windows example: C:\\ffmpeg\\bin\\ffmpeg.exe

# Cloudflare Image Generation Workers (Optional)
FLUX_WORKER_URL=https://image-smoke-ad69.fa-ra9931143.workers.dev  # Flux worker endpoint
SDXL_WORKER_URL=https://image-api.cpt-n3m0.workers.dev              # SDXL worker endpoint
SDXL_API_KEY=your_sdxl_bearer_token_here                            # SDXL Bearer token (required for SDXL)

# Environment Settings
ENVIRONMENT=production  # Options: production, development (Default: production)
DEBUG=false             # Enable debug mode (Default: false)
```

### Configuration Files

The bot stores configuration and data in the following locations:

- **Configuration**: `.env` (project root)
- **User Settings**: `data/sakaibot_user_settings.json`
- **Session Files**: `data/*.session` (created automatically after first login)
- **Cache**: `cache/` directory (group and PV caches)
- **Logs**: `logs/` directory

### First-Time Setup

1. **Get Telegram API Credentials**:
   - Visit [my.telegram.org](https://my.telegram.org)
   - Log in with your phone number
   - Go to "API development tools"
   - Create an application to get your `api_id` and `api_hash`

2. **Get AI Provider API Key**:
   - **For Gemini**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey) to get a Gemini API key
   - **For OpenRouter**: Visit [OpenRouter](https://openrouter.ai/) to get an API key

3. **Create `.env` File**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Validate Configuration**:
   ```bash
   sakaibot config validate
   ```

5. **Initial Login**:
   - Run `sakaibot monitor start` or `sakaibot menu`
   - You'll be prompted for your Telegram verification code
   - Enter the code sent to your Telegram account
   - Session file will be saved for future use

## Usage

### Command-Line Interface

After installation, the `sakaibot` command is available globally:

```bash
# Check bot status
sakaibot status

# Show help
sakaibot --help

# Start interactive menu
sakaibot menu
```

### Basic Commands

#### Status and Information

```bash
# Show current bot status and configuration
sakaibot status

# Start interactive menu system
sakaibot menu
```

### Group Management

Manage groups and message categorization:

```bash
# List all groups (admin groups by default)
sakaibot group list

# List all groups including non-admin
sakaibot group list --all

# Refresh group cache from Telegram
sakaibot group list --refresh

# Set target group for message categorization
sakaibot group set

# Set specific group by ID or name
sakaibot group set "Group Name"

# Clear target group
sakaibot group set --clear

# List topics in forum group (if target group is a forum)
sakaibot group topics

# Manage command to topic/group mappings
sakaibot group map              # List mappings
sakaibot group map --add        # Add new mapping
sakaibot group map --remove     # Remove a mapping
sakaibot group map --clear      # Clear all mappings
```

### Authorization Management

Manage authorized users who can send commands:

```bash
# List all authorized users
sakaibot auth list

# Add authorized user by username, ID, or display name
sakaibot auth add username
sakaibot auth add 123456789
sakaibot auth add "Display Name"

# Remove authorized user
sakaibot auth remove username

# Clear all authorized users
sakaibot auth clear

# Refresh private chat cache from Telegram
sakaibot auth refresh
```

### Monitoring

Control message monitoring and command processing:

```bash
# Start message monitoring (required for Telegram commands)
sakaibot monitor start

# Start with verbose output
sakaibot monitor start --verbose

# Stop monitoring (Ctrl+C also works)
sakaibot monitor stop

# Check monitoring status
sakaibot monitor status
```

### Configuration Management

Manage bot configuration:

```bash
# Display current configuration
sakaibot config show

# Show full configuration including API keys
sakaibot config show --all

# Validate configuration settings
sakaibot config validate

# Open configuration file in default editor
sakaibot config edit

# Show example configuration
sakaibot config example
```

### Telegram Commands

Once monitoring is started (`sakaibot monitor start`), you can use the following commands in Telegram. Commands must be sent by you (the bot owner) or by authorized users (see `sakaibot auth`).

#### Text-to-Speech (TTS)

Convert text to speech using Google Gemini TTS:

```text
# Basic usage - send text directly
/tts سلام، حال شما چطوره؟

# Reply to a message to convert it to speech
/tts  # (as a reply to any message)

# Specify voice
/tts voice=Kore Hello, how are you?

# Alias command (same as /tts)
/speak Hello world
```

**Available voices**: Kore, Puck, Fenrir, Zephyr, Orus (default), and more. See [Google Gemini TTS documentation](https://ai.google.dev/gemini-api/docs/speech-generation) for the full list.

#### Custom Prompts

Ask custom questions or give instructions to the AI:

```text
# Ask a question
/prompt=What is the capital of France?

# Give an instruction
/prompt=Explain quantum computing in simple terms

# Use with Persian text
/prompt=پایتخت ایران چیست؟
```

#### Translation

Translate text between languages:

```text
# Translate to target language (auto-detect source)
/translate=fa Hello world

# Translate with explicit source language
/translate=fa,en Hello world

# Reply to a message to translate it
/translate=fa  # (as a reply to any message)

# Multiple target languages
/translate=fa,es,fr Hello world
```

Supported language codes: ISO 639-1 codes (e.g., `fa`, `en`, `es`, `fr`, `de`, `ar`).

#### Message Analysis

Analyze conversation history with AI:

```text
# Analyze last N messages (default: general mode)
/analyze=100

# Analyze with specific mode
/analyze=fun=500      # Fun/humorous analysis
/analyze=romance=200  # Romance-focused analysis
/analyze=general=1000 # General conversation analysis

# Legacy format (still supported)
/analyze 500
```

**Modes**: `general` (default), `fun`, `romance`

**Limits**: Maximum messages analyzed is controlled by `USERBOT_MAX_ANALYZE_MESSAGES` (default: 10000)

#### Ask About Messages

Get AI insights about specific messages:

```text
# Ask about last N messages
/tellme=50=What topics are being discussed?

# Ask in Persian
/tellme=100=نتیجه‌گیری کلی این مکالمه چیست؟
```

**Usage**: `/tellme=<number_of_messages>=<your_question>`

The bot will analyze the specified number of recent messages and answer your question about them.

#### Image Generation

Generate images from text prompts using Flux or SDXL models:

```text
# Generate with Flux (GET, no auth required)
/image=flux/a beautiful sunset over mountains

# Generate with SDXL (POST, requires API key)
/image=sdxl/futuristic cyberpunk cityscape at night

# Simple prompts are automatically enhanced by AI
/image=flux/cat
# The AI will enhance "cat" to a detailed prompt before generation
```

**Features**:
- Automatic prompt enhancement via LLM for better results
- Separate FIFO queues per model (Flux and SDXL process independently)
- Queue position updates during processing
- Enhanced prompt shown as image caption

**Models**:
- **Flux**: Fast generation, no authentication required
- **SDXL**: High-quality generation, requires Bearer token

**Configuration**: Requires `FLUX_WORKER_URL`, `SDXL_WORKER_URL`, and `SDXL_API_KEY` in `.env`

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
