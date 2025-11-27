# Telegram Message Style Guide

## Overview

This guide defines the standard for all static bot messages (non-AI generated content) in SakaiBot. All messages should use clean English with proper Telegram formatting and contextually appropriate emojis.

## Telegram Formatting Syntax

### Supported Formats

- **Bold**: `**text**` or `__text__` (MarkdownV2) / `<b>text</b>` (HTML)
- **Italic**: `*text*` or `_text_` (MarkdownV2) / `<i>text</i>` (HTML)
- **Code**: `` `code` `` (inline) / ` ```code block``` ` (block)
- **Links**: `[text](url)` (MarkdownV2) / `<a href="url">text</a>` (HTML)

### Parse Modes

- **markdown ('md')**: Use for simple formatting, backward compatible
- **html**: Use for complex formatting, more reliable
- **None**: Use for plain text (STT responses, etc.)

## Emoji Guidelines

### Emoji Categories

#### Status & Progress
- 🎨 **Creating/Processing**: Image generation, creative tasks
- 🖼️ **Generating**: Image creation in progress
- ⏳ **Waiting/Queue**: In queue, waiting for turn
- 🤖 **AI Processing**: General AI operations
- 🎧 **Audio Processing**: Voice/STT operations
- 🗣️ **TTS/Speech**: Text-to-speech conversion
- 📤 **Sending**: Uploading/sending files
- ✅ **Success**: Completed successfully
- ⏱️ **Timeout**: Operation timed out
- 📋 **Status**: Queue position, statistics

#### Feedback
- ✅ **Success**: Operation completed
- ❌ **Error**: Operation failed
- ⚠️ **Warning**: Rate limit, validation error
- 🚫 **Blocked**: Content filtered, access denied
- 💡 **Tip**: Helpful information
- 🔐 **Auth**: Authentication/authorization
- 👤 **User**: User-related info
- 🆔 **ID**: User/chat IDs

#### Information
- 📝 **Text/Transcription**: Transcribed content
- 🔍 **Analysis**: AI summary/analysis
- 🔊 **Voice**: Voice settings
- ✨ **Enhanced**: AI enhancement
- ⚡ **Original**: No enhancement
- 🌐 **Network**: Network/connection issues
- 🔧 **Service**: Service unavailable

## Message Templates

### Loading/Processing Messages

```markdown
🎨 **Processing image request with FLUX...**
🎨 **Enhancing prompt with AI...**
🖼️ **Generating image with SDXL...**
📤 **Sending image...**
🤖 **Processing your prompt command...**
🎧 **Processing voice message** (Step 1: Transcribing)...
🗣️ **Converting text to speech...**
```

### Queue Status Messages

```markdown
⏳ **In queue** • Position: **3**
⏳ **In FLUX queue:** position 2...
📋 **Status:** In queue (Position: 1)
🔊 **Voice:** Alloy
```

### Success Messages

```markdown
✅ **Image generated!**
✅ **Done** - 14:30
✅ **Authorized**
```

### Error Messages

```markdown
❌ **Invalid command format.**
Usage: `/image=flux=<prompt>` or `/image=sdxl=<prompt>`

❌ **Invalid model:** flux-pro
Supported models: flux, sdxl

❌ **Prompt error:** Text is too long (max 500 characters)

⚠️ **Rate limit exceeded**
You have reached the request limit.
Please wait 60 seconds.
Remaining requests: 0

⏱️ **Image generation timed out.** Please try again.

🚫 **Content was filtered by the system.** Please try a different prompt.

🔐 **Authentication error:** Invalid API key.

🌐 **Network error** connecting to image server. Please try again.

🔧 **Image generation service unavailable.** Please try again later.
```

### Usage/Help Messages

```markdown
Usage: `/translate=<lang>=<text>` or reply with `/translate=<lang>`

Usage: `/analyze=<number_between_1_and_10000>` or `/analyze=<mode>=<number>` (mode: fun, romance, general)

Please use `/stt` in reply to a voice message.

❌ Please provide text or reply to a message you want to convert.

**Usage:**
`/tts=text` - Convert text to speech
or reply to a message with `/tts`
```

### Information Messages

```markdown
📝 **Transcribed Text:**
{text}

🔍 **AI Summary & Analysis:**
{summary}

🎨 Image generated with **FLUX**
✨ Enhanced by OpenRouter

**Enhanced prompt:**
{prompt}
```

## Message Structure Best Practices

### 1. Clear Hierarchy
- Use bold for primary information
- Use emojis to categorize message type
- Keep important info at the top

### 2. Concise Language
- Be direct and clear
- Avoid unnecessary words
- Use action verbs

### 3. Consistent Formatting
- **Command names**: Always in code format: `/command`
- **Model names**: Always uppercase: FLUX, SDXL
- **Values/IDs**: Use code format: `123456`
- **Emphasis**: Use bold for key information

### 4. User-Friendly Errors
- Start with emoji (❌, ⚠️, 🚫)
- Explain what went wrong
- Provide actionable guidance when possible
- Keep technical details minimal

### 5. Progressive Status Updates
- Show current step clearly
- Update position in queue regularly
- Delete status messages after completion when appropriate

## Examples by Feature

### Image Generation

**Initial Request:**
```markdown
🎨 Processing image request with FLUX...
```

**Queue Status:**
```markdown
⏳ In FLUX queue: position 2...
```

**Enhancing:**
```markdown
🎨 Enhancing prompt with AI...
```

**Generating:**
```markdown
🖼️ Generating image with SDXL...
```

**Sending:**
```markdown
📤 Sending image...
```

**Caption:**
```markdown
🎨 Image generated with FLUX
✨ Enhanced by Gemini

**Enhanced prompt:**
a beautiful sunset over mountains, photorealistic, 4k
```

### TTS (Text-to-Speech)

**Processing:**
```markdown
🗣️ Converting text to speech...
📋 Status: In queue (Position: 2)
🔊 Voice: Alloy
```

**Success:**
```markdown
🗣️ Converting text to speech...
📋 Status: Complete
🔊 Voice: Alloy
```

### STT (Speech-to-Text)

**Processing:**
```markdown
🎧 Processing voice message from User (Step 1: Transcribing)...
```

**Transcribed:**
```markdown
📝 **Transcribed Text:**
Hello, this is a test message.

⏳ (Step 2: AI Summarization & Analysis)...
```

**Complete:**
```markdown
📝 **Transcribed Text:**
Hello, this is a test message.

🔍 **AI Summary & Analysis:**
User greeted and mentioned testing functionality.
```

### AI Commands (Prompt, Translate, Analyze)

**Processing:**
```markdown
🤖 Processing your prompt command from User...
```

**Complete:**
```markdown
{AI response content}

✅ Done - 14:30
```

**Error:**
```markdown
⚠️ AI Processing Error: Failed to process your request. Please try again.
```

## Special Considerations

### 1. Bilingual Support
- Keep Persian error messages in `error_handler.py` for bilingual contexts
- Use English for all new static messages
- Maintain consistency across languages

### 2. Markdown Escaping
- Escape special characters when needed: `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`
- Use parse_mode='md' for simple messages
- Use parse_mode='html' for complex formatting
- Use parse_mode=None for plain text

### 3. Message Length
- Telegram's caption limit: 1024 characters
- Message limit: 4096 characters
- Use pagination for longer content
- Truncate gracefully with "..."

### 4. Status Message Management
- Edit status messages instead of sending new ones
- Delete temporary status messages after completion
- Handle edit failures gracefully (message might be deleted)

## Implementation Checklist

- [ ] All static messages reviewed
- [ ] Consistent emoji usage
- [ ] Proper Telegram formatting
- [ ] Clear, concise English
- [ ] User-friendly error messages
- [ ] Progressive status updates
- [ ] Appropriate parse_mode set
- [ ] Message length handled
- [ ] Tests passing
- [ ] Verified in real Telegram client

## Version History

- **v1.0** (2024): Initial style guide created
  - Established emoji standards
  - Defined message templates
  - Set formatting guidelines
