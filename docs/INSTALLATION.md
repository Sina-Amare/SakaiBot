# Installation Guide

Complete installation instructions for SakaiBot.

## Prerequisites

### Required

| Requirement | Version | Purpose             |
| ----------- | ------- | ------------------- |
| Python      | 3.10+   | Runtime environment |
| pip         | Latest  | Package manager     |
| Git         | Any     | Clone repository    |

### Optional

| Requirement | Version | Purpose                    |
| ----------- | ------- | -------------------------- |
| FFmpeg      | 4.0+    | Audio processing (TTS/STT) |
| Docker      | 20.10+  | Containerized deployment   |

## Quick Install

```bash
# Clone repository
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install package
pip install -e .

# Copy environment template
cp .env.example .env

# Edit configuration
# (use your preferred editor)
nano .env  # or: code .env
```

## Detailed Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot
```

### Step 2: Virtual Environment

**Linux/macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### Step 3: Install Dependencies

**Production:**

```bash
pip install -e .
```

**Development (includes testing/linting tools):**

```bash
pip install -e ".[dev]"
```

### Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials. See [CONFIGURATION.md](CONFIGURATION.md) for all options.

**Minimum required:**

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=+1234567890
LLM_PROVIDER=gemini
GEMINI_API_KEY_1=your_gemini_key
```

### Step 5: First Run

```bash
sakaibot monitor start
```

On first run:

1. Enter Telegram verification code when prompted
2. Session file is saved to `data/`
3. Future runs use saved session

## Installing FFmpeg

FFmpeg is required for audio processing (TTS/STT).

### Windows

1. Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract to `C:\ffmpeg`
3. Add to `.env`:
   ```env
   PATHS_FFMPEG_EXECUTABLE=C:\ffmpeg\bin\ffmpeg.exe
   ```

### macOS

```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install ffmpeg
```

### Linux (Fedora)

```bash
sudo dnf install ffmpeg
```

## Docker Installation

See [DEPLOYMENT.md](DEPLOYMENT.md) for Docker deployment instructions.

```bash
# Build image
docker build -t sakaibot:latest .

# Run with docker-compose
docker compose up -d
```

## Verifying Installation

```bash
# Check CLI is available
sakaibot --help

# Validate configuration
sakaibot config validate

# Check status
sakaibot status
```

## Troubleshooting

### Python Version Error

```
ERROR: Python 3.10+ required
```

**Solution:** Install Python 3.10 or higher from [python.org](https://python.org/downloads/).

### Module Not Found

```
ModuleNotFoundError: No module named 'telethon'
```

**Solution:** Ensure virtual environment is activated and dependencies installed:

```bash
source venv/bin/activate  # or Windows equivalent
pip install -e .
```

### FFmpeg Not Found

```
FileNotFoundError: FFmpeg not found
```

**Solution:** Install FFmpeg and set path in `.env`:

```env
PATHS_FFMPEG_EXECUTABLE=/path/to/ffmpeg
```

### Session Authentication Failed

```
SessionError: Authorization failed
```

**Solution:** Delete session file and re-authenticate:

```bash
rm data/*.session
sakaibot monitor start
```

## Next Steps

- [CONFIGURATION.md](CONFIGURATION.md) - Configure all options
- [COMMANDS.md](COMMANDS.md) - Learn all commands
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deploy to production
