## SakaiBot Project Overview

### Purpose
SakaiBot is a modern Telegram userbot with AI-assisted workflows, voice processing, and a rich CLI for monitoring, categorization, and utilities. It integrates multiple LLM providers (OpenRouter, Google Gemini), provides Persian-first experiences (prompts, phonetics), and supports STT/TTS pipelines.

### High-Level Architecture
- Core layers and responsibilities:
  - `src/core`: Configuration, constants, exceptions, settings persistence.
  - `src/ai`: AI abstraction, providers (OpenRouter/Gemini), prompt packs, processor, STT/TTS.
  - `src/telegram`: Telethon client lifecycle and event handlers for commands and categorization.
  - `src/cli`: Click-based CLI, interactive menus, command groups for status, monitoring, and configuration.
  - `src/utils`: Logging, cache helpers, general helpers, translation utilities.
  - `tests`: Unit/integration tests for AI providers, CLI, Telegram handlers, translation, and TTS.

### Entry Points
- CLI binary: `sakaibot` (via `[project.scripts]` -> `src.cli.main:cli` in `pyproject.toml`).
- Legacy script: `sakaibot.py` invokes `src.cli.main:cli` directly.
- Async app: `src/main.py` bootstraps the bot, Telegram client, handlers, and delegates to an interactive CLI loop (app-style run).

---

## Components

### Core (`src/core`)
- `config.py`
  - `Config` (Pydantic settings) loads from `.env` (preferred) or legacy `data/config.ini`.
  - Validates Telegram creds, LLM provider selection (`openrouter`|`gemini`), and optional FFmpeg path.
  - `is_ai_enabled` indicates whether provider keys are usable.
  - `load_config()` selects `.env` or INI, raising `ConfigurationError` if missing.
- `constants.py`
  - App metadata, sizes/limits, default models/voices, OpenRouter headers, and paths for logs/cache.
- `settings.py`
  - `SettingsManager` persists user-level state in `data/sakaibot_user_settings.json`:
    - `selected_target_group`, `active_command_to_topic_map`, `directly_authorized_pvs`.
  - Validates and normalizes mappings through CLI utils.
- `exceptions.py`
  - Custom exception hierarchy: `ConfigurationError`, `TelegramError`, `AIProcessorError`, etc.

### AI (`src/ai`)
- `llm_interface.py`
  - Abstract `LLMProvider` for prompt, translate, and message analysis.
- `providers/openrouter.py`
  - Uses `openai.AsyncOpenAI` with custom `httpx` client against `https://openrouter.ai/api/v1`.
  - Handles timeouts, safety filtering, and response extraction.
  - Translation prompt enforces Persian phonetic output via utilities.
- `providers/gemini.py`
  - Uses `google.generativeai` (`GenerativeModel`) with async generation and backoff.
  - Similar translation and analysis surfaces; structured extraction and safety checks.
- `processor.py`
  - Selects provider from config; exposes:
    - `execute_custom_prompt`, `translate_text_with_phonetics`, `analyze_messages`.
    - Back-compat helpers: `execute_tellme_mode`, `analyze_conversation_messages`, `answer_question_from_chat_history`.
- `stt.py`
  - Google Web Speech API via `SpeechRecognition` to transcribe WAV audio (`fa-IR` default).
- `tts.py`
  - Multi-provider TTS fallbacks with Persian focus:
    - Primary: `edge-tts` (free, reliable for supported voices).
    - Local offline: `pyttsx3` (WAV -> MP3 via `pydub`).
    - Optional: HuggingFace Inference API (if `HUGGINGFACE_API_TOKEN` exists).
    - Fallback: Google Translate public endpoint (chunked, stitched with `pydub`).
  - `generate_speech_file()` returns a temp MP3 path for Telegram upload.
- `persian_prompts.py`
  - Prompt templates, system messages, and formats for Persian outputs (translations, analysis, Q&A, voice summary).

### Telegram (`src/telegram`)
- `client.py`
  - Creates `TelegramClient` session under `data/`, manages login (code + optional 2FA), and exposes async input flow.
- `handlers.py`
  - Orchestrates bot command processing:
    - `/stt` (reply to voice): download media, convert to WAV (FFmpeg via `pydub`), STT, optional AI summary, and single final message.
    - `/tts` or `/speak`: parse params (`voice`, `rate`, `volume`), normalize text, synthesize, upload as voice note.
    - `/prompt`, `/translate`, `/analyze`, `/tellme`: clean parsing, defer to `AIProcessor`.
    - Categorization mapping: forwards replied messages to a group/topic based on configured command-to-topic map.
  - Handles long-text truncation to Telegram limits.

### CLI (`src/cli`)
- `main.py`
  - Click group with `status`, `menu`, `setup` commands.
  - If no subcommand: prints banner and prompts for interactive menu or status.
  - `show_status()` renders a table with AI provider readiness, categorization, authorization counts, and cache presence.
- `interactive.py`
  - Rich-based navigable UI with `InteractiveMenu` and `MenuState`.
  - Submenus: Groups & Categories, Monitoring & Authorization, Settings.
  - Invokes `menu_handlers` for group setup, mappings, monitoring toggle, and settings workflows.
- `commands/monitor.py`
  - `sakaibot monitor start|stop|status`.
  - Wires Telethon event handlers for owner and authorized users; injects `EventHandlers` and manages lifecycle.
  - Uses persisted settings for group/mappings/authorized PVs; displays status via Rich tables.

### Utilities (`src/utils`)
- `logging.py`: Central file-logging with auto-flush; optional console output; Windows UTF-8 handling.
- `helpers.py`: Safe filenames, text/file-size formatting, command param parser, and temp file cleanup with retries.
- `translation_utils.py`: Language mapping, robust command parsing, structured translation response extraction and formatting, translation history.

---

## Runtime Flows

### Startup and Shutdown (App mode)
1. `src/main.py` sets up logging, loads `Config`, and constructs `SakaiBot`.
2. `TelegramClientManager.initialize()` connects/authenticates; session files stored under `data/`.
3. Event handlers are prepared and CLI handler loop (`display_main_menu_loop`) runs.
4. Graceful shutdown saves interactive state and removes Telethon handlers; client disconnects.

### CLI-only Mode
- `sakaibot` → `src.cli.main:cli` → either interactive menu (`interactive.py`) or status view.
- `sakaibot monitor start` provisions Telethon client and registers `EventHandlers` without launching the full app shell.

### Monitoring Flow
- Owner filter: outgoing `^/\w+` commands; Authorized user filters: incoming commands from whitelisted IDs.
- For each command, `EventHandlers.process_command_logic()` branches to STT/TTS/AI/categorization flows, posts interim “thinking” messages, edits final responses, and cleans up temp files.

### AI Command Flows
- `/prompt=<text>`: Uses Persian comedian system prompt by default; returns raw LLM response.
- `/translate=<lang>[=<text>]` or reply mode: Validates language, builds structured prompt requesting “Translation” and “Phonetic” lines; formats standardized output.
- `/analyze=<N>`: Fetches last N messages, maps sender names, builds detailed Persian analysis prompt; returns structured analysis.
- `/tellme=<N>=<question>`: Contextual Q&A based on last N messages.

### Voice Flows
- STT: Download voice → convert to WAV (FFmpeg/pydub) → Google Web Speech (`fa-IR`) → optional AI summary fallback (Gemini env key) → return combined transcription and summary.
- TTS: Normalize text → edge-tts → fallback to pyttsx3 → optional HuggingFace → Google Translate TTS → upload as voice-note; captions mention provider when applicable.

---

## Configuration

### Environment (.env)
- Required: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE_NUMBER`.
- LLM: `LLM_PROVIDER` (`openrouter`|`gemini`) and corresponding `OPENROUTER_API_KEY`/`OPENROUTER_MODEL` or `GEMINI_API_KEY`/`GEMINI_MODEL`.
- Optional paths: `PATHS_FFMPEG_EXECUTABLE` (helps Windows), optional AI service tokens (`HUGGINGFACE_API_TOKEN`).

### Legacy INI (`data/config.ini`)
- Supported for backward compatibility; mapped into env-style keys by `Config.load_from_ini()`.

### User Settings (`data/sakaibot_user_settings.json`)
- Schema keys:
  - `selected_target_group`: dict or id
  - `active_command_to_topic_map`: mapping for categorization commands → topic ids
  - `directly_authorized_pvs`: list of user ids

---

## Error Handling & Logging
- Central exceptions: configuration, Telegram, AI, cache, validation.
- Rich logging to `logs/monitor_activity.log` with auto-flush file handler.
- Provider retries, HTTP timeouts, and safety filter reporting.
- Telegram message length enforcement and truncation.

---

## Data & Storage
- `data/`: Telethon session, user settings, optional backups.
- `cache/`: PV/group caches.
- `logs/`: monitor activity log.

---

## Testing
- `tests/unit`: AI providers, CLI, translation, TTS, Telegram handlers.
- `tests/integration`: Translation and TTS integration tests.
- `pytest.ini` configures async mode, markers, and addopts.

---

## Security & Privacy
- Never commit secrets; use `.env`.
- Authorized user list restricts who can invoke commands when monitoring.
- Confirmation keyword (`confirm`) flow available for owner workflows.
- Safety filtering surfaced from providers with meaningful messages.

---

## Performance & Limits
- Message analysis bounded by `DEFAULT_MAX_ANALYZE_MESSAGES` (10k) and token/timeout safeguards.
- TTS/STT chunking and stitching to respect provider limits and produce stable outputs.
- HTTP timeouts (OpenRouter 10m, Gemini 5m) with retry/backoff strategies.

---

## Extensibility
- Add new LLM providers by implementing `LLMProvider` and wiring in `AIProcessor` dispatch.
- Add CLI commands via `src/cli/commands/*` and expose in `cli.add_command(...)`.
- Extend event handling logic in `src/telegram/handlers.py` for new commands.
- Expand translation language mapping in `translation_utils.py`.

---

## Operational Tips & Troubleshooting
- If STT fails: verify FFmpeg availability and `pydub` can find converters; ensure WAV conversion works.
- If TTS fails: try shorter text; confirm network access; optionally set `HUGGINGFACE_API_TOKEN`; check edge-tts voice id; verify system voices for `pyttsx3`.
- If AI blocked: verify API keys, provider selection, and model names; inspect logs for safety filter blocks.
- On Windows, setting `PATHS_FFMPEG_EXECUTABLE` improves media conversion reliability.
- Use `sakaibot status` and `sakaibot monitor status` to diagnose readiness.

---

## Related Docs
- `docs/user_verification_implementation.md` — details on user verification logic and flows.


