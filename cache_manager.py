# -*- coding: utf-8 -*-
# English comments as per our rules

import json
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
PV_CACHE_FILE = "pv_cache.json"
GROUP_CACHE_FILE = "group_cache.json"
DEFAULT_PV_FETCH_LIMIT_FOR_REFRESH = 200 # Number of recent dialogs to check during refresh
DEFAULT_PV_FETCH_LIMIT_FOR_INITIAL = 400 # Number of recent dialogs for initial cache population

# --- PV Cache Functions ---
def load_pv_cache():
    if not os.path.exists(PV_CACHE_FILE):
        logger.info(f"Cache file '{PV_CACHE_FILE}' not found. No PV cache to load.")
        return None, None # Return None for list if not found
    try:
        with open(PV_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            pvs_list = cache_data.get('pvs')
            last_updated_str = cache_data.get('last_updated_utc')
            
            if not isinstance(pvs_list, list): # Ensure pvs_list is a list
                logger.warning(f"PV data in cache file '{PV_CACHE_FILE}' is not a list. Treating as empty.")
                pvs_list = None # Will be handled as empty cache

            if not pvs_list: # Handles None or empty list
                logger.info(f"Cache file '{PV_CACHE_FILE}' exists but contains no valid PV data.")
                return [], None # Return empty list and None for date

            if last_updated_str:
                if last_updated_str.endswith('Z'):
                    last_updated_dt = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                else:
                    last_updated_dt = datetime.fromisoformat(last_updated_str)
                last_updated_dt = last_updated_dt.replace(tzinfo=timezone.utc)
                logger.info(f"PV cache loaded successfully ({len(pvs_list)} entries). Last updated: {last_updated_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                return pvs_list, last_updated_dt
            else:
                logger.warning(f"PV Cache file '{PV_CACHE_FILE}' has no 'last_updated_utc'. Considered stale for update purposes, but data is loaded.")
                return pvs_list, None # Data is there, but no timestamp for age check
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from PV cache file '{PV_CACHE_FILE}'. Cache is corrupt.")
        return None, None # Indicate corrupt cache
    except Exception as e:
        logger.error(f"Unexpected error loading PV cache: {e}", exc_info=True)
        return None, None

def save_pv_cache(pvs_data_to_save: list):
    """Saves the provided list of PVs to the cache file."""
    if not isinstance(pvs_data_to_save, list):
        logger.error("Invalid data type for pvs_data_to_save in save_pv_cache. Expected list.")
        return
    try:
        current_time_utc = datetime.now(timezone.utc)
        timestamp_str = current_time_utc.isoformat().replace('+00:00', 'Z')
        cache_data = {
            'last_updated_utc': timestamp_str,
            'count': len(pvs_data_to_save),
            'pvs': pvs_data_to_save # Save the processed list
        }
        with open(PV_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        logger.info(f"PV cache ({len(pvs_data_to_save)} entries) saved to '{PV_CACHE_FILE}' at {timestamp_str}.")
    except Exception as e:
        logger.error(f"Error saving PV cache: {e}", exc_info=True)

async def get_pvs(client, telegram_utils_module, force_refresh: bool = False, 
                  fetch_limit_on_refresh: int = DEFAULT_PV_FETCH_LIMIT_FOR_REFRESH,
                  fetch_limit_on_initial: int = DEFAULT_PV_FETCH_LIMIT_FOR_INITIAL):
    """
    Gets the list of PVs.
    If force_refresh is True, fetches recent PVs from Telegram and merges them with the existing cache.
    Otherwise, returns the cached list. If cache is empty, performs an initial fetch.
    """
    logger.info(f"Getting PVs... (Force refresh: {force_refresh})")
    
    # Load existing cache. cached_pvs will be a list (possibly empty) or None if corrupt/unreadable.
    cached_pvs, _ = load_pv_cache()

    if cached_pvs is None: # Cache is corrupt or unreadable
        logger.error("PV cache is corrupt or unreadable. Attempting a fresh initial fetch.")
        cached_pvs = [] # Treat as empty for merging
        force_refresh = True # Force a fetch to try and rebuild

    if not isinstance(cached_pvs, list): # Should be handled by load_pv_cache, but as a safeguard
        logger.warning("load_pv_cache did not return a list. Initializing as empty list.")
        cached_pvs = []

    if force_refresh:
        logger.info(f"Refreshing PV data from Telegram (checking last ~{fetch_limit_on_refresh} dialogs)...")
        # Fetch a limited number of most recent dialogs to find active/new PVs
        freshly_fetched_active_pvs = await telegram_utils_module.fetch_all_private_chats(client, limit=fetch_limit_on_refresh)

        if freshly_fetched_active_pvs is not None: # Fetch was successful
            # Merge freshly_fetched_active_pvs with cached_pvs
            # Create a dictionary of existing cached PVs for efficient lookup and update
            # Ensures that PVs are unique by ID and details are updated if changed.
            merged_pvs_dict = {pv['id']: pv for pv in cached_pvs} # Start with existing cache

            for fresh_pv in freshly_fetched_active_pvs:
                # If PV exists in merged_pvs_dict, its details will be updated.
                # If it's a new PV, it will be added.
                merged_pvs_dict[fresh_pv['id']] = fresh_pv
            
            # Convert back to list
            final_pvs_list = list(merged_pvs_dict.values())
            # Sort by display_name for consistent ordering, could be optional
            final_pvs_list.sort(key=lambda x: x.get('display_name', '').lower())
            
            save_pv_cache(final_pvs_list)
            logger.info(f"PV cache updated/refreshed. Total PVs now in cache: {len(final_pvs_list)}.")
            return final_pvs_list
        else: # Fetch failed during refresh
            logger.warning("Failed to fetch fresh PV data during refresh. Returning existing cache (if any).")
            return cached_pvs # Return the old cache if fetch failed
    
    # Not force_refresh:
    if cached_pvs: # If cache exists and is not empty (and not corrupt)
        logger.info(f"Using {len(cached_pvs)} PVs from existing cache (no refresh requested).")
        return cached_pvs
    else: # No cache exists (or was empty/corrupt and refresh failed), and not force_refresh (e.g., first run)
        logger.info(f"No PV cache found or it's empty. Performing initial fetch from Telegram (checking last ~{fetch_limit_on_initial} dialogs)...")
        initial_pvs = await telegram_utils_module.fetch_all_private_chats(client, limit=fetch_limit_on_initial)
        
        if initial_pvs is not None:
            initial_pvs.sort(key=lambda x: x.get('display_name', '').lower())
            save_pv_cache(initial_pvs)
            logger.info(f"Initial PV cache created with {len(initial_pvs)} PVs.")
            return initial_pvs
        else:
            logger.error("Failed to fetch initial PV data and no cache available.")
            return [] # Return empty list if everything fails

# --- Group Cache Functions (remain unchanged from your provided code) ---
def load_group_cache():
    if not os.path.exists(GROUP_CACHE_FILE):
        logger.info(f"Cache file '{GROUP_CACHE_FILE}' not found. No group cache to load.")
        return None, None
    try:
        with open(GROUP_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            groups_list = cache_data.get('groups')
            last_updated_str = cache_data.get('last_updated_utc')
            if not groups_list:
                logger.info(f"Cache file '{GROUP_CACHE_FILE}' exists but contains no group data.")
                return None, None
            if last_updated_str:
                if last_updated_str.endswith('Z'):
                    last_updated_dt = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                else:
                    last_updated_dt = datetime.fromisoformat(last_updated_str)
                last_updated_dt = last_updated_dt.replace(tzinfo=timezone.utc)
                logger.info(f"Group cache loaded. Last updated: {last_updated_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                return groups_list, last_updated_dt
            else:
                logger.warning(f"Group Cache file '{GROUP_CACHE_FILE}' no 'last_updated_utc'. Considered stale.")
                return groups_list, None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from group cache file '{GROUP_CACHE_FILE}'. Cache is corrupt.")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error loading group cache: {e}", exc_info=True)
        return None, None

def save_group_cache(groups_data: list):
    if not isinstance(groups_data, list):
        logger.error("Invalid data type for groups_data in save_group_cache. Expected list.")
        return
    try:
        current_time_utc = datetime.now(timezone.utc)
        timestamp_str = current_time_utc.isoformat().replace('+00:00', 'Z')
        cache_data = {
            'last_updated_utc': timestamp_str,
            'count': len(groups_data),
            'groups': groups_data
        }
        with open(GROUP_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Group cache ({len(groups_data)} entries) saved to '{GROUP_CACHE_FILE}' at {timestamp_str}.")
    except Exception as e:
        logger.error(f"Error saving group cache: {e}", exc_info=True)

async def get_groups(client, telegram_utils_module, force_refresh: bool = False, require_admin_rights: bool = True):
    logger.info(f"Getting Groups... (Force refresh: {force_refresh}, Require Admin: {require_admin_rights})")
    cached_groups, last_updated_dt = load_group_cache()

    if not force_refresh and cached_groups is not None:
        logger.info("Using cached Groups.")
        return cached_groups

    if force_refresh:
        logger.info("Forcing refresh of Group data from Telegram.")
    else:
        logger.info("No valid Group cache found or refresh needed. Fetching Group data from Telegram.")
    
    fresh_groups = await telegram_utils_module.fetch_user_groups(client, require_admin_manage_topics=require_admin_rights)
    
    if fresh_groups is not None:
        save_group_cache(fresh_groups)
        return fresh_groups
    elif cached_groups is not None:
        logger.warning("Failed to fetch fresh Group data, using old Group cache.")
        return cached_groups
    else:
        logger.error("Failed to fetch fresh Group data and no Group cache available.")
        return []
