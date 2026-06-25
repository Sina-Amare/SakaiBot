<div align="center">

# 🟢 Aigram

### Telegram, but AI‑powered.

A **self‑hosted, installable AI messenger** for your Telegram account — read and **send** messages with inline media, and call the AI right inside any chat. Your account, your keys, your server. _(formerly SakaiBot)_

<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
<img src="https://img.shields.io/badge/PWA-installable-5a0fc8?logo=pwa&logoColor=white" alt="PWA">
<img src="https://img.shields.io/badge/Telegram-MTProto-26A5E4?logo=telegram&logoColor=white" alt="Telegram">
<img src="https://img.shields.io/badge/AI-Gemini%20%7C%20OpenRouter-2dd4bf" alt="AI">

<br/>

<img src="docs/screenshots/chat-dark.png" alt="Aigram — a real AI-powered Telegram messenger" width="880">

</div>

---

Aigram turns your Telegram account into a slick, glassy web app you can install on your phone. It feels like a real messenger — grouped bubbles, inline photos/stickers/voice, replies, date separators, live updates, dark + light — and layers an **AI co‑pilot** on top: analyze a chat, ask questions about its history, translate, generate images, do TTS/STT, or prompt anything. AI results appear **in the panel**, so you decide what (if anything) to send.

> [!NOTE]
> The screenshots below use an **invented demo account** (fake contacts and messages) — no real data.

## 📸 Screenshots

<table>
<tr>
<td width="50%" align="center">
  <img src="docs/screenshots/chat-light.png" alt="Light theme" width="420"><br/>
  <sub><b>Premium light theme</b> — same chat, soft and bright</sub>
</td>
<td width="50%" align="center">
  <img src="docs/screenshots/ai-result.png" alt="AI analyze result" width="420"><br/>
  <sub><b>AI in the chat</b> — analyze runs, result lands in the panel</sub>
</td>
</tr>
<tr>
<td width="50%" align="center">
  <img src="docs/screenshots/ai-sheet.png" alt="AI command sheet" width="420"><br/>
  <sub><b>✨ AI sheet</b> — analyze, ask, prompt, translate, image, TTS</sub>
</td>
<td width="50%" align="center">
  <img src="docs/screenshots/keys.png" alt="Keys and providers" width="420"><br/>
  <sub><b>Keys &amp; providers</b> — add, test, and hot‑swap API keys</sub>
</td>
</tr>
<tr>
<td colspan="2" align="center">
  <img src="docs/screenshots/chat-mobile.png" alt="Mobile PWA" width="260"><br/>
  <sub><b>Installable PWA</b> — the full messenger on your phone</sub>
</td>
</tr>
</table>

## ✨ What it does

<table>
<tr>
<td width="50%">

**💬 A real messenger**

- Read **and send** messages (text + replies)
- Inline media: photos, stickers, video, voice, files
- Grouped bubbles, date separators, relative time
- Last‑message previews in the sidebar
- Live updates, smooth + soft, **dark + light**

</td>
<td width="50%">

**🧠 AI in every chat**

- **Analyze** a chat • **Ask** about its history
- **Prompt** anything (deep‑thinking + web search)
- **Translate** with Persian phonetics
- **Image** generation (Flux / SDXL)
- **TTS / STT** (voice ↔ text, with summaries)

</td>
</tr>
<tr>
<td width="50%">

**🔑 Everything in the panel**

- Add / test / remove provider keys, hot‑reload
- Switch primary/fallback (Gemini ⇄ OpenRouter)
- Categorization & routing (group → topic map)
- Authorized users, model matrix, status, help

</td>
<td width="50%">

**🏠 Self‑host, private, free**

- Your credentials, your session — no central party
- Installable **PWA** + mobile responsive
- Multi‑key rotation, FloodWait‑safe throttling
- Runs on a €1.49 VPS, a home device, or Termux

</td>
</tr>
</table>

## ⚡ Quick start

```bash
git clone <your-fork-of-aigram> aigram && cd aigram
docker compose up -d
docker compose exec sakaibot sakaibot setup    # in-panel wizard: Telegram login + LLM keys
docker compose exec sakaibot sakaibot panel    # open the printed http://127.0.0.1:8765/?token=…
```

<details>
<summary><strong>Or run it locally without Docker</strong></summary>

```bash
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -e .
sakaibot setup     # first-run wizard writes .env and logs you in
sakaibot panel     # premium dashboard + the bot stays live in chats
```

**Prerequisites:** Python 3.10+, [FFmpeg](https://ffmpeg.org/download.html) (audio), and Telegram API creds from [my.telegram.org](https://my.telegram.org).

</details>

Open the printed `http://127.0.0.1:8765/?token=…`, pick a chat, and you're in. Install it on your phone over a free **Cloudflare Tunnel** (HTTPS → Add to Home Screen).

> **Deploy anywhere** — cheap crypto VPS (no credit card), home device / Termux / Raspberry Pi, Cloudflare Tunnel, and an Iran‑friendly path are all in **[DEPLOY.md](DEPLOY.md)**.

## 🤖 AI commands

Available from the **✨ AI** button inside any chat (results render in the panel), or as `/commands` in Telegram itself.

| Command | What it does | Flags |
| --- | --- | --- |
| `/prompt=<text>` | Ask the AI anything | `=think` (deep reasoning), `=web` (search) |
| `/translate=<lang>=<text>` | Translate, with Persian phonetics | auto‑detects source |
| `/analyze=<N>` | Analyze the last N messages | `=fun`, `=romance`, `=general`, `=think` |
| `/tellme=<N>=<question>` | Answer a question from chat history | `=think`, `=web` |
| `/image=flux\|sdxl=<prompt>` | Generate an image (prompt auto‑enhanced) | rendered inline |
| `/tts=<text>` | Text‑to‑Speech (Gemini voices) | plays inline |
| `/stt` (reply to a voice) | Transcribe + summarize a voice note | — |

## 🧠 Models & keys

Aigram runs on **Google Gemini** (primary) with **OpenRouter** as fallback, and rotates up to 4 keys per provider. Defaults are pinned to the **free‑tier‑friendly** `gemini-2.5-flash` / `gemini-2.5-flash-lite` (the newest 3.x Flash models have tiny free quotas that rate‑limit instantly). Add and **test** keys live in the **Keys & Providers** panel — no file editing, no restart.

```env
# Minimum to start (or just run `sakaibot setup`):
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+1234567890
LLM_PROVIDER=gemini
GEMINI_API_KEY_1=your_gemini_key
OPENROUTER_API_KEY_1=sk-or-v1-your-key   # fallback + image prompt enhancement
```

<details>
<summary><strong>More configuration (key rotation, image workers, FFmpeg, models)</strong></summary>

```env
# Up to 4 keys per provider — automatic rotation on rate limits
GEMINI_API_KEY_1=key1
GEMINI_API_KEY_2=key2
OPENROUTER_API_KEY_1=key1

# Model pins (free-tier friendly defaults shown)
GEMINI_MODEL_PRO=gemini-2.5-flash          # analyze, tellme, prompt
GEMINI_MODEL_FLASH=gemini-2.5-flash-lite   # translate, enhancement, summaries

# Image generation (Cloudflare Workers backend)
FLUX_WORKER_URL=https://your-flux-worker.workers.dev
SDXL_WORKER_URL=https://your-sdxl-worker.workers.dev
SDXL_API_KEY=your_bearer_token

# FFmpeg (audio) — auto-detected if on PATH
PATHS_FFMPEG_EXECUTABLE=/usr/bin/ffmpeg    # Windows: C:\ffmpeg\bin\ffmpeg.exe
```

</details>

## 🏗️ Architecture

A FastAPI + vanilla‑JS PWA (no build step) runs on the **same asyncio loop** as the Telethon client, sharing one MTProto session. The AI core *returns* values; the panel is a clean consumer that renders them — and a single audited bridge (`messenger_service.py`) is the only place that ever writes to Telegram.

```
src/
├── panel/                  # FastAPI app + vanilla-JS/PWA control panel
│   ├── app.py              # thin routes -> services
│   ├── services/           # dialogs, entity (history/media), messenger (send),
│   │                       #   commands (AI), keys, groups, status, auth
│   ├── throttle.py         # ban-safety: pacing + FloodWait handling
│   └── static/             # index.html, app.css, app.js, sw.js, manifest, icons
├── ai/                     # LLM layer: providers (Gemini/OpenRouter), TTS, STT,
│   │                       #   image gen, prompt enhancement, key rotation
├── telegram/               # Telethon integration, handlers, self-commands
├── cli/                    # Click CLI: `sakaibot panel` / `setup` / `monitor`
└── core/                   # config (Pydantic), constants, exceptions
```

| Pattern | Where | Purpose |
| --- | --- | --- |
| Shared MTProto session | `cli/utils.get_telegram_client` | one client, never a second |
| API key rotation | `ai/api_key_manager.py` | failover on rate limits / quota |
| Provider fallback | `ai/processor.py` | Gemini → OpenRouter |
| Ban‑safety throttle | `panel/throttle.py` | pacing + FloodWait, one write bridge |
| Hot reload | `panel/services/keys_service.py` | swap keys/models with no restart |

## 🛠️ Development

```bash
pip install -e ".[dev]"
ruff check .                 # lint baseline
pytest                       # default suite (live tests skipped)
pytest tests/panel -q        # panel/web tests
SAKAIBOT_RUN_LIVE_TESTS=1 pytest -m live   # real Telegram + real LLM (needs creds)
```

Live E2E uses Playwright (real Chromium) and exercises the full chat — send to **Saved Messages** only, never a third party. Regenerate the README screenshots from fake data anytime; they never contain real chats.

## ⚠️ Disclaimer

Aigram logs in as a **real Telegram account** (a userbot). That's against Telegram's ToS and can risk a ban — use a stable IP, avoid mass/automated sending, and keep your access token secret. You run your own instance; nobody else holds your session. See [DEPLOY.md](DEPLOY.md) for the safety notes.

## 📄 License

MIT — see [LICENSE](LICENSE). Copyright (c) 2025–2026 Sina Amare.

## 🙏 Built with

[Telethon](https://github.com/LonamiWebs/Telethon) · [Google Gemini](https://ai.google.dev/) · [OpenRouter](https://openrouter.ai/) · [FastAPI](https://fastapi.tiangolo.com/) · [Click](https://click.palletsprojects.com/) · [Pydantic](https://pydantic.dev/)

<div align="center"><sub>Made with 💚 by <a href="https://github.com/Sina-Amare">Sina Amare</a></sub></div>
