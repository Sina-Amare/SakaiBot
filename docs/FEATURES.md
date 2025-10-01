# SakaiBot Features Documentation

## Overview
SakaiBot is a powerful Telegram userbot that extends your Telegram experience with AI capabilities, message management, and automation features. This document provides a comprehensive guide to all available features and commands.

## 🤖 AI-Powered Features

### Multiple LLM Provider Support
- **OpenRouter**: Access to various AI models through OpenRouter API
- **Google Gemini**: Direct integration with Google's Gemini AI models
- Easily switchable via configuration (`LLM_PROVIDER` in .env)

### AI Commands

#### `/prompt=<text>`
Send custom prompts directly to the configured AI model.

**Examples:**
```
/prompt=Explain quantum computing in simple terms
/prompt=Write a Python function to calculate fibonacci numbers
/prompt=Summarize the key points of machine learning
```

#### `/translate=<target_language>[,source_language] <text>`
Translate text between languages with optional phonetic pronunciation for Persian.

**Parameters:**
- `target_language`: The language to translate to (e.g., fa, en, es, fr, de)
- `source_language`: (Optional) Source language, defaults to "auto"
- `text`: The text to translate

**Examples:**
```
/translate=fa Hello world
/translate=en,fa سلام دنیا
/translate=es Good morning
```

**Special Persian Feature:**
When translating to Persian (fa/farsi), you get:
- Persian text
- Phonetic pronunciation in English letters

#### `/analyze=<number>`
Analyze the last N messages in the current chat and provide a comprehensive summary.

**Examples:**
```
/analyze=50    # Analyze last 50 messages
/analyze=100   # Analyze last 100 messages
/analyze=500   # Analyze last 500 messages
```

**Output includes:**
- Main topics discussed
- Key participants and their contributions
- Important decisions or conclusions
- Overall sentiment analysis
- Structured Persian report

#### `/tellme=<number>=<question>`
Ask questions about chat history - the AI will answer based on the last N messages.

**Examples:**
```
/tellme=100=What were the main topics discussed?
/tellme=50=Who mentioned the meeting time?
/tellme=200=What decisions were made?
```

## 🎤 Voice & Audio Features

### Speech-to-Text (STT)
Convert voice messages to text using Google Web Speech API.

#### `/stt`
Reply to any voice message with this command to transcribe it.

**Usage:**
1. Find a voice message in any chat
2. Reply to it with `/stt`
3. Bot will transcribe and send the text

**Supported Languages:**
- Auto-detection for most languages
- Optimized for Persian and English

### Text-to-Speech (TTS)
Convert text to natural-sounding speech using Azure Neural Voices.

#### `/tts [params] <text>` or `/speak [params] <text>`
Generate voice messages from text.

**Parameters:**
- `voice=<voice_id>`: Select voice (default: fa-IR-DilaraNeural for Persian)
- `rate=<±N%>`: Adjust speech rate (e.g., -10%, +20%)
- `volume=<±N%>`: Adjust volume (e.g., -5%, +15%)

**Examples:**
```
/tts Hello world
/tts voice=en-US-JennyNeural Hello everyone
/tts rate=-10% volume=+5% This is slower and louder
/speak voice=fa-IR-FaridNeural سلام دوستان
```

**Available Persian Voices:**
- fa-IR-DilaraNeural (Female, default)
- fa-IR-FaridNeural (Male)

## 📨 Message Management & Categorization

### Private Chat (PV) Management
- **Cache System**: Fast access to your private chats without repeated API calls
- **Search**: Find chats by name, username, or user ID
- **Default Context**: Set a default chat for analysis commands

### Group Management
- **Forum Support**: Full support for Telegram forum groups with topics
- **Topic Mapping**: Map custom commands to specific forum topics
- **Admin Features**: Manage groups where you have admin rights

### Message Categorization System
Forward messages to specific groups/topics using custom commands.

**Setup Process:**
1. Select target group (regular or forum)
2. Create command mappings (e.g., /work → Work topic)
3. Use commands to categorize and forward messages

**Example Workflow:**
```
/work          # Forward to Work topic
/personal      # Forward to Personal topic
/important     # Forward to Important topic
```

## 🔐 Security & Authorization

### Multi-Level Authorization
1. **Owner Commands**: Full access to all features (you)
2. **Authorized Users**: Can send commands for your approval
3. **Confirmation Flow**: Review and approve commands from others

### Confirmation System
When authorized users send commands:
1. Message is forwarded to you
2. Reply with `confirm` to execute
3. Or ignore to reject

**Security Features:**
- Whitelist-based authorization
- Command validation
- Audit logging of all commands

## 🔄 Event Monitoring

### Global Monitoring Mode
Monitor and process commands across all your chats.

**What it monitors:**
- Your outgoing messages starting with `/`
- Commands from authorized users
- Replies for categorization

**Activation Requirements:**
- For Categorization: Target group + command mappings
- For AI Features: Valid API key configuration

## ⚙️ Configuration & Settings

### Configuration Files

#### `.env` (Primary Configuration)
```env
# Telegram Configuration
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE_NUMBER=+1234567890

# LLM Provider Selection
LLM_PROVIDER=gemini  # or openrouter

# Google Gemini
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash

# OpenRouter (Alternative)
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash

# Optional Services
ASSEMBLYAI_API_KEY=your_assemblyai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

#### Auto-Managed Files
- `data/sakaibot_session.session`: Telegram session
- `data/sakaibot_user_settings.json`: User preferences
- `cache/pv_cache.json`: Private chat cache
- `cache/group_cache.json`: Group cache
- `logs/monitor_activity.log`: Activity logs

## 📊 Data Management

### Cache System
- **Automatic Caching**: PVs and groups are cached for performance
- **Manual Refresh**: Update cache on-demand
- **Smart Updates**: Incremental updates preserve data

### Settings Persistence
- All CLI configurations are auto-saved
- Settings survive bot restarts
- JSON-based storage for easy backup

## 🚀 Advanced Features

### Batch Processing
- Process multiple messages simultaneously
- Queue commands for sequential execution
- Parallel API calls for efficiency

### Error Recovery
- Automatic retry with exponential backoff
- Graceful degradation on API failures
- Comprehensive error logging

### Performance Optimization
- Message batching for analysis
- Lazy loading of resources
- Connection pooling for API calls

## 📝 Command Quick Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/prompt=<text>` | Send AI prompt | `/prompt=Explain AI` |
| `/translate=<lang> <text>` | Translate text | `/translate=fa Hello` |
| `/analyze=<n>` | Analyze messages | `/analyze=100` |
| `/tellme=<n>=<q>` | Ask about chat | `/tellme=50=What happened?` |
| `/stt` | Voice to text | Reply with `/stt` |
| `/tts <text>` | Text to voice | `/tts Hello world` |
| `confirm` | Approve command | Reply with `confirm` |

## 🔧 Troubleshooting

### Common Issues

**AI Commands Not Working:**
- Check API key configuration
- Verify provider selection in .env
- Ensure internet connectivity

**Voice Features Failing:**
- Verify FFmpeg installation
- Check audio file size limits
- Ensure proper voice message format

**Cache Not Updating:**
- Use manual refresh option
- Check file permissions
- Clear cache if corrupted

## 📈 Usage Tips

1. **Optimize API Usage**: Use appropriate message limits for analysis
2. **Cache Management**: Refresh cache periodically for accuracy
3. **Command Shortcuts**: Create short, memorable command mappings
4. **Batch Operations**: Group similar tasks together
5. **Error Monitoring**: Check logs regularly for issues

## 🔮 Future Enhancements

Planned features include:
- Support for more LLM providers (Claude, Local LLMs)
- Advanced message filtering and search
- Scheduled command execution
- Multi-language UI support
- Enhanced voice recognition accuracy
- Custom AI model fine-tuning support

---

For more information, see [ARCHITECTURE.md](ARCHITECTURE.md) for technical details or [CLI_GUIDE.md](CLI_GUIDE.md) for interface documentation.