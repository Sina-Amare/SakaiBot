# SakaiBot Telegram Commands Guide

## How to Use Commands in Telegram

SakaiBot responds to commands sent directly in Telegram chats. When monitoring is active, you can use these commands:

### 1. **Start Monitoring First**
```bash
# From command line:
sakaibot monitor start

# Or from interactive menu:
sakaibot menu
# Select: 4 (Monitoring) → 1 (Start Monitoring)
```

### 2. **Available Telegram Commands**

Once monitoring is active, you can use these commands in any Telegram chat:

## 📝 AI Commands

### `/prompt=<your question>`
Send any question or instruction to the AI.

**Examples:**
```
/prompt=What is the weather like today?
/prompt=تحلیل کن که چرا همه جلسات کاری در نهایت به بحث در مورد غذا ختم میشن
/prompt=Write a sarcastic analysis of modern social media
```

### `/translate=<language>[,source_language] <text>`
Translate text to any language with Persian phonetics support.

**Examples:**
```
/translate=fa Hello world
/translate=persian How are you today?
/translate=en,fa سلام دنیا
/translate=spanish I love programming
```

**Reply Mode:** Reply to any message with just the language:
```
/translate=fa
/translate=english
```

### `/analyze=<number>`
Analyze the last N messages in the current chat with Persian sarcastic style.

**Examples:**
```
/analyze=50    # Analyze last 50 messages
/analyze=100   # Analyze last 100 messages
/analyze=500   # Analyze last 500 messages
```

### `/tellme=<number>=<question>`
Ask a question about the last N messages in the chat.

**Examples:**
```
/tellme=50=What were the main topics discussed?
/tellme=100=چه کسایی بیشتر حرف زدن؟
/tellme=200=Summarize the conversation with humor
```

## 🎯 Message Categorization

When you have a target group set up with command mappings, messages starting with mapped commands will be automatically forwarded to the appropriate group/topic.

### Setup Categorization:
1. Set target group:
   ```bash
   sakaibot group set
   ```

2. Add command mappings:
   ```bash
   sakaibot group map --add
   ```

3. Start monitoring:
   ```bash
   sakaibot monitor start
   ```

### Example Mappings:
- `/bug` → forwards to "Bug Reports" topic
- `/feature` → forwards to "Feature Requests" topic
- `/help` → forwards to "Support" topic

## 👥 Authorized Users

Authorized users can send commands that will be forwarded to you for approval.

### Setup:
```bash
# Add authorized user
sakaibot auth add <username_or_id>

# List authorized users
sakaibot auth list

# Remove authorized user
sakaibot auth remove <username_or_id>
```

When an authorized user sends a command, you'll receive a notification to confirm execution.

## 🔧 Command Patterns

All commands follow these patterns:
- **Owner commands**: Start with `/` and sent by you (outgoing messages)
- **Authorized commands**: Start with `/` and sent by authorized users (incoming messages)
- **Pattern matching**: `/\w+` (any word characters after slash)

## 💡 Tips

1. **Persian Support**: All AI commands fully support Persian text and will provide phonetic translations.

2. **Sarcastic Analysis**: The `/analyze` command uses the Persian sarcastic prompts you configured, providing witty observations like The Office narrator.

3. **Context-Aware**: Commands like `/tellme` and `/analyze` work with the current chat's message history.

4. **Reply Feature**: For `/translate`, you can reply to any message instead of typing the text.

5. **Background Processing**: All commands are processed asynchronously, so they won't block other operations.

## 🚀 Quick Start Example

1. Start monitoring:
   ```bash
   sakaibot monitor start --verbose
   ```

2. In any Telegram chat, type:
   ```
   /prompt=Tell me a joke
   /translate=fa artificial intelligence
   /analyze=50
   ```

3. The bot will process and respond to your commands automatically!

## ⚠️ Requirements

Before commands work, ensure:
- ✅ Bot is authenticated (`sakaibot auth status`)
- ✅ AI is configured (Gemini or OpenRouter API key)
- ✅ Monitoring is active (`sakaibot monitor start`)
- ✅ For categorization: Target group and mappings are set

## 🛑 Stop Monitoring

To stop processing commands:
```bash
sakaibot monitor stop
```

Or press `Ctrl+C` while monitoring is running.