# SakaiBot Configuration Guide

## Overview

This guide explains how to properly configure SakaiBot for use with Telegram and AI services. The application supports both modern `.env` file configuration and legacy INI file configuration.

## Prerequisites

Before configuring SakaiBot, you'll need:

1. **Telegram API credentials**:

   - API ID and API Hash from [my.telegram.org](https://my.telegram.org)
   - Your phone number (with country code)

2. **AI Provider API Key** (optional but recommended):
   - OpenRouter API key from [openrouter.ai](https://openrouter.ai)
   - OR Google Gemini API key from [Google AI Studio](https://aistudio.google.com)

## Configuration Methods

SakaiBot supports two configuration methods:

### Method 1: Environment Variables (Recommended)

Create a `.env` file in the project root with the following structure:

```env
# Telegram Configuration
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+1234567890
TELEGRAM_SESSION_NAME=sakaibot_session

# LLM Provider Configuration
LLM_PROVIDER=gemini  # or "openrouter"

# OpenRouter Configuration (if using OpenRouter)
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemma-7b-it  # or any supported model

# Google Gemini Configuration (if using Gemini)
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-pro  # or any supported model

# UserBot Configuration
USERBOT_MAX_ANALYZE_MESSAGES=1000

# Paths Configuration (optional)
PATHS_FFMPEG_EXECUTABLE=/path/to/ffmpeg  # or leave empty if ffmpeg is in PATH

# Additional Services (optional)
ASSEMBLYAI_API_KEY=your_assemblyai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### Method 2: INI Configuration (Legacy)

Create a `config.ini` file in the project root with the following structure:

```ini
[Telegram]
api_id = your_api_id
api_hash = your_api_hash
phone_number = +1234567890
session_name = sakaibot_session

[LLM]
provider = gemini

[OpenRouter]
api_key = your_openrouter_key
model = google/gemma-7b-it

[Gemini]
api_key = your_gemini_key
model = gemini-pro

[UserBot]
max_analyze_messages = 1000

[Paths]
ffmpeg_executable = /path/to/ffmpeg

[AssemblyAI]
api_key = your_assemblyai_key

[ElevenLabs]
api_key = your_elevenlabs_key
```

## Step-by-Step Setup

### 1. Telegram Configuration

1. Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number
2. Click on "API development tools"
3. Create a new application and note down the API ID and API Hash
4. Add these values to your configuration file:
   - `TELEGRAM_API_ID`: The API ID from Telegram
   - `TELEGRAM_API_HASH`: The API Hash from Telegram
   - `TELEGRAM_PHONE_NUMBER`: Your phone number with country code (e.g., `+1234567890`)

### 2. AI Provider Configuration

Choose one of the following options:

#### Option A: OpenRouter

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up and navigate to the API Keys section
3. Create a new API key
4. Add these values to your configuration:
   - `LLM_PROVIDER=openrouter`
   - `OPENROUTER_API_KEY=your_openrouter_key`
   - `OPENROUTER_MODEL` (optional, defaults to `google/gemma-7b-it`)

#### Option B: Google Gemini

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Create an API key for the Gemini API
3. Add these values to your configuration:
   - `LLM_PROVIDER=gemini`
   - `GEMINI_API_KEY=your_gemini_key`
   - `GEMINI_MODEL` (optional, defaults to `gemini-pro`)

### 3. Additional Configuration

#### FFmpeg Setup (for voice processing)

If you plan to use speech-to-text or text-to-speech features:

1. Install FFmpeg on your system
2. Find the path to the FFmpeg executable
3. Add it to your configuration as `PATHS_FFMPEG_EXECUTABLE`

#### Optional Services

- **AssemblyAI**: For enhanced speech-to-text capabilities
- **ElevenLabs**: For enhanced text-to-speech capabilities

## Configuration Validation

To verify your configuration is correct, run:

```bash
sakaibot ai config
```

This will display your current AI configuration and status.

You can also run:

```bash
sakaibot status
```

This will show the overall status of your bot, including configuration status.

## Advanced Configuration

### Custom Models

You can use any model supported by your chosen provider:

For OpenRouter, visit [OpenRouter Models](https://openrouter.ai/models) to see available models.

For Gemini, you can use models like:

- `gemini-pro`
- `gemini-1.5-pro-latest`
- `gemini-ultra` (if available)

### Message Limits

Adjust the maximum number of messages to analyze with:

```
USERBOT_MAX_ANALYZE_MESSAGES=5000  # Maximum allowed is 10000
```

## Troubleshooting

### Common Issues

1. **Invalid API Credentials**: Double-check your API ID and API Hash from Telegram
2. **Invalid Phone Number**: Ensure your phone number includes the country code and starts with `+`
3. **API Key Issues**: Verify your AI provider API keys are correct and have sufficient permissions
4. **FFmpeg Not Found**: Ensure FFmpeg is installed and the path is correctly specified

### Testing Configuration

After configuration, test your setup:

```bash
# Test Telegram connection
python sakaibot.py

# Test AI functionality
sakaibot ai test

# View current configuration
sakaibot config show
```

### Environment-Specific Configuration

For different environments (development, production), you can:

1. Create multiple `.env` files (e.g., `.env.dev`, `.env.prod`)
2. Use the `--config-file` option to specify which configuration to use:
   ```bash
   sakaibot --config-file .env.prod status
   ```

## Security Considerations

1. **Never commit** your `.env` file or API keys to version control
2. Ensure your configuration files have appropriate file permissions
3. Store API keys securely and rotate them periodically
4. Regularly review access to your Telegram account and API keys

## Next Steps

After completing the configuration:

1. Run `sakaibot pv refresh` to load your private chats
2. Run `sakaibot group list` to see your groups
3. Run `sakaibot ai test` to verify AI functionality
4. Start using the bot with `sakaibot monitor start`
