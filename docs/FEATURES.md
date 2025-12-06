# SakaiBot Features Documentation

> **Version:** 2.0.0  
> **Last Updated:** December 6, 2025

This document provides a comprehensive list of all features currently implemented in SakaiBot.

---

## Table of Contents

1. [AI Commands](#ai-commands)
2. [Voice & Speech](#voice--speech)
3. [Image Generation](#image-generation)
4. [Translation](#translation)
5. [Message Categorization](#message-categorization)
6. [CLI Interface](#cli-interface)
7. [Monitoring & Deployment](#monitoring--deployment)
8. [Security Features](#security-features)
9. [Technical Infrastructure](#technical-infrastructure)

---

## AI Commands

### `/prompt` - AI Chat

Ask the AI anything. Adapts tone based on question type (serious vs casual).

**Usage:**

```
/prompt <your question>
/prompt=think <question>     # Enable thinking mode (shows AI reasoning)
/prompt=web <question>       # Enable web search
```

**Features:**

- ✅ Adaptive tone detection (formal questions → informative; casual → comedian style)
- ✅ Persian-first responses (responds in Farsi unless asked in English)
- ✅ `=think` flag for extended reasoning mode (Gemini 2.5's native thinking)
- ✅ `=web` flag for web search augmentation
- ✅ Rate limiting per user

**Example:**

```
/prompt بهترین راه یادگیری پایتون چیه؟
/prompt=think توضیح بده چطور کوانتوم کامپیوتر کار میکنه
```

---

### `/analyze` - Conversation Analysis

Analyze chat history with different analysis styles.

**Usage:**

```
/analyze=<COUNT>                    # Analyze COUNT messages (default: Persian)
/analyze=<MODE>=<COUNT>             # Specify analysis mode
/analyze=<COUNT> en                 # Output in English
/analyze=<MODE>=<COUNT>=think       # Enable thinking mode
```

**Modes:**
| Mode | Description |
|------|-------------|
| `general` | Professional analysis - topics, decisions, insights |
| `fun` | Comedy roast by "Persian Bill Burr" - standup style |
| `romance` | Relationship/emotional signal analysis with evidence |

**Language Support:**

- **Default:** Persian (فارسی)
- **Add `en`:** English output (`/analyze=500 en`)

**Features:**

- ✅ Scalable response length (more messages → more detailed analysis)
- ✅ Thinking mode for complex analyses
- ✅ Async queue processing for large analyses
- ✅ Progress tracking during analysis
- ✅ 10-10,000 message range

**Examples:**

```
/analyze=500                 # Last 500 messages, general mode, Persian
/analyze=fun=1000            # Fun/comedy analysis, 1000 messages
/analyze=romance=200 en      # Romance analysis, English output
/analyze=general=2000=think  # General analysis with AI thinking
```

---

### `/tellme` - Question About Chat History

Ask specific questions about the chat history.

**Usage:**

```
/tellme=<COUNT>=<question>
/tellme=<COUNT>=<question>=think    # Enable thinking mode
/tellme=<COUNT>=<question>=web      # Enable web search
```

**Features:**

- ✅ Context-aware answers based on actual chat history
- ✅ Thinking mode for complex questions
- ✅ Web search for external information

**Examples:**

```
/tellme=500=کی قرار ناهار رو گذاشتیم؟
/tellme=1000=who talked the most?
/tellme=200=چه تصمیماتی گرفته شد؟=think
```

---

## Translation

### `/translate` - Multi-Language Translation

Translate text to any supported language with Persian phonetic pronunciation.

**Usage:**

```
/translate=<LANG> <text>            # Translate text to language
/translate=<LANG>                   # Reply to a message to translate it
```

**Supported Languages:**
| Code | Language | Code | Language |
|------|----------|------|----------|
| `en` | English | `es` | Spanish |
| `fr` | French | `de` | German |
| `it` | Italian | `pt` | Portuguese |
| `ru` | Russian | `zh` | Chinese |
| `ja` | Japanese | `ko` | Korean |
| `ar` | Arabic | `fa` | Persian |
| `hi` | Hindi | `tr` | Turkish |

**Features:**

- ✅ Auto language detection for source text
- ✅ Persian phonetic pronunciation for all translations
- ✅ Reply-to-message translation

**Examples:**

```
/translate=en سلام چطوری؟
# Output: Hello, how are you? (هِلو، هاو آر یو؟)

/translate=de Good morning
# Output: Guten Morgen (گوتن مورگن)
```

---

## Voice & Speech

### `/stt` - Speech-to-Text (Voice Transcription)

Transcribe voice messages to text with AI summary.

**Usage:**

```
# Reply to a voice message with:
/stt
```

**Features:**

- ✅ Google Web Speech API transcription
- ✅ Automatic Persian summary using Gemini
- ✅ FFmpeg audio conversion
- ✅ Supports Persian (fa-IR) language

---

### `/tts` - Text-to-Speech

Convert text to voice message using Google Gemini TTS.

**Usage:**

```
/tts <text to speak>
/tts                    # Reply to a message to convert it
```

**Features:**

- ✅ Google Gemini native TTS (high quality)
- ✅ Default voice: "Orus" (masculine)
- ✅ Queue system for multiple requests
- ✅ Auto-deletes command message after sending voice
- ✅ Reply-to-message support

**Examples:**

```
/tts سلام، این یک تست است
# Reply to any message:
/tts
```

---

## Image Generation

### `/image` - AI Image Generation

Generate images using Flux or SDXL models via Cloudflare Workers.

**Usage:**

```
/image=flux/<prompt>     # Generate with Flux model (fast)
/image=sdxl/<prompt>     # Generate with SDXL model (high quality)
```

**Features:**

- ✅ Automatic prompt enhancement by AI
- ✅ Two model options: Flux (fast) and SDXL (quality)
- ✅ Queue system for multiple requests
- ✅ Progress status messages
- ✅ Auto-cleanup of temporary files

**Examples:**

```
/image=flux/a persian garden at sunset
/image=sdxl/cyberpunk city with neon lights, digital art
```

---

## Message Categorization

### Automatic Message Forwarding

Forward messages to topic groups based on categories.

**Configuration:**
Set up in CLI with `sakaibot group mapping` command.

**Features:**

- ✅ Category-to-topic mapping
- ✅ Confirmation before forwarding
- ✅ Target group configuration

---

## CLI Interface

SakaiBot includes a rich CLI for management and configuration.

### Available Commands

```bash
sakaibot auth login          # Authenticate with Telegram
sakaibot auth logout         # Clear session

sakaibot config show         # Show current configuration
sakaibot config set          # Modify settings

sakaibot group list          # List cached groups/PVs
sakaibot group mapping       # Configure message categorization

sakaibot monitor start       # Start monitoring daemon
sakaibot monitor stop        # Stop monitoring
sakaibot monitor status      # Show monitoring status
```

---

## Monitoring & Deployment

### Docker Deployment

Production-ready Docker deployment with:

| Feature                | Description                        |
| ---------------------- | ---------------------------------- |
| **Multi-stage build**  | Minimal image size, secure         |
| **Non-root user**      | Container runs as `sakaibot:1000`  |
| **Health checks**      | Auto-restart on failure            |
| **Resource limits**    | 768MB RAM for 1GB VPS              |
| **Structured logging** | JSON logs with rotation            |
| **API key redaction**  | Automatic secret filtering in logs |

### Operation Modes

```bash
# Production daemon
docker compose up -d

# Interactive CLI
docker compose run --rm sakaibot cli

# Debug shell
docker compose run --rm sakaibot shell
```

---

## Security Features

### API Key Management

- ✅ **Key rotation** - Multiple Gemini keys with automatic failover
- ✅ **Key validation** - Validates keys before use
- ✅ **Circuit breaker** - Stops using exhausted keys temporarily
- ✅ **Rate limiting** - Per-user rate limits for AI commands

### Credential Security

- ✅ **Log redaction** - API keys automatically masked in logs
- ✅ **Secure file permissions** - `.env` and session files chmod 600
- ✅ **Docker volumes** - Persistent data in secure volumes
- ✅ **No secrets in images** - `.dockerignore` prevents secret leakage

### Input Validation

- ✅ **Command validation** - All inputs sanitized
- ✅ **Length limits** - Prevents DoS via oversized inputs
- ✅ **Language code validation** - Only supported languages accepted

---

## Technical Infrastructure

### AI Providers

| Provider          | Usage    | Models                               |
| ----------------- | -------- | ------------------------------------ |
| **Google Gemini** | Primary  | `gemini-2.5-pro`, `gemini-2.5-flash` |
| **OpenRouter**    | Fallback | Same models via OpenRouter API       |

**Smart Model Selection:**

- Complex tasks (analyze, tellme, prompt) → Pro model
- Simple tasks (translate, image enhance) → Flash model

### Logging System

- **Development:** Human-readable console output
- **Production:** Structured JSON logs with rotation
- **Log rotation:** 100MB max, 7 backup files
- **Docker-native:** stdout/stderr for container logs

### Key Technical Features

- ✅ **Async queue processing** for TTS, Images, Analysis
- ✅ **Retry with exponential backoff** for API calls
- ✅ **Error handling** with user-friendly messages
- ✅ **Metrics collection** for performance monitoring
- ✅ **RTL text fixing** for proper Persian display in Telegram

---

## Environment Variables

### Required

| Variable                | Description                          |
| ----------------------- | ------------------------------------ |
| `TELEGRAM_API_ID`       | Telegram API ID from my.telegram.org |
| `TELEGRAM_API_HASH`     | Telegram API Hash                    |
| `TELEGRAM_PHONE_NUMBER` | Phone number with country code       |

### AI Providers

| Variable                                       | Description                                 |
| ---------------------------------------------- | ------------------------------------------- |
| `GEMINI_API_KEY_1` through `GEMINI_API_KEY_10` | Google Gemini API keys (rotation supported) |
| `OPENROUTER_API_KEY`                           | OpenRouter API key (optional fallback)      |

### Image Generation

| Variable          | Description                       |
| ----------------- | --------------------------------- |
| `SDXL_API_KEY`    | SDXL worker authentication        |
| `FLUX_WORKER_URL` | Custom Flux worker URL (optional) |
| `SDXL_WORKER_URL` | Custom SDXL worker URL (optional) |

### Configuration

| Variable                       | Description               | Default |
| ------------------------------ | ------------------------- | ------- |
| `USERBOT_MAX_ANALYZE_MESSAGES` | Max messages for /analyze | 10000   |
| `SAKAIBOT_LOG_LEVEL`           | Log level                 | INFO    |
| `TZ`                           | Timezone                  | UTC     |

---

## Limitations & Known Issues

1. **RTL Idempotency** - `fix_rtl_display` is not strictly idempotent (applying twice may add extra markers)
2. **Session Files** - Must be transferred securely to VPS (use GPG encryption)
3. **Memory Usage** - Large analyses (5000+ messages) may require more memory

---

## Quick Reference Card

| Command                    | Description                  |
| -------------------------- | ---------------------------- |
| `/prompt <text>`           | Ask AI anything              |
| `/prompt=think <text>`     | Ask with reasoning           |
| `/translate=<lang> <text>` | Translate text               |
| `/analyze=<N>`             | Analyze N messages (Persian) |
| `/analyze=<N> en`          | Analyze in English           |
| `/analyze=fun=<N>`         | Comedy analysis              |
| `/analyze=romance=<N>`     | Relationship analysis        |
| `/tellme=<N>=<question>`   | Ask about chat history       |
| `/image=flux/<prompt>`     | Generate image (fast)        |
| `/image=sdxl/<prompt>`     | Generate image (quality)     |
| `/stt`                     | Transcribe voice (reply)     |
| `/tts <text>`              | Text to speech               |
