# -*- coding: utf-8 -*-
# English comments as per our rules

import json
import logging
import os

logger = logging.getLogger(__name__) 
SETTINGS_FILE_NAME = "sakaibot_user_settings.json"

DEFAULT_SETTINGS = {
    "selected_pv_for_categorization": None, 
    "selected_target_group": None,          
    "active_command_to_topic_map": {},      
    "directly_authorized_pvs": []           # Stores list of dicts: {'id': user_id, 'display_name': name, 'username': username}
}

def load_user_settings():
    """
    Loads user settings from the JSON file.
    If the file doesn't exist or is invalid, returns default settings.
    Ensures all default keys are present.
    """
    if not os.path.exists(SETTINGS_FILE_NAME):
        logger.info(f"Settings file '{SETTINGS_FILE_NAME}' not found. Using default settings.")
        return DEFAULT_SETTINGS.copy() 

    try:
        with open(SETTINGS_FILE_NAME, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
            
        loaded_settings_with_defaults = DEFAULT_SETTINGS.copy()
        for key, default_value in DEFAULT_SETTINGS.items():
            loaded_settings_with_defaults[key] = settings_data.get(key, default_value)
            if key == "active_command_to_topic_map" and not isinstance(loaded_settings_with_defaults[key], dict):
                logger.warning(f"Loaded 'active_command_to_topic_map' is not a dict. Resetting.")
                loaded_settings_with_defaults[key] = {} # Ensure it's a dict
            if key == "directly_authorized_pvs" and not isinstance(loaded_settings_with_defaults[key], list):
                logger.warning(f"Loaded 'directly_authorized_pvs' is not a list. Resetting.")
                loaded_settings_with_defaults[key] = [] # Ensure it's a list
        
        # Log the content of directly_authorized_pvs after loading
        auth_pvs_loaded = loaded_settings_with_defaults.get("directly_authorized_pvs", [])
        logger.info(f"User settings loaded. directly_authorized_pvs count: {len(auth_pvs_loaded)}")
        if auth_pvs_loaded:
            logger.debug(f"Loaded directly_authorized_pvs: {auth_pvs_loaded}")
            
        return loaded_settings_with_defaults
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from settings file '{SETTINGS_FILE_NAME}'. Using default settings.")
        return DEFAULT_SETTINGS.copy()
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading settings: {e}", exc_info=True)
        return DEFAULT_SETTINGS.copy()

def save_user_settings(settings_data: dict):
    """
    Saves the provided user settings to the JSON file.
    Ensures only expected keys are saved.
    """
    try:
        data_to_save = {}
        for key in DEFAULT_SETTINGS.keys(): 
            data_to_save[key] = settings_data.get(key, DEFAULT_SETTINGS[key])
        
        # Log the content of directly_authorized_pvs before saving
        auth_pvs_to_save = data_to_save.get("directly_authorized_pvs", [])
        logger.info(f"Saving user settings. directly_authorized_pvs count: {len(auth_pvs_to_save)}")
        if auth_pvs_to_save:
            logger.debug(f"Saving directly_authorized_pvs: {auth_pvs_to_save}")

        with open(SETTINGS_FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        logger.info(f"User settings saved successfully to '{SETTINGS_FILE_NAME}'.")
    except Exception as e:
        logger.error(f"An error occurred while saving user settings: {e}", exc_info=True)

