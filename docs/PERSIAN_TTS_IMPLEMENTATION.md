# Persian Text-to-Speech (TTS) Implementation

## Overview

SakaiBot now includes a free and reliable Persian Text-to-Speech feature that converts Persian text messages into voice and sends the generated audio file back to the chat.

## Implementation Details

### TTS Providers Priority Order

1. **gTTS (Google Text-to-Speech)** - Primary provider (free, online)

   - Used first for languages it supports
   - Does not support Persian (fa) language
   - Falls back gracefully when Persian is detected

2. **pyttsx3 (Local TTS Engine)** - Secondary provider (free, offline)

   - Used when gTTS doesn't support the language
   - Works offline without internet connection
   - Supports Persian text-to-speech
   - Cross-platform compatibility

3. **Hugging Face API** - Fallback provider (requires API token)

   - Used when other free providers fail
   - Requires `HUGGINGFACE_API_TOKEN` in environment

4. **Google Translate TTS** - Final fallback (free, online)
   - Used as last resort for unsupported languages
   - May be rate-limited

### Command Usage

- Use `/tts` followed by Persian text: `/tts سلام، چطوری؟`
- Or reply to a message with `/tts` to convert that message to speech
- Audio output is sent as a voice note compatible with Telegram

### Technical Specifications

- Output format: MP3 (compatible with Telegram voice notes)
- Audio files are temporary and cleaned up after sending
- Text chunking for long messages to handle API limitations
- Error handling with user-friendly Persian error messages

## Benefits

- **Free**: No paid APIs or external billing dependencies
- **Reliable**: Multiple fallback options ensure availability
- **Local**: pyttsx3 works offline for basic functionality
- **Persian-optimized**: Specifically designed to handle Persian text properly
- **Telegram-compatible**: Output format works with Telegram voice notes

## Dependencies

- `gtts` - For online TTS when language is supported
- `pyttsx3` - For local offline TTS (especially for Persian)
- `pydub` - For audio processing and format conversion
- `requests` - For API communications

## Architecture

The TTS system is modular and integrated with SakaiBot's command handling system through the `TextToSpeechProcessor` class in `src/ai/tts.py`. The system follows the failover pattern to ensure maximum availability while prioritizing free and local solutions.
