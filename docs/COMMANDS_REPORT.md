# SakaiBot Commands Report

## Table of Contents

1. [Complete Command Inventory](#complete-command-inventory)
2. [Detailed Command Analysis](#detailed-command-analysis)
3. [AI Integration Details](#ai-integration-details)
4. [TTS/STT Implementation](#ttsstt-implementation)
5. [Translation System](#translation-system)
6. [Configuration and Settings](#configuration-and-settings)
7. [Integration Points](#integration-points)

---

## Complete Command Inventory

### User-Facing Commands

#### Core Commands

| Command           | Category | Description                                  |
| ----------------- | -------- | -------------------------------------------- |
| `sakaibot status` | System   | Display current bot status and configuration |
| `sakaibot menu`   | UI       | Start interactive menu system                |
| `sakaibot setup`  | Setup    | Run interactive setup wizard (placeholder)   |

#### Group Management

| Command                           | Category | Description                                 |
| --------------------------------- | -------- | ------------------------------------------- |
| `sakaibot group list`             | Groups   | List all groups where user has admin rights |
| `sakaibot group set [identifier]` | Groups   | Set target group for message categorization |
| `sakaibot group topics`           | Groups   | List topics in the selected forum group     |
| `sakaibot group map`              | Groups   | Manage command to topic/group mappings      |

#### Authorization Management

| Command                             | Category | Description                                     |
| ----------------------------------- | -------- | ----------------------------------------------- |
| `sakaibot auth list`                | Auth     | List all authorized users                       |
| `sakaibot auth add [identifier]`    | Auth     | Add an authorized user by username, ID, or name |
| `sakaibot auth remove [identifier]` | Auth     | Remove an authorized user                       |
| `sakaibot auth clear`               | Auth     | Clear all authorized users                      |

#### Monitoring

| Command                   | Category   | Description                                       |
| ------------------------- | ---------- | ------------------------------------------------- |
| `sakaibot monitor start`  | Monitoring | Start global monitoring for commands and messages |
| `sakaibot monitor stop`   | Monitoring | Stop global monitoring                            |
| `sakaibot monitor status` | Monitoring | Show current monitoring status                    |

#### Configuration

| Command                    | Category | Description                               |
| -------------------------- | -------- | ----------------------------------------- |
| `sakaibot config show`     | Config   | Display current configuration             |
| `sakaibot config validate` | Config   | Validate configuration settings           |
| `sakaibot config edit`     | Config   | Open configuration file in default editor |
| `sakaibot config example`  | Config   | Show example configuration                |

### Internal Commands

#### Telegram Commands

| Command                                  | Category | Description                        |
| ---------------------------------------- | -------- | ---------------------------------- |
| `/stt`                                   | STT      | Transcribe voice messages to text  |
| `/tts`                                   | TTS      | Convert text to speech             |
| `/speak`                                 | TTS      | Alternative TTS command            |
| `/prompt=[text]`                         | AI       | Execute custom prompt              |
| `/translate=[lang][,source_lang] [text]` | AI       | Translate text with phonetics      |
| `/analyze=[number]`                      | AI       | Analyze chat conversation          |
| `/tellme=[number]=[question]`            | AI       | Answer questions from chat history |

---

## Detailed Command Analysis

### System Commands

#### `sakaibot status`

**Syntax:** `sakaibot status`

**Usage Example:**

```bash
sakaibot status
```

**Workflow:**

1. Load configuration from `.env` file
2. Load user settings from `data/sakaibot_user_settings.json`
3. Create status table with system components
4. Display current configuration state

**Parameters:** None

**Error Handling:**

- Configuration loading errors
- Settings file access issues
- Display formatting exceptions

**Implementation:** [`src/cli/main.py:show_status()`](src/cli/main.py:150)

**Dependencies:**

- `src.core.config.get_settings()`
- `src.core.settings.SettingsManager`
- `rich.console`, `rich.table`

---

### Group Management Commands

#### `sakaibot group list`

**Syntax:** `sakaibot group list [--refresh] [--all]`

**Usage Example:**

```bash
sakaibot group list  # List admin groups
sakaibot group list --refresh  # Refresh from Telegram
sakaibot group list --all  # Show all groups (not just admin)
```

**Workflow:**

1. Get Telegram client connection
2. Initialize cache manager
3. Fetch groups from Telegram
4. Display formatted table of groups

**Parameters:**

- `--refresh`: Force refresh from Telegram API
- `--all`: Show all groups, not just admin groups

**Error Handling:**

- Client connection failures
- API rate limits
- Network timeouts
- Data parsing errors

**Implementation:** [`src/cli/commands/group.py:_list_groups()`](src/cli/commands/group.py:20)

**Dependencies:**

- `src.cli.utils.get_telegram_client()`
- `src.utils.cache.CacheManager`
- `src.telegram.utils.TelegramUtils`
- `rich.console`, `rich.table`

---

#### `sakaibot group set`

**Syntax:** `sakaibot group set [identifier] --clear`

**Usage Example:**

```bash
sakaibot group set 123456789  # Set by ID
sakaibot group set "My Group"  # Set by name
sakaibot group set --clear  # Clear target group
```

**Workflow:**

1. Load user settings
2. If clearing, remove target group and save
3. If identifier provided, search groups
4. Interactive selection if multiple matches
5. Save selected group ID

**Parameters:**

- `identifier`: Group ID, name, or partial name (optional)
- `--clear`: Clear the target group

**Error Handling:**

- Settings file access issues
- Group cache not found
- No matching groups
- Permission errors

**Implementation:** [`src/cli/commands/group.py:_set_target_group()`](src/cli/commands/group.py:65)

**Dependencies:**

- `src.cli.utils.get_settings_manager()`
- `src.utils.cache.CacheManager`
- `rich.console`

---

### Authorization Commands

#### `sakaibot auth list`

**Syntax:** `sakaibot auth list`

**Usage Example:**

```bash
sakaibot auth list
```

**Workflow:**

1. Load user settings
2. Get authorized user IDs
3. Fetch PV details from cache
4. Display formatted table

**Parameters:** None

**Error Handling:**

- Settings file access issues
- Cache not available
- User data format errors

**Implementation:** [`src/cli/commands/auth.py:_list_authorized()`](src/cli/commands/auth.py:20)

**Dependencies:**

- `src.cli.utils.get_settings_manager()`
- `src.utils.cache.CacheManager`
- `rich.console`, `rich.table`

---

#### `sakaibot auth add`

**Syntax:** `sakaibot auth add <identifier>`

**Usage Example:**

```bash
sakaibot auth add @username
sakaibot auth add 123456789
sakaibot auth add "Display Name"
```

**Workflow:**

1. Load user settings
2. Search for user in PV cache
3. Interactive selection if multiple matches
4. Add to authorized users list
5. Save settings

**Parameters:**

- `identifier`: Username, ID, or display name

**Error Handling:**

- User not found
- Already authorized
- Settings save failures
- Cache access issues

**Implementation:** [`src/cli/commands/auth.py:_add_authorized()`](src/cli/commands/auth.py:40)

**Dependencies:**

- `src.cli.utils.get_settings_manager()`
- `src.utils.cache.CacheManager`
- `src.utils.cache.CacheManager.search_pvs()`

---

### Monitoring Commands

#### `sakaibot monitor start`

**Syntax:** `sakaibot monitor start [--verbose]`

**Usage Example:**

```bash
sakaibot monitor start
sakaibot monitor start --verbose  # Show detailed output
```

**Workflow:**

1. Validate prerequisites (target group, AI config, etc.)
2. Initialize Telegram client
3. Initialize AI and audio processors
4. Register event handlers
5. Start monitoring loop

**Parameters:**

- `--verbose`: Show detailed monitoring output

**Error Handling:**

- Configuration validation failures
- Client connection issues
- API rate limits
- Handler registration failures

**Implementation:** [`src/cli/commands/monitor.py:_start_monitoring()`](src/cli/commands/monitor.py:30)

**Dependencies:**

- `src.core.config.get_settings()`
- `src.cli.state.CLIState`
- `src.telegram.handlers.EventHandlers`
- `src.ai.processor.AIProcessor`
- `src.ai.stt.SpeechToTextProcessor`
- `src.ai.tts.TextToSpeechProcessor`

---

### Configuration Commands

#### `sakaibot config show`

**Syntax:** `sakaibot config show [--all]`

**Usage Example:**

```bash
sakaibot config show
sakaibot config show --all  # Show all values including secrets
```

**Workflow:**

1. Load configuration from settings
2. Create formatted table with all categories
3. Display configuration values
4. Show file locations

**Parameters:**

- `--all`: Show all configuration values (including secrets)

**Error Handling:**

- Configuration loading errors
- Display formatting issues

**Implementation:** [`src/cli/commands/config.py:show()`](src/cli/commands/config.py:18)

**Dependencies:**

- `src.core.config.get_settings()`
- `rich.console`, `rich.table`

---

### Telegram Commands

#### `/stt` Command

**Syntax:** `/stt` (in reply to a voice message)

**Usage Example:**

```bash
/stt  # In reply to a voice message
```

**Workflow:**

1. Check if replied to voice message
2. Download voice file
3. Convert to WAV format
4. Transcribe using Google Web Speech API
5. Generate AI summary (if configured)
6. Send combined response

**Parameters:** None (uses replied message)

**Error Handling:**

- Voice message not found
- Audio conversion failures
- Transcription errors
- AI summarization failures

**Implementation:** [`src/telegram/handlers.py:_process_stt_command()`](src/telegram/handlers.py:150)

**Dependencies:**

- `pydub` for audio conversion
- `speech_recognition` for STT
- Google Web Speech API
- `src.ai.processor.AIProcessor` (optional)
- `src.utils.helpers.clean_temp_files()`

---

#### `/tts` Command

**Syntax:** `/tts [params] <text>` or `/tts [params]` (in reply)

**Usage Example:**

```bash
/tts Hello world
/tts voice=fa-IR-DilaraNeural rate=-10% Hello world
/tts  # In reply to a text message
```

**Workflow:**

1. Parse command parameters
2. Get text from command or reply
3. Normalize text for Persian
4. Generate speech using TTS provider
5. Send voice message

**Parameters:**

- `voice`: Voice ID (default: `fa-IR-DilaraNeural`)
- `rate`: Speech rate modifier (e.g., `+10%`, `-5%`)
- `volume`: Volume modifier (e.g., `+5%`)

**Error Handling:**

- Text not provided
- TTS generation failures
- Voice sending issues
- Parameter parsing errors

**Implementation:** [`src/telegram/handlers.py:_handle_tts_command()`](src/telegram/handlers.py:570)

**Dependencies:**

- `src.ai.tts.TextToSpeechProcessor`
- `src.utils.helpers.parse_command_with_params()`
- `hazm.Normalizer` for text normalization

---

#### `/prompt` Command

**Syntax:** `/prompt=<your question or instruction>`

**Usage Example:**

```bash
prompt=What is the meaning of life?
prompt=Explain quantum computing in simple terms.
```

**Workflow:**

1. Extract prompt text
2. Use Persian comedian system message
3. Send to configured AI provider
4. Return AI response

**Parameters:**

- User prompt text

**Error Handling:**

- Empty prompt
- AI provider errors
- Response processing issues

**Implementation:** [`src/telegram/handlers.py:_handle_prompt_command()`](src/telegram/handlers.py:700)

**Dependencies:**

- `src.ai.processor.AIProcessor`
- `src.ai.persian_prompts.PERSIAN_COMEDIAN_SYSTEM`

---

#### `/translate` Command

**Syntax:** `/translate=<lang>[,source_lang] [text]` or `/translate=<lang>` (in reply)

**Usage Example:**

```bash
translate=en Hello world
translate=es,fa Hello world
translate=en  # In reply to Persian text
```

**Workflow:**

1. Parse language and text parameters
2. Extract text from replied message if needed
3. Call AI translation service
4. Format response with phonetic pronunciation
5. Return translation

**Parameters:**

- `lang`: Target language code
- `source_lang`: Source language (optional, default: auto)
- Text to translate

**Error Handling:**

- Invalid language code
- Translation failures
- Response formatting issues
- Text extraction errors

**Implementation:** [`src/telegram/handlers.py:_handle_translate_command()`](src/telegram/handlers.py:720)

**Dependencies:**

- `src.ai.processor.AIProcessor`
- `src.utils.helpers.parse_command_with_params()`

---

#### `/analyze` Command

**Syntax:** `/analyze=<number>`

**Usage Example:**

```bash
analyze=50  # Analyze last 50 messages
analyze=100  # Analyze last 100 messages
```

**Workflow:**

1. Parse number of messages
2. Fetch chat history
3. Format messages for AI
4. Send to AI for analysis
5. Return formatted analysis

**Parameters:**

- `number`: Number of messages to analyze (1-10000)

**Error Handling:**

- Invalid number
- Chat history fetch failures
- AI analysis errors
- Message processing issues

**Implementation:** [`src/telegram/handlers.py:_handle_analyze_command()`](src/telegram/handlers.py:760)

**Dependencies:**

- `telethon` for chat history
- `src.ai.processor.AIProcessor`
- `src.core.config.MAX_MESSAGE_LENGTH`

---

#### `/tellme` Command

**Syntax:** `/tellme=<number>=<your_question>`

**Usage Example:**

```bash
tellme=50=What was discussed about the project?
tellme=100=Who supported the new proposal?
```

**Workflow:**

1. Parse message count and question
2. Fetch chat history
3. Format messages for AI
4. Send question and history to AI
5. Return AI answer

**Parameters:**

- `number`: Number of messages to consider
- `question`: Question to ask about the chat history

**Error Handling:**

- Invalid parameters
- Chat history fetch failures
- AI processing errors
- Response formatting issues

**Implementation:** [`src/telegram/handlers.py:_handle_tellme_command()`](src/telegram/handlers.py:790)

**Dependencies:**

- `telethon` for chat history
- `src.ai.processor.AIProcessor`
- `re` for parameter parsing

---

## AI Integration Details

### AI Providers

#### Gemini Provider

**Implementation:** [`src/ai/providers/gemini.py`](src/ai/providers/gemini.py)

**Configuration:**

- API Key: `GEMINI_API_KEY`
- Model: `GEMINI_MODEL` (default: `gemini-2.5-flash`)

**Usage:**

```python
provider = GeminiProvider(config)
response = await provider.execute_prompt(user_prompt, system_message)
```

**Features:**

- Supports custom prompts with system messages
- Translation with Persian phonetic pronunciation
- Conversation analysis
- Question answering from chat history
- Retry logic with exponential backoff
- Safety content filtering detection

**Error Handling:**

- API key validation
- Rate limiting
- Content filtering
- Network timeouts
- Response parsing errors

---

#### OpenRouter Provider

**Implementation:** [`src/ai/providers/openrouter.py`](src/ai/providers/openrouter.py)

**Configuration:**

- API Key: `OPENROUTER_API_KEY`
- Model: `OPENROUTER_MODEL` (default: `google/gemini-2.5-flash`)

**Usage:**

```python
provider = OpenRouterProvider(config)
response = await provider.execute_prompt(user_prompt, system_message)
```

**Features:**

- Multiple model support
- Custom headers for OpenRouter API
- Timeout handling for large requests
- Error response parsing
- Fallback mechanisms

**Error Handling:**

- API key validation
- HTTP status errors
- Timeout handling
- Rate limiting
- Response parsing failures

---

### AI Prompts and System Messages

#### Persian Comedian System Message

**Location:** [`src/ai/persian_prompts.py`](src/ai/persian_prompts.py)

```python
PERSIAN_COMEDIAN_SYSTEM = """
شما یک کمدین هوشمند و پرانرژی هستید که با لحنی دوستانه و صمیمی
به سوالات کاربران پاسخ می‌دهید. پاسخ‌های شما باید:
- طنزآمیز اما محترمانه باشند
- اطلاعات مفید را با شوخی ترکیب کنند
- به زبان ساده و روان فارسی باشند
- از اصطلاحات روزمره استفاده کنند
"""
```

#### Translation System Message

```python
TRANSLATION_SYSTEM_MESSAGE = """
شما یک مترجم دقیق و حرفه‌ای هستید. وظیفه شما ترجمه متن به زبان درخواستی
به همراه ارائه تلفظ فارسی آن است. در پاسخ خود:
- ترجمه دقیق و بدون اضافه کردن محتوا ارائه دهید
- تلفظ فارسی را داخل پرانتز قرار دهید
- از فرمت "ترجمه (تلفظ فارسی)" استفاده کنید
"""
```

#### Conversation Analysis System Message

```python
CONVERSATION_ANALYSIS_SYSTEM_MESSAGE = """
شما یک تحلیل‌گر حرفه‌ای گفتگوهای فارسی هستید. وظیفه شما تحلیل
گفتگوها و ارائه خلاصه جامع است. در تحلیل خود:
- موضوعات اصلی را شناسایی کنید
- نظرات و تصمیمات کلیدی را برجسته کنید
- لحن و احساسات عمومی را تحلیل کنید
- به زبان فارسی و با ساختار واضح پاسخ دهید
"""
```

---

## TTS/STT Implementation

### Text-to-Speech (TTS)

**Implementation:** [`src/ai/tts.py`](src/ai/tts.py)

#### TTS Providers

1. **Edge TTS (Primary)**

   - **Library:** `edge-tts`
   - **Features:** Free, reliable for Persian
   - **Configuration:** No API key required
   - **Voice ID:** `fa-IR-DilaraNeural` (default)

2. **Pyttsx3 (Fallback)**

   - **Library:** `pyttsx3`
   - **Features:** Offline, local system voices
   - **Configuration:** No API key required
   - **Usage:** When other providers fail

3. **Hugging Face (Optional)**

   - **Library:** `requests`
   - **Model:** `saharmor/fastspeech2-fa`
   - **Features:** High-quality Persian TTS
   - **Configuration:** `HUGGINGFACE_API_TOKEN`

4. **Google Translate (Fallback)**
   - **Endpoint:** `https://translate.googleapis.com/translate_tts`
   - **Features:** Free, limited to 90 characters per request
   - **Configuration:** No API key required

#### TTS Workflow

```python
async def text_to_speech(self, text: str, voice: str, rate: str, volume: str):
    # 1. Try edge-tts first
    if await self._generate_with_edge_tts(text, voice, rate, volume):
        return True

    # 2. Try pyttsx3 (offline)
    if await self._generate_with_pyttsx3(text):
        return True

    # 3. Try Hugging Face (if token available)
    if await self._generate_with_huggingface(text):
        return True

    # 4. Try Google Translate
    return await self._generate_with_google(text)
```

#### TTS Parameters

- **voice:** Voice ID (default: `fa-IR-DilaraNeural`)
- **rate:** Speech rate modifier (e.g., `+0%`, `-10%`)
- **volume:** Volume modifier (e.g., `+0%`)

#### Error Handling

- Provider-specific error messages
- Fallback mechanism
- Temporary file cleanup
- Audio format validation

---

### Speech-to-Text (STT)

**Implementation:** [`src/ai/stt.py`](src/ai/stt.py)

#### STT Provider

- **Library:** `speech_recognition`
- **API:** Google Web Speech API
- **Language Support:** `fa-IR` (Persian)
- **Configuration:** No API key required

#### STT Workflow

```python
async def transcribe_voice_to_text(self, audio_wav_path: str, language: str):
    # 1. Load audio file
    with sr.AudioFile(audio_wav_path) as source:
        audio_data = self._recognizer.record(source)

    # 2. Transcribe using Google Web Speech API
    text = self._recognizer.recognize_google(audio_data, language=language)

    return text
```

#### STT Error Handling

- **WaitTimeoutError:** No speech detected
- **UnknownValueError:** Speech unintelligible
- **RequestError:** API request failed
- **FileNotFoundError:** Audio file not found

#### Audio Processing

- **Input Format:** Voice messages (OGG)
- **Conversion:** WAV format using pydub
- **Quality:** High-quality audio processing
- **Cleanup:** Automatic temporary file removal

---

## Translation System

### Translation Implementation

**Location:** [`src/ai/providers/gemini.py:translate_text()`](src/ai/providers/gemini.py:200)

**Features:**

- **Multi-language support:** Auto-detect or specify source language
- **Persian phonetics:** Automatic phonetic pronunciation generation
- **Format consistency:** Standardized output format
- **AI-powered:** Uses configured LLM provider

#### Translation Workflow

```python
async def translate_text(self, text: str, target_language: str, source_language: str):
    # 1. Build translation prompt
    if source_language.lower() == "auto":
        prompt = f"Detect language and translate to '{target_language}' with Persian phonetics"
    else:
        prompt = f"Translate from '{source_language}' to '{target_language}' with phonetics"

    # 2. Execute translation with low temperature for accuracy
    response = await self.execute_prompt(
        prompt,
        temperature=0.2,
        system_message="You are a precise translation assistant"
    )

    # 3. Format response
    return self._format_translation_response(response, text, target_language)
```

#### Phonetic Pronunciation Generation

- **Format:** `Translation (Persian Pronunciation)`
- **Example:** `Hello (هِلو)`
- **Processing:** Regex-based extraction and formatting
- **Fallback:** Raw response if formatting fails

#### Language Support

- **Source Languages:** Auto-detect or specify (English, Persian, etc.)
- **Target Languages:** Any language supported by AI provider
- **Phonetics:** Always generates Persian pronunciation guide

---

## Configuration and Settings

### Environment Variables

**Location:** `.env` file

#### Required Variables

```bash
# Telegram Configuration
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE_NUMBER=+1234567890
TELEGRAM_SESSION_NAME=sakaibot_session

# LLM Provider Configuration
LLM_PROVIDER=gemini  # or openrouter
```

#### Optional Variables

```bash
# Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# OpenRouter Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash

# Audio Processing
PATHS_FFMPEG_EXECUTABLE=/usr/local/bin/ffmpeg

# Optional Services
ASSEMBLYAI_API_KEY=your_assemblyai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
HUGGINGFACE_API_TOKEN=your_hf_token_here

# Environment
ENVIRONMENT=production
DEBUG=false
```

### Settings Persistence

**Implementation:** [`src/core/settings.py`](src/core/settings.py)

#### User Settings File

- **Location:** `data/sakaibot_user_settings.json`
- **Format:** JSON
- **Content:** Target group, command mappings, authorized users

#### Settings Structure

```json
{
  "selected_target_group": {
    "id": 123456789,
    "title": "My Group",
    "is_forum": true
  },
  "active_command_to_topic_map": {
    "1": ["translate", "tr"],
    "2": ["tts", "speak"],
    "3": ["analyze", "summary"]
  },
  "directly_authorized_pvs": [123456789, 987654321]
}
```

#### Configuration Validation

- **Command:** `sakaibot config validate`
- **Checks:** API keys, paths, directories, settings format
- **Output:** Error, warning, and success messages

---

## Integration Points

### Telegram API Integration

**Implementation:** [`src/telegram/handlers.py`](src/telegram/handlers.py)

#### Client Initialization

```python
client = TelegramClient(
    session_name,
    api_id,
    api_hash
)
```

#### Event Handlers

1. **Owner Commands:** Direct execution from bot owner
2. **Authorized Users:** Forward to owner for confirmation
3. **Categorization:** Forward messages to mapped topics

#### Message Processing Flow

```
Message Received → Parse Command → Validate Permissions →
Execute Command → Send Response → Cleanup
```

### Monitoring and Authorization

**Implementation:** [`src/cli/state.py`](src/cli/state.py)

#### CLI State Object

```python
class CLIState:
    selected_target_group: Dict[str, Any]
    active_command_to_topic_map: Dict[str, List[str]]
    directly_authorized_pvs: List[int]
    is_monitoring_active: bool
```

#### Authorization Flow

1. **Check Command:** Is it from owner or authorized user?
2. **Owner:** Execute directly
3. **Authorized User:** Forward to owner with confirmation
4. **Unauthorized:** Ignore or notify

#### Categorization Flow

1. **Check Target Group:** Is target group set?
2. **Check Mappings:** Does command have topic mapping?
3. **Forward:** Send message to mapped topic
4. **Log:** Record categorization event

### Caching Mechanisms

**Implementation:** [`src/utils/cache.py`](src/utils/cache.py)

#### Cache Types

1. **Group Cache:** `cache/group_cache.json`
2. **PV Cache:** `cache/pv_cache.json`
3. **Settings Cache:** In-memory cache for frequently accessed data

#### Cache Management

- **Refresh Commands:** `--refresh` flag to force reload
- **Expiration:** Automatic refresh when needed
- **Validation:** Data integrity checks

### Logging and Debugging

**Implementation:** [`src/utils/logging.py`](src/utils/logging.py)

#### Logging Configuration

- **Format:** Structured logging with timestamps
- **Levels:** DEBUG, INFO, WARNING, ERROR
- **Output:** Console and file logging

#### Debug Features

1. **Verbose Mode:** `--debug` flag for detailed output
2. **Command Logging:** All commands logged with context
3. **Error Tracking:** Detailed error messages and stack traces
4. **Performance Metrics:** Response times and success rates

#### Error Handling Patterns

```python
try:
    # Command execution
    result = await execute_command()
except SpecificError as e:
    # Handle specific error
    logger.error(f"Command failed: {e}")
    await send_error_message(e)
except Exception as e:
    # Generic error handling
    logger.error(f"Unexpected error: {e}", exc_info=True)
    await send_generic_error()
```

---

This report provides a comprehensive overview of all commands in the SakaiBot project, their workflows, implementation details, and integration points. Each command is analyzed with proper syntax, parameters, error handling, and dependencies to ensure a complete understanding of the system.
