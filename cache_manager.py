# -*- coding: utf-8 -*-
# English comments as per our rules

import json
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
PV_CACHE_FILE = "pv_cache.json"
GROUP_CACHE_FILE = "group_cache.json" # New cache file for groups

# --- PV Cache Functions (from previous version, unchanged) ---
def load_pv_cache():
    if not os.path.exists(PV_CACHE_FILE):
        logger.info(f"Cache file '{PV_CACHE_FILE}' not found. No PV cache to load.")
        return None, None
    try:
        with open(PV_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            pvs_list = cache_data.get('pvs')
            last_updated_str = cache_data.get('last_updated_utc')
            if not pvs_list:
                logger.info(f"Cache file '{PV_CACHE_FILE}' exists but contains no PV data.")
                return None, None
            if last_updated_str:
                if last_updated_str.endswith('Z'):
                     last_updated_dt = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                else:
                     last_updated_dt = datetime.fromisoformat(last_updated_str)
                last_updated_dt = last_updated_dt.replace(tzinfo=timezone.utc)
                logger.info(f"PV cache loaded successfully. Last updated: {last_updated_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                return pvs_list, last_updated_dt
            else:
                logger.warning(f"PV Cache file '{PV_CACHE_FILE}' no 'last_updated_utc'. Considered stale.")
                return pvs_list, None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from PV cache file '{PV_CACHE_FILE}'. Cache is corrupt.")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error loading PV cache: {e}", exc_info=True)
        return None, None

def save_pv_cache(pvs_data: list):
    if not isinstance(pvs_data, list): # Basic type check
        logger.error("Invalid data type for pvs_data in save_pv_cache. Expected list.")
        return
    try:
        current_time_utc = datetime.now(timezone.utc)
        timestamp_str = current_time_utc.isoformat().replace('+00:00', 'Z')
        cache_data = {
            'last_updated_utc': timestamp_str,
            'count': len(pvs_data),
            'pvs': pvs_data
        }
        with open(PV_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        logger.info(f"PV cache ({len(pvs_data)} entries) saved to '{PV_CACHE_FILE}' at {timestamp_str}.")
    except Exception as e:
        logger.error(f"Error saving PV cache: {e}", exc_info=True)

async def get_pvs(client, telegram_utils_module, force_refresh: bool = False):
    logger.info(f"Getting PVs... (Force refresh: {force_refresh})")
    cached_pvs, last_updated_dt = load_pv_cache()
    if not force_refresh and cached_pvs is not None:
        logger.info("Using cached PVs.")
        return cached_pvs
    if force_refresh:
        logger.info("Forcing refresh of PV data from Telegram.")
    else:
        logger.info("No valid PV cache found or refresh needed. Fetching PV data from Telegram.")
    fresh_pvs = await telegram_utils_module.fetch_all_private_chats(client)
    if fresh_pvs is not None:
        save_pv_cache(fresh_pvs)
        return fresh_pvs
    elif cached_pvs is not None:
        logger.warning("Failed to fetch fresh PV data, using old PV cache.")
        return cached_pvs
    else:
        logger.error("Failed to fetch fresh PV data and no PV cache available.")
        return []

# --- Group Cache Functions (New) ---
def load_group_cache():
    """
    Loads the Group list and the last updated timestamp from the JSON cache file.
    """
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
    """
    Saves the Group list and the current UTC timestamp to the JSON cache file.
    """
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
    """
    Gets the list of qualifying Groups, either from cache or by fetching from Telegram.
    """
    logger.info(f"Getting Groups... (Force refresh: {force_refresh}, Require Admin: {require_admin_rights})")
    # For groups, the cache key might depend on require_admin_rights if we stored them differently.
    # For now, assume one cache file for groups fetched with admin rights.
    cached_groups, last_updated_dt = load_group_cache()

    # Simple cache strategy: if cache exists and not force_refresh, use it.
    # Add smart update later (e.g., if cache is older than X days, or fetch diffs).
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
    elif cached_groups is not None: # Fetch failed, but old cache exists
        logger.warning("Failed to fetch fresh Group data, using old Group cache.")
        return cached_groups
    else: # Fetch failed, no old cache
        logger.error("Failed to fetch fresh Group data and no Group cache available.")
        return []
