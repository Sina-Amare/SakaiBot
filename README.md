# 🤖 SakaiBot v2.0

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Advanced Telegram Userbot with AI-Powered Capabilities

SakaiBot is a sophisticated Telegram userbot that leverages AI to provide intelligent message processing, speech-to-text conversion, comprehensive chat analysis, and automated message categorization.

## ✨ Features

### 🎯 Core Capabilities
- **AI-Powered Processing**: Integration with OpenRouter API for advanced LLM interactions
- **Speech Recognition**: Convert voice messages to text using multiple STT providers
- **Text-to-Speech**: Generate natural voice responses with Edge TTS
- **Chat Analysis**: Comprehensive analysis of conversation history with AI insights
- **Smart Categorization**: Automatic message routing to appropriate groups/topics

### 🛠️ Technical Features
- **Modern Architecture**: Clean, modular design following SOLID principles
- **Type Safety**: Comprehensive type hints and Pydantic validation
- **Async First**: Built on asyncio for optimal performance
- **Robust Error Handling**: Custom exception hierarchy with detailed context
- **Extensive Logging**: Structured logging with rotation and multiple outputs
- **Configuration Management**: Environment-based config with validation
- **CLI Interface**: Rich terminal UI with interactive menus

## 📋 Requirements

- Python 3.10 or higher
- FFmpeg (for audio processing)
- Telegram API credentials
- OpenRouter API key

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
make install  # Or: pip install -r requirements.txt
```

### 4. Configure the Bot
```bash
cp config.ini.example data/config.ini
# Edit data/config.ini with your credentials
```

Or use environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 5. Run the Bot
```bash
make run  # Or: python -m src.main
```

## 📁 Project Structure

```
SakaiBot/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   │   ├── config.py      # Configuration management
│   │   ├── constants.py   # Application constants
│   │   └── exceptions.py  # Custom exceptions
│   ├── telegram/          # Telegram integration
│   │   ├── client.py      # Client management
│   │   ├── handlers.py    # Event handlers
│   │   └── utils.py       # Utility functions
│   ├── ai/                # AI/LLM modules
│   │   ├── processor.py   # LLM interactions
│   │   ├── stt.py        # Speech-to-Text
│   │   └── tts.py        # Text-to-Speech
│   ├── cli/              # CLI interface
│   │   └── interface.py  # Terminal UI
│   └── utils/            # Utilities
│       └── logging.py    # Logging configuration
├── tests/                # Test suite
├── data/                 # Data files
├── cache/               # Cache directory
├── logs/                # Log files
└── docs/                # Documentation
```

## 🎮 Commands

### Bot Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/prompt=<text>` | Send prompt to AI | `/prompt=Explain quantum computing` |
| `/translate=<lang> <text>` | Translate text | `/translate=fa Hello world` |
| `/analyze=<n>` | Analyze last n messages | `/analyze=100` |
| `/stt` | Convert voice to text | Reply to voice with `/stt` |
| `/tellme=<n>=<question>` | Q&A from chat history | `/tellme=50=What was discussed?` |

### CLI Commands
```bash
make help        # Show available commands
make test        # Run tests
make lint        # Run linters
make format      # Format code
make clean       # Clean temporary files
```

## 🔧 Configuration

### Required Settings
```ini
[Telegram]
api_id = YOUR_API_ID
api_hash = YOUR_API_HASH
phone_number = +1234567890

[OpenRouter]
api_key = YOUR_OPENROUTER_KEY
model_name = deepseek/deepseek-chat
```

### Optional Settings
- AssemblyAI API key for advanced STT
- ElevenLabs API key for premium TTS
- Custom FFmpeg path
- Logging configuration

## 🧪 Development

### Install Development Dependencies
```bash
make install-dev  # Or: pip install -r requirements-dev.txt
```

### Run Tests
```bash
make test  # Or: pytest tests/
```

### Code Quality
```bash
make lint    # Run all linters
make format  # Format code with black
```

### Pre-commit Hooks
```bash
make pre-commit  # Install pre-commit hooks
```

## 📊 Architecture

### Design Principles
- **SOLID Principles**: Single responsibility, open/closed, Liskov substitution
- **Clean Architecture**: Clear separation of concerns
- **Dependency Injection**: Loose coupling between components
- **Type Safety**: Comprehensive type hints and validation

### Key Components
1. **Core Module**: Configuration, exceptions, constants
2. **Telegram Module**: Client management, event handling, utilities
3. **AI Module**: LLM processing, STT/TTS, prompt management
4. **CLI Module**: Interactive terminal interface
5. **Utils Module**: Logging, helpers, common utilities

## 🐛 Troubleshooting

### Common Issues

**FFmpeg Not Found**
```bash
# Install FFmpeg
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg      # macOS
```

**Import Errors**
```bash
# Ensure you're in the virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

**Configuration Errors**
- Verify API credentials are correct
- Check file permissions on config files
- Ensure all required fields are filled

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Sina-Amare/SakaiBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Sina-Amare/SakaiBot/discussions)

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library
- [OpenRouter](https://openrouter.ai/) - LLM API gateway
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation

---

**Note**: This is a userbot, not a regular bot. It uses your personal Telegram account and requires your phone number for authentication.