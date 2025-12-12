# Architecture Overview

Technical architecture and design patterns used in SakaiBot.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       User Interface                        │
├─────────────────────────────────┬───────────────────────────┤
│         Telegram Client         │           CLI             │
│         (Telethon)              │         (Click)           │
└─────────────────────────────────┴───────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Command Handlers                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ AI Cmds  │ │ Image    │ │ Voice    │ │ Management   │   │
│  │ /prompt  │ │ /image   │ │ /tts     │ │ /auth        │   │
│  │ /analyze │ │          │ │ /stt     │ │ /group       │   │
│  │ /tellme  │ │          │ │          │ │ /status      │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Core Services                            │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │   AI Processor   │  │        Image Generator           │ │
│  │  - Gemini        │  │  - Flux Worker                   │ │
│  │  - OpenRouter    │  │  - SDXL Worker                   │ │
│  │  - Fallback      │  │  - Prompt Enhancement            │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │   TTS Service    │  │        STT Service               │ │
│  │  - Gemini TTS    │  │  - Speech Recognition            │ │
│  │  - Voice Options │  │  - AI Summary                    │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Resilience Layer                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ API Key Mgr  │ │Circuit Breaker│ │    Rate Limiter     │ │
│  │ - Rotation   │ │ - Open/Close  │ │ - Per-user limits   │ │
│  │ - Cooldowns  │ │ - Half-open   │ │ - Sliding window    │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Google Gemini│ │  OpenRouter  │ │  Cloudflare Workers  │ │
│  │  - LLM       │ │  - Fallback  │ │  - Flux              │ │
│  │  - TTS       │ │  - Enhancer  │ │  - SDXL              │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
src/
├── ai/                         # AI & LLM Layer
│   ├── providers/              # Provider implementations
│   │   ├── gemini.py           # Google Gemini (1000+ lines)
│   │   ├── openrouter.py       # OpenRouter provider
│   │   └── tts_gemini.py       # Gemini TTS
│   ├── processor.py            # AI orchestration
│   ├── api_key_manager.py      # Key rotation logic
│   ├── prompt_enhancer.py      # Image prompt enhancement
│   ├── prompts.py              # System prompts (1000+ lines)
│   ├── image_generator.py      # Flux/SDXL client
│   ├── image_queue.py          # Image generation queue
│   ├── tts.py                  # TTS orchestration
│   ├── tts_queue.py            # TTS queue
│   ├── stt.py                  # Speech-to-text
│   └── response_metadata.py    # Response wrapper
│
├── telegram/                   # Telegram Integration
│   ├── handlers/               # Command handlers
│   │   ├── ai_handler.py       # AI commands (800+ lines)
│   │   ├── image_handler.py    # Image commands
│   │   ├── tts_handler.py      # TTS commands
│   │   └── stt_handler.py      # STT commands
│   ├── commands/               # Self-commands
│   │   └── self_commands.py    # /help, /auth, /status
│   ├── client.py               # Telethon wrapper
│   └── event_handlers.py       # Event routing
│
├── cli/                        # Command-Line Interface
│   ├── commands/               # CLI command groups
│   │   ├── monitor.py          # sakaibot monitor
│   │   ├── group.py            # sakaibot group
│   │   └── config.py           # sakaibot config
│   ├── interactive.py          # Menu system
│   └── main.py                 # Click entry point
│
├── core/                       # Core Configuration
│   ├── config.py               # Pydantic settings
│   ├── constants.py            # App constants
│   ├── exceptions.py           # Custom exceptions
│   ├── settings.py             # User settings
│   └── tts_config.py           # TTS configuration
│
└── utils/                      # Cross-Cutting Concerns
    ├── circuit_breaker.py      # Circuit breaker pattern
    ├── rate_limiter.py         # Per-user rate limiting
    ├── error_handler.py        # Error recovery
    ├── security.py             # API key masking
    ├── logging.py              # Structured logging
    ├── retry.py                # Retry with backoff
    └── validators.py           # Input validation
```

---

## Design Patterns

### 1. API Key Rotation

Automatic failover when rate limits are hit.

```python
class APIKeyManager:
    """Manages multiple API keys with auto-rotation."""

    def get_current_key(self) -> Optional[str]:
        """Get first available key."""

    def mark_key_rate_limited(self) -> bool:
        """Mark current key as rate limited, try next."""

    def mark_key_exhausted_for_day(self) -> bool:
        """Mark key as exhausted until Pacific midnight."""
```

**Key States:**

- `HEALTHY` - Available for use
- `RATE_LIMITED` - Temporary cooldown (60s default)
- `EXHAUSTED` - Until next Pacific midnight

### 2. Circuit Breaker

Prevents cascade failures to external services.

```python
class CircuitBreaker:
    """Circuit breaker for external API calls."""

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing, requests rejected immediately
    - HALF_OPEN: Testing if service recovered

    Transitions:
    - CLOSED → OPEN: After 5 consecutive failures
    - OPEN → HALF_OPEN: After 60s timeout
    - HALF_OPEN → CLOSED: After 2 consecutive successes
    - HALF_OPEN → OPEN: On any failure
```

### 3. Provider Fallback

Gemini primary with OpenRouter fallback.

```python
class AIProcessor:
    async def _execute_with_fallback(self, ...):
        try:
            return await self._primary_provider.execute(...)
        except KeysExhaustedError:
            return await self._fallback_provider.execute(...)
```

### 4. Rate Limiting

Token bucket algorithm per user.

```python
class RateLimiter:
    """Per-user rate limiting with sliding window."""

    - 10 requests per 60 seconds per user
    - Sliding window implementation
    - Automatic cleanup of old entries
```

### 5. Error Recovery

User-friendly error messages with Persian support.

```python
class ErrorHandler:
    ERROR_MESSAGES = {
        APIKeyExhaustedError: "❌ All API keys exhausted...",
        RateLimitError: "⏳ Rate limit exceeded...",
        NetworkError: "🌐 Network error...",
    }
```

---

## Data Flow

### AI Command Flow

```
User sends /prompt=<text>
        │
        ▼
┌───────────────────┐
│  Event Handler    │ Parse command, validate
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Rate Limiter    │ Check user quota
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   AI Processor    │ Route to provider
└───────────────────┘
        │
        ▼
┌───────────────────┐     ┌───────────────────┐
│  Gemini Provider  │────▶│ OpenRouter        │
└───────────────────┘     │ (fallback)        │
        │                 └───────────────────┘
        ▼
┌───────────────────┐
│  API Key Manager  │ Select healthy key
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Circuit Breaker  │ Allow/block request
└───────────────────┘
        │
        ▼
    External API
        │
        ▼
   Response to user
```

### Image Generation Flow

```
User sends /image=flux=<prompt>
        │
        ▼
┌───────────────────┐
│  Image Handler    │ Parse model and prompt
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Prompt Enhancer   │ OpenRouter enhances prompt
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Image Queue     │ FIFO queue per model
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Image Generator   │ Call Cloudflare Worker
└───────────────────┘
        │
        ▼
   Save to temp/
        │
        ▼
   Send to user
```

---

## Configuration Management

### Pydantic Settings

```python
class Config(BaseSettings):
    """Main configuration using Pydantic for validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    # Required
    telegram_api_id: int
    telegram_api_hash: str

    # With validation
    @field_validator('llm_provider')
    def validate_provider(cls, v):
        if v not in ['gemini', 'openrouter']:
            raise ValueError(...)
```

### Settings Persistence

User settings stored in JSON:

```json
{
  "selected_target_group": { "id": -1001234, "title": "My Group" },
  "active_command_to_topic_map": { "meme": 123, "news": 456 },
  "directly_authorized_pvs": [12345, 67890]
}
```

---

## Concurrency Model

- **Asyncio**: All I/O operations are async
- **Per-model queues**: Image generation uses separate queues
- **Locks**: Circuit breaker uses asyncio.Lock

---

## Security Considerations

1. **API Key Masking**: Keys masked in logs (`AIza****`)
2. **Session Protection**: Session files in `.gitignore`
3. **Authorization**: Only owner and authorized users
4. **Input Validation**: Pydantic validators on all config
5. **Rate Limiting**: Prevents abuse

---

## Directory Conventions

| Directory | Purpose            | Git Status |
| --------- | ------------------ | ---------- |
| `src/`    | Source code        | Tracked    |
| `tests/`  | Test suite         | Tracked    |
| `docs/`   | Documentation      | Tracked    |
| `data/`   | Sessions, settings | Ignored    |
| `cache/`  | Cache files        | Ignored    |
| `logs/`   | Application logs   | Ignored    |
| `temp/`   | Temporary files    | Ignored    |
