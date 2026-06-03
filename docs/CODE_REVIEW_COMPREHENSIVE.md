# Comprehensive Code Review — SakaiBot

**Review type:** Line-by-line, full codebase  
**Scope:** 72 Python files, ~17,258 lines under `src/`  
**Date:** January 2025  
**Version:** 1.0

---

## 1. Executive Summary

This review covers every Python file in `src/` in dependency order (core → utils → ai → telegram → cli → main). It documents purpose, public API, dependencies, data flow, patterns, and risks.

**Verdict:** The codebase is well-structured with clear layering, provider abstraction, key rotation, and fallback logic. The main gaps are: **circuit breakers are implemented but never used** in AI or Telegram call paths; **two sources of truth for Gemini keys** (Config vs tts_config); **core depends on cli** (settings → cli.utils); **global Config is mutated** in PromptEnhancer; and **TaskManager consumes the task exception twice** so `exc_info` is wrong. Test fixtures do not match the real Config shape.

**Critical findings (high priority):**

1. Circuit breakers (`get_ai_circuit_breaker`, `get_telegram_circuit_breaker`) are defined and exported but never imported or used in `src/ai/` or `src/telegram/`. All external API calls run without circuit-breaker protection.
2. `PromptEnhancer` mutates the global Config instance (`config.llm_provider = "openrouter"` then restore in `finally`). Concurrent image enhancements can interleave and corrupt provider selection.
3. `TaskManager._on_task_done` calls `task.exception()` twice; the first call consumes the exception, so `exc_info=task.exception()` is `None` and the log loses the traceback.
4. Core layer violation: `SettingsManager.load_user_settings` imports `normalize_command_mappings` from `..cli.utils`. Core should not depend on CLI; the import is lazy (inside the method) so the app loads, but the layering is broken.
5. Config duality: `core/tts_config.py` reads Gemini keys via `os.getenv` (GEMINI_API_KEY_TTS, GEMINI_API_KEY_1, etc.) with its own priority. `core/config.py` (Pydantic) is the main config. Two sources of truth for the same keys.

**Important findings (medium priority):**

1. `Config.is_ai_enabled` for OpenRouter checks only `openrouter_api_key` (legacy single key), not `openrouter_api_keys`. For Gemini it uses `gemini_api_keys`. Asymmetric and can report AI disabled when only numbered keys are set.
2. Test fixtures in `conftest.py` use `config.gemini_api_keys`, `config.max_analyze_messages`, `config.ffmpeg_path`; production Config uses properties `gemini_api_keys`, `userbot_max_analyze_messages`, `paths_ffmpeg_executable`. Fixtures may not reflect real Config after refactors.
3. FFmpeg path setup logic is duplicated in `BaseHandler._setup_ffmpeg_path` and `EventHandlers._setup_ffmpeg_path`; `EventHandlers._normalize_text` only delegates to `TTSHandler._normalize_text` (single implementation but indirection).
4. Rate limiter has `cleanup_old_entries()` but no code path calls it; buckets can grow for users who stop using the bot.
5. `KeyState.is_available()` mutates `exhausted_until` (clears it when the window has passed). Semantically correct but a side effect inside a predicate; callers should be aware.

---

## 2. File Inventory

| Path | Lines | Layer | Purpose |
| ---- | ----- | ----- | ------- |
| src/telegram/handlers/ai_handler.py | 819 | telegram | AI commands: prompt, translate, analyze, tellme; validation; rate limit; metrics |
| src/ai/prompts.py | 1053 | ai | System prompts and templates for LLM operations |
| src/ai/providers/gemini.py | 1022 | ai | Gemini LLM provider; key rotation; Pro/Flash; thinking |
| src/telegram/commands/self_commands.py | 940 | telegram | /help, /auth, /status, /group implementation |
| src/ai/providers/openrouter.py | 610 | ai | OpenRouter LLM provider; key rotation |
| src/cli/interactive.py | 616 | cli | Interactive menu loop and navigation |
| src/telegram/handlers/image_handler.py | 448 | telegram | /image=flux, /image=sdxl; queue; prompt enhancement |
| src/cli/utils.py | 449 | cli | Shared client, display helpers, normalize_*, get_telegram_client |
| src/cli/commands/group.py | 460 | cli | sakaibot group CLI commands |
| src/core/config.py | 364 | core | Pydantic Config; env and INI load; validators |
| src/telegram/event_handlers.py | 316 | telegram | Event routing; process_command_logic; handler delegation |
| src/cli/commands/monitor.py | 319 | cli | sakaibot monitor start/stop |
| src/utils/structured_logging.py | 337 | utils | JSON formatter; SensitiveDataFilter; production logging |
| src/telegram/handlers/tts_handler.py | 335 | telegram | /tts; TTS queue; FFmpeg |
| src/main.py | 309 | main | SakaiBot app; run(); graceful_shutdown; signal handling |
| src/utils/translation_utils.py | 291 | utils | Translation formatting and phonetics |
| src/telegram/connection_health.py | 268 | telegram | Heartbeat; reconnect; proxy restart |
| src/utils/error_handler.py | 266 | utils | User-facing error messages; decorator |
| src/ai/analyze_queue.py | 266 | ai | Per-chat AI command lock; timeout; cleanup task |
| src/utils/message_sender.py | 270 | utils | send_message_safe; edit_message_safe; pagination; retry; RTL |
| src/utils/validators.py | 263 | utils | InputValidator: prompt, language, image, number, path |
| src/ai/image_queue.py | 359 | ai | Per-model FIFO queues; Flux/SDXL processing |
| src/ai/processor.py | 399 | ai | AI orchestration; configurable provider fallback; execute_* |
| src/ai/api_key_manager.py | 432 | ai | KeyState; APIKeyManager; rotation; Pacific midnight |
| src/utils/cache.py | 286 | utils | PV/group cache; load/save JSON; get_pvs/get_groups |
| src/utils/rtl_fixer.py | 251 | utils | RTL safety for Persian/mixed text |
| src/telegram/handlers/stt_handler.py | 261 | telegram | /stt; voice download; STT + AI summary |
| src/telegram/handlers/categorization_handler.py | 212 | telegram | Categorization; forward to topic; command map |
| src/ai/prompt_enhancer.py | 210 | ai | LLM prompt enhancement; mutates Config for provider switch |
| src/utils/circuit_breaker.py | 190 | utils | CircuitBreaker; get_ai/get_telegram (unused in call paths) |
| src/ai/tts_queue.py | 215 | utils | TTS queue per chat |
| src/cli/commands/auth.py | 218 | cli | sakaibot auth list/add/remove |
| src/cli/commands/config.py | 232 | cli | sakaibot config validate |
| src/ai/image_generator.py | 259 | ai | Flux/SDXL HTTP client; temp files |
| src/telegram/utils.py | 347 | telegram | fetch_all_private_chats; fetch_user_groups; TelegramUtils |
| src/utils/helpers.py | 202 | utils | safe_filename; split_message; parse_command_with_params; clean_temp_files |
| src/ai/providers/tts_gemini.py | 200 | ai | Gemini TTS API client |
| src/core/settings.py | 135 | core | SettingsManager; load/save JSON; imports cli.utils |
| src/telegram/user_verifier.py | 171 | utils | verify_user_by_identifier; Telegram API |
| src/utils/instance_lock.py | 164 | utils | PID lock file; force-kill previous instance |
| src/telegram/client.py | 150 | telegram | TelegramClientManager; connect; auth; disconnect |
| src/utils/logging.py | 146 | utils | get_logger; LOG_FORMAT |
| src/ai/response_metadata.py | 145 | ai | AIResponseMetadata; build_response_parts |
| src/main.py (src/main.py) | 309 | main | (see above) |
| src/utils/metrics.py | 180 | utils | MetricsCollector; get_metrics_collector; TimingContext |
| src/utils/task_manager.py | 126 | utils | TaskManager; create_task; cancel_all; _on_task_done bug |
| src/utils/rate_limiter.py | 122 | utils | RateLimiter; get_ai_rate_limiter; cleanup_old_entries never called |
| src/telegram/messages.py | 114 | telegram | Message formatting helpers |
| src/cli/handler.py | 104 | cli | CLIHandler; display_main_menu_loop; injects deps |
| src/cli/menu_handlers/monitor_handler.py | 105 | cli | Monitor menu handler |
| src/cli/menu_handlers/group_handler.py | 182 | cli | Group menu handler |
| src/ai/llm_interface.py | 139 | ai | LLMProvider ABC; execute_prompt; translate; analyze; answer_question |
| src/ai/tts.py | 132 | ai | TextToSpeechProcessor; Gemini TTS |
| src/core/constants.py | 65 | core | APP_NAME; MAX_MESSAGE_LENGTH; defaults; SUPPORTED_IMAGE_MODELS |
| src/core/tts_config.py | 69 | core | TTS key priority via os.getenv; duplicate of Config concern |
| src/telegram/handlers/base.py | 82 | telegram | BaseHandler; _normalize_text; _setup_ffmpeg_path |
| src/cli/state.py | 77 | cli | CLIState; selected_target_group; active_command_to_topic_map |
| src/utils/security.py | 70 | utils | mask_api_key; mask_sensitive_data |
| src/utils/retry.py | 60 | utils | retry_with_backoff decorator |
| src/ai/stt.py | 58 | ai | SpeechToTextProcessor; Google STT |
| src/core/exceptions.py | 42 | core | SakaiBotError; ConfigurationError; TelegramError; AIProcessorError; etc. |
| src/utils/__init__.py | 35 | utils | Re-exports |
| src/cli/main.py | 182 | cli | Click entry point; sakaibot command group |
| src/telegram/handlers/__init__.py | 22 | telegram | Handler exports |
| src/core/__init__.py | 15 | core | Config; get_settings; load_config; exceptions |
| src/telegram/commands/__init__.py | 15 | telegram | Command exports |
| src/cli/commands/__init__.py | 15 | cli | Command group exports |
| src/ai/__init__.py | 14 | ai | AI exports |
| src/telegram/__init__.py | 11 | telegram | TelegramClientManager |
| src/ai/providers/__init__.py | 7 | ai | Provider exports |
| src/cli/__init__.py | 5 | cli | cli |
| src/cli/menu_handlers/__init__.py | 1 | cli | (empty) |
| src/__init__.py | 4 | main | Package |

---

## 3. Core Layer

### 3.1 constants.py

**Purpose:** Application-wide constants: app name/version, Telegram limits, cache paths, config file names, AI model defaults, logging format, image timeouts, default worker URLs.

**Dependencies:** None (typing.Final).

**Findings:** Single source for defaults used by config and other modules. `SYSTEM_VERSION` is custom; ensure it does not break Telegram compatibility. `DEFAULT_FLUX_WORKER_URL` and `DEFAULT_SDXL_WORKER_URL` are hardcoded; consider making them overridable only by env.

### 3.2 exceptions.py

**Purpose:** Custom exception hierarchy. `SakaiBotError` with `message` and optional `details`; subclasses ConfigurationError, TelegramError, AIProcessorError, CacheError, ValidationError.

**Dependencies:** typing.

**Findings:** Clean hierarchy. `__str__` includes details when present. No custom fields beyond message/details; sufficient for error_handler mapping.

### 3.3 config.py

**Purpose:** Pydantic `Config` loaded from .env (or config.ini fallback). Validators for API IDs, phone, provider, API keys, URLs, paths. Properties: `openrouter_api_keys`, `gemini_api_keys`, `is_ai_enabled`, `is_image_generation_enabled`, `ffmpeg_path_resolved`. `load_config()` tries .env then INI; `get_settings()` returns global singleton.

**Dependencies:** pydantic, pydantic_settings, pathlib, configparser, core.constants, core.exceptions.

**Findings:**

- **is_ai_enabled:** For OpenRouter it checks only `self.openrouter_api_key` and length, not `self.openrouter_api_keys`. If user sets only `OPENROUTER_API_KEY_1` (no legacy key), `is_ai_enabled` can be False. Asymmetric with Gemini which uses `gemini_api_keys`.
- **load_from_ini:** Maps only legacy INI keys (single api_key, model). Numbered keys (openrouter_api_key_1, etc.) are not read from INI; documented would help.
- **validate_ffmpeg_path:** On non-Windows, if path does not exist, only prints warning and returns v; does not raise. Callers may get invalid path.

### 3.4 settings.py

**Purpose:** `SettingsManager` loads/saves `data/sakaibot_user_settings.json`. Keys: selected_target_group, active_command_to_topic_map, directly_authorized_pvs. Merge with defaults; validate types; normalize command map via `normalize_command_mappings` from `..cli.utils`.

**Dependencies:** core.constants, core.exceptions, utils.logging, **cli.utils** (lazy import inside load_user_settings).

**Findings:**

- **Layer violation:** Core imports from cli. The import is inside the method so there is no circular import at startup, but core should not depend on CLI. Recommendation: move `normalize_command_mappings` (and `normalize_selected_group` if used by settings) to `core` or a shared util (e.g. `utils.settings_helpers`) and have both cli and core use it.
- **Logging authorized PVs:** `load_user_settings` and `save_user_settings` log authorized PVs count and at debug level the list; ensure no PII in production logs if needed.

### 3.5 tts_config.py

**Purpose:** TTS-specific config: `_get_google_api_key()` reads env with priority GEMINI_API_KEY_TTS, GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY, GOOGLE_API_KEY. Exposes GOOGLE_API_KEY, MAX_RETRIES, RETRY_DELAYS, API_TIMEOUT, TTS_MODEL, DEFAULT_VOICE, audio settings.

**Dependencies:** os, dotenv (optional).

**Findings:**

- **Config duality:** Gemini keys are also in Config (Pydantic). TTS code (e.g. tts_gemini) may use tts_config while the rest of the app uses Config. Two sources of truth; key rotation in Config is not reflected in tts_config. Recommendation: have TTS use Config (e.g. config.gemini_api_keys or a dedicated TTS key list from Config) or document that tts_config is the only source for TTS and keep it in sync with env.

---

## 4. Utils Layer

### 4.1 logging.py

**Purpose:** `get_logger(name)` returns standard library logger with LOG_FORMAT. Used everywhere.

**Findings:** Simple; no structured fields. Production uses structured_logging when Docker/env is set.

### 4.2 structured_logging.py

**Purpose:** SensitiveDataFilter (redact API keys, tokens, session, phone); JSONFormatter; production setup with rotation and optional JSON. Used from main for Docker vs local.

**Findings:** Redaction patterns are broad; avoid logging full message bodies that might contain user content if needed for compliance.

### 4.3 security.py

**Purpose:** mask_api_key (show first/last N chars); mask_sensitive_data (regex); sanitize_log_message. Used in logs and error paths.

**Findings:** Adequate for masking. mask_api_key with short keys returns asterisks; good.

### 4.4 validators.py

**Purpose:** InputValidator: validate_prompt, validate_language_code, sanitize_command_input, validate_command_args, validate_file_path, validate_number, validate_image_model, validate_image_prompt. Used by telegram handlers.

**Findings:** validate_image_prompt logs "harmful" patterns but does not block (by design). validate_file_path rejects absolute Windows paths; safe for server use.

### 4.5 rate_limiter.py

**Purpose:** RateLimiter (per-user sliding window); get_ai_rate_limiter() singleton. check_rate_limit(user_id), get_remaining_requests, reset_user_limit, cleanup_old_entries.

**Findings:** cleanup_old_entries() is never called. Buckets grow unbounded for inactive users. Recommendation: call cleanup from a periodic task (e.g. same as analyze_queue cleanup) or from a low-frequency timer.

### 4.6 circuit_breaker.py

**Purpose:** CircuitBreaker (CLOSED/OPEN/HALF_OPEN); failure_threshold=5, success_threshold=2, timeout=60; async call(). get_telegram_circuit_breaker() and get_ai_circuit_breaker() return global singletons.

**Findings:** **Circuit breakers are never used.** No file in src/ai or src/telegram imports or calls these. All Gemini, OpenRouter, and Telegram API calls run without circuit protection. Recommendation: wrap outbound calls (e.g. in AIProcessor or provider methods, and in TelegramClientManager or send_message paths) with the appropriate circuit breaker.

### 4.7 retry.py

**Purpose:** retry_with_backoff decorator (max_retries, base_delay, max_delay, exponential_base, exceptions). Used by message_sender and potentially elsewhere.

**Findings:** Catches exceptions tuple; re-raises after last attempt. No jitter; acceptable for this use case.

### 4.8 task_manager.py

**Purpose:** TaskManager holds WeakSet of asyncio tasks; create_task(coro), cancel_all(), get_active_task_count(). get_task_manager() singleton. _on_task_done callback when task completes.

**Findings:**

- **Bug:** _on_task_done calls `task.exception()` in the `if` condition (which consumes the exception) and again in `exc_info=task.exception()`. The second call returns None, so the warning log does not get the traceback. Fix: assign once, e.g. `exc = task.exception()` then use `exc` in both the condition and exc_info.
- WeakSet: tasks can be collected before cancel_all iterates; iteration over WeakSet is valid but the set can shrink during iteration. cancel_all builds a list first, so it's safe.

### 4.9 metrics.py

**Purpose:** MetricsCollector (counters, gauges, timers, histories); get_metrics_collector(); TimingContext. Used in ai_handler and image_handler for timing.

**Findings:** In-memory only; no export (Prometheus/StatsD). Handlers record timings; useful for local debugging but not for production dashboards unless an exporter is added.

### 4.10 error_handler.py

**Purpose:** ERROR_MESSAGES map from exception types to user-facing HTML; ErrorHandler.get_user_message(error); handles image timeout/rate limit; decorator for async error handling. Used by handlers to send friendly replies.

**Findings:** Map is comprehensive; image-specific and generic cases covered. No audit logging of errors; consider logging error type (not full message) for metrics.

### 4.11 helpers.py

**Purpose:** safe_filename, format_duration, truncate_text, format_file_size, ensure_directory, clean_temp_files, parse_command_with_params, split_message (Telegram-friendly chunking at paragraph/sentence/word).

**Findings:** split_message uses reserve_length; used by message_sender. clean_temp_files uses time.sleep (blocking); called from async paths (e.g. after sending a file); consider asyncio.sleep or offload to thread if needed to avoid blocking event loop.

### 4.12 cache.py

**Purpose:** CacheManager: load_pv_cache, save_pv_cache, load_group_cache, save_group_cache; get_pvs(client, telegram_utils, force_refresh, ...), get_groups(...). Uses TelegramUtilsProtocol for fetch_all_private_chats and fetch_user_groups.

**Findings:** Cache files under cache/; JSON with last_updated_utc. get_pvs/get_groups are async and take client + telegram_utils; no global client dependency.

### 4.13 message_sender.py

**Purpose:** MessageSender(client). send_message_safe (retry, RTL fix); edit_message_safe; send_long_message (split + pagination). Uses split_message, retry_with_backoff, ensure_rtl_safe.

**Findings:** Retry decorator applied to inner _send; max_retries passed. Handles "message not modified" by returning False instead of raising; correct.

### 4.14 instance_lock.py

**Purpose:** InstanceLock(lock_file). acquire(force=True): PID file in data/.sakaibot.lock; if existing PID running and force, kill it (taskkill on Windows, SIGTERM then SIGKILL on Unix). release() removes file if PID matches.

**Findings:** Force-kill is aggressive but documented. On Windows tasklist/taskkill; on Unix os.kill(pid, 0) and SIGTERM/SIGKILL. _is_process_running(pid) on Windows uses subprocess; ensure no shell injection (PID is int; safe).

### 4.15 rtl_fixer.py

**Purpose:** ensure_rtl_safe(text) for Persian/RTL display in Telegram. Used by message_sender.

**Findings:** Logic is self-contained; no dependency on external services.

### 4.16 translation_utils.py

**Purpose:** Translation output formatting (e.g. phonetics). Used by AI/translate flow.

**Findings:** No security-sensitive input; used after LLM output.

---

## 5. AI Layer

### 5.1 llm_interface.py

**Purpose:** Abstract LLMProvider: execute_prompt, translate_text, analyze_messages, answer_question_from_history; is_configured, provider_name, model_name; close().

**Findings:** Clear contract. Providers (Gemini, OpenRouter) implement it; AIProcessor uses primary + fallback.

### 5.2 response_metadata.py

**Purpose:** AIResponseMetadata dataclass (response_text, thinking_*, web_search_*, model_used, model_fallback_*, provider_fallback_*). build_response_parts(metadata) returns (header, footer) for display. build_execution_footer deprecated.

**Findings:** Metadata is rich; handlers use it for footer/header. Good for transparency when fallback is used.

### 5.3 api_key_manager.py

**Purpose:** KeyState (key, status, failed_at, error_count, exhausted_until); is_available(cooldown) clears exhausted_until when past; mark_healthy, mark_failed. APIKeyManager(api_keys, cooldown, provider_name): get_current_key, mark_key_rate_limited, mark_key_exhausted_for_day, _compute_next_pacific_midnight_utc, all_keys_exhausted. GeminiKeyManager/initialize_gemini_key_manager aliases.

**Findings:**

- KeyState.is_available: Mutates exhausted_until when the window has passed. Intentional but side effect in a predicate; documented.
- Pacific midnight: Correct for Gemini RPD reset; timezone handling with pytz is correct.
- mark_key_exhausted_for_day: Sets exhausted_until to next Pacific midnight UTC; other keys are tried via _find_available_key.

### 5.4 processor.py

**Purpose:** AIProcessor(config): primary provider (Gemini or OpenRouter) and optional fallback (OpenRouter when primary is Gemini). _execute_with_fallback(primary_func, fallback_func, ...) catches key-exhaustion–style errors and calls fallback; sets provider_fallback_applied and thinking_requested/thinking_applied when fallback has no thinking. execute_custom_prompt, translate_text_with_phonetics, analyze_messages, answer_question_from_chat_history; analyze_conversation_messages and execute_tellme_mode compatibility wrappers.

**Findings:**

- translate_text_with_phonetics: No fallback (calls _provider directly); if primary is Gemini and keys exhausted, translation fails. Could add fallback for translate as well.
- analyze_messages: Routes through _execute_with_fallback, so the configured fallback provider can serve analysis when the primary provider fails.
- Participant mapping: analyze_messages builds processed_messages with from_id and participant_mapping; handles None mapping.

### 5.5 providers/gemini.py

**Purpose:** GeminiProvider(LLMProvider): uses config.gemini_api_keys or single key; GeminiKeyManager for rotation; Pro/Flash model selection; execute_prompt, translate_text, analyze_messages, answer_question_from_history; thinking and web search when supported; marks key rate limited or exhausted on 429/quota.

**Findings:** Large file (1000+ lines); model selection and thinking logic are complex. Key manager is initialized from config.gemini_api_keys; getattr(config, 'gemini_api_keys', []) used for backward compat. Pro exhausted_until fallback to Flash is documented.

### 5.6 providers/openrouter.py

**Purpose:** OpenRouterProvider(LLMProvider): openrouter_api_keys from config; APIKeyManager for rotation; execute_prompt, translate_text, analyze_messages, answer_question_from_history. No thinking/web search in API (or stubbed).

**Findings:** Mirrors Gemini interface; key rotation and error handling consistent.

### 5.7 prompt_enhancer.py

**Purpose:** PromptEnhancer(ai_processor). enhance_prompt(user_prompt): try OpenRouter then Gemini; returns (enhanced_prompt, model_used). _try_enhance_with_openrouter: **mutates get_settings().llm_provider to "openrouter"** then restore in finally. _try_enhance_with_gemini: same with "gemini".

**Findings:**

- **Global config mutation:** get_settings() returns the global Config singleton. Mutating config.llm_provider affects any other code that reads provider during the enhancement call. If two image generations run concurrently, they can flip provider back and forth. Recommendation: do not mutate global Config; instead pass a temporary "effective provider" into AIProcessor for this call only, or call a dedicated method that uses OpenRouter/Gemini for enhancement without changing global state.
- Enhancement failure: Falls back to original prompt and model_used "none"; acceptable.

### 5.8 image_generator.py

**Purpose:** ImageGenerator: calls Flux/SDXL worker URLs (from config); downloads image to temp; returns path. Timeouts from constants.

**Findings:** Uses config for URLs and SDXL key; no circuit breaker. Failures propagate to handler.

### 5.9 image_queue.py

**Purpose:** ImageQueue: per-model lists (flux, sdxl); add_request, get_queue_position, get_status; process_next_flux/process_next_sdxl with callbacks. Request storage by request_id.

**Findings:** Processing is sequential per model; no global lock documented but handlers are assumed to drive processing. Queue state is in-memory; restart clears it.

### 5.10 analyze_queue.py

**Purpose:** AnalyzeQueue: per-chat active request; try_start_analysis returns (ok, error_message); release_analysis when done; background cleanup task every CLEANUP_INTERVAL to release timed-out locks. PROTECTED_COMMANDS = analyze, prompt, tellme.

**Findings:** Clean shutdown via stop_cleanup_task (called from main graceful_shutdown). Timeout 5 minutes; no persistent queue.

### 5.11 tts.py, tts_queue.py, stt.py

**Purpose:** TextToSpeechProcessor (Gemini TTS); TTS queue per chat; SpeechToTextProcessor (Google STT). tts_config used for TTS key in tts_gemini.

**Findings:** TTS key from tts_config (os.getenv) not from Config; reinforces Config vs tts_config duality.

### 5.12 prompts.py

**Purpose:** Large set of prompt templates (translation, analysis, tellme, image enhancement, etc.). Used by providers and prompt_enhancer.

**Findings:** 1000+ lines; consider splitting by domain (translation, analysis, image) for maintainability. No user input interpolated unsanitized; format() used with controlled args.

---

## 6. Telegram Layer

### 6.1 client.py

**Purpose:** TelegramClientManager(config): initialize() creates Telethon client, connects, authenticates (send_code_request, sign_in, 2FA); disconnect(). _get_user_input runs input() in a daemon thread and awaits completion with asyncio.sleep(0.1).

**Findings:** Session path under data/; no circuit breaker around connect or get_me. Auth loop is blocking on user input; acceptable for interactive startup.

### 6.2 utils.py

**Purpose:** TelegramUtils: fetch_all_private_chats, fetch_user_groups (with admin/manage topics filter). Used by cache and CLI.

**Findings:** Depends on Telethon client; no retry in this layer (callers may retry).

### 6.3 user_verifier.py

**Purpose:** TelegramUserVerifier(client): verify_user_by_identifier(identifier) tries int ID, then username, then search by name; raises TelegramError on FloodWait/RPC; returns formatted user dict or None.

**Findings:** Handles FloodWaitError and maps to TelegramError; good for auth flow.

### 6.4 messages.py

**Purpose:** Message formatting helpers for Telegram. Used by handlers.

**Findings:** No external calls; formatting only.

### 6.5 commands/self_commands.py

**Purpose:** handle_help_command, handle_auth_command, handle_status_command, handle_group_command. Large (940 lines); implements /help, /auth list|add|remove, /status, /group list|select|topics|map. Uses settings, cache, user_verifier, config.

**Findings:** Self-commands are owner-facing or auth-user-facing. Status shows config summary; ensure no secrets in status output (masked in code). Auth add/remove persists to settings; no separate audit log.

### 6.6 handlers/base.py

**Purpose:** BaseHandler(ffmpeg_path): _normalize_text (zero-width, whitespace); _setup_ffmpeg_path (PATH and pydub converter); _restore_ffmpeg_path.

**Findings:** FFmpeg logic duplicated with EventHandlers._setup_ffmpeg_path; consider single helper in utils or base and call from both.

### 6.7 handlers/ai_handler.py

**Purpose:** handle_other_ai_commands: parses /prompt, /translate, /analyze, /tellme; validates with InputValidator; rate limit (get_ai_rate_limiter); uses analyze_queue for analyze/prompt/tellme; calls AIProcessor; uses get_metrics_collector and TimingContext; splits long replies; build_response_parts for footer/header.

**Findings:** Rate limiter and analyze_queue used; metrics recorded. No circuit breaker around AIProcessor calls. Validation and sanitization at handler level; good.

### 6.8 handlers/image_handler.py

**Purpose:** /image=flux|sdxl=prompt; validates model and prompt; prompt_enhancer; image_queue; ImageGenerator; sends image and caption; metrics.

**Findings:** Queue position communicated to user; prompt enhancement can mutate Config (see prompt_enhancer). No circuit breaker for image worker HTTP calls.

### 6.9 handlers/tts_handler.py, stt_handler.py

**Purpose:** TTS: /tts text or reply; TTS queue; FFmpeg for conversion. STT: reply to voice; download; STT + AI summary; task_manager.create_task for async processing.

**Findings:** STT uses task_manager; TTS uses queue. FFmpeg path from BaseHandler/EventHandlers.

### 6.10 handlers/categorization_handler.py

**Purpose:** Handles reply-with-command for categorization; command_to_topic map (topic_id -> list of commands or legacy command -> topic_id); forwards message to target group/topic via ForwardMessagesRequest.

**Findings:** Supports both new format (topic_id: [commands]) and legacy (command: topic_id). selected_target_group from cli_state_ref; handles dict or old int format.

### 6.11 event_handlers.py

**Purpose:** EventHandlers(ai_processor, stt_processor, tts_processor, ffmpeg_path): process_command_logic dispatches to self-commands, /stt, /tts, /image=, _ai_handler.handle_other_ai_commands, _categorization_handler.handle_categorization_commands. _handle_stt_command creates task via task_manager. categorization_reply_handler_owner and authorized_user_command_handler delegate to CategorizationHandler.

**Findings:** process_command_logic is the single entry for command handling; clear delegation. SimpleEvent shim for self-commands (edit only); sufficient.

### 6.12 connection_health.py

**Purpose:** ConnectionHealthMonitor(client_manager): start_monitoring() runs _monitoring_loop (heartbeat get_me every 120s); on failure exponential backoff reconnect; after PROXY_RESTART_THRESHOLD failures can restart proxy (subprocess). stop_monitoring() cancels task.

**Findings:** Reconnect and proxy restart are production-oriented. Logs WARNING/CRITICAL at failure thresholds.

---

## 7. CLI Layer

### 7.1 state.py

**Purpose:** CLIState(config): selected_target_group (raw + normalized via normalize_selected_group); active_command_to_topic_map (setter normalizes via normalize_command_mappings); directly_authorized_pvs; is_monitoring_active; settings_saved_on_cli_exit; registered_handler_info. to_settings_dict() for persistence.

**Findings:** selected_target_group getter imports normalize_selected_group from ..cli.utils (lazy). Normalization is in cli.utils; used by core.settings and cli.state. Moving normalization to core or shared util would remove core→cli dependency.

### 7.2 utils.py

**Purpose:** Shared client globals (set_shared_client, get_shared_client, clear_shared_client); display_* (banner, error, success, warning, info); get_telegram_client (shared or new, with lock check via psutil); get_cache_manager, get_settings_manager; format_pv_table, format_group_table; normalize_selected_group, normalize_command_mappings. Used by main, handler, commands, menu_handlers, and core.settings.

**Findings:** get_telegram_client uses psutil.pid_exists(pid) if lock file exists; optional dependency psutil (ImportError handled). normalize_command_mappings and normalize_selected_group are the functions imported by core.settings and cli.state; centralizing them would fix the layer violation.

### 7.3 main.py (cli)

**Purpose:** Click group "sakaibot"; commands group, config, monitor, auth; main entry runs async main() and passes client to interactive menu. Banner and env setup.

**Findings:** Entry point is clear; async main() is invoked from Click callback.

### 7.4 handler.py

**Purpose:** CLIHandler(cache_manager, telegram_utils, settings_manager, event_handlers): display_main_menu_loop(client) shows menu, handles options (monitor, group, exit); loads/saves settings on exit; registers Telegram handlers when starting monitor; passes cli_state to event handlers.

**Findings:** Handler info (owner_handler, owner_filter, auth_handler, auth_filters) stored for graceful_shutdown so main can remove handlers. Correct.

### 7.5 interactive.py

**Purpose:** start_interactive_menu(client, cli_handler); menu options; delegates to MonitorMenuHandler and GroupMenuHandler. Rich panels and input.

**Findings:** Long file; menu flow is linear. No global state beyond passed refs.

### 7.6 commands/monitor.py, auth.py, group.py, config.py

**Purpose:** Click commands for sakaibot monitor start|stop, auth list|add|remove, group list|select|topics|map, config validate. Use get_telegram_client, get_settings, SettingsManager, state, etc.

**Findings:** config validate loads config and reports; does not write. Monitor start uses shared client when available; otherwise starts new connection. Auth and group modify settings and persist via SettingsManager.

### 7.7 menu_handlers/monitor_handler.py, group_handler.py

**Purpose:** MonitorMenuHandler: start/stop monitoring; register/unregister Telegram handlers; normalize_selected_group. GroupMenuHandler: group list, select, topics, map; uses group commands and state.

**Findings:** Menu handlers call into commands and utils; state is shared via CLIHandler/cli_state.

---

## 8. Entry and Startup/Shutdown

### 8.1 main.py (src/main.py)

**Purpose:** main() sets up logging (Docker vs local), load_config(), creates SakaiBot(config), await bot.run(). SakaiBot.__init__: builds TelegramClientManager, CacheManager, SettingsManager, AIProcessor, STT/TTS processors, EventHandlers, CLIHandler, InstanceLock; sets SIGINT handler. run(): acquire instance lock (force=True), initialize client, set_shared_client, start analyze_queue cleanup, start ConnectionHealthMonitor, await cli_handler.display_main_menu_loop(client). On exit: graceful_shutdown (analyze_queue stop, health monitor stop, save settings, remove event handlers), task_manager.cancel_all(), disconnect client, clear_shared_client, release instance lock.

**Findings:**

- Signal handler: SIGINT sets _is_shutting_down and sys.exit(0). Async cleanup runs in main() except/finally (KeyboardInterrupt, Exception, finally block). So graceful_shutdown is not run from the signal handler itself; it runs when the main coroutine exits (e.g. after sys.exit(0) the process exits, so actually the at-exit path is the finally block when asyncio.run(main()) returns or when main() raises). Note: sys.exit(0) in signal handler terminates the process; the finally in main() may not run if the process exits immediately. Check: In CPython, sys.exit(0) raises SystemExit; asyncio.run() will catch it and the finally in main() may not run. So graceful_shutdown might not run on first Ctrl+C if the process exits via sys.exit in the signal handler. Recommendation: In signal handler, set flag and return; let the main loop (or a shutdown task) notice the flag and call graceful_shutdown, then exit. Or ensure that sys.exit is not used from the signal handler and instead the main loop exits normally so that finally runs.
- Second Ctrl+C: _signal_handler checks _is_shutting_down and then os._exit(1). Good for force quit.
- Graceful shutdown order: analyze_queue, health_monitor, settings save, handler removal, then in finally task_manager.cancel_all(), disconnect, clear_shared_client, instance_lock.release(). Correct order.

---

## 9. Cross-Cutting Findings

### 9.1 Patterns

- **Singleton getters:** get_settings(), get_task_manager(), get_metrics_collector(), get_ai_rate_limiter(), get_telegram_circuit_breaker(), get_ai_circuit_breaker(), get_shared_client(), get_gemini_key_manager(). All lazy-initialized.
- **Handler composition:** EventHandlers composes AIHandler, ImageHandler, TTSHandler, STTHandler, CategorizationHandler; each handler is focused. BaseHandler for shared FFmpeg/normalize.
- **Provider abstraction:** LLMProvider interface; Gemini and OpenRouter implement; AIProcessor holds primary + fallback and uses _execute_with_fallback for prompt and answer_question (but not for translate or analyze).
- **Fallback chain:** AIProcessor uses the configured primary provider and optional LLM_FALLBACK_PROVIDER for prompt, translate, analyze, tellme, and prompt enhancement flows.
- **Rate limit + key rotation:** Per-user rate limiter in handlers; API key rotation in providers (mark_key_rate_limited, mark_key_exhausted_for_day). No circuit breaker in any call path.

### 9.2 Dependency and Layering

- **Core → CLI:** settings.py imports cli.utils (normalize_command_mappings) inside load_user_settings. Violation; move normalization to core or utils.
- **CLI → core, telegram:** CLI uses Config, SettingsManager, TelegramClientManager, event_handlers. Correct.
- **Telegram → ai, utils:** Event handlers use AIProcessor, validators, rate_limiter, task_manager, metrics. Correct.

### 9.3 Config and Secrets

- **Config (Pydantic):** Single load from .env or INI; validators; properties for keys. Main source for everything except TTS key.
- **tts_config:** os.getenv for Gemini keys with TTS-specific priority. Used by TTS code. Duplicate source of truth.
- **Secrets in logs:** SensitiveDataFilter and mask_api_key used; no intentional logging of raw keys.

### 9.4 Error Handling

- Custom exceptions raised from core, ai, telegram; ErrorHandler.get_user_message maps to HTML for user. Handlers catch and send friendly messages. Consistent.
- Some paths return None or False instead of raising (e.g. edit_message_safe on "not modified"). Documented.

### 9.5 Async and Concurrency

- Event loop throughout; Telethon is async. Blocking: clean_temp_files (time.sleep), _get_user_input (thread + await). Instance lock is process-level; no cross-process async.
- TaskManager tracks tasks; cancel_all on shutdown. WeakSet iteration in cancel_all is safe (list copy first).
- PromptEnhancer mutates global Config; concurrent image enhancements can interleave provider. Fix by not mutating Config.

### 9.6 Tests

- conftest: mock_config has gemini_api_keys, max_analyze_messages, ffmpeg_path. Real Config has gemini_api_key_1..4 and property gemini_api_keys, userbot_max_analyze_messages, paths_ffmpeg_executable. Fixtures should match Config for regression safety.
- Unit tests for api_key_manager, circuit_breaker, rate_limiter, rtl_fixer, validators. No unit tests for AIProcessor or telegram handlers.
- Integration tests present (e.g. thinking); more coverage for processor fallback and one full handler flow would help.

---

## 10. Logic and Bug Risks

| Location | Risk | Severity |
| -------- | ---- | -------- |
| task_manager.py:48–52 | task.exception() called twice; second call returns None so exc_info is wrong | High |
| prompt_enhancer.py:75–76, 127–128 | Mutates get_settings().llm_provider; concurrent calls can corrupt provider | High |
| main.py: _signal_handler | sys.exit(0) in signal handler may prevent finally block from running; graceful_shutdown might not run on first Ctrl+C | Medium |
| config.py: is_ai_enabled (OpenRouter) | Uses only openrouter_api_key; ignores openrouter_api_keys | Medium |
| rate_limiter.py | cleanup_old_entries() never called; unbounded growth of _buckets | Low |
| KeyState.is_available | Mutates exhausted_until; side effect in predicate | Low (documented) |
| helpers.py: clean_temp_files | time.sleep(0.1) in async context; blocks event loop briefly | Low |
| circuit_breaker.py | get_ai_circuit_breaker and get_telegram_circuit_breaker never used | High (missing protection) |

---

## 11. Recommendations

### High priority

1. **Use circuit breakers:** Wrap all Gemini/OpenRouter API calls (in provider methods or AIProcessor) with get_ai_circuit_breaker().call(...). Wrap Telegram send_message/get_me (or client methods) with get_telegram_circuit_breaker().call(...). Add tests that verify circuit opens after N failures.
2. **Stop mutating global Config in PromptEnhancer:** Pass a temporary provider context into AIProcessor for the enhancement call, or add execute_prompt_for_enhancement(provider_hint="openrouter") that does not change global llm_provider. Ensure concurrent image enhancements cannot flip provider.
3. **Fix TaskManager._on_task_done:** Store exception once: `exc = task.exception()`; then use `if exc:` and `exc_info=exc` (or log exc with logger.exception in the branch where exc is not None).
4. **Fix core → cli dependency:** Move normalize_command_mappings and normalize_selected_group to core (e.g. core.settings_helpers or core.normalize) or to utils. Have SettingsManager and CLIState import from there. Remove cli import from core.
5. **Unify Gemini key source for TTS:** Either have TTS use Config (e.g. first key from config.gemini_api_keys or a dedicated TTS key from Config) or document that tts_config is the only source for TTS and keep it in sync with env. Prefer Config for single source of truth.

### Medium priority

1. **Config.is_ai_enabled for OpenRouter:** Check `len(self.openrouter_api_keys) > 0` in addition to (or instead of) legacy openrouter_api_key so that numbered keys alone enable AI.
2. **Align test fixtures with Config:** In conftest, use the same field names and types as Config (userbot_max_analyze_messages, paths_ffmpeg_executable, and gemini_api_keys as property or list built from gemini_api_key_1..4). Add a test that loads real Config from a minimal env and asserts shape.
3. **Signal handling and graceful shutdown:** Ensure first Ctrl+C always runs graceful_shutdown. Option: in signal handler, set a flag and schedule asyncio.create_task(shutdown()) or stop the main loop so that finally block runs; avoid sys.exit(0) in handler so that main() can exit normally and finally runs.
4. **Call rate_limiter.cleanup_old_entries:** From the same periodic task that runs analyze_queue cleanup, or a timer every N minutes, call get_ai_rate_limiter().cleanup_old_entries() to avoid unbounded bucket growth.
5. **Add unit tests for AIProcessor:** Test _execute_with_fallback (primary fails with key exhaustion then fallback called); test that translate and analyze do not use fallback when primary is Gemini (or add fallback and test). Add one handler test (e.g. prompt command with mocked processor).

### Low priority

1. **Deduplicate FFmpeg path setup:** Extract one function (e.g. in helpers or base) that takes ffmpeg_path and returns (path_modified, original_path); use it from BaseHandler and EventHandlers.
2. **Split very large files:** When touching prompts.py, gemini.py, or ai_handler.py, consider splitting by domain (prompts by feature, provider by method group, handler by command).
3. **Document circuit breaker usage:** In ARCHITECTURE.md, state that circuit breakers exist but are not yet wired, and add a short "Resilience" section after wiring them.
4. **Metrics export:** If production dashboards are needed, add a Prometheus HTTP endpoint or push to existing metrics backend and document key metrics (request count, latency, error rate, circuit state, key rotation events).

---

## 12. Appendix

### A. Glossary

- **PV:** Private chat (Telegram).
- **RPD:** Requests per day (Gemini quota).
- **Pro/Flash:** Gemini model tiers; Pro for complex tasks, Flash for simple; separate quotas.
- **cli_state_ref:** Dict reference passed to event handlers for selected_target_group, active_command_to_topic_map, etc.; backed by CLIState.

### B. Dependency Snippets (Layer Violations)

- `core/settings.py` → `from ..cli.utils import normalize_command_mappings` (inside load_user_settings).
- `cli/state.py` → `from ..cli.utils import normalize_selected_group` (inside property getter).
- PromptEnhancer → `config.llm_provider = "openrouter"` / `"gemini"` (get_settings() global).

### C. Files That Import Circuit Breakers

- Only `src/utils/__init__.py` re-exports get_telegram_circuit_breaker and get_ai_circuit_breaker. No other file in src/ imports or calls them.

---

*End of comprehensive review.*
