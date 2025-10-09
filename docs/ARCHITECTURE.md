# SakaiBot Architecture

## Overview

SakaiBot is an advanced Telegram userbot with AI capabilities that provides a comprehensive solution for message automation, categorization, and AI-assisted interactions. The architecture is designed with modularity and extensibility in mind, following a layered approach that separates concerns and promotes maintainability.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                    SakaiBot Application                     │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   CLI Layer     │  │   Core Layer    │  │   AI Layer   │ │
│  │                 │  │              │ │
│  │ - Commands      │  │ - Config        │  │ - LLM        │ │
│  │ - Menu System   │  │ - Exceptions    │  │ - Providers  │ │
│  │ - Utils         │  │ - Constants     │  │ - Processor  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                              │                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Telegram Layer │  │   Utils Layer   │  │   TTS/STT    │ │
│  │                 │  │              │ │
│  │ - Client        │  │ - Cache         │  │ - Speech     │ │
│  │ - Handlers      │  │ - Logging       │  │ - Text       │ │
│  │ - Utils         │  │ - Helpers       │  └──────────────┘ │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

### Component Architecture

#### 1. Core Layer

The Core layer contains fundamental components that provide the foundation for the entire application:

- **Configuration Management** (`src/core/config.py`): Handles application configuration using Pydantic for validation, supporting both `.env` files and legacy INI configuration.
- **Constants** (`src/core/constants.py`): Defines application-wide constants and settings.
- **Exceptions** (`src/core/exceptions.py`): Custom exception classes for error handling throughout the application.

#### 2. Telegram Layer

The Telegram layer manages all interactions with the Telegram API:

- **Client Management** (`src/telegram/client.py`): Handles authentication, session management, and connection to the Telegram API using the Telethon library.
- **Event Handlers** (`src/telegram/handlers.py`): Processes incoming messages, commands, and events from Telegram.
- **Utilities** (`src/telegram/utils.py`): Provides helper functions for working with Telegram entities and data.

#### 3. AI Layer

The AI layer provides intelligent processing capabilities:

- **LLM Interface** (`src/ai/llm_interface.py`): Abstract interface defining the contract for LLM providers.
- **AI Processor** (`src/ai/processor.py`): Orchestrates AI operations and manages the selected LLM provider.
- **Providers** (`src/ai/providers/`): Implementation of different LLM providers (OpenRouter, Google Gemini).
- **Persian Prompts** (`src/ai/persian_prompts.py`): Specialized prompts for Persian language processing.

#### 4. CLI Layer

The Command Line Interface layer provides user interaction:

- **Main CLI** (`src/cli/main.py`): Entry point for the command-line interface using Click.
- **Commands** (`src/cli/commands/`): Implementation of various CLI commands (pv, group, auth, monitor, ai, config).
- **Interactive Menu** (`src/cli/interactive.py`): Provides an interactive menu system for easier navigation.
- **State Management** (`src/cli/state.py`): Manages application state during CLI operations.

#### 5. Utils Layer

The utilities layer provides common functionality:

- **Cache Management** (`src/utils/cache.py`): Handles caching of Telegram data to reduce API calls.
- **Logging** (`src/utils/logging.py`): Implements application-wide logging.
- **Helpers** (`src/utils/helpers.py`): Common utility functions used throughout the application.

## Data Flow

### Message Processing Flow

```
1. Telegram Message Received
   ↓
2. Event Handler Processes Message
   ↓
3. Command Parsing (STT, TTS, AI, etc.)
   ↓
4. AI Processing (if applicable)
   ↓
5. Response Generation
   ↓
6. Telegram Response Sent
```

### Configuration Flow

```
1. Load .env file or config.ini
   ↓
2. Validate using Pydantic
   ↓
3. Apply to Config object
   ↓
4. Use throughout application
```

## Key Design Patterns

### 1. Abstract Factory Pattern

The LLM provider system uses an abstract factory pattern with the `LLMProvider` interface and concrete implementations for different providers (OpenRouter, Gemini).

### 2. Observer Pattern

Telegram event handlers implement an observer pattern to respond to incoming messages and events.

### 3. Singleton Pattern

Configuration management uses a singleton pattern through the `get_settings()` function to ensure consistent configuration access.

### 4. Dependency Injection

Components receive their dependencies (configuration, processors, etc.) rather than creating them directly, promoting loose coupling.

## Security Considerations

1. **Authentication**: Secure Telegram authentication with 2FA support
2. **API Keys**: Secure handling of LLM provider API keys
3. **Authorization**: Role-based command access with confirmation flows
4. **Data Protection**: Proper session file management and sensitive data protection

## Scalability Features

1. **Caching**: PV and group data caching to reduce API calls
2. **Asynchronous Processing**: Async/await patterns for concurrent operations
3. **Modular Design**: Easy to extend with new features and providers
4. **Resource Management**: Proper cleanup of resources and connections

## Error Handling

The architecture implements comprehensive error handling at multiple levels:

1. **Application Level**: Global exception handling in main application
2. **Component Level**: Specific error handling within each module
3. **API Level**: Retry logic and timeout handling for external API calls
4. **User Level**: Clear error messages for end users

## Performance Considerations

1. **Caching**: Reduces redundant API calls
2. **Async Processing**: Non-blocking operations for better responsiveness
3. **Resource Management**: Proper cleanup of temporary files and connections
4. **Efficient Data Structures**: Optimized data handling for large message histories
