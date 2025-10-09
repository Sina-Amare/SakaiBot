# SakaiBot CLI Documentation

## Overview

The SakaiBot CLI provides a comprehensive command-line interface for managing and interacting with your Telegram userbot. The CLI is built using the Click framework and provides several command groups for different functionalities.

## Getting Started

### Running the CLI

You can run the CLI in several ways:

```bash
# Direct Python execution
python sakaibot.py

# Using the installed command (if installed)
sakaibot

# Show help
sakaibot --help
```

### Global Options

- `--debug`: Enable debug mode for more verbose output
- `--config-file`: Specify a custom configuration file path

## Command Structure

The CLI is organized into several command groups:

```
sakaibot [OPTIONS] COMMAND [ARGS]...
```

### Available Commands

- `ai`: AI provider management and testing
- `auth`: Authorization management
- `config`: Configuration management
- `group`: Group management
- `monitor`: Monitoring controls
- `pv`: Private chat management
- `status`: Show current bot status
- `menu`: Start interactive menu system
- `setup`: Run interactive setup wizard

## Detailed Command Reference

### PV (Private Chats) Commands

Manage your private conversations with contacts.

#### `sakaibot pv list`

List all cached private chats.

**Options:**

- `--limit INTEGER`: Number of PVs to display (default: 50)
- `--refresh`: Refresh cache before listing

**Example:**

```bash
sakaibot pv list --limit 100
sakaibot pv list --refresh
```

#### `sakaibot pv refresh`

Refresh PV list from Telegram.

**Options:**

- `--fetch-limit INTEGER`: Number of recent chats to fetch (default: 200)

**Example:**

```bash
sakaibot pv refresh --fetch-limit 500
```

#### `sakaibot pv search`

Search for private chats by name, username, or ID.

**Arguments:**

- `QUERY`: Search query

**Options:**

- `--limit INTEGER`: Maximum results to show (default: 10)

**Example:**

```bash
sakaibot pv search "john"
sakaibot pv search "123456789" --limit 5
```

#### `sakaibot pv set-context`

Set default PV context for analysis commands.

**Arguments:**

- `IDENTIFIER`: PV identifier (username, ID, or name)

**Options:**

- `--clear`: Clear the default context

**Example:**

```bash
sakaibot pv set-context john_doe
sakaibot pv set-context --clear
```

#### `sakaibot pv context`

Show current default PV context.

**Example:**

```bash
sakaibot pv context
```

### Group Commands

Manage your Telegram groups.

#### `sakaibot group list`

List all cached groups.

**Options:**

- `--limit INTEGER`: Number of groups to display (default: 50)
- `--refresh`: Refresh cache before listing

#### `sakaibot group refresh`

Refresh group list from Telegram.

**Options:**

- `--fetch-limit INTEGER`: Number of recent groups to fetch (default: 200)

#### `sakaibot group search`

Search for groups by name or ID.

**Arguments:**

- `QUERY`: Search query

**Options:**

- `--limit INTEGER`: Maximum results to show (default: 10)

#### `sakaibot group set`

Set target group for categorization.

**Arguments:**

- `IDENTIFIER`: Group identifier (username, ID, or name)

**Options:**

- `--clear`: Clear the selected group

#### `sakaibot group map`

Manage command to topic mappings for forum groups. This command allows you to map specific commands to specific topics within a forum group.

**Options:**

- `--add`: Add a new mapping
- `--remove`: Remove an existing mapping
- `--clear`: Clear all mappings
- `--list`: List all existing mappings (default)

**Example:**

```bash
# List all current mappings
sakaibot group map --list

# Add a new mapping (will prompt for command and target topic)
sakaibot group map --add

# Remove a mapping
sakaibot group map --remove

# Clear all mappings
sakaibot group map --clear
```

When adding a mapping, if the target group is a forum, you will be prompted to select a specific topic for the command. Multiple commands can be mapped to the same topic.

#### `sakaibot group topics`

List topics in the selected group.

### Auth Commands

Manage authorized users who can interact with your bot.

#### `sakaibot auth list`

List authorized users.

#### `sakaibot auth add`

Add an authorized user.

**Arguments:**

- `IDENTIFIER`: User identifier (username, ID, or name)

#### `sakaibot auth remove`

Remove an authorized user.

**Arguments:**

- `IDENTIFIER`: User identifier (username, ID, or name)

### Monitor Commands

Control the monitoring of messages.

#### `sakaibot monitor start`

Start processing messages and commands.

#### `sakaibot monitor stop`

Stop processing messages.

#### `sakaibot monitor status`

Show monitoring status.

### AI Commands

Manage and test AI functionality.

#### `sakaibot ai test`

Test AI configuration with a simple prompt.

**Options:**

- `--prompt TEXT`: Test prompt (default: "Hello, please respond with 'AI is working!'")

**Example:**

```bash
sakaibot ai test
sakaibot ai test --prompt "What's the weather like?"
```

#### `sakaibot ai config`

Show current AI configuration.

**Example:**

```bash
sakaibot ai config
```

#### `sakaibot ai translate`

Translate text using AI.

**Arguments:**

- `TEXT`: Text to translate
- `TARGET_LANGUAGE`: Target language

**Options:**

- `--source TEXT`: Source language (default: auto)

**Example:**

```bash
sakaibot ai translate "Hello world" "Persian"
sakaibot ai translate "Bonjour" "English" --source French
```

#### `sakaibot ai prompt`

Send a custom prompt to AI.

**Arguments:**

- `PROMPT`: The prompt to send

**Options:**

- `--max-tokens INTEGER`: Maximum response tokens (default: 1500)
- `--temperature FLOAT`: Response creativity (0.0-1.0) (default: 0.7)

**Example:**

```bash
sakaibot ai prompt "Explain quantum computing in simple terms"
sakaibot ai prompt "Write a poem about programming" --max-tokens 2000 --temperature 0.9
```

### Config Commands

Manage configuration settings.

#### `sakaibot config show`

Show current configuration.

#### `sakaibot config validate`

Validate configuration.

### Status Command

#### `sakaibot status`

Show current bot status and configuration.

### Menu Command

#### `sakaibot menu`

Start interactive menu system with a navigable interface.

### Setup Command

#### `sakaibot setup`

Run interactive setup wizard (coming soon).

## Interactive Menu

The interactive menu provides a user-friendly way to navigate SakaiBot's features:

```bash
sakaibot menu
```

This command starts a menu-driven interface where you can:

- View and manage private chats
- Manage groups and categorization
- Configure AI settings
- Start/stop monitoring
- Access various bot features

## Command Examples

### Basic Operations

```bash
# Check bot status
sakaibot status

# List private chats
sakaibot pv list

# Search for a contact
sakaibot pv search "friend_name"

# Refresh contact list
sakaibot pv refresh

# Test AI functionality
sakaibot ai test

# Show AI configuration
sakaibot ai config
```

### Advanced Operations

```bash
# Translate text
sakaibot ai translate "Hello, how are you?" "Persian"

# Send custom prompt to AI
sakaibot ai prompt "Summarize the benefits of Python programming"

# Set default context for analysis
sakaibot pv set-context "important_contact"

# Add authorized user
sakaibot auth add "trusted_friend"

# Start monitoring
sakaibot monitor start
```

## Error Handling

The CLI provides clear error messages when commands fail:

- Invalid configuration will result in configuration error messages
- Network issues will be reported with appropriate error details
- Invalid arguments will show usage information
- API errors from AI providers will be displayed with troubleshooting tips

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Usage error (invalid arguments)
- `3`: Configuration error
- `4`: API or network error

## Tips and Best Practices

1. **Use the interactive menu** (`sakaibot menu`) if you're new to the CLI
2. **Refresh your PV and group lists** regularly with `sakaibot pv refresh` and `sakaibot group refresh`
3. **Test your AI configuration** with `sakaibot ai test` before relying on AI features
4. **Use the status command** (`sakaibot status`) to verify your configuration
5. **Set up authorized users** with `sakaibot auth add` to control who can use your bot's features
