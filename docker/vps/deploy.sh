#!/bin/bash
# =============================================================================
# deploy.sh - One-command SakaiBot deployment
# =============================================================================
# This script handles the entire deployment process:
# 1. Prepares network for Docker build (disables proxy)
# 2. Pulls latest code from GitHub
# 3. Builds Docker image
# 4. Enables VPN proxy (if configured)
# 5. Starts the bot
#
# Usage: /root/deploy.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAKAIBOT_DIR="/root/SakaiBot"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              SakaiBot VPS Deployment                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if SakaiBot directory exists
if [ ! -d "$SAKAIBOT_DIR" ]; then
    echo "ERROR: SakaiBot directory not found at $SAKAIBOT_DIR"
    echo "Please clone the repository first:"
    echo "  git clone https://github.com/Sina-Amare/SakaiBot.git $SAKAIBOT_DIR"
    exit 1
fi

cd "$SAKAIBOT_DIR"

# Step 1: Prepare network for build
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/5: Preparing network for Docker build..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
/root/prepare_for_build.sh

# Step 2: Pull latest code
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2/5: Pulling latest code..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git fetch origin
git reset --hard origin/main
echo "✓ Code updated to latest version"

# Step 3: Build Docker image
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3/5: Building Docker image..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose build
echo "✓ Docker image built successfully"

# Step 4: Enable VPN proxy (if configured)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4/5: Configuring network proxy..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f /root/proxy.env ]; then
    /root/enable_proxy.sh
else
    echo "No proxy configuration found (/root/proxy.env)"
    echo "Skipping VPN proxy setup - using direct connection"
fi

# Step 5: Start the bot
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5/5: Starting SakaiBot..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose down 2>/dev/null || true
docker compose up -d

# Show status
sleep 3
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✓ Deployment Complete!                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Container Status:"
docker compose ps
echo ""
echo "To view logs: docker compose logs -f"
echo ""
