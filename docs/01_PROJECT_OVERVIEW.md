# Project Overview

## Purpose & Scope

**SakaiBot** is an advanced Telegram user-bot that provides AI-powered message processing, translation, text-to-speech (TTS), speech-to-text (STT), conversation analysis, and automated message categorization. The bot operates as a **user-bot** (not an official Telegram Bot API bot), meaning it runs using a user account's credentials via the Telegram Client API (MTProto).

### Core Problem Solved

The bot addresses the need for:
- **AI-powered conversation assistance** in Telegram chats
- **Multilingual translation** with phonetic support (especially Persian)
- **Voice message processing** (transcription and generation)
- **Automated message organization** through categorization and forwarding
- **Conversation analysis** using LLM capabilities

### Current State

**Status**: ✅ **Functional Beta (v2.0.0)**

The project is in a **functional beta stage** with all core features implemented and working. The codebase is well-structured, tested, and ready for production use with minor deployment infrastructure additions.

**Development Stage**: 
- ✅ Core functionality: Complete
- ✅ Testing: Comprehensive (unit + integration)
- 🚧 Deployment infrastructure: Partial (missing Docker, CI/CD)
- 🚧 Production monitoring: Basic (logging only, no metrics/alerting)

### User-Bot Context

**Important**: This is a **user-bot**, not an official Telegram bot. Key differences:

- **Authentication**: Uses user account credentials (phone number, API ID/Hash from [my.telegram.org](https://my.telegram.org))
- **Session Files**: Stores `.session` files for persistent authentication
- **Rate Limits**: Subject to Telegram user account rate limits (more restrictive than Bot API)
- **Account Risk**: User-bots violate Telegram's Terms of Service - account could be banned
- **Capabilities**: Can access all user account features (groups, private chats, etc.)

**Legal Note**: Running user-bots may violate Telegram's Terms of Service. Users should be aware of potential account restrictions.

## AI Integration Summary

### LLM Providers

The bot supports **multiple AI providers** through a clean abstraction layer:

1. **Google Gemini** (`src/ai/providers/gemini.py`)
   - Models: `gemini-2.5-flash` (default), configurable
   - Features: Chat completion, translation, conversation analysis
   - TTS: Separate Gemini TTS API for text-to-speech

2. **OpenRouter** (`src/ai/providers/openrouter.py`)
   - Models: `google/gemini-2.5-flash` (default), configurable
   - Features: Chat completion, translation, conversation analysis
   - Gateway: Routes to multiple LLM providers via OpenRouter API

### AI Capabilities

- **Custom Prompts** (`/prompt=...`): Execute arbitrary AI instructions
- **Translation** (`/translate=...`): Multi-language translation with phonetic support
- **Conversation Analysis** (`/analyze=...`): Analyze chat history with different modes (general, fun, romance)
- **Question Answering** (`/tellme=...`): Answer questions based on chat history
- **Text-to-Speech** (`/tts`): Convert text to voice using Google Gemini TTS
- **Speech-to-Text** (`/stt`): Transcribe voice messages using Google Web Speech API

### AI Processing Flow

```
User Command → Handler → AI Processor → Provider (Gemini/OpenRouter) → Response
```

## Technology Stack

### Core Language & Runtime

- **Python**: 3.10+ (tested on 3.10, 3.11, 3.12)
- **Async Framework**: `asyncio` (native Python async/await)
- **Package Management**: `setuptools` (via `pyproject.toml`)

### Telegram Integration

- **Library**: `telethon>=1.30.0` (MTProto client library)
- **Encryption**: `cryptg>=0.4.0` (optional, for faster encryption)
- **Session Management**: File-based (`.session` files in `data/` directory)

### AI & ML Libraries

- **OpenAI SDK**: `openai>=1.0.0` (for OpenRouter integration)
- **Google GenAI**: `google-generativeai>=0.1.0` (for Gemini LLM)
- **Google GenAI TTS**: `google-genai>=0.8.0` (for text-to-speech)
- **Speech Recognition**: `SpeechRecognition>=3.10.0` (for STT)
- **Audio Processing**: `pydub` (for audio format conversion)

### Configuration & Validation

- **Pydantic**: `pydantic>=2.0.0` (configuration validation)
- **Pydantic Settings**: `pydantic-settings>=2.0.0` (environment variable management)
- **Python Dotenv**: `python-dotenv>=1.0.0` (`.env` file support)

### CLI & User Interface

- **Click**: `click` (CLI framework)
- **Rich**: `rich` (terminal formatting, colors, progress indicators)
- **Tabulate**: `tabulate` (table formatting)

### Utilities

- **Async File I/O**: `aiofiles>=23.0.0`
- **Timezone**: `pytz>=2023.3`
- **HTTP Client**: `httpx` (via OpenAI SDK for OpenRouter)

### Testing

- **Pytest**: `pytest>=7.0.0`
- **Pytest AsyncIO**: `pytest-asyncio>=0.21.0`
- **Coverage**: `pytest-cov` (via dev dependencies)

### Development Tools

- **Black**: Code formatter (line length: 100)
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pre-commit**: Git hooks (optional)

## Project Structure

```
SakaiBot/
├── src/                    # Source code
│   ├── ai/                 # AI providers and processors
│   │   ├── providers/      # LLM provider implementations
│   │   │   ├── gemini.py   # Google Gemini provider
│   │   │   ├── openrouter.py  # OpenRouter provider
│   │   │   └── tts_gemini.py  # Gemini TTS provider
│   │   ├── processor.py    # AI processing logic
│   │   ├── stt.py          # Speech-to-text
│   │   ├── tts.py          # Text-to-speech
│   │   └── tts_queue.py    # TTS request queue
│   ├── cli/                # Command-line interface
│   │   ├── commands/       # CLI commands
│   │   │   ├── auth.py      # Authorization management
│   │   │   ├── config.py    # Configuration management
│   │   │   ├── group.py     # Group management
│   │   │   └── monitor.py   # Monitoring control
│   │   ├── menu_handlers/   # Interactive menu handlers
│   │   ├── handler.py       # CLI handler
│   │   ├── interactive.py   # Interactive menu
│   │   └── main.py         # CLI entry point
│   ├── core/               # Core functionality
│   │   ├── config.py        # Configuration management
│   │   ├── constants.py     # Application constants
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── health.py        # Health checks
│   │   ├── settings.py      # Settings management
│   │   └── tts_config.py    # TTS configuration
│   ├── telegram/           # Telegram integration
│   │   ├── client.py        # Telegram client wrapper
│   │   ├── handlers.py      # Message handlers
│   │   ├── handlers/        # Specialized handlers
│   │   │   ├── ai_handler.py
│   │   │   ├── stt_handler.py
│   │   │   ├── tts_handler.py
│   │   │   ├── categorization_handler.py
│   │   │   └── base.py
│   │   ├── user_verifier.py # User verification
│   │   └── utils.py         # Telegram utilities
│   ├── utils/              # Utility modules
│   │   ├── cache.py         # Cache management
│   │   ├── circuit_breaker.py  # Circuit breaker pattern
│   │   ├── error_handler.py    # Error handling
│   │   ├── helpers.py          # Helper functions
│   │   ├── logging.py          # Logging setup
│   │   ├── message_sender.py   # Message sending utilities
│   │   ├── metrics.py          # Metrics collection
│   │   ├── rate_limiter.py     # Rate limiting
│   │   ├── retry.py            # Retry logic
│   │   ├── security.py         # Security utilities
│   │   ├── task_manager.py     # Task management
│   │   ├── translation_utils.py # Translation utilities
│   │   └── validators.py       # Input validation
│   └── main.py             # Main application entry point
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
├── pyproject.toml         # Project configuration
├── setup.py                # Package setup
└── README.md               # User documentation
```

## Key Capabilities

### Telegram Features
- Private chat management
- Group message handling
- User verification and authorization
- Message forwarding and categorization
- Forum topic support (for message categorization)

### AI Features
- Multiple LLM provider support (swappable)
- Custom prompt execution
- Intelligent translation with phonetic support
- Conversation analysis with multiple modes
- Question answering based on chat history

### Voice Processing
- Speech-to-text (STT) using Google Web Speech API
- Text-to-speech (TTS) using Google Gemini TTS
- High-quality Persian language support
- Automatic language detection
- Multiple voice options for TTS

### CLI Interface
- Interactive menu system
- Command-line utilities
- Status monitoring
- Configuration management
- Rich terminal output with progress indicators

---

**Next**: See `02_ARCHITECTURE.md` for detailed system design and component relationships.

