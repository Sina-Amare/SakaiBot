"""
Configuration management module for SakaiBot.

This module handles all configuration loading, validation, and environment variable management
using Pydantic for type safety and validation.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from pydantic import BaseSettings, Field, validator, SecretStr
from pydantic.types import PositiveInt


class Environment(str, Enum):
    """Application environment enumeration."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class TelegramConfig(BaseSettings):
    """Telegram API configuration."""
    
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: SecretStr = Field(..., description="Telegram API Hash")
    phone_number: str = Field(..., description="Phone number for Telegram account")
    session_name: str = Field(default="sakaibot_session", description="Session file name")
    
    class Config:
        env_prefix = "TELEGRAM_"


class OpenRouterConfig(BaseSettings):
    """OpenRouter API configuration for LLM interactions."""
    
    api_key: SecretStr = Field(..., description="OpenRouter API key")
    model_name: str = Field(
        default="deepseek/deepseek-chat",
        description="Default model to use"
    )
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    max_tokens: PositiveInt = Field(default=1500, description="Maximum tokens for responses")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Model temperature")
    timeout: PositiveInt = Field(default=30, description="API timeout in seconds")
    max_retries: PositiveInt = Field(default=3, description="Maximum retry attempts")
    
    @validator("temperature")
    def validate_temperature(cls, v: float) -> float:
        """Ensure temperature is within valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v
    
    class Config:
        env_prefix = "OPENROUTER_"


class UserBotConfig(BaseSettings):
    """UserBot specific configuration."""
    
    max_analyze_messages: PositiveInt = Field(
        default=5000,
        description="Maximum messages to analyze in a single operation"
    )
    max_message_length: PositiveInt = Field(
        default=4096,
        description="Maximum length for a single message"
    )
    confirmation_keyword: str = Field(
        default="confirm",
        description="Keyword for confirming forwarded commands"
    )
    default_tts_voice: str = Field(
        default="fa-IR-DilaraNeural",
        description="Default TTS voice for edge-tts"
    )
    
    class Config:
        env_prefix = "USERBOT_"


class PathConfig(BaseSettings):
    """File path configuration."""
    
    ffmpeg_executable: Optional[Path] = Field(
        default=None,
        description="Path to FFmpeg executable"
    )
    cache_dir: Path = Field(
        default=Path("cache"),
        description="Directory for cache files"
    )
    logs_dir: Path = Field(
        default=Path("logs"),
        description="Directory for log files"
    )
    session_dir: Path = Field(
        default=Path("."),
        description="Directory for session files"
    )
    
    @validator("cache_dir", "logs_dir", "session_dir", pre=True)
    def create_directories(cls, v: Path) -> Path:
        """Ensure directories exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @validator("ffmpeg_executable", pre=True)
    def validate_ffmpeg(cls, v: Optional[str]) -> Optional[Path]:
        """Validate FFmpeg executable path."""
        if v:
            path = Path(v)
            if not path.exists() or not path.is_file():
                raise ValueError(f"FFmpeg executable not found at: {v}")
            return path
        return None
    
    class Config:
        env_prefix = "PATH_"


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Default logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file_name: str = Field(
        default="sakaibot.log",
        description="Log file name"
    )
    max_file_size: PositiveInt = Field(
        default=10485760,  # 10MB
        description="Maximum log file size in bytes"
    )
    backup_count: PositiveInt = Field(
        default=5,
        description="Number of backup log files to keep"
    )
    
    @validator("level")
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}")
        return v.upper()
    
    class Config:
        env_prefix = "LOGGING_"


class Settings(BaseSettings):
    """Main application settings."""
    
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Current environment"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode flag"
    )
    
    # Sub-configurations
    telegram: TelegramConfig
    openrouter: OpenRouterConfig
    userbot: UserBotConfig
    paths: PathConfig
    logging: LoggingConfig
    
    # Optional API configurations
    assemblyai_api_key: Optional[SecretStr] = Field(
        default=None,
        env="ASSEMBLYAI_API_KEY",
        description="AssemblyAI API key for STT"
    )
    elevenlabs_api_key: Optional[SecretStr] = Field(
        default=None,
        env="ELEVENLABS_API_KEY",
        description="ElevenLabs API key for TTS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            """Priority: init_settings > env > file."""
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )
    
    @classmethod
    def load_from_env(cls) -> "Settings":
        """
        Load settings from environment variables and .env file.
        
        Returns:
            Settings: Validated settings instance
            
        Raises:
            ValidationError: If required settings are missing or invalid
        """
        # Load sub-configurations
        telegram = TelegramConfig()
        openrouter = OpenRouterConfig()
        userbot = UserBotConfig()
        paths = PathConfig()
        logging = LoggingConfig()
        
        # Create main settings
        return cls(
            telegram=telegram,
            openrouter=openrouter,
            userbot=userbot,
            paths=paths,
            logging=logging
        )
    
    def get_safe_dict(self) -> Dict[str, Any]:
        """
        Get settings as dictionary with sensitive values masked.
        
        Returns:
            Dict[str, Any]: Settings dictionary with masked secrets
        """
        data = self.dict()
        
        # Mask sensitive fields
        sensitive_paths = [
            ("telegram", "api_hash"),
            ("openrouter", "api_key"),
            ("assemblyai_api_key",),
            ("elevenlabs_api_key",),
        ]
        
        for path in sensitive_paths:
            current = data
            for key in path[:-1]:
                if key in current:
                    current = current[key]
            
            last_key = path[-1]
            if last_key in current and current[last_key]:
                current[last_key] = "***MASKED***"
        
        return data


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the settings singleton.
    
    Returns:
        Settings: Application settings instance
        
    Raises:
        ValidationError: If settings are invalid
    """
    global _settings
    if _settings is None:
        _settings = Settings.load_from_env()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload settings from environment.
    
    Returns:
        Settings: Fresh settings instance
    """
    global _settings
    _settings = Settings.load_from_env()
    return _settings