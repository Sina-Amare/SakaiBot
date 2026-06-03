# Model Usage

This document maps SakaiBot commands to the model settings they use. It does
not include API keys or secrets.

## Current Local `.env` Model Settings

```env
LLM_PROVIDER=gemini
LLM_FALLBACK_PROVIDER=openrouter

GEMINI_MODEL_PRO=gemini-2.5-flash
GEMINI_MODEL_FLASH=gemini-3.1-flash-lite
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_MODEL_PRO_FALLBACK=gemini-3.1-flash-lite
GEMINI_TTS_MODEL=gemini-3.1-flash-tts-preview
GEMINI_TTS_VOICE=Orus
STT_AI_SUMMARY_ENABLED=false
GEMINI_SUMMARY_MODEL=gemini-3.1-flash-lite

OPENROUTER_MODEL_PRO=deepseek/deepseek-v4-flash:free
OPENROUTER_MODEL_FLASH=deepseek/deepseek-v4-flash:free
OPENROUTER_MODEL=deepseek/deepseek-v4-flash:free
```

## Selection Rules

`LLM_PROVIDER` decides the primary LLM provider.

`LLM_FALLBACK_PROVIDER` decides the fallback provider. Supported values are:

- `openrouter`
- `gemini`
- `none`

If unset, the legacy behavior is preserved: Gemini primary falls back to
OpenRouter; OpenRouter primary has no fallback.

Each provider now supports per-command model overrides. If an override is
unset, the provider uses its tier model:

- Complex tier: `/prompt`, `/analyze`, `/tellme`
- Simple tier: `/translate`, image prompt enhancement
- Legacy/default tier: unknown task types

## Command Mapping

| Command | Primary model with current `.env` | Override key | Fallback model with current `.env` | Fallback override key |
| --- | --- | --- | --- | --- |
| `/prompt` | `GEMINI_MODEL_PROMPT` = `gemini-2.5-flash` | `GEMINI_MODEL_PROMPT` | `OPENROUTER_MODEL_PRO` = `deepseek/deepseek-v4-flash:free` | `OPENROUTER_MODEL_PROMPT` |
| `/analyze` | `GEMINI_MODEL_ANALYZE` = `gemini-2.5-flash` | `GEMINI_MODEL_ANALYZE` | `OPENROUTER_MODEL_PRO` = `deepseek/deepseek-v4-flash:free` | `OPENROUTER_MODEL_ANALYZE` |
| `/tellme` | `GEMINI_MODEL_TELLME` = `gemini-2.5-flash` | `GEMINI_MODEL_TELLME` | `OPENROUTER_MODEL_PRO` = `deepseek/deepseek-v4-flash:free` | `OPENROUTER_MODEL_TELLME` |
| `/translate` | `GEMINI_MODEL_TRANSLATE` = `gemini-3.1-flash-lite` | `GEMINI_MODEL_TRANSLATE` | `OPENROUTER_MODEL_FLASH` = `deepseek/deepseek-v4-flash:free` | `OPENROUTER_MODEL_TRANSLATE` |
| `/image=flux=...` prompt enhancement | `GEMINI_MODEL_PROMPT_ENHANCER` = `gemini-3.1-flash-lite` | `GEMINI_MODEL_PROMPT_ENHANCER` | `OPENROUTER_MODEL_FLASH` = `deepseek/deepseek-v4-flash:free` | `OPENROUTER_MODEL_PROMPT_ENHANCER` |
| `/image=sdxl=...` prompt enhancement | `GEMINI_MODEL_PROMPT_ENHANCER` = `gemini-3.1-flash-lite` | `GEMINI_MODEL_PROMPT_ENHANCER` | `OPENROUTER_MODEL_FLASH` = `deepseek/deepseek-v4-flash:free` | `OPENROUTER_MODEL_PROMPT_ENHANCER` |
| `/tts` | `GEMINI_TTS_MODEL` = `gemini-3.1-flash-tts-preview` | `GEMINI_TTS_MODEL` or `TTS_MODEL` | None | None |
| `/stt` transcription | Google Web Speech API via `speech_recognition` | Not model-configurable | None | None |
| `/stt` optional AI summary | disabled by `STT_AI_SUMMARY_ENABLED=false`; if enabled, `GEMINI_MODEL_VOICE_SUMMARY` = `gemini-3.1-flash-lite` | `GEMINI_MODEL_VOICE_SUMMARY` or `GEMINI_SUMMARY_MODEL` | `OPENROUTER_MODEL_VOICE_SUMMARY` if configured, else OpenRouter legacy/default | `OPENROUTER_MODEL_VOICE_SUMMARY` |

## Image Generation Notes

`/image=flux=...` and `/image=sdxl=...` are not Gemini/OpenRouter image
model calls. They are command aliases routed to Cloudflare Workers:

- `FLUX_WORKER_URL`
- `SDXL_WORKER_URL`

The exact image model behind those workers is controlled by the worker
implementation, not by the bot process. The bot now exposes LLM model control
for the prompt enhancement step.

## Gemini Model Fallback

When a Gemini complex-tier request hits Pro quota, SakaiBot falls back to:

```env
GEMINI_MODEL_PRO_FALLBACK=gemini-3.1-flash-lite
```

Provider-level fallback is separate and controlled by:

```env
LLM_FALLBACK_PROVIDER=openrouter
```
