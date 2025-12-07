# VPS Proxy Setup Guide

This guide explains how to deploy SakaiBot on a VPS with optional VPN proxy support.

## Quick Deploy (One Command)

```bash
ssh root@YOUR_VPS_IP
/root/deploy.sh
```

This single command handles everything: network prep → git pull → build → proxy → start.

---

## Initial Setup (First Time Only)

### 1. Clone Repository

```bash
ssh root@YOUR_VPS_IP
git clone https://github.com/Sina-Amare/SakaiBot.git /root/SakaiBot
cd /root/SakaiBot
cp .env.example .env
# Edit .env with your credentials
```

### 2. Install Deploy Scripts

```bash
cp docker/vps/*.sh /root/
chmod +x /root/*.sh
```

### 3. Configure VPN Proxy (Optional)

If your VPS location is blocked by Google APIs, configure VPN tunneling:

```bash
cp docker/vps/proxy.env.example /root/proxy.env
nano /root/proxy.env
```

Edit `proxy.env`:

```bash
PROXY_ENABLED=true
VPN_SERVER_IP=YOUR_VPN_IP    # Your VPN server's IP
VPS_PUBLIC_IP=YOUR_VPS_IP    # Your VPS public IP
```

> **Note:** If you don't need VPN proxy, set `PROXY_ENABLED=false` or skip creating the file.

### 4. Setup Xray + Redsocks (If Using Proxy)

See [Full Proxy Setup](#full-proxy-setup-for-vpn-tunneling) below.

### 5. Deploy

```bash
/root/deploy.sh
```

---

## Updating the Bot

To deploy the latest version:

```bash
ssh root@YOUR_VPS_IP
/root/deploy.sh
```

That's it! The script handles everything automatically.

---

## Full Proxy Setup (For VPN Tunneling)

Only needed if your VPS is in a region blocked by Google APIs.

### Install Xray

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
```

### Configure Xray

Create `/usr/local/etc/xray/config.json`:

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
            "users": [{ "id": "YOUR_UUID", "encryption": "none" }]
          }
        ]
      }
    }
  ]
}
```

Start Xray:

```bash
systemctl enable xray && systemctl restart xray
```

### Install Redsocks

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

---

## Troubleshooting

**Docker build fails with apt-get errors:**

- The `prepare_for_build.sh` script should handle this
- Check: `curl https://api.ipify.org` (should show VPS IP during build)

**API calls show "location not supported":**

- Run `/root/enable_proxy.sh`
- Verify: `curl https://api.ipify.org` (should show VPN IP)

**Xray not working:**

- Check: `systemctl status xray`
- Logs: `journalctl -u xray -n 50`
