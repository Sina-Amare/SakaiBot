# SakaiBot Features

## Overview

SakaiBot is an advanced Telegram userbot with AI capabilities that provides a comprehensive solution for message automation, categorization, and AI-assisted interactions. This document details all the features available in the application.

## Core Features

### 1. AI Integration

SakaiBot supports multiple LLM providers for intelligent processing:

#### Multiple Provider Support

- **OpenRouter**: Access to various models through the OpenRouter API
- **Google Gemini**: Google's advanced AI models
- Easy switching between providers via configuration

#### AI-Powered Commands

- **/prompt**: Send custom prompts to the AI
- **/translate**: Translate text with phonetic pronunciation
- **/analyze**: Analyze conversation history
- **/tellme**: Ask questions based on chat history

### 2. Speech Processing

#### Speech-to-Text (STT)

- Convert voice messages to text
- Reply to voice messages with `/stt` command
- AI-powered transcription with context understanding
- Support for multiple languages

#### Text-to-Speech (TTS)

- Convert text to voice messages
- Use the `/tts` command with Persian text.
- Generates natural-sounding voice messages using a free, reliable engine.
- Support for Persian and other languages

### 3. Message Management

#### Automated Categorization

- Forward messages to specific topics in groups
- Set up command-topic mappings
- Organize conversations automatically
- Support for Telegram forum topics

#### Message Analysis

- Summarize long conversations
- Analyze conversation patterns
- Extract key information from chat history
- Understand participant interactions

### 4. Command-Line Interface

#### Rich Interactive Menu

- Navigate with numbered options
- Access all features through a menu system
- Colorful terminal interface with progress indicators
- Easy-to-use navigation

#### Command Groups

- **PV Management**: Handle private chats
- **Group Management**: Manage groups and topics
- **Authorization**: Control access for other users
- **Monitoring**: Start/stop message processing
- **AI Tools**: Test and configure AI features

### 5. Authorization System

#### Multi-Level Authorization

- Owner account with full access
- Authorized users with limited permissions
- Confirmation flows for sensitive actions
- Secure command execution

#### Confirmation Flows

- Prevent accidental actions
- Explicit confirmation for forwarding messages
- Secure handling of categorization commands

## Detailed Feature Descriptions

### AI Features

#### Prompt Command

The `/prompt` command allows you to send custom requests to the AI:

- Usage: `/prompt=your question or instruction`
- Example: `/prompt=Summarize the key points from our conversation`

#### Translation with Phonetics

The `/translate` command provides translations with phonetic pronunciation:

- Usage: `/translate=language [text]` or reply with `/translate=language`
- Example: `/translate=Persian Hello, how are you?`
- Provides both translation and phonetic pronunciation for Persian

#### Conversation Analysis

The `/analyze` command analyzes conversation history:

- Usage: `/analyze=number_of_messages`
- Example: `/analyze=50` (analyzes last 50 messages)
- Provides detailed summaries and insights

#### Question Answering

The `/tellme` command answers questions based on chat history:

- Usage: `/tellme=number_of_messages=your_question`
- Example: `/tellme=10=What did John say about the project?`

### Message Categorization

#### Topic-Based Organization

SakaiBot allows you to categorize messages by forwarding them to specific topics in forum groups:

1. Set a target group with `sakaibot group set`
2. Configure command-to-topic mappings using `sakaibot group map`
3. Use commands like `/work`, `/personal`, etc., when replying to messages
4. Messages are automatically forwarded to the appropriate topic

#### Forum Group Mapping

The enhanced forum group mapping feature supports:

- **Multiple Commands Per Topic**: Multiple different commands can map to the same forum topic, allowing for flexible categorization (e.g., both `/help` and `/support` can map to a "Support" topic)
- **Interactive Mapping Setup**: Use `sakaibot group map --add` to interactively set up command-topic mappings
- **Flexible Topic Selection**: When mapping commands, you can select specific forum topics or the main group chat
- **Listing Mappings**: Use `sakaibot group map --list` to view all current command-topic mappings
- **Dynamic Updates**: Modify mappings as needed without restarting the bot
- **Backward Compatibility**: Existing configurations continue to work seamlessly

This feature enables more sophisticated message organization in forum groups, allowing users to create intuitive command systems for categorizing incoming messages into appropriate topics.

#### Smart Forwarding

- Preserves message context
- Maintains original formatting where possible
- Supports both individual messages and message ranges

### Speech Features

#### STT (Speech-to-Text)

- Reply to voice messages with `/stt`
- Transcribes voice to text
- Provides AI-generated summary of the content
- Works with multiple languages

#### TTS (Text-to-Speech)

- Convert text to voice messages with `/tts` or `/speak`
- Supports parameters like voice, rate, and volume
- Example: `/tts voice=PersianFemale rate=+10% Hello world`
- Can reply to text messages to convert them to voice

### Monitoring Features

#### Event Handling

- Real-time message processing
- Command recognition and execution
- Support for both direct commands and reply-based commands
- Asynchronous processing for better performance

#### Activity Tracking

- Monitor bot status with `sakaibot monitor status`
- Start/stop monitoring with simple commands
- Detailed logging of all activities

## User Experience Features

### Rich Terminal Interface

- Colorful output using the Rich library
- Progress indicators for long-running operations
- Clear error messages and helpful prompts
- Responsive design for better user experience

### Caching System

- Reduces API calls to Telegram
- Faster access to PV and group lists
- Automatic cache refresh options
- Efficient data storage and retrieval

### Error Handling

- Comprehensive error messages
- Graceful degradation when services are unavailable
- Automatic retry mechanisms for API calls
- Detailed logging for troubleshooting

## Advanced Features

### Custom Configuration

- Flexible configuration system with .env support
- Support for multiple AI providers
- Customizable message limits
- Extensible architecture for new features

### Extensibility

- Plugin architecture for new AI providers
- Modular design for easy feature addition
- Well-documented APIs for customization
- Support for additional services (AssemblyAI, ElevenLabs)

### Security

- Secure API key handling
- Session management for Telegram
- Authorization controls for different users
- Protection against unauthorized access

## Integration Capabilities

### Telegram Features

- Full access to Telegram API via Telethon
- Support for private chats, groups, and channels
- Message forwarding and copying
- Media handling (text, voice, images, etc.)

### AI Service Integration

- Seamless integration with OpenRouter
- Support for Google Gemini
- Easy switching between providers
- Consistent interface across providers

## Performance Features

### Asynchronous Processing

- Non-blocking operations
- Concurrent message handling
- Efficient resource utilization
- Better responsiveness under load

### Resource Management

- Proper cleanup of temporary files
- Connection management for APIs
- Memory-efficient processing of large datasets
- Automatic resource release on exit

## Summary

SakaiBot combines the power of AI with Telegram automation to provide a comprehensive userbot solution. The features are designed to be both powerful and accessible, with a focus on privacy, security, and ease of use. Whether you're looking to automate routine tasks, analyze conversations, or enhance your Telegram experience with AI capabilities, SakaiBot provides a robust and extensible platform.
