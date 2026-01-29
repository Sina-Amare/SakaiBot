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

| Variable       | Required | Default  | Description                                |
| -------------- | -------- | -------- | ------------------------------------------ |
| `LLM_PROVIDER` | ✅       | `gemini` | Primary provider: `gemini` or `openrouter` |

### Gemini Configuration

Get API keys from [Google AI Studio](https://aistudio.google.com/apikey).

| Variable             | Required | Default            | Description              |
| -------------------- | -------- | ------------------ | ------------------------ |
| `GEMINI_API_KEY_1`   | ✅\*     | -                  | Primary Gemini API key   |
| `GEMINI_API_KEY_2`   | ❌       | -                  | Secondary key (rotation) |
| `GEMINI_API_KEY_3`   | ❌       | -                  | Tertiary key (rotation)  |
| `GEMINI_API_KEY_4`   | ❌       | -                  | Fourth key (rotation)    |
| `GEMINI_API_KEY_TTS` | ❌       | -                  | Dedicated TTS key        |
| `GEMINI_MODEL_PRO`   | ❌       | `gemini-2.5-pro`   | Model for complex tasks  |
| `GEMINI_MODEL_FLASH` | ❌       | `gemini-2.5-flash` | Model for simple tasks   |

\*Required if `LLM_PROVIDER=gemini`

```env
GEMINI_API_KEY_1=your_primary_key
GEMINI_API_KEY_2=your_backup_key
GEMINI_MODEL_PRO=gemini-2.5-pro
GEMINI_MODEL_FLASH=gemini-2.5-flash
```

### OpenRouter Configuration

Get API keys from [OpenRouter](https://openrouter.ai/).

| Variable                 | Required | Default                   | Description                |
| ------------------------ | -------- | ------------------------- | -------------------------- |
| `OPENROUTER_API_KEY_1`   | ✅\*\*   | -                         | Primary OpenRouter API key |
| `OPENROUTER_API_KEY_2`   | ❌       | -                         | Secondary key (rotation)   |
| `OPENROUTER_API_KEY_3`   | ❌       | -                         | Tertiary key (rotation)    |
| `OPENROUTER_API_KEY_4`   | ❌       | -                         | Fourth key (rotation)      |
| `OPENROUTER_MODEL_PRO`   | ❌       | `google/gemini-2.5-pro`   | Model for complex tasks    |
| `OPENROUTER_MODEL_FLASH` | ❌       | `google/gemini-2.5-flash` | Model for simple tasks     |

\*\*Required for prompt enhancement and Gemini fallback

```env
OPENROUTER_API_KEY_1=sk-or-v1-your_key_here
OPENROUTER_MODEL_PRO=google/gemini-2.5-pro
OPENROUTER_MODEL_FLASH=google/gemini-2.5-flash
```

> **Note:** OpenRouter is used for:
>
> 1. Image prompt enhancement (primary)
> 2. Fallback when all Gemini keys are exhausted

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
