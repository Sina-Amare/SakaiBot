# Architecture & System Design

## Component Map

### Core Modules

#### 1. Configuration Layer (`src/core/`)

**`config.py`** - Main configuration management
- **Responsibility**: Load and validate configuration from `.env` or `config.ini`
- **Technology**: Pydantic `BaseSettings` for type-safe configuration
- **Key Features**:
  - Environment variable loading
  - Backward compatibility with INI files
  - API key validation
  - Provider selection (OpenRouter/Gemini)

**`settings.py`** - User settings persistence
- **Responsibility**: Manage user-specific settings (authorized users, target groups, command mappings)
- **Storage**: JSON file (`data/sakaibot_user_settings.json`)
- **Key Data**:
  - `selected_target_group`: Target group for message categorization
  - `active_command_to_topic_map`: Command-to-topic mappings
  - `directly_authorized_pvs`: List of authorized user IDs

**`constants.py`** - Application constants
- **Responsibility**: Centralized constants (message limits, default models, etc.)
- **Key Constants**:
  - `MAX_MESSAGE_LENGTH`: 4096 (Telegram limit)
  - `DEFAULT_MAX_ANALYZE_MESSAGES`: 10000
  - `DEFAULT_TTS_VOICE`: "Orus"
  - Model names, cache file paths, etc.

**`exceptions.py`** - Custom exception hierarchy
- **Base**: `SakaiBotError`
- **Derived**: `ConfigurationError`, `TelegramError`, `AIProcessorError`, `CacheError`, `ValidationError`

#### 2. Telegram Integration Layer (`src/telegram/`)

**`client.py`** - TelegramClientManager
- **Responsibility**: Manage Telegram client lifecycle
- **Key Methods**:
  - `initialize()`: Connect and authenticate
  - `_authenticate()`: Handle 2FA and code verification
  - `disconnect()`: Graceful disconnection
- **Session Management**: Stores session files in `data/` directory

**`handlers.py`** - EventHandlers (main handler coordinator)
- **Responsibility**: Route messages to specialized handlers
- **Composition Pattern**: Delegates to specialized handlers:
  - `STTHandler`: Speech-to-text processing
  - `TTSHandler`: Text-to-speech processing
  - `AIHandler`: AI commands (prompt, translate, analyze, tellme)
  - `CategorizationHandler`: Message forwarding to topics

**`handlers/ai_handler.py`** - AI command processing
- **Commands Handled**: `/prompt`, `/translate`, `/analyze`, `/tellme`
- **Features**:
  - Rate limiting per user
  - Input validation
  - Metrics tracking
  - Error handling with user-friendly messages

**`handlers/tts_handler.py`** - Text-to-speech processing
- **Commands Handled**: `/tts`, `/speak`
- **Features**:
  - Queue-based processing (prevents overload)
  - Status updates during processing
  - Voice selection support
  - Automatic cleanup of temporary files

**`handlers/stt_handler.py`** - Speech-to-text processing
- **Commands Handled**: `/stt`
- **Features**:
  - Voice message transcription
  - AI-powered summarization of transcriptions
  - Language detection

**`handlers/categorization_handler.py`** - Message categorization
- **Responsibility**: Forward messages to target groups/topics based on commands
- **Features**:
  - Command-to-topic mapping
  - Confirmation flow for authorized users
  - Support for both legacy and new mapping formats

**`user_verifier.py`** - User verification
- **Responsibility**: Verify users by ID, username, or display name
- **Features**:
  - FloodWait error handling
  - Cache integration for performance

#### 3. AI Processing Layer (`src/ai/`)

**`processor.py`** - AIProcessor (main AI interface)
- **Responsibility**: High-level AI operations
- **Key Methods**:
  - `execute_custom_prompt()`: Execute arbitrary prompts
  - `translate_text_with_phonetics()`: Translation with phonetic support
  - `analyze_messages()`: Conversation analysis
  - `answer_question_from_chat_history()`: Q&A based on history
- **Provider Abstraction**: Works with any `LLMProvider` implementation

**`llm_interface.py`** - LLMProvider (abstract base class)
- **Responsibility**: Define interface for LLM providers
- **Key Methods**:
  - `execute_prompt()`: Basic prompt execution
  - `translate_text()`: Translation
  - `analyze_messages()`: Message analysis
- **Implementations**: `GeminiProvider`, `OpenRouterProvider`

**`providers/gemini.py`** - Google Gemini implementation
- **Features**:
  - Direct Google GenAI API integration
  - Retry logic with exponential backoff
  - Persian prompt templates
  - Multiple analysis modes (general, fun, romance)

**`providers/openrouter.py`** - OpenRouter implementation
- **Features**:
  - OpenRouter API gateway integration
  - Custom HTTP client configuration
  - Same interface as Gemini provider

**`tts.py`** - TextToSpeechProcessor
- **Responsibility**: TTS processing coordination
- **Provider**: Google Gemini TTS (via `providers/tts_gemini.py`)
- **Features**:
  - Voice selection and validation
  - Audio file generation

**`stt.py`** - SpeechToTextProcessor
- **Responsibility**: STT processing
- **Provider**: Google Web Speech API (via `speech_recognition` library)
- **Features**:
  - Language detection
  - Audio format conversion

**`tts_queue.py`** - TTS request queue
- **Responsibility**: Queue management for TTS requests
- **Features**:
  - Prevents API overload
  - Status tracking (pending, processing, completed, failed)
  - Request prioritization

#### 4. CLI Layer (`src/cli/`)

**`main.py`** - CLI entry point
- **Framework**: Click
- **Commands**: `status`, `menu`, `setup` (planned)
- **Command Groups**: `group`, `auth`, `monitor`, `config`

**`handler.py`** - CLIHandler
- **Responsibility**: Main CLI interaction logic
- **Features**:
  - Interactive menu system
  - State management
  - Integration with Telegram client

**`interactive.py`** - Interactive menu
- **Responsibility**: Rich terminal menu interface
- **Features**:
  - Numbered menu options
  - Status displays
  - Progress indicators

**`commands/`** - CLI command implementations
- **`auth.py`**: User authorization management
- **`config.py`**: Configuration display and validation
- **`group.py`**: Group and topic management
- **`monitor.py`**: Message monitoring control

#### 5. Utilities Layer (`src/utils/`)

**`error_handler.py`** - Error handling utilities
- **Features**:
  - User-friendly Persian error messages
  - Retry decision logic
  - Error logging with sanitization

**`rate_limiter.py`** - Rate limiting
- **Pattern**: Token bucket algorithm
- **Scope**: Per-user rate limiting
- **Configuration**: 10 requests per 60 seconds (default)

**`circuit_breaker.py`** - Circuit breaker pattern
- **Purpose**: Prevent cascading failures
- **States**: Closed, Open, Half-Open

**`task_manager.py`** - Async task management
- **Responsibility**: Track and cancel async tasks
- **Features**:
  - WeakSet for automatic cleanup
  - Graceful shutdown support

**`cache.py`** - CacheManager
- **Responsibility**: Cache PVs and groups
- **Storage**: JSON files in `cache/` directory
- **Features**:
  - Timestamp tracking
  - Automatic refresh logic

**`message_sender.py`** - MessageSender
- **Responsibility**: Reliable message delivery
- **Features**:
  - Automatic message splitting (for long messages)
  - Pagination support
  - Safe editing (handles duplicate content errors)

**`security.py`** - Security utilities
- **Features**:
  - API key masking for logs
  - Sensitive data sanitization

**`metrics.py`** - Metrics collection
- **Purpose**: Track performance and usage
- **Features**:
  - Counter, gauge, timing metrics
  - Tag-based categorization

**`validators.py`** - InputValidator
- **Responsibility**: Validate and sanitize user input
- **Validations**:
  - Prompt length and content
  - Language codes (ISO 639-1)
  - Number ranges

## Dependency Relationships

```
┌─────────────────────────────────────────────────────────┐
│                    Main Entry Point                      │
│              (sakaibot.py, src/main.py)                 │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐      ┌─────────▼──────────┐
│  CLI Handler   │      │  Telegram Client   │
│  (src/cli/)    │      │  (src/telegram/)   │
└───────┬────────┘      └─────────┬──────────┘
        │                         │
        │                         │
┌───────▼─────────────────────────▼──────────┐
│         Event Handlers                      │
│    (src/telegram/handlers.py)              │
└───────┬─────────────────────────────────────┘
        │
        ├──► AI Handler ──► AI Processor ──► LLM Providers
        │
        ├──► TTS Handler ──► TTS Processor ──► Gemini TTS
        │
        ├──► STT Handler ──► STT Processor ──► Google Web Speech
        │
        └──► Categorization Handler
```

## Entry Points and Execution Flow

### 1. CLI Entry Point (`sakaibot` command)

```
sakaibot.py
  └─> src/cli/main.py:cli()
      └─> setup_environment()
      └─> display_banner()
      └─> [Command execution or interactive menu]
```

### 2. Main Application Entry Point

```
src/main.py:main()
  └─> setup_logging()
  └─> load_config()
  └─> SakaiBot(config)
      └─> Initialize components:
          ├─> TelegramClientManager
          ├─> AIProcessor
          ├─> SpeechToTextProcessor
          ├─> TextToSpeechProcessor
          ├─> EventHandlers
          └─> CLIHandler
  └─> bot.run()
      └─> client_manager.initialize()
      └─> cli_handler.display_main_menu_loop()
```

### 3. Message Processing Flow

```
Telegram Message Received
  └─> EventHandlers.categorization_reply_handler_owner()
      └─> Check for confirmation flow
      └─> process_command_logic()
          ├─> Parse command type
          ├─> Route to specialized handler:
          │   ├─> STT Handler (if /stt)
          │   ├─> TTS Handler (if /tts or /speak)
          │   ├─> AI Handler (if /prompt, /translate, /analyze, /tellme)
          │   └─> Categorization Handler (if categorization command)
          └─> Send response
```

### 4. AI Command Processing Flow

```
User sends /prompt=question
  └─> AIHandler.handle_other_ai_commands()
      └─> Parse command
      └─> Check rate limit
      └─> Create async task
          └─> AIHandler.process_ai_command()
              └─> AIProcessor.execute_custom_prompt()
                  └─> Provider.execute_prompt()
                      └─> [Gemini or OpenRouter API call]
                          └─> Response processing
                              └─> MessageSender.send_long_message()
```

## State Management Approach

### 1. Configuration State

- **Source**: `.env` file or `config.ini`
- **Loading**: Lazy loading via `get_settings()` singleton
- **Validation**: Pydantic validation on load
- **Persistence**: File-based, not runtime mutable

### 2. User Settings State

- **Source**: `data/sakaibot_user_settings.json`
- **Management**: `SettingsManager` class
- **Key State**:
  - `selected_target_group`: Current target group for categorization
  - `active_command_to_topic_map`: Command mappings
  - `directly_authorized_pvs`: Authorized user list
- **Persistence**: Saved on CLI exit or graceful shutdown

### 3. CLI State

- **Location**: `src/cli/state.py` - `CLIState` class
- **Scope**: Runtime state during CLI session
- **Key State**:
  - `is_monitoring_active`: Whether message monitoring is running
  - `registered_handler_info`: Event handler references
  - `settings_saved_on_cli_exit`: Flag to prevent duplicate saves
- **Persistence**: Transient, not saved to disk

### 4. Cache State

- **Location**: `cache/pv_cache.json`, `cache/group_cache.json`
- **Management**: `CacheManager` class
- **Refresh Logic**: 
  - PVs: Refresh if cache is empty or >24 hours old
  - Groups: Refresh on demand or if cache is empty
- **Persistence**: JSON files with timestamps

### 5. Task State

- **Management**: `TaskManager` (singleton via `get_task_manager()`)
- **Storage**: `WeakSet` of asyncio tasks
- **Lifecycle**: Tasks automatically removed when completed
- **Shutdown**: All tasks cancelled during graceful shutdown

## Data Flow

### Message Reception Pipeline

```
Telegram Server
  └─> Telethon Client (Event Listener)
      └─> EventHandlers (Router)
          └─> Specialized Handler
              ├─> Input Validation
              ├─> Rate Limiting Check
              ├─> Task Creation (async)
              └─> Response Generation
                  └─> MessageSender
                      └─> Telegram Client
                          └─> Telegram Server
```

### AI Request/Response Handling

```
User Input
  └─> Command Parser
      └─> Input Validator
          └─> AI Processor
              └─> Provider Selection (Gemini/OpenRouter)
                  └─> API Request
                      ├─> Retry Logic (if needed)
                      ├─> Circuit Breaker Check
                      └─> Response Processing
                          └─> Message Formatting
                              └─> Response Delivery
```

### Data Persistence Strategy

1. **Session Files**: `data/*.session` (Telethon managed)
2. **User Settings**: `data/sakaibot_user_settings.json` (JSON)
3. **Cache**: `cache/*.json` (JSON with timestamps)
4. **Logs**: `logs/*.log` (text files)
5. **Temporary Files**: Created in project root, cleaned up after use

**No Database**: All persistence is file-based JSON. This is simple but may not scale for high-volume usage.

## External API Call Patterns

### 1. Telegram API (via Telethon)

- **Pattern**: Async event-driven
- **Rate Limiting**: Handled by Telethon (automatic FloodWait handling)
- **Error Handling**: Custom `TelegramError` exceptions
- **Retry**: Built into Telethon library

### 2. AI Provider APIs

**Gemini API**:
- **Pattern**: Direct HTTP calls via `google.generativeai`
- **Rate Limiting**: Application-level rate limiter
- **Retry**: Custom retry logic with exponential backoff
- **Error Handling**: `AIProcessorError` exceptions

**OpenRouter API**:
- **Pattern**: OpenAI SDK with custom base URL
- **Rate Limiting**: Application-level rate limiter
- **Retry**: OpenAI SDK retry + custom logic
- **Error Handling**: `AIProcessorError` exceptions

### 3. TTS API (Gemini TTS)

- **Pattern**: Synchronous HTTP calls (wrapped in `asyncio.to_thread`)
- **Queue**: TTS queue prevents concurrent overload
- **Error Handling**: Returns success/failure boolean

### 4. STT API (Google Web Speech)

- **Pattern**: Synchronous API calls (via `speech_recognition` library)
- **Error Handling**: `AIProcessorError` exceptions
- **Retry**: Not implemented (should be added)

## Design Patterns & Standards Compliance

### SOLID Principles

**✅ Single Responsibility Principle (SRP)**
- Each handler has a single responsibility (AI, TTS, STT, categorization)
- Providers are separated by concern (Gemini, OpenRouter)
- Utilities are focused (rate limiting, caching, error handling)

**✅ Open/Closed Principle (OCP)**
- Provider abstraction allows adding new providers without modifying existing code
- Handler base class enables extension
- Configuration system is extensible

**✅ Liskov Substitution Principle (LSP)**
- All providers implement `LLMProvider` interface correctly
- Handlers can be substituted via base class

**✅ Interface Segregation Principle (ISP)**
- `LLMProvider` interface is focused (not bloated)
- Protocol-based dependencies (e.g., `TelegramUtilsProtocol`)

**✅ Dependency Inversion Principle (DIP)**
- High-level modules depend on abstractions (`LLMProvider`, not concrete implementations)
- Dependency injection used throughout (processors injected into handlers)

### KISS/YAGNI Compliance

**✅ KISS (Keep It Simple, Stupid)**
- File-based persistence (simple, no database overhead)
- Direct JSON storage (no ORM complexity)
- Clear, straightforward command parsing

**⚠️ YAGNI (You Aren't Gonna Need It)**
- Some abstraction may be over-engineered for current needs
- Metrics system exists but not heavily used
- Circuit breaker implemented but may not be necessary for current scale

### DRY (Don't Repeat Yourself)

**✅ Good Practices**:
- Common utilities extracted (`helpers.py`, `validators.py`)
- Shared error handling (`error_handler.py`)
- Reusable message sending (`message_sender.py`)

**⚠️ Areas for Improvement**:
- Some hardcoded Persian error messages (should be centralized)
- Duplicate command parsing logic in some handlers
- Similar retry patterns could be unified

### Separation of Concerns

**✅ Excellent Separation**:
- Business logic (AI processing) separate from Telegram handling
- Configuration management isolated
- Error handling centralized
- Utilities are pure functions where possible

**Architecture Style**: **Modular Event-Driven Architecture**
- Event-driven message processing
- Modular component design
- Clear boundaries between layers

---

**Next**: See `03_FEATURES.md` for complete feature inventory.

