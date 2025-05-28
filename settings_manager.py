# -*- coding: utf-8 -*-
# English comments as per our rules

import json
import logging
import os

logger = logging.getLogger(__name__) # Inherits logger config from main.py
SETTINGS_FILE_NAME = "sakaibot_user_settings.json"

DEFAULT_SETTINGS = {
    "selected_pv_for_categorization": None,
    "selected_target_group": None,
    "active_command_to_topic_map": {}
}

def load_user_settings():
    """
    Loads user settings from the JSON file.
    If the file doesn't exist or is invalid, returns default settings.
    """
    if not os.path.exists(SETTINGS_FILE_NAME):
        logger.info(f"Settings file '{SETTINGS_FILE_NAME}' not found. Using default settings.")
        return DEFAULT_SETTINGS.copy() # Return a copy to avoid modifying defaults

    try:
        with open(SETTINGS_FILE_NAME, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
            # Ensure all keys from DEFAULT_SETTINGS are present, fill with default if missing
            for key, default_value in DEFAULT_SETTINGS.items():
                if key not in settings_data:
                    logger.warning(f"Key '{key}' not found in settings file. Using default value: {default_value}")
                    settings_data[key] = default_value
            logger.info(f"User settings loaded successfully from '{SETTINGS_FILE_NAME}'.")
            return settings_data
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from settings file '{SETTINGS_FILE_NAME}'. Using default settings.")
        return DEFAULT_SETTINGS.copy()
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading settings: {e}", exc_info=True)
        return DEFAULT_SETTINGS.copy()

def save_user_settings(settings_data: dict):
    """
    Saves the provided user settings to the JSON file.

    Args:
        settings_data (dict): A dictionary containing the settings to save.
                              Expected keys: "selected_pv_for_categorization",
                                             "selected_target_group",
                                             "active_command_to_topic_map".
    """
    try:
        # Ensure all expected keys are present before saving
        # This also helps to maintain a consistent structure in the JSON file.
        data_to_save = {}
        for key in DEFAULT_SETTINGS.keys():
            data_to_save[key] = settings_data.get(key, DEFAULT_SETTINGS[key])
            
        with open(SETTINGS_FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        logger.info(f"User settings saved successfully to '{SETTINGS_FILE_NAME}'.")
    except Exception as e:
        logger.error(f"An error occurred while saving user settings: {e}", exc_info=True)

# Example usage (for testing, not for final use here):
# if __name__ == '__main__':
#     # Test loading (file might not exist initially)
#     current_settings = load_user_settings()
#     print("Loaded settings:", current_settings)

#     # Modify some settings
#     current_settings["selected_target_group"] = {"id": -100123, "title": "Test Group"}
#     current_settings["active_command_to_topic_map"] = {"testcmd": 12345}
    
#     # Test saving
#     save_user_settings(current_settings)
    
#     # Test loading again
#     reloaded_settings = load_user_settings()
#     print("Reloaded settings:", reloaded_settings)

#     if reloaded_settings["selected_target_group"] and \
#        reloaded_settings["selected_target_group"]["id"] == -100123:
#         print("Settings save and load test successful for group.")
#     else:
#         print("Settings save and load test FAILED for group.")

#     if reloaded_settings["active_command_to_topic_map"].get("testcmd") == 12345:
#         print("Settings save and load test successful for command map.")
#     else:
#         print("Settings save and load test FAILED for command map.")
