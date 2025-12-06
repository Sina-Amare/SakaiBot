# VPS Proxy Setup Guide

This guide explains how to set up a US VPN proxy for SakaiBot on a VPS. This is **only needed** if your VPS location is blocked by Google APIs (e.g., Gemini, Google Speech).

## Prerequisites

- VPS with root access
- VLESS VPN config (or similar)
- Docker and Docker Compose installed

---

## Quick Reference: Rebuilding the Bot

> **Where to run these commands:** SSH into your VPS first, then run these in the SakaiBot folder.

**Step 1: Connect to your VPS**

```bash
ssh root@YOUR_VPS_IP
cd /root/SakaiBot
```

**Step 2: Rebuild and restart (4 commands)**

```bash
# Turn off VPN routing (so Docker can download packages)
/root/disable_proxy.sh

# Get latest code and rebuild the Docker image
git pull
docker compose build

# Turn VPN routing back on (so bot uses US IP for API calls)
/root/enable_proxy.sh

# Start the bot
docker compose up -d
```

**That's it!** The bot will now run with all traffic routed through the US VPN.

### Step 1: Install Xray

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
```

### Step 2: Configure Xray

Create `/usr/local/etc/xray/config.json` with your VPN config:

```json
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "port": 10808,
      "listen": "0.0.0.0",
      "protocol": "socks",
      "settings": { "udp": true }
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "YOUR_VPN_SERVER",
            "port": 443,
            "users": [
              {
                "id": "YOUR_UUID",
                "encryption": "none",
                "flow": "xtls-rprx-vision"
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "YOUR_SNI",
          "fingerprint": "firefox",
          "publicKey": "YOUR_PUBLIC_KEY",
          "shortId": "YOUR_SHORT_ID"
        }
      }
    }
  ]
}
```

Start Xray:

```bash
systemctl enable xray && systemctl restart xray
```

### Step 3: Install Redsocks

```bash
apt-get update && apt-get install -y redsocks
```

Create `/etc/redsocks.conf`:

```
base {
    log_debug = off;
    log_info = on;
    log = "syslog:daemon";
    daemon = on;
    redirector = iptables;
}

redsocks {
    local_ip = 127.0.0.1;
    local_port = 12345;
    ip = 127.0.0.1;
    port = 10808;
    type = socks5;
}
```

### Step 4: Create Proxy Scripts

Create `/root/disable_proxy.sh`:

```bash
#!/bin/bash
echo '[1/3] Stopping redsocks...'
systemctl stop redsocks 2>/dev/null
echo '[2/3] Clearing iptables rules...'
iptables -t nat -F OUTPUT 2>/dev/null
iptables -t nat -F REDSOCKS 2>/dev/null
echo '[3/3] Verifying...'
IP=$(curl -s https://api.ipify.org --max-time 10)
echo "Current IP: $IP"
```

Create `/root/enable_proxy.sh`:

```bash
#!/bin/bash
VPN_IP="YOUR_VPN_SERVER_IP"  # Get this by pinging your VPN server
echo '[1/4] Starting redsocks...'
systemctl start redsocks && sleep 1
echo '[2/4] Setting up iptables...'
iptables -t nat -N REDSOCKS 2>/dev/null
iptables -t nat -F REDSOCKS
iptables -t nat -A REDSOCKS -d 0.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 10.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 127.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 172.16.0.0/12 -j RETURN
iptables -t nat -A REDSOCKS -d 192.168.0.0/16 -j RETURN
iptables -t nat -A REDSOCKS -d $VPN_IP -j RETURN
iptables -t nat -A REDSOCKS -p tcp -j REDIRECT --to-ports 12345
iptables -t nat -A OUTPUT -p tcp -j REDSOCKS
echo '[3/4] Verifying...'
IP=$(curl -s https://api.ipify.org --max-time 15)
echo "Current IP: $IP (should be US IP)"
```

Make executable:

```bash
chmod +x /root/disable_proxy.sh /root/enable_proxy.sh
```

### Step 5: Fix Docker DNS

Create `/etc/docker/daemon.json`:

```json
{
  "dns": ["8.8.8.8", "1.1.1.1"]
}
```

Restart Docker:

```bash
systemctl restart docker
```

### Step 6: Deploy SakaiBot

```bash
cd /root
git clone https://github.com/Sina-Amare/SakaiBot.git
cd SakaiBot
cp .env.example .env
# Edit .env with your credentials

/root/disable_proxy.sh
docker compose build
/root/enable_proxy.sh
docker compose up -d
```

---

## Troubleshooting

**Docker build fails with apt-get errors:**

- Run `/root/disable_proxy.sh` before building
- Check Docker DNS: `cat /etc/docker/daemon.json`

**API calls show "location not supported":**

- Run `/root/enable_proxy.sh`
- Verify with: `curl https://api.ipify.org` (should show US IP)

**Xray not working:**

- Check status: `systemctl status xray`
- Check logs: `journalctl -u xray -n 50`
