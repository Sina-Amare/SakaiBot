# How to Run SakaiBot

## Prerequisites
1. Python 3.10 or higher
2. FFmpeg installed (for audio processing)
3. Telegram API credentials
4. OpenRouter API key

## Step 1: Setup Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

## Step 2: Install Dependencies
```bash
# Install all requirements
pip install -r requirements.txt
```

## Step 3: Configure the Bot

### Option A: Using config.ini (Recommended)
```bash
# Copy the example config
cp config.ini.example data/config.ini

# Edit the config file
nano data/config.ini  # or use your favorite editor
```

Fill in these required fields:
```ini
[Telegram]
api_id = YOUR_API_ID_HERE
api_hash = YOUR_API_HASH_HERE  
phone_number = +YOUR_PHONE_NUMBER

[OpenRouter]
api_key = YOUR_OPENROUTER_API_KEY
model_name = deepseek/deepseek-chat
```

### Option B: Using Environment Variables
```bash
# Copy the example env file
cp .env.example .env

# Edit the .env file
nano .env
```

Fill in:
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+your_phone_number
OPENROUTER_API_KEY=your_openrouter_key
```

## Step 4: Run the Bot

### Standard Run
```bash
python -m src.main
```

### With Debug Mode
```bash
python -m src.main --debug
```

### Using Make
```bash
make run
```

### First Time Setup
On first run, you'll need to:
1. Enter the verification code sent to your Telegram
2. Enter your 2FA password (if you have one enabled)

## Step 5: Using the Bot

### In Telegram
Send commands to yourself or from authorized users:
- `/prompt=Your question here` - Ask AI anything
- `/translate=fa Hello world` - Translate text
- `/analyze=100` - Analyze last 100 messages
- `/stt` - Reply to a voice message to convert to text

### In the CLI Menu
The bot will show an interactive menu where you can:
1. List and search private chats
2. Set default chat for analysis
3. Configure message forwarding
4. Manage authorized users
5. Toggle monitoring

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the virtual environment
source venv/bin/activate
# Reinstall requirements
pip install -r requirements.txt
```

### FFmpeg Not Found
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows - Download from ffmpeg.org
```

### Configuration Errors
- Double-check your API credentials
- Ensure phone number includes country code (+1234567890)
- Make sure config.ini is in the data/ directory

### Permission Errors
```bash
# Make sure directories exist
mkdir -p data cache logs temp
```

## Quick Test
Run the system test to verify everything works:
```bash
python test_system.py
```

## Stop the Bot
Press `Ctrl+C` to stop the bot gracefully.

## Development Mode
For development with auto-reload:
```bash
make dev
# OR
python -m src.main --debug
```

## Additional Commands
```bash
make help        # Show all available commands
make test        # Run tests
make lint        # Check code quality
make format      # Format code
make clean       # Clean temporary files
```