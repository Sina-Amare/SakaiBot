# Configuration Reference

Complete configuration options for SakaiBot.

## Environment Variables

All configuration uses environment variables via `.env` file.

```bash
cp .env.example .env
```

---

## Telegram API

Get credentials from [my.telegram.org](https://my.telegram.org).

| Variable                | Required | Default            | Description                    |
| ----------------------- | -------- | ------------------ | ------------------------------ |
| `TELEGRAM_API_ID`       | ✅       | -                  | Telegram API ID                |
| `TELEGRAM_API_HASH`     | ✅       | -                  | Telegram API Hash              |
| `TELEGRAM_PHONE_NUMBER` | ✅       | -                  | Phone number with country code |
| `TELEGRAM_SESSION_NAME` | ❌       | `sakaibot_session` | Session file name              |

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE_NUMBER=+1234567890
TELEGRAM_SESSION_NAME=sakaibot_session
```

---

## LLM Provider

### Primary Provider

| Variable                | Required | Default            | Description                                      |
| ----------------------- | -------- | ------------------ | ------------------------------------------------ |
| `LLM_PROVIDER`          | ✅       | `gemini`           | Primary provider: `gemini` or `openrouter`       |
| `LLM_FALLBACK_PROVIDER` | ❌       | `openrouter`*      | Fallback provider: `openrouter`, `gemini`, `none` |

\*Default fallback is `openrouter` only when `LLM_PROVIDER=gemini`; OpenRouter primary defaults to no fallback.

### Gemini Configuration

Get API keys from [Google AI Studio](https://aistudio.google.com/apikey).

| Variable                    | Required | Default                         | Description                  |
| --------------------------- | -------- | ------------------------------- | ---------------------------- |
| `GEMINI_API_KEY_1`          | ✅\*     | -                               | Primary Gemini API key       |
| `GEMINI_API_KEY_2`          | ❌       | -                               | Secondary key (rotation)     |
| `GEMINI_API_KEY_3`          | ❌       | -                               | Tertiary key (rotation)      |
| `GEMINI_API_KEY_4`          | ❌       | -                               | Fourth key (rotation)        |
| `GEMINI_API_KEY_TTS`        | ❌       | -                               | Dedicated TTS key            |
| `GEMINI_MODEL_PRO`          | ❌       | `gemini-2.5-flash`              | Complex-task tier model      |
| `GEMINI_MODEL_FLASH`        | ❌       | `gemini-3.1-flash-lite`         | Simple-task tier model       |
| `GEMINI_MODEL_PRO_FALLBACK` | ❌       | `GEMINI_MODEL_FLASH`            | Model used when Pro quota is exhausted |
| `GEMINI_TTS_MODEL`          | ❌       | `gemini-3.1-flash-tts-preview`  | TTS model                    |
| `GEMINI_TTS_VOICE`          | ❌       | `Orus`                          | Default TTS voice            |
| `GEMINI_SUMMARY_MODEL`      | ❌       | `gemini-3.1-flash-lite`         | Direct STT summary fallback  |

\*Required if `LLM_PROVIDER=gemini`

```env
GEMINI_API_KEY_1=your_primary_key
GEMINI_API_KEY_2=your_backup_key
GEMINI_MODEL_PRO=gemini-2.5-flash
GEMINI_MODEL_FLASH=gemini-3.1-flash-lite
GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview
GEMINI_TTS_VOICE=Orus
```

Optional per-command Gemini overrides:

```env
GEMINI_MODEL_PROMPT=gemini-2.5-flash
GEMINI_MODEL_ANALYZE=gemini-2.5-flash
GEMINI_MODEL_TELLME=gemini-2.5-flash
GEMINI_MODEL_TRANSLATE=gemini-3.1-flash-lite
GEMINI_MODEL_PROMPT_ENHANCER=gemini-3.1-flash-lite
GEMINI_MODEL_VOICE_SUMMARY=gemini-3.1-flash-lite
```

### OpenRouter Configuration

Get API keys from [OpenRouter](https://openrouter.ai/).

| Variable                 | Required | Default                   | Description                |
| ------------------------ | -------- | ------------------------- | -------------------------- |
| `OPENROUTER_API_KEY_1`   | ✅\*\*   | -                         | Primary OpenRouter API key |
| `OPENROUTER_API_KEY_2`   | ❌       | -                         | Secondary key (rotation)   |
| `OPENROUTER_API_KEY_3`   | ❌       | -                         | Tertiary key (rotation)    |
| `OPENROUTER_API_KEY_4`   | ❌       | -                         | Fourth key (rotation)      |
| `OPENROUTER_MODEL_PRO`   | ❌       | `openrouter/free`   | Complex-task tier model    |
| `OPENROUTER_MODEL_FLASH` | ❌       | `openrouter/free` | Simple-task tier model     |
| `OPENROUTER_MODEL`       | ❌       | flash tier                | Legacy/default model       |

\*\*Required for prompt enhancement and Gemini fallback

```env
OPENROUTER_API_KEY_1=sk-or-v1-your_key_here
OPENROUTER_MODEL_PRO=openrouter/free
OPENROUTER_MODEL_FLASH=openrouter/free
```

Optional per-command OpenRouter overrides:

```env
OPENROUTER_MODEL_PROMPT=openrouter/free
OPENROUTER_MODEL_ANALYZE=openrouter/free
OPENROUTER_MODEL_TELLME=openrouter/free
OPENROUTER_MODEL_TRANSLATE=openrouter/free
OPENROUTER_MODEL_PROMPT_ENHANCER=openrouter/free
OPENROUTER_MODEL_VOICE_SUMMARY=openrouter/free
```

> **Note:** OpenRouter is used for:
>
> 1. Image prompt enhancement when selected as primary or fallback
> 2. Fallback when Gemini is primary and `LLM_FALLBACK_PROVIDER=openrouter`

---

## Image Generation

Cloudflare Workers for image generation.

| Variable          | Required | Default       | Description          |
| ----------------- | -------- | ------------- | -------------------- |
| `FLUX_WORKER_URL` | ❌       | Community URL | Flux worker endpoint |
| `SDXL_WORKER_URL` | ❌       | -             | SDXL worker endpoint |
| `SDXL_API_KEY`    | ❌       | -             | SDXL Bearer token    |

```env
FLUX_WORKER_URL=https://your-flux-worker.workers.dev
SDXL_WORKER_URL=https://your-sdxl-worker.workers.dev
SDXL_API_KEY=your_bearer_token
```

---

## Paths

| Variable                  | Required | Default     | Description           |
| ------------------------- | -------- | ----------- | --------------------- |
| `PATHS_FFMPEG_EXECUTABLE` | ❌       | System PATH | Path to FFmpeg binary |

```env
# Windows
PATHS_FFMPEG_EXECUTABLE=C:\ffmpeg\bin\ffmpeg.exe

# Linux/macOS
PATHS_FFMPEG_EXECUTABLE=/usr/bin/ffmpeg
```

---

## Application Settings

| Variable                       | Required | Default       | Description                              |
| ------------------------------ | -------- | ------------- | ---------------------------------------- |
| `ENVIRONMENT`                  | ❌       | `development` | Environment: `development`, `production` |
| `DEBUG`                        | ❌       | `false`       | Enable debug logging                     |
| `USERBOT_MAX_ANALYZE_MESSAGES` | ❌       | `10000`       | Max messages for `/analyze`              |

```env
ENVIRONMENT=production
DEBUG=false
USERBOT_MAX_ANALYZE_MESSAGES=10000
```

---

## API Key Rotation

SakaiBot automatically rotates API keys when rate limits are hit:

1. **Multiple Keys:** Configure up to 4 keys per provider
2. **Automatic Failover:** When Key 1 is exhausted, switches to Key 2
3. **Pacific Midnight Reset:** Daily quotas reset at midnight Pacific time
4. **Per-Model Tracking:** Pro and Flash models have separate quotas

### Example Multi-Key Setup

```env
# Gemini keys (auto-rotation)
GEMINI_API_KEY_1=AIza...primary
GEMINI_API_KEY_2=AIza...backup1
GEMINI_API_KEY_3=AIza...backup2
GEMINI_API_KEY_4=AIza...backup3

# OpenRouter keys (auto-rotation)
OPENROUTER_API_KEY_1=sk-or-v1-primary
OPENROUTER_API_KEY_2=sk-or-v1-backup
```

---

## File Locations

| Path                               | Purpose                                    |
| ---------------------------------- | ------------------------------------------ |
| `.env`                             | Configuration file                         |
| `data/*.session`                   | Telegram session files                     |
| `data/sakaibot_user_settings.json` | User settings (authorized users, mappings) |
| `cache/`                           | Group and PV cache                         |
| `logs/`                            | Application logs                           |
| `temp/`                            | Temporary files (images)                   |

---

## Validation

```bash
# Validate configuration
sakaibot config validate

# Show current configuration
sakaibot config show

# Show all including masked secrets
sakaibot config show --all
```

---

## Security Best Practices

1. **Never commit `.env`** - It's in `.gitignore`
2. **Use `.env.example`** - Template without secrets
3. **Rotate keys periodically** - Update keys regularly
4. **Limit authorized users** - Only authorize trusted users
5. **Review logs** - Monitor for suspicious activity
