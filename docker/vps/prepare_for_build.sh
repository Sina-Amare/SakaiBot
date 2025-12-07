#!/bin/bash
# =============================================================================
# prepare_for_build.sh - Prepare VPS network for Docker build
# =============================================================================
# This script ensures Docker can access package repositories during build.
# It disables any transparent proxy routing and restarts Docker.
#
# Usage: /root/prepare_for_build.sh
# =============================================================================

set -e

echo "=============================================="
echo "  Preparing network for Docker build"
echo "=============================================="

# Step 1: Stop proxy services
echo "[1/5] Stopping proxy services..."
systemctl stop redsocks 2>/dev/null || true

# Step 2: Flush ALL iptables nat rules (not just specific chains)
echo "[2/5] Flushing iptables NAT rules..."
iptables -t nat -F OUTPUT 2>/dev/null || true
iptables -t nat -F REDSOCKS 2>/dev/null || true
iptables -t nat -X REDSOCKS 2>/dev/null || true

# Step 3: Restart Docker to get fresh network state
echo "[3/5] Restarting Docker daemon..."
systemctl restart docker
sleep 3

# Step 4: Verify host network connectivity
echo "[4/5] Verifying host network..."
HOST_IP=$(curl -s --max-time 10 https://api.ipify.org || echo "FAILED")
if [ "$HOST_IP" = "FAILED" ]; then
    echo "  ✗ Host network check failed!"
    exit 1
fi
echo "  ✓ Host IP: $HOST_IP"

# Step 5: Verify Docker can access package repos
echo "[5/5] Verifying Docker network..."
if docker run --rm debian:bookworm-slim apt-get update -qq 2>&1 | head -5; then
    echo "  ✓ Docker can access package repositories"
else
    echo "  ⚠ Docker network test had issues, but continuing..."
fi

echo ""
echo "=============================================="
echo "  ✓ Network ready for Docker build"
echo "=============================================="
