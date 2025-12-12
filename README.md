<p align="center">
  <h1 align="center">🤖 SakaiBot</h1>
  <p align="center">
    <strong>AI-Powered Telegram Userbot with Multi-LLM Support</strong>
  </p>
  <p align="center">
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style"></a>
    <img src="https://img.shields.io/badge/telegram-userbot-blue?logo=telegram" alt="Telegram">
    <img src="https://img.shields.io/badge/AI-Gemini%20%7C%20OpenRouter-purple" alt="AI Providers">
  </p>
</p>

---

A production-ready Telegram userbot featuring **multi-LLM support** (Gemini + OpenRouter), **image generation** (Flux/SDXL), **voice processing** (TTS/STT), and **intelligent message management**. Built with resilience patterns including API key rotation, circuit breakers, and graceful fallbacks.

## ✨ Highlights

<table>
<tr>
<td width="50%">

**🧠 AI Capabilities**

- Multi-LLM fallback (Gemini → OpenRouter)
- Deep thinking mode with reasoning summaries
- Web search grounding for real-time info
- Persian comedian personality for fun analysis

</td>
<td width="50%">

**🎨 Image Generation**

- Flux (fast, artistic) & SDXL (photorealistic)
- AI-powered prompt enhancement
- Independent queues per model
- Cloudflare Workers backend

</td>
</tr>
<tr>
<td width="50%">

**🎤 Voice Processing**

- Text-to-Speech (Gemini TTS)
- Speech-to-Text with AI summaries
- Multiple voice options
- Persian language support

</td>
<td width="50%">

**⚡ Production Ready**

- API key rotation with cooldowns
- Circuit breakers for external APIs
- Per-user rate limiting
- Structured logging & error handling

</td>
</tr>
</table>

## 📑 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Commands Reference](#-commands-reference)
- [Architecture](#-architecture)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Features

### AI Commands

| Command                    | Description              | Flags                                      |
| -------------------------- | ------------------------ | ------------------------------------------ |
| `/prompt=<text>`           | Ask AI anything          | `=think` (deep reasoning), `=web` (search) |
| `/translate=<lang>=<text>` | Translate with phonetics | Auto-detect source                         |
| `/analyze=<N>`             | Analyze chat messages    | `=fun`, `=romance`, `=general`, `=think`   |
| `/tellme=<N>=<question>`   | Ask about chat history   | `=think`, `=web`                           |

### Image Generation

| Command                | Model | Speed   | Auth         |
| ---------------------- | ----- | ------- | ------------ |
| `/image=flux=<prompt>` | Flux  | ~15-30s | None         |
| `/image=sdxl=<prompt>` | SDXL  | ~20-40s | Bearer token |

### Voice Processing

| Command                 | Description                    |
| ----------------------- | ------------------------------ |
| `/tts=<text>`           | Text-to-Speech                 |
| `/stt` (reply to voice) | Speech-to-Text with AI summary |

### Management

| Command                  | Description                      |
| ------------------------ | -------------------------------- |
| `/auth list/add/remove`  | Manage authorized users          |
| `/group list/select/map` | Configure message categorization |
| `/status`                | Bot status and statistics        |
| `/help [topic]`          | Comprehensive help system        |

## 🏃 Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/Sina-Amare/SakaiBot.git && cd SakaiBot

# 2. Create virtual environment
python -m venv venv && source venv/bin/activate  # Linux/macOS
# python -m venv venv && venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -e .

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 5. Start monitoring
sakaibot monitor start
```

## 📦 Installation

### Prerequisites

- **Python 3.10+** - [Download](https://python.org/downloads/)
- **FFmpeg** - Required for audio processing ([Download](https://ffmpeg.org/download.html))
- **Telegram API** - Get credentials from [my.telegram.org](https://my.telegram.org)

### Detailed Steps

<details>
<summary><strong>1. Clone Repository</strong></summary>

```bash
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot
```

</details>

<details>
<summary><strong>2. Create Virtual Environment</strong></summary>

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

</details>

<details>
<summary><strong>3. Install Package</strong></summary>

```bash
# Production install
pip install -e .

# Development install (includes test/lint tools)
pip install -e ".[dev]"
```

</details>

<details>
<summary><strong>4. Configure Environment</strong></summary>

```bash
cp .env.example .env
# Edit .env with your credentials
```

See [Configuration](#-configuration) for detailed options.

</details>

<details>
<summary><strong>5. First Run</strong></summary>

```bash
sakaibot monitor start
# Enter Telegram verification code when prompted
# Session is saved for future use
```

</details>

## ⚙️ Configuration

### Required Settings

```env
# Telegram API (from my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+1234567890

# Primary LLM Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY_1=your_gemini_key
```

### OpenRouter (Required for Fallback & Prompt Enhancement)

```env
# OpenRouter is used for:
# 1. Image prompt enhancement (primary)
# 2. Fallback when Gemini keys are exhausted
OPENROUTER_API_KEY_1=sk-or-v1-your-key
```

### Optional Settings

<details>
<summary><strong>Multiple API Keys (Rotation)</strong></summary>

```env
# Up to 4 keys per provider - automatic rotation on rate limits
GEMINI_API_KEY_1=key1
GEMINI_API_KEY_2=key2
GEMINI_API_KEY_3=key3
GEMINI_API_KEY_4=key4

OPENROUTER_API_KEY_1=key1
OPENROUTER_API_KEY_2=key2
```

</details>

<details>
<summary><strong>Image Generation Workers</strong></summary>

```env
# Flux (public, no auth)
FLUX_WORKER_URL=https://your-flux-worker.workers.dev

# SDXL (requires your own worker + API key)
SDXL_WORKER_URL=https://your-sdxl-worker.workers.dev
SDXL_API_KEY=your_bearer_token
```

</details>

<details>
<summary><strong>FFmpeg Path</strong></summary>

```env
# Windows
PATHS_FFMPEG_EXECUTABLE=C:\ffmpeg\bin\ffmpeg.exe

# Linux/macOS
PATHS_FFMPEG_EXECUTABLE=/usr/bin/ffmpeg
```

</details>

## 📖 Commands Reference

### AI Commands

#### `/prompt` - Ask AI Anything

```text
/prompt=What is quantum computing?
/prompt=Explain this code: [paste code]
/prompt=Write a poem about stars=think      # Deep reasoning
/prompt=Latest news about AI=web            # Web search
```

#### `/translate` - Translation with Phonetics

```text
/translate=en=سلام دنیا              # Persian → English
/translate=fa=Hello world           # English → Persian
/translate=de                       # (reply) Translate to German
```

Output includes phonetic pronunciation in Persian script.

#### `/analyze` - Chat Analysis

```text
/analyze=100                        # Last 100 messages (Persian)
/analyze=500 en                     # English output
/analyze=fun=1000                   # Comedy roast style
/analyze=romance=200                # Relationship analysis
/analyze=general=500=think          # Deep analysis mode
```

**Modes:**

- `general` - Professional, structured analysis
- `fun` - Persian comedian style (Bill Burr-esque)
- `romance` - Emotional/relationship signals

#### `/tellme` - Ask About History

```text
/tellme=50=What topics were discussed?
/tellme=100=Who was most active?=think
/tellme=200=Summarize the drama=web
```

### Image Generation

```text
/image=flux=sunset over mountains
/image=sdxl=cyberpunk city, neon lights, 4k
```

- Prompts are automatically enhanced by AI
- Queue system with position updates
- Images sent with enhanced prompt as caption

### Voice Commands

```text
/tts=Hello, how are you?            # Text to speech
/tts                                # (reply) Convert message to speech
/stt                                # (reply to voice) Transcribe + summarize
```

### Authorization

```text
/auth list                          # View authorized users
/auth add @username                 # Add by username
/auth add 123456789                 # Add by user ID
/auth remove @username              # Remove user
```

### Group Categorization

```text
/group list                         # View your groups
/group select <id>                  # Select target forum group
/group topics                       # List topics in selected group
/group map category=topic_id        # Map category to topic
```

## 🏗️ Architecture

```
SakaiBot/
├── src/
│   ├── ai/                     # AI & LLM Layer
│   │   ├── providers/          # Gemini, OpenRouter implementations
│   │   ├── processor.py        # AI orchestration with fallback
│   │   ├── api_key_manager.py  # Key rotation & quota tracking
│   │   ├── prompt_enhancer.py  # Image prompt enhancement
│   │   ├── prompts.py          # System prompts (1000+ lines)
│   │   ├── tts.py              # Text-to-Speech (Gemini)
│   │   └── stt.py              # Speech-to-Text
│   │
│   ├── telegram/               # Telegram Integration
│   │   ├── handlers/           # Command handlers
│   │   ├── commands/           # Self-commands (help, auth, status)
│   │   ├── client.py           # Telethon wrapper
│   │   └── event_handlers.py   # Event routing
│   │
│   ├── cli/                    # Command-Line Interface
│   │   ├── commands/           # CLI command groups
│   │   ├── interactive.py      # Menu system
│   │   └── main.py             # Click entry point
│   │
│   ├── core/                   # Core Utilities
│   │   ├── config.py           # Pydantic configuration
│   │   ├── constants.py        # App constants
│   │   └── exceptions.py       # Custom exceptions
│   │
│   └── utils/                  # Cross-Cutting Concerns
│       ├── circuit_breaker.py  # Circuit breaker pattern
│       ├── rate_limiter.py     # Per-user rate limiting
│       ├── error_handler.py    # Error recovery strategies
│       ├── security.py         # API key masking
│       └── logging.py          # Structured logging
│
├── tests/                      # Test Suite
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
│
├── docker/                     # Docker Configuration
├── data/                       # Session files (gitignored)
├── cache/                      # Cache files (gitignored)
└── logs/                       # Application logs (gitignored)
```

### Key Patterns

| Pattern           | Implementation   | Purpose                           |
| ----------------- | ---------------- | --------------------------------- |
| API Key Rotation  | `APIKeyManager`  | Automatic failover on rate limits |
| Circuit Breaker   | `CircuitBreaker` | Prevent cascade failures          |
| Rate Limiting     | `RateLimiter`    | Per-user request throttling       |
| Provider Fallback | `AIProcessor`    | Gemini → OpenRouter fallback      |
| Error Recovery    | `ErrorHandler`   | User-friendly error messages      |

## 🛠️ Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Quality Checks

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type check
mypy src

# Run tests
pytest
pytest --cov=src --cov-report=html
```

### Running Tests

```bash
pytest                          # All tests
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
pytest -m "not slow"            # Skip slow tests
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feat/my-feature`
3. **Commit** using [Conventional Commits](https://conventionalcommits.org/):
   ```
   feat(ai): add new analysis mode
   fix(tts): resolve encoding issue
   docs: update command reference
   ```
4. **Push** and open a **Pull Request**

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

```
Copyright (c) 2025 Sina Amare
```

## 🙏 Acknowledgments

Built with these excellent libraries:

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client
- [Google Gemini](https://ai.google.dev/) - AI models & TTS
- [OpenRouter](https://openrouter.ai/) - LLM gateway
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Pydantic](https://pydantic.dev/) - Configuration validation

---

<p align="center">
  <strong>Made with ❤️ by <a href="https://github.com/Sina-Amare">Sina Amare</a></strong>
</p>
