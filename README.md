# SakaiBot 🤖

_SakaiBot is an advanced and intelligent Telegram **user‑bot** that equips power‑users with a rich toolbox for message management, conversation analysis, AI interaction, and task automation—all from the comfort of Telegram._

---

## Key Features ✨

### 🔸 Advanced Private Chat _(PV)_ & Group Management

- **Cache** and **retrieve** your list of private chats and groups.
- **Search** through PVs by _name_, _username_, or _ID_.
- **Set** a _default_ PV context for text‑analysis commands.

### 🔸 Intelligent Message Categorisation

- **Choose** a _target_ group (regular or forum) for sending categorised messages.
- **Map** custom commands to **topics** inside forum groups—or straight to the main chat.

### 🔸 AI‑Powered Processing & Analysis

- **Custom Prompt Execution** – Send prompts directly to _Large Language Models_ (LLMs) via the **OpenRouter** API.
- **Text Translation** – Translate text into multiple languages (including _Persian phonetic pronunciation_) using an LLM.
- **Conversation Analysis** – Produce comprehensive, structured Persian reports of chat histories.
- **Q\&A from Chat History** – Ask intelligent questions that are answered from previous messages.
- **Speech‑to‑Text (STT)** – Convert Telegram voice messages to text via **Google Web Speech API** (_pluggable_ for other providers).

### 🔸 Comprehensive Command‑Line Interface _(CLI)_

- Interactive **menu** for every bot setting and function.
- Manage the list of **authorised users** who can issue commands.

### 🔸 Event Monitoring & Secure Control

- **Monitor** outgoing messages from the bot‑owner and incoming messages from authorised users.
- _Confirmation flow_—execute commands suggested by others only after explicit approval.

### 🔸 Persistent Settings & Cache

- Automatic **save/load** of user‑specific settings and cache—your preferences survive restarts.

---

## Technology Stack 🛠️

| Layer                | Technology                                            |
| -------------------- | ----------------------------------------------------- |
| **Language**         | Python ≥ 3.10                                         |
| **Telegram API**     | [Telethon](https://github.com/LonamiWebs/Telethon)    |
| **AI / LLMs**        | OpenRouter API, `openai` Python lib                   |
| **Speech‑to‑Text**   | `SpeechRecognition` + Google Web Speech API           |
| **Audio Processing** | [`pydub`](https://github.com/jiaaro/pydub) (+ FFmpeg) |
| **Config Mgmt.**     | `configparser`                                        |
| **Date & Time**      | `pytz`, `datetime`                                    |

---

## Setup and Installation 🚀

### Prerequisites

- **Python** ≥ 3.10 – [Download](https://www.python.org/downloads/)
- **FFmpeg** – Required by _pydub_ for audio processing. Make sure `ffmpeg` is on your system `PATH` _or_ specify its location in `config.ini`.
- **Telegram Account** – Needed to obtain `api_id` & `api_hash`.

### Installation Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/Sina-Amare/SakaiBot
   cd SakaiBot
   ```

2. **Create & activate a virtual environment**

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install the required libraries**

   1. _Generate_ `requirements.txt` (first time only):

      ```bash
      pip freeze > requirements.txt
      ```

   2. _Install_ dependencies (on any machine):

      ```bash
      pip install -r requirements.txt
      ```

### Configuration

1. Copy `config.ini.example` to `config.ini` _(if the example exists)_, otherwise edit `config.ini` directly.
2. Open `config.ini` and fill in **all** sections:

   ```ini
   [Telegram]
   api_id       = <YOUR_API_ID>
   api_hash     = <YOUR_API_HASH>
   phone_number = +1234567890

   [UserBot]
   session_name          = sakaibot_session
   max_analyze_messages  = 100

   [OpenRouter]
   api_key    = <YOUR_OPENROUTER_KEY>
   model_name = deepseek/deepseek-chat

   ; Optional providers
   [AssemblyAI]
   api_key = <YOUR_ASSEMBLYAI_KEY>

   [API_KEYS]
   elevenlabs_api_key = <YOUR_ELEVENLABS_KEY>

   [Paths]
   ffmpeg_executable = /usr/local/bin/ffmpeg  ; or leave blank if on PATH
   ```

---

## Usage 📖

### Running the Bot

```bash
python main.py
```

On the _first_ run you will be prompted for:

1. Your **phone number**
2. The **Telegram confirmation code**
3. Your **2‑factor password** (if enabled)

### CLI Menu Options

The interactive menu lets you:

1. **List** cached PVs
2. **Refresh** PV list from Telegram
3. **Search** PVs
4. **Set** default PV context
5. **Set/Change** categorisation target group
6. **Manage** command mappings
7. **Start/Stop** _GLOBAL_ monitoring
8. **Manage** authorised PVs
9. **Exit** & save settings

### Core Telegram Commands

| Command                               | Description                                        | Example                                 |
| ------------------------------------- | -------------------------------------------------- | --------------------------------------- |
| `/prompt=<text>`                      | Send a prompt directly to the configured LLM       | `/prompt=Summarise the last chat`       |
| `/translate=<target>[,source] <text>` | Translate text. `source` can be `auto`.            | `/translate=fa Hello there`             |
| `/analyze=<n>`                        | Analyse the last _n_ messages in the current chat  | `/analyze=250`                          |
| `/tellme=<n>=<question>`              | Ask a question answered from the last _n_ messages | `/tellme=100=What were the key topics?` |
| `/stt` _(reply to a voice)_           | Convert voice message to text                      | _(reply to voice)_ `/stt`               |
| `/yourMappedCmd` _(reply)_            | Forward message to the mapped group/topic          | —                                       |
| `confirm` _(reply to forwarded cmd)_  | Confirm and execute somebody else’s command        | —                                       |

> **Tip:** Use these commands only in chats with _yourself_ or other **authorised PVs**.

### Configuration Details

| File                                 | Purpose                                                 |
| ------------------------------------ | ------------------------------------------------------- |
| `config.ini`                         | **Never** commit this! Holds API keys & core settings.  |
| `sakaibot_user_settings.json`        | Your CLI‑configured preferences. Managed automatically. |
| `pv_cache.json` / `group_cache.json` | Cached lists for speedy look‑ups. Auto‑managed.         |

---

## Contributing 🤝

Pull Requests, feature ideas, and bug reports are all warmly welcomed. Please open an **Issue** first to discuss major changes.

1. **Fork** the project
2. **Create** your feature branch: `git checkout -b feat/amazing-feature`
3. **Commit** your changes: `git commit -m "feat: add amazing feature"`
4. **Push** to the branch: `git push origin feat/amazing-feature`
5. **Open** a Pull Request

---

## License 📄

SakaiBot is released under the **MIT License**. See the [LICENSE](LICENSE) file for full details.
