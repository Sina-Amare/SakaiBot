# SakaiBot Docker Deployment Guide

This guide covers deploying SakaiBot to a VPS using Docker.

## Prerequisites

- VPS with Docker installed (Ubuntu 22.04+ recommended)
- At least 1GB RAM, 1 vCPU, 10GB storage
- SSH access to VPS
- Local machine with SakaiBot code and active Telegram session

## Quick Start

```bash
# On VPS:
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot
docker compose build
docker compose up -d
```

## Detailed Setup

### 1. Install Docker on VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker compose version
```

### 2. Clone Repository

```bash
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot
mkdir -p logs data cache secrets
chmod 700 secrets
```

### 3. Transfer Credentials Securely

**Option A: GPG Encrypted Transfer (Recommended)**

On your LOCAL machine:

```bash
# Prepare secrets
cp .env secrets/.env.production
cp data/*.session secrets/

# Create encrypted archive
tar -czf - secrets/ | gpg --symmetric --cipher-algo AES256 > sakaibot-secrets.tar.gz.gpg

# Transfer to VPS
scp sakaibot-secrets.tar.gz.gpg user@your-vps:~/SakaiBot/

# Clean up locally
rm -rf secrets/*
```

On your VPS:

```bash
cd ~/SakaiBot

# Decrypt
gpg --decrypt sakaibot-secrets.tar.gz.gpg | tar -xzf -

# Move files
mv secrets/.env.production .env
mv secrets/*.session data/

# Secure permissions
chmod 600 .env data/*.session

# Cleanup
rm sakaibot-secrets.tar.gz.gpg
rm -rf secrets/*
```

**Option B: Direct SCP (Less Secure)**

```bash
# Only with SSH key auth
scp .env user@your-vps:~/SakaiBot/.env
scp data/*.session user@your-vps:~/SakaiBot/data/
```

### 4. Build and Run

```bash
# Build image
docker compose build

# Start in background
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 5. First-Time Authentication

If you don't have a session file, authenticate interactively:

```bash
docker compose run --rm sakaibot cli
```

Follow the prompts to log in with your Telegram account.

## Commands Reference

| Task             | Command                                                    |
| ---------------- | ---------------------------------------------------------- |
| Build image      | `docker compose build`                                     |
| Start monitoring | `docker compose up -d`                                     |
| Stop             | `docker compose down`                                      |
| View logs        | `docker compose logs -f`                                   |
| Interactive CLI  | `docker compose run --rm sakaibot cli`                     |
| Shell access     | `docker compose run --rm sakaibot shell`                   |
| Check status     | `docker compose ps`                                        |
| Restart          | `docker compose restart`                                   |
| Update           | `git pull && docker compose build && docker compose up -d` |

## Monitoring & Troubleshooting

### View Logs

```bash
# All logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail 100

# Filter errors (with jq)
docker compose logs 2>&1 | grep -i error
```

### Check Health

```bash
# Container status
docker ps

# Detailed health
docker inspect sakaibot | jq '.[0].State.Health'

# Resource usage
docker stats sakaibot
```

### Common Issues

**Container won't start:**

- Check `.env` file exists and has correct values
- Verify session file is in `data/` directory
- View logs: `docker compose logs`

**Telegram disconnects:**

- Check your phone is online
- Verify session wasn't invalidated (log in again if needed)
- Check network connectivity from VPS

**Out of memory:**

- Reduce `USERBOT_MAX_ANALYZE_MESSAGES` in `.env`
- Check `docker stats` for memory usage
- Increase VPS RAM if needed

## Security Best Practices

1. **Never commit secrets** - `.env`, `.session` files must stay out of git
2. **Use encrypted transfer** - Always GPG encrypt before transferring
3. **Restrict file permissions** - `chmod 600` for all sensitive files
4. **Enable firewall** - Only allow SSH and required ports
5. **Keep updated** - Regularly pull updates and rebuild

## Backup Strategy

```bash
# Backup data volume
docker run --rm -v sakaibot_sakaibot_data:/data -v $(pwd):/backup \
    alpine tar czf /backup/sakaibot-data-backup.tar.gz -C /data .

# Restore
docker run --rm -v sakaibot_sakaibot_data:/data -v $(pwd):/backup \
    alpine tar xzf /backup/sakaibot-data-backup.tar.gz -C /data
```

## Updating SakaiBot

```bash
cd ~/SakaiBot

# Stop current container
docker compose down

# Pull latest code
git pull origin main

# Rebuild image
docker compose build

# Start updated container
docker compose up -d

# Verify
docker compose logs -f
```

## Rollback

If an update causes issues:

```bash
# Stop broken container
docker compose down

# Revert to previous commit
git checkout HEAD~1

# Rebuild and start
docker compose build
docker compose up -d
```
