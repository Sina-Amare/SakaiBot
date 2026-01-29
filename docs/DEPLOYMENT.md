# Deployment Guide

Production deployment options for SakaiBot.

## Deployment Options

| Method | Best For              | Complexity |
| ------ | --------------------- | ---------- |
| Local  | Development, testing  | Low        |
| Docker | Production, isolation | Medium     |
| VPS    | Always-on monitoring  | Medium     |

---

## Local Deployment

### Running Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Start monitoring
sakaibot monitor start

# Or with verbose output
sakaibot monitor start --verbose
```

### Running in Background (Linux/macOS)

```bash
# Using nohup
nohup sakaibot monitor start > logs/sakaibot.log 2>&1 &

# Using screen
screen -S sakaibot
sakaibot monitor start
# Ctrl+A, D to detach

# Using tmux
tmux new -s sakaibot
sakaibot monitor start
# Ctrl+B, D to detach
```

---

## Docker Deployment

### Building Image

```bash
docker build -t sakaibot:latest .
```

### Running with Docker Compose

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  sakaibot:
    build: .
    container_name: sakaibot
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./cache:/app/cache
      - ./.env:/app/.env:ro
    healthcheck:
      test: ["/healthcheck.sh"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Docker Features

- **Multi-stage build**: Minimal image size
- **Non-root user**: Security hardened
- **Tini init**: Proper signal handling
- **Health checks**: Auto-restart on failure
- **Volume mounts**: Persistent data

---

## VPS Deployment

### Prerequisites

- Ubuntu 22.04+ / Debian 12+
- Python 3.10+
- 1GB RAM minimum
- FFmpeg (for audio)

### Setup Script

```bash
#!/bin/bash
# setup-vps.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip ffmpeg git

# Clone repository
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install package
pip install -e .

# Configure
cp .env.example .env
nano .env  # Edit with your credentials
```

### Systemd Service

Create `/etc/systemd/system/sakaibot.service`:

```ini
[Unit]
Description=SakaiBot Telegram Userbot
After=network.target

[Service]
Type=simple
User=sakaibot
WorkingDirectory=/home/sakaibot/SakaiBot
ExecStart=/home/sakaibot/SakaiBot/venv/bin/sakaibot monitor start
Restart=always
RestartSec=10

Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### Enable Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable sakaibot

# Start service
sudo systemctl start sakaibot

# Check status
sudo systemctl status sakaibot

# View logs
journalctl -u sakaibot -f
```

---

## Environment Configuration

### Production Settings

```env
ENVIRONMENT=production
DEBUG=false
```

### Logging

Logs are written to `logs/` directory:

- `monitor_activity.log` - Monitor events
- Application logs with rotation

---

## Health Monitoring

### Docker Health Check

Built-in health check in Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/healthcheck.sh"]
```

### Manual Health Check

```bash
# Check if process is running
ps aux | grep sakaibot

# Check systemd status
systemctl status sakaibot

# Check Docker health
docker inspect --format='{{.State.Health.Status}}' sakaibot
```

---

## Updating

### Local/VPS Update

```bash
cd SakaiBot
git pull origin main
pip install -e .
sudo systemctl restart sakaibot  # if using systemd
```

### Docker Update

```bash
cd SakaiBot
git pull origin main
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## Troubleshooting

### Session Expired

```bash
# Remove old session
rm data/*.session

# Re-authenticate
sakaibot monitor start
```

### Service Won't Start

```bash
# Check logs
journalctl -u sakaibot -n 50

# Verify configuration
sakaibot config validate
```

### Memory Issues

```bash
# Check memory usage
docker stats sakaibot

# Limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
```

---

## Security Checklist

- [ ] Use non-root user
- [ ] Keep `.env` permissions restricted (`chmod 600`)
- [ ] Enable firewall (only outbound needed)
- [ ] Rotate API keys periodically
- [ ] Monitor logs for errors
- [ ] Keep system updated
