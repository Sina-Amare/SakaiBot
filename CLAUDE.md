# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SakaiBot is a Telegram userbot built with Python that provides AI-powered message processing, speech-to-text conversion, chat analysis, and automated message categorization capabilities.

## Development Commands

### Running the Bot

```bash
python -m src.main
# or with debug mode
python -m src.main --debug
```

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Virtual Environment Setup

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

## Architecture & Key Components

### Core Modules

- **main.py**: Entry point, handles Telegram client initialization, config loading, and signal handling
- **event_handlers.py**: Processes incoming Telegram commands and messages from authorized users
- **ai_processor.py**: Interfaces with OpenRouter API for LLM interactions, handles STT/TTS operations
- **cli_handler.py**: Interactive CLI menu system for bot configuration and management
- **telegram_utils.py**: Telegram API utilities for fetching chats, groups, and managing permissions
- **cache_manager.py**: Manages persistent caching of PV lists and group data
- **settings_manager.py**: Handles loading/saving user settings and preferences

### Configuration

- **data/config.ini**: Contains API keys and core settings (never commit)  
- **data/sakaibot_user_settings.json**: User preferences managed by CLI
- **data/sakaibot_session.session**: Telegram session file
- **cache/pv_cache.json** / **cache/group_cache.json**: Cached Telegram data (regenerable)

### Key Design Patterns

1. **Async Architecture**: All Telegram operations use asyncio for non-blocking execution
2. **Event-Driven**: Uses Telethon's event handlers for monitoring messages
3. **Worker Tasks**: Long-running operations (STT, AI processing) run as background tasks
4. **Centralized State**: CLI state managed through `cli_state` dictionary
5. **Modular Logging**: Separate loggers per module, all writing to `monitor_activity.log`

### Command Processing Flow

1. Authorized user sends command (e.g., `/prompt=`, `/translate=`, `/analyze=`)
2. Event handler validates permissions and parses command
3. For AI commands: calls `ai_processor.execute_custom_prompt()` with OpenRouter API
4. For STT: downloads voice, converts to WAV using pydub/ffmpeg, processes with Google Speech API
5. Results sent back to appropriate Telegram chat

### Dependencies

- **telethon**: Telegram client library
- **openai**: For OpenRouter API integration
- **SpeechRecognition**: Google Speech-to-Text
- **pydub**: Audio format conversion (requires ffmpeg)
- **pytz**: Timezone handling

## Important Notes

- FFmpeg must be installed and accessible (configured in config.ini or PATH)
- The bot uses a session file (`sakaibot_session.session`) for persistent Telegram auth
- All file paths in the codebase use UTF-8 encoding
- The bot monitors both incoming messages from authorized users and outgoing messages from the bot owner

## Core Development Principles

### 1. Simplicity First

- Start with the simplest solution that works
- Only add complexity when absolutely necessary
- Prefer readable code over clever optimizations
- Use existing libraries rather than reinventing wheels

### 2. Robustness & Error Handling

- Every external API call must have retry logic
- All user inputs must be validated
- Implement fallback mechanisms for critical paths
- Log errors comprehensively but securely
- Never let the bot crash - graceful degradation preferred

### 3. Code Quality Standards

- Type hints for all function parameters and returns
- Docstrings for all public functions and classes
- Maximum function length: 50 lines
- Maximum file length: 500 lines
- Test coverage minimum: 80%
- All database queries must use parameterized statements

### 4. Security Guidelines

- Never log sensitive data (API keys, user tokens)
- Validate and sanitize all GitHub URLs
- Use environment variables for all secrets
- Implement rate limiting on all endpoints
- Regular dependency updates for security patches

### 5. Performance Considerations

- Database queries must use appropriate indexes
- Implement caching for frequently accessed data
- Use async/await for I/O operations
- Chunk large code repositories for analysis
- Monitor memory usage during repository processing

## Development Workflow

### Test After Implementation

- Test each component immediately after implementation before moving to the next component
- Early detection of issues through immediate testing
- Validation of functionality at each step
- Always run tests after completing a module or significant feature
- **ALWAYS activate virtual environment before running tests**: `source venv/bin/activate`

### Proactive Commit Management

Ask the user to commit changes at appropriate checkpoints:

- After completing a major feature or module
- Before starting a significant refactoring
- After successful testing of components
- When switching between different areas of work
- Before any risky operations

### Credential Management

- **Never hardcode credentials** - Always use environment variables
- **When credentials are needed**:
  1. PAUSE implementation
  2. Ask user to provide specific credential with clear instructions
  3. WAIT for user confirmation
  4. Only then proceed with implementation

### User Action Protocol

When user action is required:

1. **PAUSE** current task
2. **PROVIDE** clear, step-by-step instructions
3. **WAIT** for user to complete and confirm
4. **CONTINUE** only after confirmation

### Examples of User Actions:

- **Creating Telegram Bot**: "Please create a Telegram bot using BotFather. Instructions: [step-by-step guide]. Let me know when done and provide the BOT_TOKEN."
- **Getting API Keys**: "Please obtain OpenRouter API key from [website]. Let me know when you have it."
- **Installing Packages**: "Please run: `pip install [packages]` in your terminal. Confirm when installation is complete."
- **Testing Setup**: "Please test [specific feature]. Let me know if it works or any errors you encounter."

### Development Responsibilities

- **Claude Code handles**: All code implementation, documentation, configuration files
- **User handles**: Environment setup, credential acquisition, package installation, testing
- **Run subagents** : when neccessary upon tasks.
- **directory check** : always make sure files are in their correct place e.g : tests ==> tests/ , configs==>config/ ,etc
