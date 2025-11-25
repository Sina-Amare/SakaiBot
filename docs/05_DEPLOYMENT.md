# Configuration & Deployment

## Environment Setup

### Required Environment Variables

**Structure** (not actual values - see `.env.example` when created):

```env
# Telegram API Credentials (REQUIRED)
TELEGRAM_API_ID=<integer>
TELEGRAM_API_HASH=<string>
TELEGRAM_PHONE_NUMBER=<string>  # Format: +1234567890

# LLM Provider Selection (REQUIRED)
LLM_PROVIDER=gemini|openrouter

# AI Provider API Key (REQUIRED - set the one matching LLM_PROVIDER)
GEMINI_API_KEY=<string>  # If LLM_PROVIDER=gemini
OPENROUTER_API_KEY=<string>  # If LLM_PROVIDER=openrouter

# Optional Configuration
TELEGRAM_SESSION_NAME=sakaibot_session
GEMINI_API_KEY_TTS=<string>  # Optional: Separate TTS key
GEMINI_MODEL=gemini-2.5-flash
OPENROUTER_MODEL=google/gemini-2.5-flash
USERBOT_MAX_ANALYZE_MESSAGES=10000
PATHS_FFMPEG_EXECUTABLE=/path/to/ffmpeg
ENVIRONMENT=production|development
DEBUG=false
```

### API Keys and Credentials Architecture

**Configuration Loading Order**:
1. `.env` file (project root) - **Primary method**
2. `data/config.ini` - **Legacy fallback**
3. Environment variables (system-level)

**Security**:
- ✅ API keys never committed to git (`.gitignore` excludes `.env`, `config.ini`)
- ✅ API keys masked in logs (only last 4 characters visible)
- ⚠️ Session files stored in plain text (not encrypted)
- ⚠️ No secret management service integration

**Credential Sources**:
- **Telegram API**: [my.telegram.org](https://my.telegram.org) - "API development tools"
- **Google Gemini**: [Google AI Studio](https://makersuite.google.com/app/apikey)
- **OpenRouter**: [OpenRouter.ai](https://openrouter.ai/) - API keys section

### Configuration Files

**Primary Configuration**: `.env` (project root)
- **Format**: Key-value pairs
- **Loading**: Via `pydantic-settings` (automatic)
- **Validation**: Pydantic validators on load

**Legacy Configuration**: `data/config.ini` (backward compatibility)
- **Format**: INI file with sections
- **Loading**: `Config.load_from_ini()` method
- **Migration**: Automatically converted to environment variable format

**User Settings**: `data/sakaibot_user_settings.json`
- **Format**: JSON
- **Content**: User-specific settings (authorized users, target groups, mappings)
- **Management**: `SettingsManager` class

**Session Files**: `data/*.session`
- **Format**: Telethon session files (binary)
- **Purpose**: Persistent Telegram authentication
- **Security**: ⚠️ Not encrypted (stored in plain text)

### Development Setup Steps

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd SakaiBot
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # Linux/macOS:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # Or install as package:
   pip install -e .
   # For development:
   pip install -e ".[dev]"
   ```

4. **Create `.env` File**
   ```bash
   # ⚠️ MISSING: .env.example should exist but doesn't
   # Create .env manually with required variables (see structure above)
   ```

5. **Validate Configuration**
   ```bash
   sakaibot config validate
   ```

6. **Initial Login**
   ```bash
   sakaibot monitor start
   # Or:
   sakaibot menu
   # Enter verification code when prompted
   ```

### Dependency Management

**Production Dependencies**: `requirements.txt`
- Core dependencies only
- Version constraints: Minimum versions specified

**Project Configuration**: `pyproject.toml`
- Package metadata
- Build system configuration
- Tool configurations (Black, Ruff, MyPy, Pytest)
- Entry points: `sakaibot = src.cli.main:cli`

**Installation Methods**:
1. **Direct**: `pip install -r requirements.txt`
2. **Editable**: `pip install -e .` (development)
3. **With Dev Tools**: `pip install -e ".[dev]"`

**Lock Files**: ⚠️ **Missing**
- No `requirements.lock` or `poetry.lock`
- Dependencies resolved at install time
- **Recommendation**: Consider adding dependency locking for reproducible builds

## Deployment Readiness Analysis

### ⚠️ BLOCKERS (Prevents Deployment Right Now)

#### 1. Missing `.env.example` Template
- **Issue**: No template file for configuration
- **Impact**: Users must manually create `.env` without guidance
- **Severity**: **HIGH** - Deployment blocker
- **Fix**: Create `.env.example` with all variables documented

#### 2. No Docker Configuration
- **Issue**: No `Dockerfile` or `docker-compose.yml`
- **Impact**: Manual deployment only, no containerization
- **Severity**: **HIGH** - Deployment blocker for modern deployments
- **Fix**: Create Docker configuration

#### 3. No Deployment Documentation
- **Issue**: README has setup but no deployment guide
- **Impact**: Users must figure out deployment themselves
- **Severity**: **MEDIUM** - Not a blocker but important
- **Fix**: Add deployment section to docs

#### 4. No CI/CD Pipeline
- **Issue**: No automated testing/deployment
- **Impact**: Manual testing and deployment
- **Severity**: **MEDIUM** - Not a blocker but best practice
- **Fix**: Set up GitHub Actions or similar

### Technical Requirements

#### Runtime Environment

**Python Version**: 3.10 or higher
- **Tested Versions**: 3.10, 3.11, 3.12
- **System Dependencies**: None (pure Python, except FFmpeg)

**FFmpeg** (Required for audio processing):
- **Purpose**: Audio format conversion for STT/TTS
- **Installation**:
  - **Linux**: `sudo apt-get install ffmpeg` (Debian/Ubuntu)
  - **macOS**: `brew install ffmpeg`
  - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Configuration**: Set `PATHS_FFMPEG_EXECUTABLE` in `.env` if not in PATH

**System Dependencies**: None (all Python dependencies)

#### Recommended Deployment Platform

**Option 1: VPS (Virtual Private Server)** ⭐ **Recommended**
- **Providers**: DigitalOcean, Linode, Vultr, AWS EC2, etc.
- **Requirements**:
  - Ubuntu 20.04+ or Debian 11+ (recommended)
  - 1GB RAM minimum (2GB recommended)
  - 10GB storage minimum
  - Python 3.10+
  - FFmpeg installed
- **Advantages**:
  - Full control
  - Persistent storage for sessions
  - Can run 24/7
- **Setup**: Manual installation following development setup steps

**Option 2: Docker Container**
- **Status**: ⚠️ **Not Available** (needs to be created)
- **Requirements**: Docker and Docker Compose
- **Advantages**:
  - Isolated environment
  - Easy deployment
  - Reproducible builds
- **Setup**: Would require `Dockerfile` and `docker-compose.yml`

**Option 3: Cloud Functions/Serverless**
- **Status**: ⚠️ **Not Suitable**
- **Reason**: User-bots require persistent connections and state
- **Assessment**: Not recommended for this use case

**Option 4: Local Machine**
- **Status**: ✅ **Suitable for Development**
- **Limitations**: Requires machine to be always on
- **Use Case**: Personal use, development, testing

#### Resource Requirements

**Memory (RAM)**:
- **Minimum**: 512MB
- **Recommended**: 1-2GB
- **Usage**: Low (Python process + Telegram client)

**CPU**:
- **Minimum**: 1 core
- **Recommended**: 2 cores
- **Usage**: Low to moderate (async I/O bound, not CPU intensive)

**Storage**:
- **Minimum**: 1GB
- **Recommended**: 5-10GB
- **Usage**:
  - Code: ~50MB
  - Dependencies: ~500MB
  - Session files: <10MB
  - Cache: <100MB
  - Logs: Variable (rotate regularly)

**Network**:
- **Bandwidth**: Low (text messages, occasional voice)
- **Latency**: Low latency preferred (for real-time responses)
- **Requirements**: Stable internet connection

#### Monitoring and Maintenance Needs

**Current Monitoring**:
- ✅ **Logging**: File-based logging to `logs/` directory
- ✅ **Metrics**: Collected but not visualized
- ⚠️ **Health Checks**: Basic implementation
- ⚠️ **Alerting**: None

**Recommended Monitoring**:
1. **Log Rotation**: Set up log rotation (logrotate on Linux)
2. **Health Checks**: Enhance health check endpoint
3. **Metrics Dashboard**: Add visualization (Prometheus + Grafana, or simpler solution)
4. **Alerting**: Set up alerts for:
   - Bot disconnections
   - High error rates
   - API failures
   - Disk space

**Maintenance Tasks**:
- **Regular**: Check logs for errors
- **Weekly**: Review cache files (refresh if needed)
- **Monthly**: Update dependencies
- **As Needed**: Clear old log files

### Legal/Licensing

#### Dependency Licenses

**Core Dependencies** (all permissive):
- **Telethon**: LGPL-3.0 (allows commercial use)
- **Pydantic**: MIT (permissive)
- **Click**: BSD-3-Clause (permissive)
- **Rich**: MIT (permissive)
- **OpenAI SDK**: MIT (permissive)
- **Google GenAI**: Apache-2.0 (permissive)

**Assessment**: ✅ **No License Conflicts** - All dependencies allow commercial use

#### Third-Party API Terms of Service

**Telegram**:
- ⚠️ **User-Bot Violation**: User-bots violate Telegram's Terms of Service
- **Risk**: Account could be banned
- **Mitigation**: Documented in README, users should be aware

**Google Gemini API**:
- ✅ **Terms**: Standard Google Cloud API terms
- **Usage**: Pay-per-use (check current pricing)
- **Limitations**: Rate limits apply

**OpenRouter API**:
- ✅ **Terms**: Standard API terms
- **Usage**: Pay-per-use (check current pricing)
- **Limitations**: Rate limits apply

**Google Web Speech API** (STT):
- ✅ **Terms**: Free for reasonable use
- **Limitations**: Rate limits may apply

## Deployment Scenarios

### Scenario 1: VPS Deployment (Recommended)

**Steps**:

1. **Provision VPS**
   - Choose provider (DigitalOcean, Linode, etc.)
   - Select Ubuntu 22.04 LTS
   - Minimum: 1GB RAM, 1 vCPU, 25GB storage

2. **Initial Server Setup**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python 3.10+
   sudo apt install python3.10 python3.10-venv python3-pip -y
   
   # Install FFmpeg
   sudo apt install ffmpeg -y
   
   # Install Git
   sudo apt install git -y
   ```

3. **Deploy Application**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd SakaiBot
   
   # Create virtual environment
   python3.10 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -e .
   
   # Create .env file
   nano .env
   # (Add all required configuration)
   
   # Validate configuration
   sakaibot config validate
   ```

4. **Run as Service** (systemd)
   ```bash
   # Create systemd service file
   sudo nano /etc/systemd/system/sakaibot.service
   ```
   
   **Service File Content**:
   ```ini
   [Unit]
   Description=SakaiBot Telegram User-Bot
   After=network.target
   
   [Service]
   Type=simple
   User=your-user
   WorkingDirectory=/path/to/SakaiBot
   Environment="PATH=/path/to/SakaiBot/venv/bin"
   ExecStart=/path/to/SakaiBot/venv/bin/sakaibot monitor start
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   # Enable and start service
   sudo systemctl daemon-reload
   sudo systemctl enable sakaibot
   sudo systemctl start sakaibot
   
   # Check status
   sudo systemctl status sakaibot
   ```

5. **Log Management**
   ```bash
   # Set up log rotation
   sudo nano /etc/logrotate.d/sakaibot
   ```
   
   **Logrotate Config**:
   ```
   /path/to/SakaiBot/logs/*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

### Scenario 2: Docker Deployment (Future)

**Status**: ⚠️ **Not Implemented** - Would require:

1. **Dockerfile**:
   ```dockerfile
   FROM python:3.10-slim
   
   WORKDIR /app
   
   # Install FFmpeg
   RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
   
   # Copy requirements
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application
   COPY . .
   RUN pip install -e .
   
   # Create data directories
   RUN mkdir -p data cache logs
   
   # Run application
   CMD ["sakaibot", "monitor", "start"]
   ```

2. **docker-compose.yml**:
   ```yaml
   version: '3.8'
   
   services:
     sakaibot:
       build: .
       volumes:
         - ./data:/app/data
         - ./cache:/app/cache
         - ./logs:/app/logs
         - ./.env:/app/.env
       restart: unless-stopped
       environment:
         - PYTHONUNBUFFERED=1
   ```

### Scenario 3: Development/Testing

**Steps**: Same as development setup (see above)

**Use Case**: Local development, personal use, testing

## Configuration Validation

**Validation Command**: `sakaibot config validate`

**Checks Performed**:
1. ✅ Required environment variables present
2. ✅ API ID is positive integer
3. ✅ API hash length >= 10 characters
4. ✅ Phone number starts with "+"
5. ✅ LLM provider is "gemini" or "openrouter"
6. ✅ Selected provider has valid API key
7. ✅ API key format validation (basic checks)
8. ✅ FFmpeg path exists (if specified)

**Error Messages**: Clear, actionable error messages for each validation failure

## Troubleshooting

### Common Issues

1. **"Configuration file not found"**
   - **Solution**: Create `.env` file in project root
   - **Template**: See environment variables structure above

2. **"FFmpeg not found"**
   - **Solution**: Install FFmpeg or set `PATHS_FFMPEG_EXECUTABLE` in `.env`

3. **"Telegram authentication failed"**
   - **Solution**: Check API credentials, ensure phone number format is correct (+country code)

4. **"AI processor not configured"**
   - **Solution**: Set API key for selected LLM provider in `.env`

5. **"Session file corrupted"**
   - **Solution**: Delete `data/*.session` files and re-authenticate

---

**Next**: See `06_DEVELOPMENT.md` for development context and standards.

