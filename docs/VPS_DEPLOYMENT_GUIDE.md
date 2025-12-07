# VPS Deployment Guide - Quick Reference

Simple step-by-step guide for deploying SakaiBot to your VPS from Windows (WSL or PowerShell).

---

## Prerequisites

- VPS with SSH access (root user)
- WSL installed on Windows (or use PowerShell)
- SSH key configured (or password access)

---

## 1. Connect to VPS

### Option A: From WSL Terminal

```bash
ssh root@YOUR_VPS_IP
```

**Example:**

```bash
ssh root@192.168.1.100
```

### Option B: From PowerShell

```powershell
wsl ssh root@YOUR_VPS_IP
```

**Example:**

```powershell
wsl ssh root@192.168.1.100
```

**Note:** Replace `YOUR_VPS_IP` with your actual VPS IP address.

---

## 2. Navigate to SakaiBot Directory

Once connected to VPS:

```bash
cd /root/SakaiBot
```

**Verify you're in the right place:**

```bash
pwd
# Should show: /root/SakaiBot

ls -la
# Should show: docker-compose.yml, Dockerfile, src/, etc.
```

---

## 3. Pull Latest Code from Git

```bash
git fetch origin
git reset --hard origin/main
```

**What this does:**

- Fetches latest changes from GitHub
- Resets your local code to match the main branch exactly

**Verify update:**

```bash
git log -1
# Shows the latest commit
```

---

## 4. Build and Deploy Container

### Quick Method (Recommended)

If you have the deploy script set up:

```bash
/root/deploy.sh
```

This single command does everything:

1. Prepares network for build
2. Pulls latest code (already done in step 3, but script does it again)
3. Builds Docker image
4. Configures proxy (if needed)
5. Starts the container

### Manual Method

If you prefer to do it step by step:

```bash
# Stop existing container (if running)
docker compose down

# Build the image
docker compose build

# Start the container
docker compose up -d
```

---

## 5. Verify Deployment

### Check Container Status

```bash
docker compose ps
```

**Expected output:**

```
NAME        IMAGE           STATUS      PORTS
sakaibot    sakaibot:latest Up 30s
```

### View Logs

```bash
# Follow logs in real-time
docker compose logs -f

# View last 50 lines
docker compose logs --tail=50

# Exit logs: Press Ctrl+C
```

### Check if Bot is Running

Look for these in the logs:

- `SakaiBot started successfully`
- `Telegram client connected`
- No error messages

---

## Complete Workflow (All Steps)

Here's the complete workflow in one go:

```bash
# 1. Connect to VPS
ssh root@YOUR_VPS_IP

# 2. Go to directory
cd /root/SakaiBot

# 3. Pull latest code
git fetch origin
git reset --hard origin/main

# 4. Deploy (if deploy script exists)
/root/deploy.sh

# OR manually:
docker compose down
docker compose build
docker compose up -d

# 5. Check status
docker compose ps
docker compose logs -f
```

---

## Common Commands Reference

### Container Management

```bash
# Start container
docker compose up -d

# Stop container
docker compose down

# Restart container
docker compose restart

# Rebuild and restart
docker compose up -d --build
```

### Viewing Information

```bash
# Container status
docker compose ps

# Live logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100

# Container resource usage
docker stats sakaibot
```

### Troubleshooting

```bash
# Enter container shell
docker compose exec sakaibot /bin/bash

# Check container logs for errors
docker compose logs sakaibot | grep -i error

# Restart if stuck
docker compose restart
```

---

## First Time Setup

If this is your first time deploying:

### 1. Clone Repository

```bash
ssh root@YOUR_VPS_IP
git clone https://github.com/Sina-Amare/SakaiBot.git /root/SakaiBot
cd /root/SakaiBot
```

### 2. Copy Deploy Scripts

```bash
cp docker/vps/*.sh /root/
chmod +x /root/*.sh
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your credentials
nano .env
# Or use: vi .env
```

**Required settings in `.env`:**

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `GEMINI_API_KEY` (or `GEMINI_API_KEYS`)
- Other provider keys as needed

### 4. Configure Proxy (Optional)

Only if your VPS location is blocked by Google APIs:

```bash
cp docker/vps/proxy.env.example /root/proxy.env
nano /root/proxy.env
```

Set:

```bash
PROXY_ENABLED=true
VPN_SERVER_IP=YOUR_VPN_IP
VPS_PUBLIC_IP=YOUR_VPS_IP
```

### 5. Deploy

```bash
/root/deploy.sh
```

---

## Troubleshooting

### Connection Issues

**Can't connect via SSH:**

```bash
# Check if SSH is running on VPS
# Verify IP address is correct
# Check firewall settings
```

**Permission denied:**

```bash
# Make sure you're using root user
# Or use: ssh user@VPS_IP then sudo su
```

### Git Issues

**Git pull fails:**

```bash
# Check internet connection
ping 8.8.8.8

# Verify git remote
git remote -v

# Try again
git fetch origin
```

### Docker Issues

**Build fails:**

```bash
# Check Docker is running
docker --version

# Check disk space
df -h

# Clean up old images
docker system prune -a
```

**Container won't start:**

```bash
# Check logs for errors
docker compose logs

# Verify .env file exists
ls -la .env

# Check permissions
chmod 600 .env
```

**Container keeps restarting:**

```bash
# View logs to see why
docker compose logs -f

# Check resource limits
docker stats sakaibot
```

---

## Quick Tips

1. **Always pull before deploying** - Ensures you have latest code
2. **Check logs after deployment** - Verify everything started correctly
3. **Use `-d` flag** - Runs containers in background (detached mode)
4. **Keep .env secure** - Never commit it to git, use `chmod 600`
5. **Monitor logs** - Use `docker compose logs -f` to watch in real-time

---

## Summary: One-Line Deployment

After initial setup, updating is just:

```bash
ssh root@YOUR_VPS_IP "cd /root/SakaiBot && git fetch origin && git reset --hard origin/main && /root/deploy.sh"
```

Or step by step:

```bash
ssh root@YOUR_VPS_IP
cd /root/SakaiBot
git fetch origin && git reset --hard origin/main
/root/deploy.sh
docker compose logs -f
```

---

**That's it!** You're now ready to deploy SakaiBot to your VPS.
