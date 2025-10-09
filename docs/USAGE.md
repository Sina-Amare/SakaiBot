# SakaiBot Usage Guide

## Overview

This guide provides instructions for using SakaiBot's features, whether you're a developer setting up the bot or an end-user interacting with its features through Telegram.

## Getting Started

### Prerequisites

Before using SakaiBot, ensure you have:

1. A Telegram account
2. Your own Telegram API credentials (API ID and Hash)
3. An AI provider API key (optional but recommended)

### Initial Setup

1. Install SakaiBot:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure your credentials (see [Configuration Guide](CONFIGURATION.md) for details)

3. Run the application:

   ```bash
   python sakaibot.py
   ```

4. Follow the authentication process to connect your Telegram account

## Basic Usage

### Using the Interactive Menu

When you start SakaiBot without any commands, you'll be presented with an interactive menu:

```
Would you like to:
 [1] 🎛️  Interactive Menu (navigate with numbers)
  [2] 📊 Show Status (default)
  [3] 🚪 Exit
```

Select option 1 to access the interactive menu system where you can:

- View and manage private chats
- Manage groups and categorization
- Configure AI settings
- Start/stop monitoring
- Access various bot features

### Using Command Line Interface

You can also use SakaiBot directly through command-line commands:

```bash
# Check bot status
sakaibot status

# List private chats
sakaibot pv list

# Test AI functionality
sakaibot ai test
```

## Telegram Commands

Once your bot is running and monitoring is active, you can use various commands in Telegram:

### AI Commands

#### `/prompt` - Custom AI Queries

Ask the AI anything using this command:

- Usage: `/prompt=your question or instruction`
- Example: `/prompt=Explain quantum computing in simple terms`

#### `/translate` - Translation with Phonetics

Translate text with Persian phonetic pronunciation:

- Usage: `/translate=language [text]` or reply to a message with `/translate=language`
- Example: `/translate=Persian Hello, how are you?`
- Provides both translation and phonetic pronunciation

#### `/analyze` - Conversation Analysis

Analyze recent conversation history:

- Usage: `/analyze=number_of_messages`
- Example: `/analyze=50` (analyzes last 50 messages)
- Provides detailed summaries and insights

#### `/tellme` - Question Answering

Ask questions based on recent chat history:

- Usage: `/tellme=number_of_messages=your_question`
- Example: `/tellme=10=What did John say about the project?`

### Speech Commands

#### `/stt` - Speech-to-Text

Convert voice messages to text:

- Reply to a voice message with `/stt`
- The bot will transcribe the voice message and provide an AI summary

#### `/tts` or `/speak` - Text-to-Speech

Convert text to voice messages:

- Usage: `/tts [params] <text>` or reply to a text message with `/tts [params]`
- Parameters: `voice=<voice_id>`, `rate=<±N%>`, `volume=<±N%>`
- Example: `/tts voice=en-US-JennyNeural rate=-10% Hello world`

### Categorization Commands

When configured with categorization settings, you can use commands to forward messages to specific topics:

- Use custom commands like `/work`, `/personal`, etc. when replying to messages
- Messages will be forwarded to the configured topic in your target group

#### Forum Group Mapping

For forum groups, you can set up specific command-to-topic mappings using the CLI:

1. Set your target forum group:

   ```bash
   sakaibot group set "your_forum_group"
   ```

2. Map commands to specific topics:

   ```bash
   sakaibot group map --add
   ```

   This will prompt you to enter a command and select a topic for it.

3. Multiple commands can be mapped to the same topic, allowing for flexible categorization:

   - `/help` and `/support` can both map to a "Support" topic
   - `/news` and `/updates` can both map to an "Announcements" topic

4. List current mappings:
   ```bash
   sakaibot group map --list
   ```

When you send a command (like `/help`) in reply to a message, the bot will forward that message to the corresponding topic in your forum group.

## Managing Your Setup

### Private Chats (PVs)

Manage your private conversations:

```bash
# List private chats
sakaibot pv list

# Refresh PV list from Telegram
sakaibot pv refresh

# Search for a contact
sakaibot pv search "john"

# Set default context for analysis
sakaibot pv set-context "important_contact"
```

### Groups

Manage your groups:

```bash
# List groups
sakaibot group list

# Set target group for categorization
sakaibot group set "my_group"
```

### Authorization

Control who can use your bot's features:

```bash
# List authorized users
sakaibot auth list

# Add an authorized user
sakaibot auth add "trusted_friend"

# Remove an authorized user
sakaibot auth remove "username"
```

### Monitoring

Control message monitoring:

```bash
# Start monitoring
sakaibot monitor start

# Stop monitoring
sakaibot monitor stop

# Check monitoring status
sakaibot monitor status
```

## Advanced Usage

### Custom Configuration

You can customize various aspects of the bot:

- Adjust message limits in configuration
- Set up multiple AI provider accounts
- Configure different voices for TTS
- Set up custom categorization commands

### Using the Interactive Menu

The interactive menu provides a user-friendly way to navigate all features:

```bash
sakaibot menu
```

This command starts a menu-driven interface where you can access all bot features through numbered options.

### AI Configuration

Configure your AI settings:

```bash
# Show current AI configuration
sakaibot ai config

# Test AI functionality
sakaibot ai test

# Translate text
sakaibot ai translate "Hello world" "Persian"

# Send custom prompt
sakaibot ai prompt "Summarize the benefits of Python programming"
```

## Tips for Effective Usage

### Best Practices

1. **Regular Updates**: Keep your bot updated with the latest version
2. **Refresh Contacts**: Regularly refresh your PV and group lists
3. **Secure API Keys**: Keep your API keys secure and rotate them periodically
4. **Monitor Usage**: Keep track of API usage to manage costs

### Troubleshooting

Common issues and solutions:

- **Authentication Problems**: Ensure your Telegram credentials are correct
- **AI Not Responding**: Check your AI provider configuration and API key validity
- **Commands Not Working**: Verify monitoring is active with `sakaibot monitor status`
- **Voice Processing Issues**: Ensure FFmpeg is properly installed and configured

### Performance Optimization

- Use caching features to reduce API calls
- Configure appropriate message limits
- Use selective monitoring for specific chats if needed

## Security Considerations

- Only authorize trusted users to use your bot's features
- Regularly review and update your authorized user list
- Monitor usage of your AI API keys
- Secure your configuration files

## Getting Help

If you encounter issues:

1. Check the [FAQ](FAQ.md) for common questions
2. Review the detailed [CLI documentation](CLI.md)
3. Examine the [configuration guide](CONFIGURATION.md) for setup issues
4. Look at the [features documentation](FEATURES.md) for detailed feature explanations

## Summary

SakaiBot provides a comprehensive solution for Telegram automation with AI capabilities. Whether you're using it for personal productivity, conversation analysis, or message categorization, the bot offers a range of features to enhance your Telegram experience. Start with the interactive menu for an easy introduction, then explore the command-line interface for more advanced usage.
