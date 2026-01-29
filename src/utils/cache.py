"""Cache management for SakaiBot."""

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Protocol

from ..core.constants import (
    PV_CACHE_FILE,
    GROUP_CACHE_FILE,
    DEFAULT_PV_FETCH_LIMIT_REFRESH,
    DEFAULT_PV_FETCH_LIMIT_INITIAL
)
from ..core.exceptions import CacheError
from .logging import get_logger


class TelegramUtilsProtocol(Protocol):
    """Protocol for telegram utils dependency."""
    
    async def fetch_all_private_chats(self, client, offset_date=None, limit=None) -> List[Dict[str, Any]]:
        ...
    
    async def fetch_user_groups(self, client, require_admin_manage_topics: bool = True) -> List[Dict[str, Any]]:
        ...


class CacheManager:
    """Manages caching for PVs and groups."""
    
    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._pv_cache_file = Path(PV_CACHE_FILE)
        self._group_cache_file = Path(GROUP_CACHE_FILE)
    
    def _load_cache_file(self, cache_file: Path) -> tuple[Optional[List[Dict[str, Any]]], Optional[datetime]]:
        """Load cache data from JSON file."""
        if not cache_file.exists():
            self._logger.info(f"Cache file '{cache_file}' not found")
            return None, None
        
        try:
            with cache_file.open('r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            data_list = cache_data.get('pvs' if 'pv' in cache_file.name else 'groups')
            last_updated_str = cache_data.get('last_updated_utc')
            
            if not isinstance(data_list, list):
                self._logger.warning(f"Data in cache file '{cache_file}' is not a list")
                return None, None
            
            if not data_list:
                self._logger.info(f"Cache file '{cache_file}' exists but contains no data")
                return [], None
            
            last_updated_dt = None
            if last_updated_str:
                try:
                    if last_updated_str.endswith('Z'):
                        last_updated_dt = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                    else:
                        last_updated_dt = datetime.fromisoformat(last_updated_str)
                    last_updated_dt = last_updated_dt.replace(tzinfo=timezone.utc)
                except ValueError as e:
                    self._logger.warning(f"Invalid timestamp in cache: {e}")
            
            self._logger.info(
                f"Cache loaded: {len(data_list)} entries, "
                f"last updated: {last_updated_dt.strftime('%Y-%m-%d %H:%M:%S %Z') if last_updated_dt else 'Unknown'}"
            )
            return data_list, last_updated_dt
        
        except json.JSONDecodeError:
            self._logger.error(f"Error decoding JSON from cache file '{cache_file}'. Cache is corrupt")
            return None, None
        except Exception as e:
            self._logger.error(f"Unexpected error loading cache: {e}", exc_info=True)
            return None, None
    
    def _save_cache_file(
        self,
        cache_file: Path,
        data: List[Dict[str, Any]],
        data_key: str
    ) -> None:
        """Save cache data to JSON file."""
        if not isinstance(data, list):
            raise CacheError(f"Invalid data type for cache. Expected list, got {type(data)}")
        
        try:
            current_time_utc = datetime.now(timezone.utc)
            timestamp_str = current_time_utc.isoformat().replace('+00:00', 'Z')
            
            cache_data = {
                'last_updated_utc': timestamp_str,
                'count': len(data),
                data_key: data
            }
            
            # Ensure parent directory exists
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with cache_file.open('w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)
            
            self._logger.info(
                f"Cache saved: {len(data)} entries to '{cache_file}' at {timestamp_str}"
            )
        
        except Exception as e:
            self._logger.error(f"Error saving cache: {e}", exc_info=True)
            raise CacheError(f"Failed to save cache: {e}")
    
    def load_pv_cache(self) -> tuple[Optional[List[Dict[str, Any]]], Optional[datetime]]:
        """Load PV cache from file."""
        return self._load_cache_file(self._pv_cache_file)
    
    def save_pv_cache(self, pvs_data: List[Dict[str, Any]]) -> None:
        """Save PV cache to file."""
        self._save_cache_file(self._pv_cache_file, pvs_data, 'pvs')
    
    def load_group_cache(self) -> tuple[Optional[List[Dict[str, Any]]], Optional[datetime]]:
        """Load group cache from file."""
        return self._load_cache_file(self._group_cache_file)
    
    def save_group_cache(self, groups_data: List[Dict[str, Any]]) -> None:
        """Save group cache to file."""
        self._save_cache_file(self._group_cache_file, groups_data, 'groups')
    
    async def get_pvs(
        self,
        client,
        telegram_utils,
        force_refresh: bool = False,
        fetch_limit_on_refresh: int = DEFAULT_PV_FETCH_LIMIT_REFRESH,
        fetch_limit_on_initial: int = DEFAULT_PV_FETCH_LIMIT_INITIAL
    ) -> List[Dict[str, Any]]:
        """Get list of PVs with caching and refresh capabilities."""
        self._logger.info(f"Getting PVs (force_refresh: {force_refresh})")
        
        # Load existing cache
        cached_pvs, _ = self.load_pv_cache()
        
        if cached_pvs is None:  # Cache is corrupt or unreadable
            self._logger.error("PV cache is corrupt or unreadable. Performing fresh fetch")
            cached_pvs = []
            force_refresh = True
        
        if not isinstance(cached_pvs, list):
            self._logger.warning("Cache data is not a list. Initializing as empty")
            cached_pvs = []
        
        if force_refresh:
            self._logger.info(f"Refreshing PV data from Telegram (limit: {fetch_limit_on_refresh})")
            try:
                fresh_pvs = await telegram_utils.fetch_all_private_chats(
                    client, limit=fetch_limit_on_refresh
                )
                
                if fresh_pvs is not None:
                    # Merge with existing cache
                    merged_pvs_dict = {pv['id']: pv for pv in cached_pvs}
                    
                    for fresh_pv in fresh_pvs:
                        merged_pvs_dict[fresh_pv['id']] = fresh_pv
                    
                    final_pvs = list(merged_pvs_dict.values())
                    final_pvs.sort(key=lambda x: x.get('display_name', '').lower())
                    
                    self.save_pv_cache(final_pvs)
                    self._logger.info(f"PV cache updated. Total PVs: {len(final_pvs)}")
                    return final_pvs
                else:
                    self._logger.warning("Failed to fetch fresh PV data during refresh")
                    return cached_pvs
            
            except Exception as e:
                self._logger.error(f"Error during PV refresh: {e}", exc_info=True)
                return cached_pvs
        
        # Not force_refresh
        if cached_pvs:
            self._logger.info(f"Using {len(cached_pvs)} PVs from existing cache")
            return cached_pvs
        else:
            # No cache exists, perform initial fetch
            self._logger.info(f"No PV cache found. Performing initial fetch (limit: {fetch_limit_on_initial})")
            try:
                initial_pvs = await telegram_utils.fetch_all_private_chats(
                    client, limit=fetch_limit_on_initial
                )
                
                if initial_pvs is not None:
                    initial_pvs.sort(key=lambda x: x.get('display_name', '').lower())
                    self.save_pv_cache(initial_pvs)
                    self._logger.info(f"Initial PV cache created with {len(initial_pvs)} PVs")
                    return initial_pvs
                else:
                    self._logger.error("Failed to fetch initial PV data")
                    return []
            
            except Exception as e:
                self._logger.error(f"Error during initial PV fetch: {e}", exc_info=True)
                return []
    
    async def get_groups(
        self,
        client,
        telegram_utils,
        force_refresh: bool = False,
        require_admin_rights: bool = True
    ) -> List[Dict[str, Any]]:
        """Get list of groups with caching and refresh capabilities."""
        self._logger.info(f"Getting groups (force_refresh: {force_refresh}, require_admin: {require_admin_rights})")
        
        cached_groups, _ = self.load_group_cache()
        
        if not force_refresh and cached_groups is not None:
            self._logger.info("Using cached groups")
            return cached_groups
        
        if force_refresh:
            self._logger.info("Forcing refresh of group data from Telegram")
        else:
            self._logger.info("No valid group cache found. Fetching from Telegram")
        
        try:
            fresh_groups = await telegram_utils.fetch_user_groups(
                client, require_admin_manage_topics=require_admin_rights
            )
            
            if fresh_groups is not None:
                self.save_group_cache(fresh_groups)
                return fresh_groups
            elif cached_groups is not None:
                self._logger.warning("Failed to fetch fresh group data, using old cache")
                return cached_groups
            else:
                self._logger.error("Failed to fetch fresh group data and no cache available")
                return []
        
        except Exception as e:
            self._logger.error(f"Error during group fetch: {e}", exc_info=True)
            if cached_groups is not None:
                return cached_groups
            return []
    
    def search_pvs(self, pvs_list: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Search PVs by query (ID, username, or display name)."""
        if not query:
            self._logger.debug("Search query is empty")
            return []
        
        results = []
        query_lower = query.lower()
        
        # Try to parse as integer for ID search
        query_as_int = None
        try:
            query_as_int = int(query)
        except ValueError:
            pass
        
        for pv in pvs_list:
            # Search by ID
            if query_as_int is not None and pv['id'] == query_as_int:
                results.append(pv)
                continue
            
            # Search by username
            pv_username = pv.get('username', '')
            if pv_username:
                pv_username_lower = pv_username.lower()
                search_username = query_lower[1:] if query_lower.startswith('@') else query_lower
                if search_username in pv_username_lower:
                    results.append(pv)
                    continue
            
            # Search by display name
            if query_lower in pv.get('display_name', '').lower():
                results.append(pv)
                continue
        
        return results
