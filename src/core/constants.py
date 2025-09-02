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
PV_CACHE_FILE: Final[str] = "data/pv_cache.json"
GROUP_CACHE_FILE: Final[str] = "data/group_cache.json"
DEFAULT_PV_FETCH_LIMIT_REFRESH: Final[int] = 200
DEFAULT_PV_FETCH_LIMIT_INITIAL: Final[int] = 400

# Configuration Constants
CONFIG_FILE_NAME: Final[str] = "data/config.ini"
SETTINGS_FILE_NAME: Final[str] = "data/sakaibot_user_settings.json"
DEFAULT_MAX_ANALYZE_MESSAGES: Final[int] = 5000

# AI Constants
DEFAULT_OPENROUTER_MODEL: Final[str] = "google/gemini-2.5-flash"
DEFAULT_GEMINI_MODEL: Final[str] = "gemini-2.5-flash"
DEFAULT_TTS_VOICE: Final[str] = "fa-IR-DilaraNeural"
CONFIRMATION_KEYWORD: Final[str] = "confirm"

# Logging Constants
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MONITOR_LOG_FILE: Final[str] = "logs/monitor_activity.log"

# HTTP Headers for OpenRouter
OPENROUTER_HEADERS: Final[dict[str, str]] = {
    "HTTP-Referer": "http://localhost/sakaibot",
    "X-Title": "SakaiBot"
}
