"""Constants used throughout SakaiBot."""

from typing import Final

# Application Constants
APP_NAME: Final[str] = "SakaiBot"
APP_VERSION: Final[str] = "2.0.0"
APP_DESCRIPTION: Final[str] = "Modern Telegram Userbot with AI Capabilities"

# Telegram Constants
MAX_MESSAGE_LENGTH: Final[int] = 4096
SYSTEM_VERSION: Final[str] = "4.16.30-vxCUSTOM"

# Cache Constants
PV_CACHE_FILE: Final[str] = "cache/pv_cache.json"
GROUP_CACHE_FILE: Final[str] = "cache/group_cache.json"
DEFAULT_PV_FETCH_LIMIT_REFRESH: Final[int] = 200
DEFAULT_PV_FETCH_LIMIT_INITIAL: Final[int] = 400

# Configuration Constants
CONFIG_FILE_NAME: Final[str] = "data/config.ini"
SETTINGS_FILE_NAME: Final[str] = "data/sakaibot_user_settings.json"
DEFAULT_MAX_ANALYZE_MESSAGES: Final[int] = 10000

# AI Constants
MAX_OUTPUT_TOKENS: Final[int] = 100000
DEFAULT_OPENROUTER_MODEL: Final[str] = "google/gemini-2.5-flash"
DEFAULT_GEMINI_MODEL: Final[str] = "gemini-2.5-flash"
DEFAULT_TTS_VOICE: Final[str] = "Orus"  # Google GenAI TTS voice (masculine)
CONFIRMATION_KEYWORD: Final[str] = "confirm"

# Logging Constants
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_WITH_CORRELATION: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
MONITOR_LOG_FILE: Final[str] = "logs/monitor_activity.log"

# HTTP Headers for OpenRouter
OPENROUTER_HEADERS: Final[dict[str, str]] = {
    "HTTP-Referer": "http://localhost/sakaibot",
    "X-Title": "SakaiBot"
}

# Image Generation Constants
SUPPORTED_IMAGE_MODELS: Final[list[str]] = ["flux", "sdxl"]
IMAGE_GENERATION_TIMEOUT: Final[int] = 120  # seconds
IMAGE_GENERATION_CONNECT_TIMEOUT: Final[int] = 30  # seconds
MAX_IMAGE_PROMPT_LENGTH: Final[int] = 1000
IMAGE_TEMP_DIR: Final[str] = "temp/images"
DEFAULT_FLUX_WORKER_URL: Final[str] = "https://image-smoke-ad69.fa-ra9931143.workers.dev"
DEFAULT_SDXL_WORKER_URL: Final[str] = "https://image-api.cpt-n3m0.workers.dev"