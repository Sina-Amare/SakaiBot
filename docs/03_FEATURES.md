# Feature Inventory

## Message Handling and Command Processing

### ✅ Complete Features

#### 1. Command Routing System
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers.py`, `src/telegram/handlers/categorization_handler.py`
- **Trigger**: Automatic (all messages from owner or authorized users)
- **Mechanism**: Event handlers registered via Telethon
- **Features**:
  - Owner message handling (direct commands)
  - Authorized user command handling (with confirmation flow)
  - Command parsing and validation
  - Error handling with user-friendly messages

#### 2. Confirmation Flow
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/categorization_handler.py`
- **Trigger**: Authorized users send commands, owner replies with "confirm"
- **Mechanism**: Reply-based confirmation system
- **Purpose**: Allows owner to review and approve authorized user commands

## AI-Powered Conversation Features

### ✅ Complete Features

#### 1. Custom Prompt Command (`/prompt=...`)
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/ai_handler.py`
- **Trigger**: Command `/prompt=<your question or instruction>`
- **AI Integration**: 
  - Provider: Configurable (Gemini or OpenRouter)
  - Model: `gemini-2.5-flash` (default)
  - System Message: Persian comedian personality
- **Features**:
  - Input validation and sanitization
  - Rate limiting (10 requests per 60 seconds per user)
  - Long message splitting (handles responses >4096 chars)
  - Error handling with Persian error messages
- **Limitations**: 
  - No conversation context retention between prompts
  - No streaming responses (waits for complete response)

#### 2. Translation Command (`/translate=...`)
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/ai_handler.py`, `src/utils/translation_utils.py`
- **Trigger**: 
  - `/translate=<target_lang> <text>`
  - `/translate=<target_lang>,<source_lang> <text>`
  - Reply to message with `/translate=<target_lang>`
- **AI Integration**:
  - Provider: Configurable (Gemini or OpenRouter)
  - Specialized translation prompts with phonetic support
  - Auto-detection of source language
- **Features**:
  - Multi-language support (ISO 639-1 codes)
  - Phonetic pronunciation for Persian
  - Reply-to-message support
  - STT result extraction (removes formatting when translating STT output)
- **Limitations**:
  - Single target language per command (no batch translation)
  - No translation history/cache

#### 3. Conversation Analysis (`/analyze=...`)
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/ai_handler.py`
- **Trigger**: 
  - `/analyze=<number_of_messages>`
  - `/analyze=<mode>=<number>` (modes: general, fun, romance)
  - Legacy: `/analyze <number>`
- **AI Integration**:
  - Provider: Configurable (Gemini or OpenRouter)
  - Specialized analysis prompts per mode
  - Message history formatting
- **Features**:
  - Multiple analysis modes:
    - `general`: Standard conversation analysis
    - `fun`: Humorous/entertaining analysis
    - `romance`: Romance-focused analysis
  - Configurable message limit (1-10000, default: 10000)
  - Participant name mapping
  - Timestamp preservation
- **Limitations**:
  - Only analyzes text messages (ignores media)
  - No incremental analysis (always analyzes from scratch)
  - Maximum 10000 messages (hard limit)

#### 4. Question Answering (`/tellme=...`)
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/ai_handler.py`
- **Trigger**: `/tellme=<number_of_messages>=<your_question>`
- **AI Integration**:
  - Provider: Configurable (Gemini or OpenRouter)
  - Question-answering system message
  - Context from chat history
- **Features**:
  - Answers questions based on chat history
  - Configurable message window (1-10000)
  - Question validation
- **Limitations**:
  - No follow-up question support
  - No answer confidence scoring

## Voice Processing Features

### ✅ Complete Features

#### 1. Text-to-Speech (`/tts`, `/speak`)
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/tts_handler.py`, `src/ai/tts.py`
- **Trigger**: 
  - `/tts <text>` or `/speak <text>`
  - Reply to message with `/tts` or `/speak`
  - `/tts voice=<voice_name> <text>` (voice selection)
- **AI Integration**: 
  - Provider: Google Gemini TTS API
  - Voice: Configurable (default: "Orus")
  - Available voices: Kore, Puck, Fenrir, Zephyr, Orus, and 27+ others
- **Features**:
  - Queue-based processing (prevents API overload)
  - Status updates during processing
  - Voice selection support
  - Text normalization for TTS
  - Automatic cleanup of temporary files
  - Reply-to-message support
- **Limitations**:
  - No rate/volume/pitch control (parameters exist but not fully implemented)
  - Queue position updates every 2 seconds (could be more frequent)
  - No batch TTS processing

#### 2. Speech-to-Text (`/stt`)
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/stt_handler.py`, `src/ai/stt.py`
- **Trigger**: Reply to voice message with `/stt`
- **AI Integration**:
  - STT Provider: Google Web Speech API (via `speech_recognition` library)
  - AI Summarization: Gemini/OpenRouter (for transcription analysis)
- **Features**:
  - Voice message transcription
  - Language detection (default: Persian `fa-IR`)
  - AI-powered summarization of transcriptions
  - Formatted output with transcription and analysis
- **Limitations**:
  - Requires FFmpeg for audio conversion (must be configured)
  - No retry logic for STT failures
  - Single language per transcription (no multi-language detection)
  - No confidence scores for transcription

## Automation Capabilities

### ✅ Complete Features

#### 1. Message Categorization
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/categorization_handler.py`
- **Trigger**: Reply to message with command (e.g., `/work`, `/personal`)
- **Mechanism**: Command-to-topic mapping system
- **Features**:
  - Forward messages to target group
  - Support for forum topics (topic-specific forwarding)
  - Command mapping configuration (via CLI)
  - Legacy and new mapping format support
  - Confirmation flow for authorized users
- **Configuration**:
  - Target group selection (via CLI: `sakaibot group set`)
  - Command-to-topic mapping (via CLI: `sakaibot group map`)
- **Limitations**:
  - Only forwards text messages (media forwarding not fully tested)
  - No automatic categorization (requires manual command)
  - No categorization history/analytics

## User Interaction Patterns

### ✅ Complete Features

#### 1. Direct Commands (Owner)
- **Status**: ✅ Complete
- **Mechanism**: Owner's messages are processed immediately
- **No Confirmation**: Required (owner has full access)

#### 2. Authorized User Commands
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/categorization_handler.py`
- **Mechanism**: 
  1. Authorized user sends command
  2. Bot notifies owner
  3. Owner replies with "confirm"
  4. Command executes
- **Features**:
  - User authorization management (via CLI: `sakaibot auth`)
  - Confirmation keyword: "confirm"
  - User verification by ID, username, or display name

#### 3. Inline Replies
- **Status**: ✅ Complete
- **Supported Commands**: `/tts`, `/stt`, `/translate`
- **Mechanism**: Reply to message with command (extracts content from replied message)

#### 4. Command Parameters
- **Status**: ✅ Complete
- **Location**: `src/utils/helpers.py` - `parse_command_with_params()`
- **Format**: `/command param=value param2=value2 text`
- **Supported Parameters**:
  - TTS: `voice`, `rate`, `volume`
  - Translation: Language codes

## Admin/Control Features

### ✅ Complete Features

#### 1. CLI Interface
- **Status**: ✅ Complete
- **Location**: `src/cli/main.py`
- **Entry Point**: `sakaibot` command (global after installation)
- **Commands**:
  - `sakaibot status` - Show bot status
  - `sakaibot menu` - Interactive menu
  - `sakaibot group` - Group management
  - `sakaibot auth` - Authorization management
  - `sakaibot monitor` - Monitoring control
  - `sakaibot config` - Configuration management

#### 2. Group Management
- **Status**: ✅ Complete
- **Location**: `src/cli/commands/group.py`
- **Commands**:
  - `sakaibot group list` - List groups (admin groups by default)
  - `sakaibot group set` - Set target group for categorization
  - `sakaibot group topics` - List topics in forum group
  - `sakaibot group map` - Manage command-to-topic mappings
- **Features**:
  - Group caching (performance optimization)
  - Forum topic support
  - Group refresh from Telegram

#### 3. Authorization Management
- **Status**: ✅ Complete
- **Location**: `src/cli/commands/auth.py`
- **Commands**:
  - `sakaibot auth list` - List authorized users
  - `sakaibot auth add <identifier>` - Add authorized user
  - `sakaibot auth remove <identifier>` - Remove authorized user
  - `sakaibot auth clear` - Clear all authorized users
  - `sakaibot auth refresh` - Refresh private chat cache
- **Features**:
  - User identification by ID, username, or display name
  - PV cache for performance
  - User verification before authorization

#### 4. Monitoring Control
- **Status**: ✅ Complete
- **Location**: `src/cli/commands/monitor.py`
- **Commands**:
  - `sakaibot monitor start` - Start message monitoring
  - `sakaibot monitor stop` - Stop monitoring
  - `sakaibot monitor status` - Check monitoring status
- **Features**:
  - Graceful start/stop
  - Verbose mode support
  - Status tracking

#### 5. Configuration Management
- **Status**: ✅ Complete
- **Location**: `src/cli/commands/config.py`
- **Commands**:
  - `sakaibot config show` - Display configuration
  - `sakaibot config show --all` - Show full config (including API keys)
  - `sakaibot config validate` - Validate configuration
  - `sakaibot config edit` - Open config file in editor
  - `sakaibot config example` - Show example configuration
- **Features**:
  - Configuration validation
  - Masked API key display (default)
  - Editor integration

## Image Generation Features

### ✅ Complete Features

#### 1. Image Generation (`/image=flux/...`, `/image=sdxl/...`)
- **Status**: ✅ Complete
- **Location**: `src/telegram/handlers/image_handler.py`
- **Trigger**: 
  - `/image=flux/<prompt>` - Generate using Flux worker
  - `/image=sdxl/<prompt>` - Generate using SDXL worker
- **AI Integration**:
  - Prompt enhancement via OpenRouter/Gemini before generation
  - System message specialized for image generation prompt engineering
- **Features**:
  - LLM-based prompt enhancement for better image quality
  - Separate FIFO queues per model (Flux and SDXL process independently)
  - Sequential processing within each model queue
  - Queue position updates during processing
  - Status updates: "🎨 Enhancing prompt...", "🖼️ Generating image...", "📤 Sending image..."
  - Enhanced prompt shown as image caption
  - Comprehensive error handling with Persian messages
  - Rate limiting integration (reuses AI rate limiter)
  - Metrics tracking
- **Workers**:
  - **Flux**: GET request, no authentication required
  - **SDXL**: POST request with Bearer token authentication
- **Configuration**: 
  - `FLUX_WORKER_URL` - Flux worker endpoint
  - `SDXL_WORKER_URL` - SDXL worker endpoint
  - `SDXL_API_KEY` - SDXL Bearer token
- **Limitations**:
  - Sequential processing within each model (one request at a time per model)
  - Temporary image files stored locally before sending
  - Maximum prompt length: 1000 characters

## Media Handling

### ✅ Complete Features

#### 1. Voice Message Handling
- **Status**: ✅ Complete
- **Support**: 
  - Voice note transcription (STT)
  - Voice note generation (TTS)
- **Format**: OGG Opus (Telegram native), WAV (for processing)

#### 2. Audio Processing
- **Status**: ✅ Complete
- **Requirements**: FFmpeg (must be configured)
- **Features**:
  - Audio format conversion
  - Audio normalization
  - Temporary file cleanup

### 🚧 Partial Features

#### 1. Media Forwarding
- **Status**: 🚧 Partial
- **Support**: Text messages fully supported
- **Limitations**: Media forwarding in categorization not fully tested
- **Location**: `src/telegram/handlers/categorization_handler.py`

## Known Limitations

### Feature Limitations

1. **No Conversation Memory**: Each AI command is independent (no context retention)
2. **No Streaming Responses**: All AI responses wait for completion before sending
3. **Limited Media Support**: Primarily text-focused, media handling is basic
4. **No Batch Operations**: Commands process one item at a time
5. **No Scheduled Tasks**: No cron-like scheduling for automated actions
6. **No Database**: All persistence is file-based JSON (may not scale)
7. **No Web Interface**: CLI-only, no web dashboard
8. **No Metrics Dashboard**: Metrics collected but no visualization

### Technical Limitations

1. **Rate Limiting**: Per-user rate limiting may be too restrictive for some use cases
2. **Queue Management**: TTS queue is in-memory (lost on restart)
3. **Cache Refresh**: Manual refresh required for groups/PVs (no automatic refresh)
4. **Error Recovery**: Some errors may require manual intervention
5. **Session Management**: Session files are not encrypted at rest

### User-Bot Specific Limitations

1. **Account Risk**: Violates Telegram ToS, account could be banned
2. **Rate Limits**: Subject to user account limits (stricter than Bot API)
3. **No Bot Features**: Cannot use Bot API features (webhooks, inline keyboards, etc.)
4. **Single Account**: One user account per instance

## File/Module Locations Summary

| Feature | Primary Location | Supporting Files |
|---------|-----------------|------------------|
| AI Commands | `src/telegram/handlers/ai_handler.py` | `src/ai/processor.py`, `src/ai/providers/` |
| Image Generation | `src/telegram/handlers/image_handler.py` | `src/ai/image_generator.py`, `src/ai/prompt_enhancer.py`, `src/ai/image_queue.py` |
| TTS | `src/telegram/handlers/tts_handler.py` | `src/ai/tts.py`, `src/ai/tts_queue.py`, `src/ai/providers/tts_gemini.py` |
| STT | `src/telegram/handlers/stt_handler.py` | `src/ai/stt.py` |
| Categorization | `src/telegram/handlers/categorization_handler.py` | `src/cli/commands/group.py` |
| Authorization | `src/cli/commands/auth.py` | `src/telegram/user_verifier.py` |
| CLI | `src/cli/main.py` | `src/cli/handler.py`, `src/cli/interactive.py`, `src/cli/commands/` |
| Configuration | `src/core/config.py` | `src/core/settings.py`, `src/core/constants.py` |
| Error Handling | `src/utils/error_handler.py` | `src/core/exceptions.py` |
| Rate Limiting | `src/utils/rate_limiter.py` | Used in `ai_handler.py`, `image_handler.py` |
| Caching | `src/utils/cache.py` | `cache/pv_cache.json`, `cache/group_cache.json` |

---

**Next**: See `04_CODE_QUALITY.md` for technical debt and code quality assessment.

