# SakaiBot CLI Documentation

## Overview

SakaiBot provides a modern command-line interface built with Click and Rich libraries, offering a professional user experience with colored output, interactive prompts, and intuitive commands.

## Installation & Setup

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### Quick Start
```bash
# Clone repository
git clone https://github.com/yourusername/SakaiBot
cd SakaiBot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure bot
cp .env.example .env
# Edit .env with your credentials

# Run the bot
python sakaibot.py
```

## Command Structure

```
sakaibot [OPTIONS] COMMAND [ARGS]
```

### Global Options
- `--debug` - Enable debug mode for verbose output
- `--config-file PATH` - Use custom configuration file
- `--help` - Show help message

## Commands Reference

### 📊 Status & Configuration

#### `sakaibot status`
Display current bot status and configuration overview.

```bash
sakaibot status
```

Shows:
- System configuration status
- AI provider status and model
- Categorization settings
- Authorization status
- Cache availability

#### `sakaibot config`
Manage bot configuration.

```bash
# Show current configuration
sakaibot config show
sakaibot config show --all  # Show full values

# Validate configuration
sakaibot config validate

# Show example configuration
sakaibot config example

# Edit configuration
sakaibot config edit
```

### 💬 Private Chat Management

#### `sakaibot pv`
Manage private chats (PVs).

```bash
# List cached private chats
sakaibot pv list
sakaibot pv list --limit 50 --refresh

# Refresh PV cache from Telegram
sakaibot pv refresh
sakaibot pv refresh --fetch-limit 300

# Search for private chats
sakaibot pv search "john"
sakaibot pv search "@username" --limit 10

# Set default context for analysis
sakaibot pv set-context "@johndoe"
sakaibot pv set-context --clear

# Show current context
sakaibot pv context
```

### 👥 Group Management

#### `sakaibot group`
Manage groups and categorization settings.

```bash
# List groups
sakaibot group list
sakaibot group list --refresh --all

# Set target group for categorization
sakaibot group set "Work Team"
sakaibot group set --clear

# List topics in forum group
sakaibot group topics

# Manage command mappings
sakaibot group map           # List current mappings
sakaibot group map --add      # Add new mapping
sakaibot group map --remove   # Remove a mapping
sakaibot group map --clear    # Clear all mappings
```

### 🔐 Authorization Management

#### `sakaibot auth`
Manage authorized users who can send commands.

```bash
# List authorized users
sakaibot auth list

# Add authorized user
sakaibot auth add "@username"
sakaibot auth add "John Doe"
sakaibot auth add 12345678  # By user ID

# Remove authorization
sakaibot auth remove "@username"
sakaibot auth remove 12345678

# Clear all authorizations
sakaibot auth clear
```

### 🔄 Monitoring

#### `sakaibot monitor`
Control global monitoring for commands and messages.

```bash
# Start monitoring
sakaibot monitor start
sakaibot monitor start --verbose  # Show detailed output

# Stop monitoring
sakaibot monitor stop

# Show monitoring status
sakaibot monitor status
```

### 🤖 AI Features

#### `sakaibot ai`
AI provider management and testing.

```bash
# Test AI configuration
sakaibot ai test
sakaibot ai test --prompt "Custom test prompt"

# Show AI configuration
sakaibot ai config

# Send custom prompt
sakaibot ai prompt "Explain quantum computing"
sakaibot ai prompt "Write code" --max-tokens 2000 --temperature 0.5

# Translate text
sakaibot ai translate "Hello world" fa
sakaibot ai translate "Bonjour" en --source fr
```

## Interactive Features

### Rich Output
- ✅ **Colored text** for better readability
- 📊 **Tables** for structured data display
- 🔄 **Progress spinners** during operations
- ⚠️ **Clear messages** for errors, warnings, and success

### Interactive Prompts
- **Choice selection** from lists
- **Confirmation prompts** for destructive actions
- **Text input** with validation
- **Number input** with range validation

## Command Examples

### Initial Setup
```bash
# 1. Check configuration
sakaibot config validate

# 2. Show current status
sakaibot status

# 3. Refresh contact list
sakaibot pv refresh

# 4. Set up categorization
sakaibot group set "My Group"
sakaibot group map --add

# 5. Add authorized users
sakaibot auth add "@trusted_user"

# 6. Start monitoring
sakaibot monitor start
```

### Daily Usage
```bash
# Check bot status
sakaibot status

# Search and message a contact
sakaibot pv search "john"

# Monitor for commands
sakaibot monitor start --verbose
```

### AI Operations
```bash
# Test AI is working
sakaibot ai test

# Translate message
sakaibot ai translate "Hello friend" persian

# Send custom prompt
sakaibot ai prompt "Summarize the benefits of Python"
```

## Advanced Usage

### Scripting
The CLI is designed for easy scripting:

```bash
#!/bin/bash
# daily_refresh.sh

# Refresh all caches
sakaibot pv refresh --fetch-limit 500
sakaibot group list --refresh

# Check status
sakaibot monitor status

# Start monitoring if not active
if ! sakaibot monitor status | grep -q "Active"; then
    sakaibot monitor start
fi
```

### Shell Aliases
Add to your shell configuration (`.bashrc`, `.zshrc`):

```bash
alias sb='python ~/SakaiBot/sakaibot.py'
alias sbmon='python ~/SakaiBot/sakaibot.py monitor start'
alias sbstatus='python ~/SakaiBot/sakaibot.py status'
alias sbpv='python ~/SakaiBot/sakaibot.py pv list'
```

### Environment Variables
You can override configuration with environment variables:

```bash
export TELEGRAM_API_ID=12345678
export LLM_PROVIDER=gemini
export DEBUG=true

sakaibot status  # Will use these values
```

## Troubleshooting

### Common Issues

#### Command Not Found
```bash
# Make script executable
chmod +x sakaibot.py

# Or use Python directly
python sakaibot.py [command]
```

#### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### Configuration Errors
```bash
# Validate configuration
sakaibot config validate

# Check specific provider
sakaibot ai config
```

#### Permission Errors
```bash
# Fix directory permissions
chmod 755 data/ cache/ logs/

# Fix file permissions
chmod 644 .env
```

## Tips & Best Practices

### Performance
- **Cache regularly**: Refresh PV cache weekly for accuracy
- **Limit fetches**: Use reasonable limits when refreshing
- **Monitor selectively**: Only monitor when needed

### Security
- **Protect .env**: Never commit or share your .env file
- **Rotate keys**: Change API keys periodically
- **Limit authorizations**: Only authorize trusted users
- **Review logs**: Check logs regularly for issues

### Organization
- **Use contexts**: Set default PV for frequent conversations
- **Map commands**: Create intuitive command mappings
- **Document mappings**: Keep a list of your custom commands

## Keyboard Shortcuts

- `Ctrl+C` - Stop current operation or monitoring
- `Tab` - Auto-completion (where supported)
- `Enter` - Confirm selection
- `Ctrl+D` - Exit CLI

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Connection error
- `130` - Interrupted by user (Ctrl+C)

## Getting Help

```bash
# General help
sakaibot --help

# Command-specific help
sakaibot pv --help
sakaibot monitor --help

# Subcommand help
sakaibot pv list --help
```

## See Also

- [FEATURES.md](FEATURES.md) - Complete feature documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration guide
- [DEVELOPMENT.md](DEVELOPMENT.md) - Developer documentation