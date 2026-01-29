# =============================================================================
# SakaiBot Production Docker Image
# Multi-stage build for minimal image size and security
# =============================================================================
# Build: docker build -t sakaibot:latest .
# Run:   docker compose up -d
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build package
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

# Prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (better layer caching)
COPY requirements.txt .

# Install Python dependencies to user directory
RUN pip install --user --no-warn-script-location -r requirements.txt

# Copy source code
COPY pyproject.toml setup.py README.md ./
COPY src/ ./src/

# Install package (non-editable for production)
RUN pip install --user --no-warn-script-location .


# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Image metadata
LABEL org.opencontainers.image.title="SakaiBot" \
      org.opencontainers.image.description="AI-powered Telegram Userbot with multi-LLM support" \
      org.opencontainers.image.vendor="Sina-Amare" \
      org.opencontainers.image.source="https://github.com/Sina-Amare/SakaiBot" \
      org.opencontainers.image.licenses="MIT"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/home/sakaibot/.local/bin:$PATH" \
    # Docker-specific settings
    SAKAIBOT_DOCKER=1 \
    SAKAIBOT_LOG_JSON=1 \
    SAKAIBOT_LOG_LEVEL=INFO \
    # Timezone
    TZ=UTC

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg for audio processing
    ffmpeg \
    # Tini - proper init system for containers
    tini \
    # Curl for health checks
    curl \
    # CA certificates for HTTPS
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Create non-root user for security
RUN groupadd --gid 1000 sakaibot \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash sakaibot

# Create application directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/cache /app/temp \
    && chown -R sakaibot:sakaibot /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/sakaibot/.local

# Set working directory
WORKDIR /app

# Copy application code with correct ownership
COPY --chown=sakaibot:sakaibot src/ ./src/
COPY --chown=sakaibot:sakaibot pyproject.toml setup.py ./

# Copy Docker-specific scripts
COPY --chown=sakaibot:sakaibot docker/entrypoint.sh /entrypoint.sh
COPY --chown=sakaibot:sakaibot docker/healthcheck.sh /healthcheck.sh

# Make scripts executable
RUN chmod +x /entrypoint.sh /healthcheck.sh

# Switch to non-root user
USER sakaibot

# Declare volumes for persistent data
VOLUME ["/app/data", "/app/logs", "/app/cache"]

# Health check - runs every 30 seconds after 60s startup period
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/healthcheck.sh"]

# Use tini as init system (handles signals properly, reaps zombies)
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]

# Default command: start monitoring daemon
CMD ["monitor"]
