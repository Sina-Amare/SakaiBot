# SakaiBot 🤖

Advanced Telegram userbot with AI capabilities, message automation, and powerful command-line interface.

## ✨ Features

- **🤖 AI Integration** - Multiple LLM providers (OpenRouter, Google Gemini)
- **💬 Smart Commands** - Custom prompts, translations, conversation analysis
- **🎤 Voice Processing** - Speech-to-text and text-to-speech (including high-quality Persian TTS)
- **📨 Message Management** - Automated categorization and forwarding
- **🔐 Security** - Multi-level authorization and confirmation flows
- **🎨 Modern CLI** - Rich terminal interface with colors and progress indicators

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Telegram API credentials ([obtain here](https://my.telegram.org))
- AI provider API key (OpenRouter or Google Gemini)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/SakaiBot
cd SakaiBot

# Create virtual environment
python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure bot
cp .env.example .env
# Edit .env with your credentials

# Run the bot
python sakaibot.py
```

## 📖 Basic Usage

### Check Status

```bash
sakaibot status
```

### Manage Private Chats

```bash
sakaibot pv list              # List private chats
sakaibot pv search "john"     # Search contacts
sakaibot pv refresh           # Update from Telegram
```

### AI Commands

```bash
sakaibot ai test              # Test AI configuration
sakaibot ai translate "Hello" fa  # Translate text
sakaibot ai prompt "Explain Python"  # Custom prompt
```

### Text-to-Speech (TTS)

The `/tts` command converts text to speech using Google Gemini TTS. It supports automatic language detection and high-quality neural voices.

**Persian TTS:**

To convert Persian text to speech, use the `/tts` command:

```
/tts سلام، حال شما چطوره؟
```

**Other Languages:**

The TTS automatically detects the language. You can also specify a voice:

```
/tts voice=Kore Hello, how are you?
```

Available voices: Kore, Puck, Fenrir, Zephyr, and more. See [Google Gemini TTS documentation](https://ai.google.dev/gemini-api/docs/speech-generation) for the full list.

### Start Monitoring

```bash
sakaibot monitor start        # Start processing commands
```

## 📚 Documentation

Complete documentation is available in the `docs/` directory:

- [**Architecture**](docs/ARCHITECTURE.md) - Technical design and structure
- [**API**](docs/API.md) - API reference and usage
- [**Configuration**](docs/CONFIGURATION.md) - Setup and configuration guide
- [**CLI Guide**](docs/CLI.md) - Complete command reference
- [**Features**](docs/FEATURES.md) - Detailed feature documentation
- [**Persian Features**](docs/PERSIAN_FEATURES.md) - Persian language support (فارسی)
- [**Testing**](docs/TESTING.md) - Testing framework and procedures
- [**Usage Guide**](docs/USAGE.md) - End-user usage instructions
- [**FAQ**](docs/FAQ.md) - Frequently asked questions
- [**Contributing**](docs/CONTRIBUTING.md) - Guidelines for contributors

## 🔧 Configuration

Create a `.env` file with your credentials:

```env
# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+1234567890

# AI Provider (choose one)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_API_KEY_TTS=your_gemini_tts_key  # Optional: TTS-specific key
# or
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
```

See [.env.example](.env.example) for full configuration options.

## 🏗️ Project Structure

```
SakaiBot/
├── src/              # Source code
│   ├── ai/          # AI providers and processors
│   ├── cli/         # Command-line interface
│   ├── core/        # Core functionality
│   ├── telegram/    # Telegram integration
│   └── utils/       # Utilities
├── docs/            # Documentation
├── tests/           # Test suite
├── data/            # User data (sessions, settings)
├── cache/           # Cache files
└── logs/            # Application logs
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](docs/CONTRIBUTING.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [OpenRouter](https://openrouter.ai/) - LLM API gateway
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI model

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/SakaiBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/SakaiBot/discussions)
- **Email**: your.email@example.com

---

Made with ❤️ by [Sina Amare](https://github.com/yourusername)
