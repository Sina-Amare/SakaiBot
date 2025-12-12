# Commands Reference

Complete reference for all SakaiBot commands.

## Quick Reference

| Command                    | Description       | Example                              |
| -------------------------- | ----------------- | ------------------------------------ |
| `/prompt=<text>`           | Ask AI anything   | `/prompt=What is quantum computing?` |
| `/translate=<lang>=<text>` | Translate text    | `/translate=en=سلام`                 |
| `/analyze=<N>`             | Analyze messages  | `/analyze=100`                       |
| `/tellme=<N>=<question>`   | Ask about history | `/tellme=50=Who talked most?`        |
| `/image=<model>=<prompt>`  | Generate image    | `/image=flux=sunset`                 |
| `/tts=<text>`              | Text to speech    | `/tts=Hello world`                   |
| `/stt`                     | Speech to text    | (reply to voice)                     |
| `/auth <action>`           | Manage users      | `/auth list`                         |
| `/group <action>`          | Manage groups     | `/group list`                        |
| `/status`                  | Bot status        | `/status`                            |
| `/help [topic]`            | Help system       | `/help ai`                           |

---

## AI Commands

### `/prompt` - Ask AI Anything

Ask questions or give instructions to the AI.

**Syntax:**

```text
/prompt=<your text>
/prompt=<your text>=think    # Deep reasoning mode
/prompt=<your text>=web      # Web search enabled
```

**Examples:**

```text
/prompt=What is quantum computing?
/prompt=Explain this Python code: [paste]
/prompt=Write a poem about stars
/prompt=Latest AI news=web
/prompt=Solve this math problem step by step=think
```

**Flags:**

- `=think` - Enables deep reasoning mode with thinking summaries
- `=web` - Enables web search for real-time information

---

### `/translate` - Translation with Phonetics

Translate text between languages with Persian phonetic pronunciation.

**Syntax:**

```text
/translate=<target_lang>=<text>
/translate=<target_lang>           # Reply to message
```

**Examples:**

```text
/translate=en=سلام دنیا
/translate=fa=Hello world
/translate=de=Good morning
/translate=ja                      # Reply to translate message
```

**Language Codes:** ISO 639-1 codes

- `en` - English
- `fa` - Persian/Farsi
- `ar` - Arabic
- `es` - Spanish
- `fr` - French
- `de` - German
- `zh` - Chinese
- `ja` - Japanese
- `ru` - Russian
- _Any ISO 639-1 code_

---

### `/analyze` - Chat Analysis

Analyze conversation history with AI-powered insights.

**Syntax:**

```text
/analyze=<N>                       # Last N messages
/analyze=<mode>=<N>                # With mode
/analyze=<N> en                    # English output
/analyze=<mode>=<N>=think          # With thinking
```

**Modes:**

| Mode      | Description           | Style                   |
| --------- | --------------------- | ----------------------- |
| `general` | Professional analysis | Formal, structured      |
| `fun`     | Comedy roast          | Persian Bill Burr style |
| `romance` | Relationship analysis | Emotional signals       |

**Examples:**

```text
/analyze=100                       # General mode, Persian
/analyze=500 en                    # General mode, English
/analyze=fun=1000                  # Fun mode, Persian
/analyze=romance=200               # Romance mode, Persian
/analyze=fun=500 en                # Fun mode, English
/analyze=general=500=think         # With deep thinking
```

**Limits:** Maximum messages controlled by `USERBOT_MAX_ANALYZE_MESSAGES` (default: 10,000)

---

### `/tellme` - Ask About Chat History

Ask specific questions about recent messages.

**Syntax:**

```text
/tellme=<N>=<question>
/tellme=<N>=<question>=think       # Deep reasoning
/tellme=<N>=<question>=web         # Web search
```

**Examples:**

```text
/tellme=50=What topics were discussed?
/tellme=100=Who was most active?
/tellme=200=Summarize the main conflicts
/tellme=100=What decisions were made?=think
/tellme=50=Is this news accurate?=web
```

---

## Image Generation

### `/image` - Generate Images

Create images from text prompts using AI models.

**Syntax:**

```text
/image=<model>=<prompt>
```

**Models:**

| Model  | Speed   | Auth Required | Best For           |
| ------ | ------- | ------------- | ------------------ |
| `flux` | ~15-30s | No            | Artistic, creative |
| `sdxl` | ~20-40s | Yes (Bearer)  | Photorealistic     |

**Examples:**

```text
/image=flux=sunset over mountains
/image=sdxl=cyberpunk city at night, neon lights, 4k
/image=flux=cute cat playing with yarn
/image=sdxl=professional headshot, studio lighting
```

**Features:**

- Automatic prompt enhancement by AI
- Queue system with position updates
- Enhanced prompt shown in caption

---

## Voice Commands

### `/tts` - Text to Speech

Convert text to speech audio.

**Syntax:**

```text
/tts=<text>
/tts                               # Reply to message
```

**Examples:**

```text
/tts=Hello, how are you today?
/tts=سلام، حال شما چطوره؟
/tts                               # Reply to convert message
```

**Voice:** Uses Google Gemini TTS with Orus voice (default)

---

### `/stt` - Speech to Text

Transcribe voice messages with AI summary.

**Syntax:**

```text
/stt                               # Reply to voice message
```

**Features:**

- Accurate transcription
- AI-generated summary
- Works with voice notes, audio files

---

## Management Commands

### `/auth` - User Authorization

Manage users who can send commands.

**Syntax:**

```text
/auth list                         # List authorized users
/auth add <identifier>             # Add user
/auth remove <identifier>          # Remove user
```

**Examples:**

```text
/auth list
/auth add @username
/auth add 123456789
/auth remove @username
```

---

### `/group` - Group Categorization

Configure message forwarding to forum topics.

**Syntax:**

```text
/group list                        # View your groups
/group list <page>                 # Paginated list
/group select <id>                 # Select target group
/group topics                      # List topics in group
/group map                         # Show mappings
/group map <category>=<topic_id>   # Add mapping
/group clear                       # Clear all mappings
```

**Examples:**

```text
/group list
/group list 2
/group select -1001234567890
/group topics
/group map meme=123
```

**Usage:** After mapping, reply to any message with the category name to forward it to the corresponding topic.

---

### `/status` - Bot Status

Display bot status and system information.

**Syntax:**

```text
/status
```

**Shows:**

- Account info
- Authorized users count
- Monitoring status
- Target group
- System resources (CPU, RAM)

---

### `/help` - Help System

Comprehensive help and documentation.

**Syntax:**

```text
/help                              # Main help
/help <topic>                      # Specific topic
/help fa                           # Persian help
```

**Topics:**

- `images` - Image generation guide
- `ai` - AI commands guide
- `voice` - Voice commands guide
- `auth` - Authorization guide
- `group` - Categorization guide
- `fa` - Persian version

---

## Rate Limits

| Limit                    | Value  |
| ------------------------ | ------ |
| Requests per minute      | 10     |
| Max analyze messages     | 10,000 |
| Image generation timeout | 120s   |

---

## Command Flags

| Flag     | Available On                     | Description          |
| -------- | -------------------------------- | -------------------- |
| `=think` | `/prompt`, `/analyze`, `/tellme` | Deep reasoning mode  |
| `=web`   | `/prompt`, `/tellme`             | Web search grounding |
| `en`     | `/analyze`                       | English output       |

---

## Special Behaviors

### Reply Commands

Some commands can be used as replies:

| Command             | Reply Behavior                    |
| ------------------- | --------------------------------- |
| `/tts`              | Convert replied message to speech |
| `/stt`              | Transcribe replied voice          |
| `/translate=<lang>` | Translate replied message         |

### Message Editing

Commands edit your original message with:

1. Processing status
2. Final result

### Error Handling

Failed commands show:

- User-friendly error message
- Recovery suggestions
- Original command preserved
