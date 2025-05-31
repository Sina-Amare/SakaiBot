SakaiBot 🤖

SakaiBot is an advanced and intelligent Telegram userbot developed to provide a suite of powerful tools for message management, conversation analysis, AI interaction, and task automation within Telegram.

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
Advanced Private Chat (PV) and Group Management:

Caching and retrieval of private chat lists and groups.

Search through PVs by name, username, or ID.

Set a default PV context for text analysis commands.

Intelligent Message Categorization:

Ability to set a target group (regular or forum) for sending categorized messages.

Map custom commands to specific topics in forum groups or to the main group chat.

AI-Powered Processing and Analysis:

Custom Prompt Execution: Send prompts directly to Large Language Models (LLMs) via the OpenRouter API.

Text Translation: Translate text into various languages, including Persian phonetic pronunciation (using LLM).

Conversation Analysis: Generate comprehensive and structured analytical reports of chat histories in Persian.

Q&A from Chat History: Get intelligent answers to questions based on the content of previous messages.

Speech-to-Text (STT): Convert voice messages to text using Google Web Speech API (with extensibility for other services).

Comprehensive Command-Line Interface (CLI):

Interactive menu for managing all bot settings and functionalities.

Manage authorized users for using bot commands.

Event Monitoring and Control:

Monitor outgoing messages from the bot owner and incoming messages from authorized users for command execution.

"Confirmation flow" for securely executing commands suggested by others.

Persistent Settings and Cache Management:

Automatic saving and loading of user-specific settings and cache data.

Technology Stack 🛠️
Programming Language: Python 3.10+

Core Telegram Library: Telethon

Artificial Intelligence:

Access to various models via OpenRouter API

SpeechRecognition library for STT (with Google Web Speech API)

OpenAI Python library (for interacting with OpenRouter, which has an OpenAI-compatible API)

Audio Processing: Pydub (for audio format conversion)

Configuration Management: configparser

Date & Time Handling: pytz, datetime

Setup and Installation 🚀
Prerequisites
Python: Version 3.10 or higher. Download from the official Python website.

FFmpeg: Required by pydub for audio processing (essential for the STT feature). FFmpeg must be installed on your system and accessible via the system's PATH, or its path must be specified in the config.ini file. Installation guides can be found on the official FFmpeg website.

Telegram Account: To obtain api_id and api_hash.

Installation Steps
Clone the Repository:

git clone [YOUR_GITHUB_REPOSITORY_URL]
cd SakaiBot

Create and Activate a Virtual Environment (Highly Recommended):

python -m venv venv

# On Windows

venv\Scripts\activate

# On macOS/Linux

source venv/bin/activate

Install Required Libraries:
First, you need to create a requirements.txt file. In your activated virtual environment, run the following command to save the list of currently installed packages:

pip freeze > requirements.txt

Note: Ensure that only the project's core libraries are included in this file, not all libraries from your global Python environment. If you've just created the virtual environment and installed only the project dependencies, this command will work correctly.

Once requirements.txt is created, others (or yourself in a new environment) can install all dependencies with:

pip install -r requirements.txt

Configuration
Create a copy of config.ini.example

Fill in config.ini with your details:

[Telegram]:

api_id and api_hash: Obtain these from my.telegram.org.

phone_number: Your Telegram phone number in international format (e.g., +1234567890).

[UserBot]:

session_name: A custom name for the Telegram session file (e.g., sakaibot_session).

max_analyze_messages: Maximum number of messages to fetch for the /analyze command.

[OpenRouter]:

api_key: Your API key from OpenRouter.

model_name: The name of the model you want to use from OpenRouter (e.g., deepseek/deepseek-chat).

[AssemblyAI] (Optional, if implemented):

api_key: Your API key from AssemblyAI.

[API_KEYS] (Optional, if ElevenLabs is implemented):

elevenlabs_api_key: Your API key from ElevenLabs.

[Paths] (Optional):

ffmpeg_executable: The full path to your ffmpeg.exe (or ffmpeg) executable (e.g., C:\ffmpeg\bin\ffmpeg.exe). This is not necessary if FFmpeg is in your system's PATH.

Usage 📖
Running the Bot
After installation and configuration, run the bot using:

python main.py

On the first run, you might be prompted to enter your phone number, the Telegram confirmation code, and your 2FA password (if enabled).

CLI Menu Options
Once the bot starts successfully, an interactive CLI menu will be displayed, allowing you to manage various aspects of the bot:

List All Cached Private Chats (PVs)

Refresh/Update PV List from Telegram (Recent Chats)

Search PVs (from cached list)

Set Default PV Context (for /analyze)

Set/Change Categorization Target Group

Manage Categorization Command Mappings

Start/Stop GLOBAL Monitoring (for categorization & AI commands)

Manage Directly Authorized PVs

Exit (Save Settings)

Core Telegram Commands (In your chat with yourself or authorized PVs)
/prompt=<your prompt text>: Sends your prompt to the OpenRouter LLM.

/translate=<target_lang>[,source_lang] <text_to_translate>: Translates text. (e.g., /translate=fa Hello there or /translate=en,auto سلام خوبی؟)

/analyze=<number_of_messages>: Analyzes the last n messages in the current chat.

/tellme=<number_of_messages>=<your_question>: Asks the bot a question based on the last n messages in the current chat.

/stt (in reply to a voice message): Converts the voice message to text and provides a summary.

/<custom_categorization_command> (in reply to a message): Forwards the replied message to the mapped group/topic.

confirm (in reply to a command message from another user that was forwarded to you): Confirms and executes that command.

Configuration Details
config.ini: Contains core settings and API keys for connecting to Telegram and external services. Never share this file in public repositories.

sakaibot_user_settings.json: Stores your user-specific settings configured via the CLI (e.g., selected PV, target group, command mappings, authorized PVs). This file is managed automatically by the bot.

pv_cache.json & group_cache.json: These files cache your private chat list and group list, respectively, for faster access and are updated automatically by the bot.

Contributing 🤝
if you have ideas for improvement or encounter any issues, feel free to open an Issue in the project's GitHub repository.

License 📄
This project is licensed under the MIT License. See the LICENSE file for details.
