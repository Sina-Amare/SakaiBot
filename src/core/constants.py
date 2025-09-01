"""
Constants and magic values used throughout SakaiBot.

This module centralizes all constants to avoid magic numbers/strings
scattered throughout the codebase.
"""

from enum import Enum, auto
from typing import Final


# Application Information
APP_NAME: Final[str] = "SakaiBot"
APP_VERSION: Final[str] = "2.0.0"
APP_DESCRIPTION: Final[str] = "Advanced Telegram userbot with AI capabilities"

# File Names
DEFAULT_SESSION_NAME: Final[str] = "sakaibot_session"
DEFAULT_CONFIG_FILE: Final[str] = "config.ini"
ENV_FILE: Final[str] = ".env"
USER_SETTINGS_FILE: Final[str] = "sakaibot_user_settings.json"
PV_CACHE_FILE: Final[str] = "pv_cache.json"
GROUP_CACHE_FILE: Final[str] = "group_cache.json"

# Telegram Limits
MAX_MESSAGE_LENGTH: Final[int] = 4096
MAX_CAPTION_LENGTH: Final[int] = 1024
MAX_FILE_SIZE: Final[int] = 52428800  # 50MB in bytes
MAX_VOICE_DURATION: Final[int] = 3600  # 1 hour in seconds
TELEGRAM_FLOOD_WAIT_MIN: Final[int] = 1
TELEGRAM_FLOOD_WAIT_MAX: Final[int] = 120

# AI/LLM Configuration
DEFAULT_MODEL: Final[str] = "deepseek/deepseek-chat"
DEFAULT_MAX_TOKENS: Final[int] = 1500
DEFAULT_TEMPERATURE: Final[float] = 0.7
MIN_TEMPERATURE: Final[float] = 0.0
MAX_TEMPERATURE: Final[float] = 2.0
DEFAULT_TOP_P: Final[float] = 1.0
DEFAULT_FREQUENCY_PENALTY: Final[float] = 0.0
DEFAULT_PRESENCE_PENALTY: Final[float] = 0.0

# API Configuration
API_TIMEOUT_SECONDS: Final[int] = 30
API_MAX_RETRIES: Final[int] = 3
API_RETRY_DELAY_BASE: Final[float] = 1.0
API_RETRY_DELAY_MAX: Final[float] = 60.0
RATE_LIMIT_WINDOW_SECONDS: Final[int] = 60
RATE_LIMIT_MAX_REQUESTS: Final[int] = 20

# Audio Processing
AUDIO_SAMPLE_RATE: Final[int] = 16000
AUDIO_CHANNELS: Final[int] = 1
AUDIO_FORMAT: Final[str] = "wav"
MAX_AUDIO_FILE_SIZE: Final[int] = 10485760  # 10MB in bytes
SUPPORTED_AUDIO_FORMATS: Final[tuple] = ("mp3", "wav", "ogg", "m4a", "flac")

# Cache Configuration
CACHE_TTL_SECONDS: Final[int] = 3600  # 1 hour
CACHE_MAX_SIZE: Final[int] = 1000
CACHE_CLEANUP_INTERVAL: Final[int] = 300  # 5 minutes

# CLI Configuration
CLI_MENU_WIDTH: Final[int] = 60
CLI_MAX_DISPLAY_ITEMS: Final[int] = 20
CLI_INPUT_TIMEOUT: Final[int] = 300  # 5 minutes
CLI_CLEAR_SCREEN_LINES: Final[int] = 50

# Logging Configuration
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
LOG_MAX_FILE_SIZE: Final[int] = 10485760  # 10MB
LOG_BACKUP_COUNT: Final[int] = 5
LOG_ENCODING: Final[str] = "utf-8"

# Commands
COMMAND_PREFIX: Final[str] = "/"
CONFIRMATION_KEYWORD: Final[str] = "confirm"
CANCEL_KEYWORD: Final[str] = "cancel"

# Persian/Farsi Specific
DEFAULT_TTS_VOICE_FA: Final[str] = "fa-IR-DilaraNeural"
DEFAULT_TTS_VOICE_EN: Final[str] = "en-US-AriaNeural"
PERSIAN_TIMEZONE: Final[str] = "Asia/Tehran"

# File Paths (relative to project root)
DEFAULT_CACHE_DIR: Final[str] = "cache"
DEFAULT_LOGS_DIR: Final[str] = "logs"
DEFAULT_TEMP_DIR: Final[str] = "temp"
DEFAULT_BACKUP_DIR: Final[str] = "backups"

# Regex Patterns
PHONE_NUMBER_PATTERN: Final[str] = r"^\+?[1-9]\d{1,14}$"
USERNAME_PATTERN: Final[str] = r"^@?[a-zA-Z0-9_]{5,32}$"
COMMAND_PATTERN: Final[str] = r"^/(\w+)(?:=(.+))?$"
URL_PATTERN: Final[str] = r"https?://[^\s]+"

# Time Configuration
DEFAULT_TIMEZONE: Final[str] = "UTC"
DATETIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT: Final[str] = "%Y-%m-%d"
TIME_FORMAT: Final[str] = "%H:%M:%S"

# Analysis Configuration
DEFAULT_MAX_ANALYZE_MESSAGES: Final[int] = 5000
MIN_ANALYZE_MESSAGES: Final[int] = 1
MAX_ANALYZE_MESSAGES: Final[int] = 10000
ANALYSIS_CHUNK_SIZE: Final[int] = 100

# Monitoring Configuration
MONITOR_CHECK_INTERVAL: Final[float] = 0.5  # seconds
MONITOR_QUEUE_MAX_SIZE: Final[int] = 1000
MONITOR_BATCH_SIZE: Final[int] = 10

# Error Messages
ERROR_CONFIG_NOT_FOUND: Final[str] = "Configuration file not found"
ERROR_INVALID_CONFIG: Final[str] = "Invalid configuration"
ERROR_AUTH_FAILED: Final[str] = "Authentication failed"
ERROR_PERMISSION_DENIED: Final[str] = "Permission denied"
ERROR_API_KEY_MISSING: Final[str] = "API key is missing"
ERROR_NETWORK_ERROR: Final[str] = "Network error occurred"
ERROR_TIMEOUT: Final[str] = "Operation timed out"
ERROR_RATE_LIMIT: Final[str] = "Rate limit exceeded"
ERROR_INVALID_INPUT: Final[str] = "Invalid input provided"
ERROR_FILE_NOT_FOUND: Final[str] = "File not found"

# Success Messages
SUCCESS_CONFIG_LOADED: Final[str] = "Configuration loaded successfully"
SUCCESS_AUTHENTICATED: Final[str] = "Authentication successful"
SUCCESS_MESSAGE_SENT: Final[str] = "Message sent successfully"
SUCCESS_FILE_SAVED: Final[str] = "File saved successfully"
SUCCESS_CACHE_UPDATED: Final[str] = "Cache updated successfully"


class CommandType(Enum):
    """Enumeration of available command types."""
    PROMPT = "prompt"
    TRANSLATE = "translate"
    ANALYZE = "analyze"
    TELLME = "tellme"
    STT = "stt"
    TTS = "tts"
    HELP = "help"
    STATUS = "status"
    CONFIG = "config"
    CUSTOM = "custom"


class MessageType(Enum):
    """Enumeration of message types."""
    TEXT = auto()
    VOICE = auto()
    AUDIO = auto()
    VIDEO = auto()
    DOCUMENT = auto()
    PHOTO = auto()
    STICKER = auto()
    LOCATION = auto()
    CONTACT = auto()
    POLL = auto()


class ChatType(Enum):
    """Enumeration of chat types."""
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"
    FORUM = "forum"


class UserRole(Enum):
    """Enumeration of user roles."""
    OWNER = "owner"
    ADMIN = "admin"
    AUTHORIZED = "authorized"
    USER = "user"
    RESTRICTED = "restricted"
    BANNED = "banned"


class ProcessingStatus(Enum):
    """Enumeration of processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class CacheStatus(Enum):
    """Enumeration of cache statuses."""
    HIT = "hit"
    MISS = "miss"
    EXPIRED = "expired"
    INVALID = "invalid"
    UPDATING = "updating"


class LogLevel(Enum):
    """Enumeration of log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# System Messages
SYSTEM_MESSAGES = {
    "startup": f"{APP_NAME} v{APP_VERSION} starting...",
    "shutdown": f"{APP_NAME} shutting down...",
    "ready": f"{APP_NAME} is ready!",
    "processing": "Processing your request...",
    "thinking": "Thinking...",
    "typing": "Typing...",
    "uploading": "Uploading...",
    "downloading": "Downloading...",
    "converting": "Converting...",
    "analyzing": "Analyzing messages...",
    "translating": "Translating text...",
    "transcribing": "Transcribing audio...",
    "generating": "Generating response...",
}

# Emoji Constants
EMOJI = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "processing": "⏳",
    "completed": "✨",
    "failed": "💔",
    "robot": "🤖",
    "speech": "💬",
    "voice": "🎤",
    "audio": "🎧",
    "document": "📄",
    "folder": "📁",
    "settings": "⚙️",
    "lock": "🔒",
    "unlock": "🔓",
    "key": "🔑",
    "search": "🔍",
    "refresh": "🔄",
    "save": "💾",
    "delete": "🗑️",
    "edit": "✏️",
    "copy": "📋",
    "paste": "📌",
    "star": "⭐",
    "heart": "❤️",
    "fire": "🔥",
    "lightning": "⚡",
    "clock": "🕐",
    "calendar": "📅",
    "globe": "🌍",
    "mail": "📧",
    "phone": "📱",
    "computer": "💻",
}

# Language Codes
LANGUAGES = {
    "en": "English",
    "fa": "Persian (Farsi)",
    "ar": "Arabic", 
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "hi": "Hindi",
    "tr": "Turkish",
}

# TTS Voices by Language
TTS_VOICES = {
    "fa": ["fa-IR-DilaraNeural", "fa-IR-FaridNeural"],
    "en": ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural"],
    "ar": ["ar-SA-HamedNeural", "ar-SA-ZariyahNeural"],
    "es": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"],
    "fr": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural"],
    "de": ["de-DE-KatjaNeural", "de-DE-ConradNeural"],
    "it": ["it-IT-ElsaNeural", "it-IT-DiegoNeural"],
    "pt": ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "ru": ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"],
    "zh": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
    "ja": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"],
    "ko": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"],
    "hi": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"],
    "tr": ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"],
}