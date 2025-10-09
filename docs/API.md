# SakaiBot API Documentation

## Overview

SakaiBot provides a comprehensive API for interacting with Telegram and AI services. The API is organized into several modules, each handling specific functionality.

## Core API

### Configuration API

#### `Config` Class

The `Config` class manages application configuration using Pydantic for validation.

```python
from src.core.config import Config, load_config, get_settings
```

**Properties:**

- `telegram_api_id`: Telegram API ID
- `telegram_api_hash`: Telegram API Hash
- `telegram_phone_number`: Telegram phone number
- `llm_provider`: LLM provider (openrouter or gemini)
- `openrouter_api_key`: OpenRouter API key
- `gemini_api_key`: Google Gemini API key
- `is_ai_enabled`: Boolean indicating if AI features are enabled

**Methods:**

- `load_config()`: Load configuration from .env file or config.ini
- `get_settings()`: Get or create the global settings instance

### Exception API

#### Custom Exceptions

Defined in `src/core/exceptions.py`

- `ConfigurationError`: Raised when configuration is invalid
- `TelegramError`: Raised for Telegram-related errors
- `AIProcessorError`: Raised for AI processing errors

## Telegram API

### Client Management

#### `TelegramClientManager` Class

Manages Telegram client connection and authentication.

```python
from src.telegram.client import TelegramClientManager
```

**Methods:**

- `initialize()`: Initialize and connect the Telegram client
- `disconnect()`: Disconnect the Telegram client
- `is_connected()`: Check if client is connected

### Event Handlers

#### `EventHandlers` Class

Handles Telegram events and commands.

```python
from src.telegram.handlers import EventHandlers
```

**Methods:**

- `categorization_reply_handler_owner()`: Handle owner's messages for categorization and commands
- `authorized_user_command_handler()`: Handle commands from authorized users
- `process_command_logic()`: Process command logic for various types of commands

### Utilities

#### `TelegramUtils` Class

Provides helper functions for working with Telegram entities.

```python
from src.telegram.utils import TelegramUtils
```

## AI API

### LLM Interface

#### `LLMProvider` Abstract Class

Abstract base class for LLM providers.

```python
from src.ai.llm_interface import LLMProvider
```

**Abstract Methods:**

- `execute_prompt()`: Execute a prompt and return the response
- `translate_text()`: Translate text to target language
- `analyze_messages()`: Analyze a list of messages

### AI Processor

#### `AIProcessor` Class

Handles AI processing operations using configured LLM provider.

```python
from src.ai.processor import AIProcessor
```

**Properties:**

- `is_configured`: Check if AI processor is properly configured
- `provider_name`: Get the current provider name
- `model_name`: Get the current model name

**Methods:**

- `execute_custom_prompt()`: Execute a custom prompt using the configured LLM provider
- `translate_text_with_phonetics()`: Translate text with Persian phonetic pronunciation
- `analyze_messages()`: Analyze a collection of messages
- `close()`: Clean up provider resources

### AI Providers

#### `OpenRouterProvider` Class

Implementation for OpenRouter LLM provider.

```python
from src.ai.providers.openrouter import OpenRouterProvider
```

#### `GeminiProvider` Class

Implementation for Google Gemini LLM provider.

```python
from src.ai.providers.gemini import GeminiProvider
```

## CLI API

### Command Interface

The CLI is built using the Click framework and provides several command groups:

#### PV Commands

Manage private chats (PVs):

- `sakaibot pv list`: List all cached private chats
- `sakaibot pv refresh`: Refresh PV list from Telegram
- `sakaibot pv search <query>`: Search for private chats
- `sakaibot pv set-context <identifier>`: Set default PV context for analysis
- `sakaibot pv context`: Show current default PV context

#### Group Commands

Manage groups:

- `sakaibot group list`: List groups
- `sakaibot group set <identifier>`: Set target group for categorization
- `sakaibot group topics`: List topics in the selected group

#### Auth Commands

Manage authorization:

- `sakaibot auth list`: List authorized users
- `sakaibot auth add <identifier>`: Add authorized user
- `sakaibot auth remove <identifier>`: Remove authorized user

#### Monitor Commands

Manage monitoring:

- `sakaibot monitor start`: Start processing messages
- `sakaibot monitor stop`: Stop processing messages
- `sakaibot monitor status`: Show monitoring status

#### AI Commands

Manage AI features:

- `sakaibot ai test`: Test AI configuration
- `sakaibot ai config`: Show current AI configuration
- `sakaibot ai translate <text> <target_language>`: Translate text using AI
- `sakaibot ai prompt <prompt>`: Send a custom prompt to AI

#### Config Commands

Manage configuration:

- `sakaibot config show`: Show current configuration
- `sakaibot config validate`: Validate configuration

## Utility API

### Cache Management

#### `CacheManager` Class

Handles caching of Telegram data.

```python
from src.utils.cache import CacheManager
```

**Methods:**

- `get_pvs()`: Get private chats with caching
- `get_groups()`: Get groups with caching
- `search_pvs()`: Search private chats
- `search_groups()`: Search groups

### Logging

#### `setup_logging()` Function

Sets up application-wide logging.

```python
from src.utils.logging import setup_logging, get_logger
```

**Functions:**

- `setup_logging()`: Initialize logging configuration
- `get_logger()`: Get a logger instance for a specific module

## Speech Processing API

### Speech-to-Text

#### `SpeechToTextProcessor` Class

Handles speech-to-text conversion.

```python
from src.ai.stt import SpeechToTextProcessor
```

**Methods:**

- `transcribe_voice_to_text()`: Convert voice file to text

### Text-to-Speech

#### `TextToSpeechProcessor` Class

Handles text-to-speech conversion.

```python
from src.ai.tts import TextToSpeechProcessor
```

**Methods:**

- `text_to_speech()`: Convert text to speech using Edge-TTS

## Command Line Interface

### Running the CLI

The main entry point is `sakaibot.py` which initializes the CLI:

```bash
python sakaibot.py
# or
sakaibot
```

### Global Options

- `--debug`: Enable debug mode
- `--config-file`: Path to config file

### Interactive Menu

The application also provides an interactive menu system:

```bash
sakaibot menu
```

## Event System

SakaiBot uses an event-driven architecture where Telegram events trigger processing:

1. Telegram client receives a message
2. Event handler processes the message
3. Command parsing determines the action
4. Appropriate service (AI, STT, TTS, etc.) processes the request
5. Response is sent back to Telegram

## Error Handling API

The API provides comprehensive error handling through custom exceptions and proper error propagation throughout the system.
