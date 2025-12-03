"""Modern configuration management using Pydantic."""

import os
import configparser
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import List
from .constants import (
    CONFIG_FILE_NAME,
    DEFAULT_MAX_ANALYZE_MESSAGES,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_MODEL_PRO,
    DEFAULT_GEMINI_MODEL_FLASH,
    DEFAULT_OPENROUTER_MODEL_PRO,
    DEFAULT_OPENROUTER_MODEL_FLASH,
    DEFAULT_TTS_VOICE,
    DEFAULT_FLUX_WORKER_URL,
    DEFAULT_SDXL_WORKER_URL
)
from .exceptions import ConfigurationError


class Config(BaseSettings):
    """Main configuration class using Pydantic for validation."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Telegram Configuration
    telegram_api_id: int = Field(..., description="Telegram API ID")
    telegram_api_hash: str = Field(..., description="Telegram API Hash")
    telegram_phone_number: str = Field(..., description="Telegram Phone Number")
    telegram_session_name: str = Field(default="sakaibot_session", description="Telegram Session Name")
    
    # LLM Provider Configuration
    llm_provider: str = Field(default="openrouter", description="LLM Provider (openrouter or gemini)")
    
    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API Key (fallback)")
    openrouter_model: str = Field(default=DEFAULT_OPENROUTER_MODEL, description="OpenRouter Model Name (legacy)")
    openrouter_model_pro: str = Field(default=DEFAULT_OPENROUTER_MODEL_PRO, description="OpenRouter Pro Model (complex tasks)")
    openrouter_model_flash: str = Field(default=DEFAULT_OPENROUTER_MODEL_FLASH, description="OpenRouter Flash Model (simple tasks)")
    
    # Google Gemini Configuration - Multiple API Keys with rotation
    gemini_api_key: Optional[str] = Field(default=None, description="Primary Gemini API Key (legacy, also used as key 1)")
    gemini_api_key_1: Optional[str] = Field(default=None, description="Gemini API Key 1 (Primary)")
    gemini_api_key_2: Optional[str] = Field(default=None, description="Gemini API Key 2 (Fallback 1)")
    gemini_api_key_3: Optional[str] = Field(default=None, description="Gemini API Key 3 (Fallback 2)")
    gemini_model: str = Field(default=DEFAULT_GEMINI_MODEL, description="Gemini Model Name (legacy)")
    gemini_model_pro: str = Field(default=DEFAULT_GEMINI_MODEL_PRO, description="Gemini Pro Model (complex tasks: analyze, tellme, prompt)")
    gemini_model_flash: str = Field(default=DEFAULT_GEMINI_MODEL_FLASH, description="Gemini Flash Model (simple tasks: translate, image)")
    
    # UserBot Configuration
    userbot_max_analyze_messages: int = Field(
        default=DEFAULT_MAX_ANALYZE_MESSAGES,
        description="Maximum messages to analyze",
        ge=1,
        le=10000
    )
    
    # Paths Configuration
    paths_ffmpeg_executable: Optional[str] = Field(default=None, description="Path to FFmpeg executable")
    
    # Image Generation Configuration
    flux_worker_url: str = Field(
        default=DEFAULT_FLUX_WORKER_URL,
        description="Flux Cloudflare Worker endpoint URL"
    )
    sdxl_worker_url: str = Field(
        default=DEFAULT_SDXL_WORKER_URL,
        description="SDXL Cloudflare Worker endpoint URL"
    )
    sdxl_api_key: Optional[str] = Field(default=None, description="SDXL Worker Bearer token")
    
    # Application Settings
    environment: str = Field(default="production", description="Environment (development/production)")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    @field_validator("telegram_api_id")
    @classmethod
    def validate_api_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Telegram API ID must be positive")
        return v
    
    @field_validator("telegram_api_hash")
    @classmethod
    def validate_api_hash(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("Telegram API Hash must be at least 10 characters")
        return v
    
    @field_validator("telegram_phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not v or not v.startswith("+"):
            raise ValueError("Phone number must start with +")
        return v
    
    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        if v not in ["openrouter", "gemini"]:
            raise ValueError("LLM provider must be 'openrouter' or 'gemini'")
        return v
    
    @field_validator("openrouter_api_key")
    @classmethod
    def validate_openrouter_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate OpenRouter API key format."""
        if not v:
            return None
        # Check for placeholder values
        if "YOUR_OPENROUTER_API_KEY_HERE" in v or "YOUR_API_KEY" in v.upper():
            return None
        # Minimum length check
        if len(v) < 10:
            return None
        # Basic format validation (OpenRouter keys are typically alphanumeric with dashes/underscores)
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            return None
        return v
    
    @field_validator("gemini_api_key", "gemini_api_key_1", "gemini_api_key_2", "gemini_api_key_3")
    @classmethod
    def validate_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Gemini API key format."""
        if not v:
            return None
        # Check for placeholder values
        if "YOUR_GEMINI_API_KEY_HERE" in v or "YOUR_API_KEY" in v.upper():
            return None
        # Minimum length check
        if len(v) < 10:
            return None
        # Google API keys typically start with "AIza" or are base64-like
        # Basic format validation
        if not all(c.isalnum() or c in ['-', '_', '='] for c in v):
            return None
        return v
    
    @property
    def gemini_api_keys(self) -> List[str]:
        """Get all available Gemini API keys for rotation."""
        keys = []
        # Collect all valid keys, prioritizing numbered keys
        for key in [self.gemini_api_key_1, self.gemini_api_key_2, self.gemini_api_key_3]:
            if key and len(key) > 10:
                keys.append(key)
        
        # If no numbered keys, fall back to legacy gemini_api_key
        if not keys and self.gemini_api_key and len(self.gemini_api_key) > 10:
            keys.append(self.gemini_api_key)
        
        return keys
    
    @field_validator("paths_ffmpeg_executable")
    @classmethod
    def validate_ffmpeg_path(cls, v: Optional[str]) -> Optional[str]:
        # Skip validation for Windows paths when running on Linux/WSL
        if v and v.startswith("C:\\"):
            # Windows path, skip validation on Linux
            return v
        if v and not Path(v).exists():
            # Only validate if it's a Unix-style path
            import platform
            if platform.system() != "Windows":
                # On non-Windows, just warn but don't fail
                print(f"Warning: FFmpeg executable not found at: {v}")
            return v
        return v
    
    @field_validator("flux_worker_url")
    @classmethod
    def validate_flux_worker_url(cls, v: str) -> str:
        """Validate Flux worker URL format."""
        if not v:
            raise ValueError("Flux worker URL cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Flux worker URL must start with http:// or https://")
        return v
    
    @field_validator("sdxl_worker_url")
    @classmethod
    def validate_sdxl_worker_url(cls, v: str) -> str:
        """Validate SDXL worker URL format."""
        if not v:
            raise ValueError("SDXL worker URL cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("SDXL worker URL must start with http:// or https://")
        return v
    
    @field_validator("sdxl_api_key")
    @classmethod
    def validate_sdxl_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate SDXL API key format."""
        if not v:
            return None
        # Check for placeholder values
        if "YOUR_SDXL_API_KEY_HERE" in v or "YOUR_API_KEY" in v.upper():
            return None
        # Minimum length check
        if len(v) < 10:
            return None
        # Basic format validation (Bearer tokens are typically alphanumeric with dashes/underscores)
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            return None
        return v
    
    @property
    def is_ai_enabled(self) -> bool:
        """Check if AI features are properly configured."""
        if self.llm_provider == "openrouter":
            return bool(
                self.openrouter_api_key
                and "YOUR_OPENROUTER_API_KEY_HERE" not in (self.openrouter_api_key or "")
                and len(self.openrouter_api_key or "") > 10
            )
        elif self.llm_provider == "gemini":
            # Check if any Gemini API key is available
            return len(self.gemini_api_keys) > 0
        return False
    
    @property
    def is_image_generation_enabled(self) -> bool:
        """Check if image generation is properly configured."""
        # Flux doesn't require API key, just URL
        # SDXL requires both URL and API key
        flux_configured = bool(
            self.flux_worker_url
            and self.flux_worker_url.startswith(("http://", "https://"))
        )
        sdxl_configured = bool(
            self.sdxl_worker_url
            and self.sdxl_worker_url.startswith(("http://", "https://"))
            and self.sdxl_api_key
            and "YOUR_SDXL_API_KEY_HERE" not in (self.sdxl_api_key or "")
            and len(self.sdxl_api_key or "") > 10
        )
        return flux_configured or sdxl_configured
    
    @property
    def ffmpeg_path_resolved(self) -> Optional[str]:
        """Get resolved FFmpeg path."""
        return self.paths_ffmpeg_executable
    
    @classmethod
    def load_from_ini(cls, config_file: str = CONFIG_FILE_NAME) -> "Config":
        """Load configuration from INI file for backward compatibility."""
        if not os.path.exists(config_file):
            raise ConfigurationError(f"Configuration file '{config_file}' not found")
        
        config_parser = configparser.ConfigParser()
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_parser.read_file(f)
        except Exception as e:
            raise ConfigurationError(f"Could not read '{config_file}': {e}")
        
        # Extract values from INI and convert to environment-style keys
        env_values = {}
        
        # Map INI sections to environment variables
        section_mappings = {
            "Telegram": {
                "api_id": "TELEGRAM_API_ID",
                "api_hash": "TELEGRAM_API_HASH",
                "phone_number": "TELEGRAM_PHONE_NUMBER"
            },
            "UserBot": {
                "session_name": "TELEGRAM_SESSION_NAME",
                "max_analyze_messages": "USERBOT_MAX_ANALYZE_MESSAGES"
            },
            "LLM": {
                "provider": "LLM_PROVIDER"
            },
            "OpenRouter": {
                "api_key": "OPENROUTER_API_KEY",
                "model": "OPENROUTER_MODEL"
            },
            "Gemini": {
                "api_key": "GEMINI_API_KEY",
                "model": "GEMINI_MODEL"
            },
            "Paths": {
                "ffmpeg_executable": "PATHS_FFMPEG_EXECUTABLE"
            }
        }
        
        for section_name, key_mappings in section_mappings.items():
            if config_parser.has_section(section_name):
                for ini_key, env_key in key_mappings.items():
                    if config_parser.has_option(section_name, ini_key):
                        env_values[env_key] = config_parser.get(section_name, ini_key)
        
        # Create config from parsed values
        return cls(**env_values)


def load_config() -> Config:
    """Load configuration from .env file or config.ini."""
    try:
        # Try loading from .env first (modern approach)
        if os.path.exists(".env"):
            return Config()
        
        # Fall back to config.ini (legacy support)
        if os.path.exists(CONFIG_FILE_NAME):
            return Config.load_from_ini()
        
        raise ConfigurationError("No configuration file found (.env or config.ini)")
    
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"Failed to load configuration: {e}")


# Global settings instance (loaded lazily)
settings: Optional[Config] = None

def get_settings() -> Config:
    """Get or create the global settings instance."""
    global settings
    if settings is None:
        settings = load_config()
    return settings
