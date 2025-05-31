SakaiBot 🤖
SakaiBot is an advanced and intelligent Telegram user‑bot that equips power‑users with a rich toolbox for message management, conversation analysis, AI interaction, and task automation—all from the comfort of Telegram.

Table of Contents

Key Features
Technology Stack
Setup and Installation
Prerequisites
Installation Steps
Configuration

Usage
Running the Bot
CLI Menu Options
Core Telegram Commands
Configuration Details

Contributing
License

Key Features ✨
🔸 Advanced Private Chat (PV) & Group Management

Cache and retrieve your list of private chats and groups.
Search through PVs by name, username, or ID.
Set a default PV context for text‑analysis commands.

🔸 Intelligent Message Categorization

Choose a target \*group (regular or forum) for sending categorized messages.
Map custom commands to topics inside forum groups—or straight to the main chat.

🔸 AI‑Powered Processing & Analysis

Custom Prompt Execution – Send prompts directly to Large Language Models (LLMs) via the OpenRouter API.
Text Translation – Translate text into multiple languages \*(including Persian phonetic pronunciation) using an LLM.
Conversation Analysis – Produce comprehensive, structured Persian reports of chat histories.
Q&A from Chat History – Ask intelligent questions that are answered from previous messages.
Speech‑to‑Text (STT) – Convert Telegram voice messages to text via Google Web Speech API (pluggable for other providers).

🔸 Comprehensive Command‑Line Interface (CLI)

Interactive menu for every bot setting and function.
Manage the list of authorized users who can issue commands.

🔸 Event Monitoring & Secure Control

Monitor outgoing messages from the bot‑owner and incoming messages from authorized users.
Confirmation flow—execute commands suggested by others only after explicit approval.

🔸 Persistent Settings & Cache

Automatic save/load of user‑specific settings and cache—your preferences survive restarts.

Technology Stack 🛠️

Layer
Technology

Language
Python ≥ 3.10

Telegram API
Telethon

AI / LLMs
OpenRouter API, openai Python lib

Speech‑to‑Text
SpeechRecognition + Google Web Speech API

Audio Processing
pydub (+ FFmpeg)

Config Mgmt.
configparser

Date & Time
pytz, datetime

Setup and Installation 🚀
Prerequisites

Python ≥ 3.10 – Download
FFmpeg – Required by pydub for audio processing. Make sure ffmpeg is on your system PATH or specify its location in config.ini.
Telegram Account – Needed to obtain api_id & api_hash.

Installation Steps

Clone the repository
git clone https://github.com/<your‑username>/SakaiBot.git
cd SakaiBot

Create & activate a virtual environment
python -m venv venv

# Windows

venv\Scripts\activate

# macOS / Linux

source venv/bin/activate

Install the required libraries

Generate requirements.txt (first time only):
pip freeze > requirements.txt

Install dependencies (on any machine):
pip install -r requirements.txt

Configuration

Copy config.ini.example to config.ini (if the example exists), otherwise edit config.ini directly.

Open config.ini and fill in all sections:
[Telegram]
api_id = <YOUR_API_ID>
api_hash = <YOUR_API_HASH>
phone_number = +1234567890

[UserBot]
session_name = sakaibot_session
max_analyze_messages = 100

[OpenRouter]
api_key = <YOUR_OPENROUTER_KEY>
model_name = deepseek/deepseek-chat

; Optional providers
[AssemblyAI]
api_key = <YOUR_ASSEMBLYAI_KEY>

[API_KEYS]
elevenlabs_api_key = <YOUR_ELEVENLABS_KEY>

[Paths]
ffmpeg_executable = /usr/local/bin/ffmpeg ; or leave blank if on PATH

Usage 📖
Running the Bot
python main.py

On the first run you will be prompted for:

Your phone number
The Telegram confirmation code
Your 2‑factor password (if enabled)

CLI Menu Options
The interactive menu lets you:

List cached PVs
Refresh PV list from Telegram
Search PVs
Set default PV context
Set/Change categorization target group
Manage command mappings
Start/Stop GLOBAL monitoring
Manage authorized PVs
Exit & save settings

Core Telegram Commands

Command
Description
Example

/prompt=<text>
Send a prompt directly to the configured LLM
/prompt=Summarize the last chat

/translate=<target>[,source] <text>
Translate text. source can be auto.
/translate=fa Hello there

/analyze=<n>
Analyze the last n messages in the current chat
/analyze=250

/tellme=<n>=<question>
Ask a question answered from the last n messages
/tellme=100=What were the key topics?

/stt (reply to a voice)
Convert voice message to text
(reply to voice) /stt

/yourMappedCmd (reply)
Forward message to the mapped group/topic
—

confirm (reply to forwarded cmd)
Confirm and execute somebody else’s command
—

Tip: Use these commands only in chats with yourself or other authorized PVs.

Configuration Details

File
Purpose

config.ini
Never commit this! Holds API keys & core settings.

sakaibot_user_settings.json
Your CLI‑configured preferences. Managed automatically.

pv_cache.json / group_cache.json
Cached lists for speedy look‑ups. Auto‑managed.

Contributing 🤝
Pull Requests, feature ideas, and bug reports are all warmly welcomed. Please open an Issue first to discuss major changes.

Fork the project
Create your feature branch: git checkout -b feat/amazing-feature
Commit your changes: git commit -m "feat: add amazing feature"
Push to the branch: git push origin feat/amazing-feature
Open a Pull Request

License 📄
SakaiBot is released under the MIT License. See the LICENSE file for full details.
