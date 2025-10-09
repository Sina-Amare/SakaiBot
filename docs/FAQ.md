# SakaiBot FAQ

## General Questions

### What is SakaiBot?

SakaiBot is an advanced Telegram userbot with AI capabilities that provides a comprehensive solution for message automation, categorization, and AI-assisted interactions. It allows you to automate various tasks on Telegram, analyze conversations, translate messages, and interact with AI directly from your Telegram chats.

### What are the main features of SakaiBot?

- **AI Integration**: Multiple LLM providers (OpenRouter, Google Gemini)
- **Smart Commands**: Custom prompts, translations, conversation analysis
- **Voice Processing**: Speech-to-text and text-to-speech capabilities
- **Message Management**: Automated categorization and forwarding
- **Security**: Multi-level authorization and confirmation flows
- **Modern CLI**: Rich terminal interface with colors and progress indicators

### Is SakaiBot free to use?

The core SakaiBot application is free and open-source. However, you'll need to pay for the AI services you use (OpenRouter or Google Gemini) and Telegram API usage according to their respective pricing models.

## Setup and Configuration

### How do I get Telegram API credentials?

1. Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number
2. Click on "API development tools"
3. Create a new application and note down the API ID and API Hash

### What AI providers are supported?

SakaiBot currently supports:

- OpenRouter (with access to multiple models)
- Google Gemini

### How do I configure AI providers?

You can configure AI providers by setting the appropriate environment variables in your `.env` file:

- For OpenRouter: `LLM_PROVIDER=openrouter` and `OPENROUTER_API_KEY=your_key`
- For Gemini: `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=your_key`

### Why do I need to authenticate with Telegram?

SakaiBot is a userbot, which means it operates from your personal Telegram account rather than as a separate bot. This allows it to access your private chats, groups, and perform actions on your behalf. The authentication process is secure and follows Telegram's authentication protocols.

## Usage Questions

### How do I start using SakaiBot after installation?

1. Complete the configuration with your credentials
2. Run `python sakaibot.py` or `sakaibot`
3. Complete the Telegram authentication process
4. Use the interactive menu or CLI commands to access features
5. Start monitoring with `sakaibot monitor start` to enable Telegram commands

### What's the difference between the CLI and Telegram commands?

- **CLI commands**: Used directly in the terminal to manage the bot, configure settings, and perform administrative tasks
- **Telegram commands**: Used within Telegram chats when monitoring is active, allowing for real-time interaction with AI and automation features

### How do I use the categorization feature?

1. Set a target group with `sakaibot group set "group_name"`
2. Configure command-topic mappings in the settings
3. When monitoring is active, reply to messages with categorization commands (like `/work`, `/personal`, etc.)
4. Messages will be forwarded to the appropriate topic in your target group

### Can multiple people use my SakaiBot?

Yes, you can authorize other users to use certain features of your bot using the authorization system:

```bash
sakaibot auth add "username_or_id"
```

Authorized users can then use AI commands and other features you grant them access to.

## AI Features

### How does the translation feature work?

The translation feature uses your configured AI provider to translate text. It supports Persian phonetic pronunciation to help with pronunciation. Use `/translate=language [text]` or reply to a message with `/translate=language`.

### What languages are supported for speech processing?

Speech processing capabilities depend on the underlying services (AssemblyAI, Edge-TTS). Common languages like English, Persian, and others are supported. The specific languages depend on the AI provider and TTS service being used.

### Why might AI commands fail?

AI commands might fail for several reasons:

- Invalid or expired API key
- Network connectivity issues
- AI provider service outages
- Content filtering by the AI provider
- Rate limiting from the API provider

## Troubleshooting

### The bot won't connect to Telegram

- Verify your API ID and Hash are correct
- Check your phone number format (should include country code with +)
- Ensure you can log into Telegram normally with your account
- Check your internet connection

### AI commands are not responding

- Verify your AI provider configuration is correct
- Check that your API key is valid and has sufficient credits
- Ensure the AI provider service is operational
- Check for any network connectivity issues

### Commands in Telegram are not working

- Make sure monitoring is active (`sakaibot monitor start`)
- Verify you're using the correct command format
- Check that you have the necessary permissions to use the command

### Voice messages are not being processed

- Ensure FFmpeg is installed and properly configured
- Check that your audio processing API keys are configured (AssemblyAI, etc.)
- Verify the audio format is supported

### The bot is not responding to commands

- Check if monitoring is active with `sakaibot monitor status`
- Verify the bot has proper permissions in the chat
- Ensure there are no network connectivity issues
- Check the logs for any error messages

## Performance and Security

### Is it safe to use SakaiBot with my Telegram account?

Yes, SakaiBot is designed to be safe for your Telegram account. It uses official Telegram APIs and follows security best practices. However, as with any third-party application:

- Only install from official sources
- Keep your API credentials secure
- Review the code if you're technically inclined
- Don't share your session files with others

### How does SakaiBot handle my data?

SakaiBot stores minimal data locally:

- Session information in the `data/` directory
- Cached PV and group information in the `cache/` directory
- Settings in the `data/settings.json` file
  The application doesn't store your messages or personal data beyond what's necessary for operation.

### Can I limit which chats the bot monitors?

Currently, the bot monitors all chats by default when monitoring is active. You can control access through the authorization system to determine who can use the bot's features in which chats.

## Advanced Questions

### How do I switch between AI providers?

You can switch between AI providers by changing the `LLM_PROVIDER` setting in your configuration:

- Set to `openrouter` for OpenRouter
- Set to `gemini` for Google Gemini
  Then update the corresponding API key and model settings.

### Can I customize the bot's behavior?

Yes, SakaiBot is designed to be extensible:

- You can modify the source code to customize behavior
- Add new commands by extending the command system
- Implement new AI providers by following the LLMProvider interface
- Modify prompts and responses as needed

### How do I update SakaiBot?

To update SakaiBot:

1. Pull the latest changes from the repository: `git pull`
2. Update dependencies: `pip install -r requirements.txt`
3. Check the release notes for any configuration changes needed
4. Restart the application

### What should I do if I encounter a bug?

1. Check if the issue is already reported in the GitHub issues
2. Update to the latest version to see if the issue is resolved
3. Enable debug mode to get more detailed logs
4. Report the issue on GitHub with detailed information about the problem
