"""Settings management for SakaiBot."""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from .constants import SETTINGS_FILE_NAME
from .exceptions import ConfigurationError
from ..utils.logging import get_logger


class SettingsManager:
    """Manages user settings persistence."""
    
    def __init__(self, settings_file: str = SETTINGS_FILE_NAME) -> None:
        self._settings_file = Path(settings_file)
        self._logger = get_logger(self.__class__.__name__)
        
        self._default_settings = {
            "selected_target_group": None,
            "active_command_to_topic_map": {},
            "directly_authorized_pvs": []
        }
    
    def load_user_settings(self) -> Dict[str, Any]:
        """Load user settings from JSON file.
        
        Returns default settings if file doesn't exist or is invalid.
        Ensures all default keys are present.
        """
        if not self._settings_file.exists():
            self._logger.info(f"Settings file '{self._settings_file}' not found. Using default settings")
            return self._default_settings.copy()
        
        try:
            with self._settings_file.open('r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            # Merge with defaults to ensure all keys are present
            loaded_settings = self._default_settings.copy()
            for key, default_value in self._default_settings.items():
                loaded_value = settings_data.get(key, default_value)
                
                # Validate data types
                if key == "active_command_to_topic_map":
                    if not isinstance(loaded_value, dict):
                        self._logger.warning(f"Loaded '{key}' is not a dict. Resetting to default")
                        loaded_value = {}
                    else:
                        # Further validate the contents of the command map
                        from ..cli.utils import normalize_command_mappings
                        normalized = normalize_command_mappings(loaded_value)
                        if normalized != loaded_value:
                            self._logger.warning(f"Loaded '{key}' had an invalid format and was normalized.")
                            loaded_value = normalized
                elif key == "directly_authorized_pvs" and not isinstance(loaded_value, list):
                    self._logger.warning(f"Loaded '{key}' is not a list. Resetting to default")
                    loaded_value = []
                
                loaded_settings[key] = loaded_value
            
            # Log loaded authorized PVs
            auth_pvs = loaded_settings.get("directly_authorized_pvs", [])
            self._logger.info(f"User settings loaded. Authorized PVs count: {len(auth_pvs)}")
            if auth_pvs:
                self._logger.debug(f"Loaded authorized PVs: {auth_pvs}")
            
            return loaded_settings
        
        except json.JSONDecodeError:
            self._logger.error(f"Error decoding JSON from settings file '{self._settings_file}'. Using defaults")
            return self._default_settings.copy()
        except Exception as e:
            self._logger.error(f"Unexpected error loading settings: {e}", exc_info=True)
            return self._default_settings.copy()
    
    def save_user_settings(self, settings_data: Dict[str, Any]) -> None:
        """Save user settings to JSON file.
        
        Ensures only expected keys are saved.
        """
        try:
            # Filter to only save expected keys
            data_to_save = {}
            for key in self._default_settings.keys():
                data_to_save[key] = settings_data.get(key, self._default_settings[key])
            
            # Log authorized PVs being saved
            auth_pvs = data_to_save.get("directly_authorized_pvs", [])
            self._logger.info(f"Saving user settings. Authorized PVs count: {len(auth_pvs)}")
            if auth_pvs:
                self._logger.debug(f"Saving authorized PVs: {auth_pvs}")
            
            # Ensure parent directory exists
            self._settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with self._settings_file.open('w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            
            self._logger.info(f"User settings saved successfully to '{self._settings_file}'")
        
        except Exception as e:
            self._logger.error(f"Error saving user settings: {e}", exc_info=True)
            raise ConfigurationError(f"Failed to save user settings: {e}")
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get a copy of default settings."""
        return self._default_settings.copy()
    
    def validate_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Validate settings data structure."""
        try:
            # Check if all required keys are present
            for key in self._default_settings.keys():
                if key not in settings_data:
                    self._logger.warning(f"Missing key '{key}' in settings data")
                    return False
            
            # Validate data types
            if not isinstance(settings_data.get("active_command_to_topic_map"), dict):
                self._logger.warning("active_command_to_topic_map is not a dict")
                return False
            
            if not isinstance(settings_data.get("directly_authorized_pvs"), list):
                self._logger.warning("directly_authorized_pvs is not a list")
                return False
            
            return True
        
        except Exception as e:
            self._logger.error(f"Error validating settings: {e}")
            return False
