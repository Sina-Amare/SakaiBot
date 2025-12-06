#!/bin/bash
# =============================================================================
# SakaiBot Docker Entrypoint
# =============================================================================
# This script runs when the container starts. It validates configuration,
# checks for required files, and starts the appropriate mode.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                       SakaiBot                               ║"
echo "║           AI-Powered Telegram Userbot                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_env() {
    local var_name=$1
    local is_required=${2:-true}
    
    if [ -z "${!var_name}" ]; then
        if [ "$is_required" = true ]; then
            log_error "Required environment variable $var_name is not set"
            return 1
        else
            log_warn "Optional environment variable $var_name is not set"
            return 0
        fi
    fi
    return 0
}

mask_value() {
    local value=$1
    local len=${#value}
    if [ $len -gt 8 ]; then
        echo "${value:0:4}****${value: -4}"
    else
        echo "****"
    fi
}

# -----------------------------------------------------------------------------
# Configuration Validation
# -----------------------------------------------------------------------------

log_info "Validating configuration..."

# Required: Telegram credentials
TELEGRAM_OK=true
check_env "TELEGRAM_API_ID" true || TELEGRAM_OK=false
check_env "TELEGRAM_API_HASH" true || TELEGRAM_OK=false
check_env "TELEGRAM_PHONE_NUMBER" true || TELEGRAM_OK=false

if [ "$TELEGRAM_OK" = false ]; then
    log_error "Telegram configuration is incomplete. Cannot start."
    log_error "Please ensure TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE_NUMBER are set."
    exit 1
fi

log_info "Telegram configuration: OK"

# Check for AI provider (at least one required for AI features)
AI_CONFIGURED=false
if [ -n "$GEMINI_API_KEY" ] || [ -n "$GEMINI_API_KEY_1" ]; then
    log_info "Gemini API: Configured ($(mask_value "${GEMINI_API_KEY_1:-$GEMINI_API_KEY}"))"
    AI_CONFIGURED=true
fi

if [ -n "$OPENROUTER_API_KEY" ]; then
    log_info "OpenRouter API: Configured ($(mask_value "$OPENROUTER_API_KEY"))"
    AI_CONFIGURED=true
fi

if [ "$AI_CONFIGURED" = false ]; then
    log_warn "No AI API keys configured. AI features will be disabled."
fi

# Check for optional image generation
if [ -n "$SDXL_API_KEY" ]; then
    log_info "SDXL Image Generation: Configured"
fi

if [ -n "$FLUX_WORKER_URL" ]; then
    log_info "Flux Image Generation: Configured"
fi

# -----------------------------------------------------------------------------
# Directory Permissions Check
# -----------------------------------------------------------------------------

log_info "Checking directory permissions..."

for dir in /app/data /app/logs /app/cache /app/temp; do
    if [ ! -d "$dir" ]; then
        log_warn "Directory $dir does not exist, creating..."
        mkdir -p "$dir" 2>/dev/null || {
            log_error "Cannot create directory $dir"
            exit 1
        }
    fi
    
    if [ ! -w "$dir" ]; then
        log_error "Cannot write to $dir - check volume permissions"
        exit 1
    fi
done

log_info "Directory permissions: OK"

# -----------------------------------------------------------------------------
# Session File Check
# -----------------------------------------------------------------------------

SESSION_FILE=$(find /app/data -name "*.session" 2>/dev/null | head -1)

if [ -z "$SESSION_FILE" ]; then
    log_warn "No session file found in /app/data/"
    log_warn "First-time authentication will be required."
    log_warn ""
    log_warn "If you need to authenticate interactively, run:"
    log_warn "  docker compose run --rm sakaibot cli"
    log_warn ""
    
    # If trying to start monitor without session, warn but continue
    # The bot will prompt for authentication
    if [ "${1:-monitor}" = "monitor" ]; then
        log_warn "Starting in monitor mode without session - authentication prompt expected"
    fi
else
    log_info "Session file found: $(basename "$SESSION_FILE")"
fi

# -----------------------------------------------------------------------------
# Environment Summary
# -----------------------------------------------------------------------------

echo ""
log_info "=== Startup Configuration ==="
log_info "Mode:        ${1:-monitor}"
log_info "Log Level:   ${SAKAIBOT_LOG_LEVEL:-INFO}"
log_info "Log Format:  ${SAKAIBOT_LOG_JSON:-0} (1=JSON)"
log_info "Timezone:    ${TZ:-UTC}"
log_info "Docker Mode: ${SAKAIBOT_DOCKER:-0}"
echo ""

# -----------------------------------------------------------------------------
# Command Execution
# -----------------------------------------------------------------------------

case "${1:-monitor}" in
    monitor)
        log_info "Starting monitoring daemon..."
        log_info "Press Ctrl+C to stop (or docker compose down)"
        echo ""
        exec python -m src.cli.main monitor start --verbose
        ;;
    
    cli)
        log_info "Starting interactive CLI..."
        log_info "Use the menu to configure and start monitoring"
        echo ""
        exec python -m src.cli.main menu
        ;;
    
    status)
        log_info "Checking monitoring status..."
        exec python -m src.cli.main monitor status
        ;;
    
    validate)
        log_info "Validating configuration..."
        exec python -m src.cli.main config validate
        ;;
    
    shell)
        log_info "Starting bash shell..."
        exec /bin/bash
        ;;
    
    test)
        log_info "Running tests..."
        exec pytest tests/ -v
        ;;
    
    *)
        log_info "Executing custom command: $@"
        exec "$@"
        ;;
esac
