#!/bin/bash
# =============================================================================
# enable_proxy.sh - Enable VPN transparent proxy for running container
# =============================================================================
# This script routes all outbound TCP traffic through the VPN proxy.
# Required for accessing Google APIs from blocked regions.
#
# Configuration: Edit /root/proxy.env with your VPN settings
# Usage: /root/enable_proxy.sh
# =============================================================================

set -e

# Load configuration
CONFIG_FILE="/root/proxy.env"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    echo "Please copy docker/vps/proxy.env.example to /root/proxy.env and configure it."
    exit 1
fi
source "$CONFIG_FILE"

# Check if proxy is enabled
if [ "$PROXY_ENABLED" != "true" ]; then
    echo "Proxy is disabled in configuration. Skipping..."
    exit 0
fi

# Validate required settings
if [ -z "$VPN_SERVER_IP" ] || [ "$VPN_SERVER_IP" = "YOUR_VPN_SERVER_IP_HERE" ]; then
    echo "ERROR: VPN_SERVER_IP not configured in $CONFIG_FILE"
    exit 1
fi

echo "=============================================="
echo "  Enabling VPN Transparent Proxy"
echo "=============================================="
echo "  VPN Server: $VPN_SERVER_IP"
echo "=============================================="

# Step 1: Start redsocks
echo "[1/4] Starting redsocks..."
systemctl start redsocks
sleep 1

# Step 2: Verify redsocks is running
echo "[2/4] Verifying redsocks..."
if pgrep redsocks > /dev/null; then
    echo "  ✓ redsocks is running"
else
    echo "  ✗ redsocks failed to start"
    exit 1
fi

# Step 3: Setup iptables rules
echo "[3/4] Setting up iptables rules..."

# Create REDSOCKS chain if needed
iptables -t nat -N REDSOCKS 2>/dev/null || true
iptables -t nat -F REDSOCKS

# Exclude local/private addresses from proxying
iptables -t nat -A REDSOCKS -d 0.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 10.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 127.0.0.0/8 -j RETURN
iptables -t nat -A REDSOCKS -d 172.16.0.0/12 -j RETURN
iptables -t nat -A REDSOCKS -d 192.168.0.0/16 -j RETURN

# Exclude VPN server itself (prevent routing loops)
iptables -t nat -A REDSOCKS -d "$VPN_SERVER_IP" -j RETURN

# Redirect all other TCP traffic to redsocks
iptables -t nat -A REDSOCKS -p tcp -j REDIRECT --to-ports "${REDSOCKS_PORT:-12345}"

# Apply to OUTPUT chain
iptables -t nat -A OUTPUT -p tcp -j REDSOCKS

# Step 4: Verify proxy connection
echo "[4/4] Verifying proxy connection..."
sleep 2
PROXY_IP=$(curl -s --max-time 15 https://api.ipify.org || echo "FAILED")

if [ "$PROXY_IP" = "FAILED" ]; then
    echo "  ✗ Could not verify proxy connection"
    exit 1
elif [ "$PROXY_IP" = "$VPS_PUBLIC_IP" ]; then
    echo "  ⚠ Warning: Still using VPS IP ($PROXY_IP), proxy may not be working"
else
    echo "  ✓ Proxy active! Current IP: $PROXY_IP"
fi

echo ""
echo "=============================================="
echo "  ✓ VPN proxy enabled"
echo "=============================================="
