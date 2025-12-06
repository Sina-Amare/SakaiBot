#!/bin/bash
# =============================================================================
# SakaiBot Docker Health Check
# =============================================================================
# This script is called by Docker's HEALTHCHECK instruction.
# Returns 0 (healthy) or 1 (unhealthy).
# =============================================================================

# Check if the main Python process is running
if ! pgrep -f "python.*src" > /dev/null 2>&1; then
    echo "UNHEALTHY: SakaiBot process not found"
    exit 1
fi

# Check if data directory is accessible
if [ ! -d "/app/data" ] || [ ! -r "/app/data" ]; then
    echo "UNHEALTHY: Data directory not accessible"
    exit 1
fi

# Check if logs directory is writable
if [ ! -w "/app/logs" ]; then
    echo "UNHEALTHY: Logs directory not writable"
    exit 1
fi

# Check log file activity (optional - don't fail if no recent activity)
LOG_FILE="/app/logs/sakaibot.log"
if [ -f "$LOG_FILE" ]; then
    # Check if log was updated in last 10 minutes
    LAST_MOD=$(stat -c %Y "$LOG_FILE" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_MOD))
    
    if [ $DIFF -gt 600 ]; then
        echo "WARNING: No log activity in 10 minutes (bot may be idle)"
        # Don't fail - the bot might just be waiting for messages
    fi
fi

# Check disk space on data volume
USAGE=$(df /app/data 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
if [ -n "$USAGE" ] && [ "$USAGE" -gt 90 ]; then
    echo "UNHEALTHY: Disk usage at ${USAGE}% (above 90% threshold)"
    exit 1
fi

# Check memory usage of the process (optional warning)
if command -v ps > /dev/null 2>&1; then
    MEM_MB=$(ps -o rss= -p $(pgrep -f "python.*src" | head -1) 2>/dev/null | awk '{print int($1/1024)}')
    if [ -n "$MEM_MB" ] && [ "$MEM_MB" -gt 700 ]; then
        echo "WARNING: Memory usage at ${MEM_MB}MB (approaching limit)"
        # Don't fail yet, just warn
    fi
fi

echo "HEALTHY"
exit 0
