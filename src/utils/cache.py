"""Cache management utilities for SakaiBot.

This module provides caching functionality for various data types.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching of data with TTL support."""
    
    def __init__(self, cache_dir: Path, default_ttl: int = 3600):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Path to cache file
        """
        # Sanitize key for filesystem
        safe_key = key.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_key}.json"
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if not found or expired
            
        Returns:
            Cached value or default
        """
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry['expires'] > time.time():
                return entry['value']
            else:
                del self._memory_cache[key]
        
        # Check file cache
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('expires', 0) > time.time():
                        # Store in memory cache for faster access
                        self._memory_cache[key] = data
                        return data['value']
                    else:
                        # Expired, delete file
                        cache_file.unlink()
            except Exception as e:
                logger.error(f"Error reading cache for key '{key}': {e}")
        
        return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        expires = time.time() + ttl
        
        entry = {
            'value': value,
            'expires': expires,
            'created': time.time()
        }
        
        # Store in memory cache
        self._memory_cache[key] = entry
        
        # Store in file cache
        cache_file = self._get_cache_file(key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing cache for key '{key}': {e}")
    
    async def delete(self, key: str) -> None:
        """Delete value from cache.
        
        Args:
            key: Cache key
        """
        # Remove from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        # Remove file
        cache_file = self._get_cache_file(key)
        if cache_file.exists():
            try:
                cache_file.unlink()
            except Exception as e:
                logger.error(f"Error deleting cache for key '{key}': {e}")
    
    async def clear(self) -> None:
        """Clear all cache."""
        # Clear memory cache
        self._memory_cache.clear()
        
        # Clear file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.error(f"Error deleting cache file '{cache_file}': {e}")
    
    async def cleanup_expired(self) -> int:
        """Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        cleaned = 0
        current_time = time.time()
        
        # Clean memory cache
        keys_to_delete = []
        for key, entry in self._memory_cache.items():
            if entry['expires'] <= current_time:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self._memory_cache[key]
            cleaned += 1
        
        # Clean file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('expires', 0) <= current_time:
                        cache_file.unlink()
                        cleaned += 1
            except Exception as e:
                logger.error(f"Error checking cache file '{cache_file}': {e}")
        
        return cleaned


class PVCacheManager:
    """Manages caching of Private Chat (PV) data."""
    
    def __init__(self, cache_file: Path):
        """Initialize PV cache manager.
        
        Args:
            cache_file: Path to PV cache file
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> List[Dict[str, Any]]:
        """Load PV cache from file.
        
        Returns:
            List of PV data
        """
        if not self.cache_file.exists():
            return []
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading PV cache: {e}")
            return []
    
    def save(self, pvs: List[Dict[str, Any]]) -> None:
        """Save PV data to cache file.
        
        Args:
            pvs: List of PV data
        """
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(pvs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving PV cache: {e}")
    
    def update(self, pv_id: int, data: Dict[str, Any]) -> None:
        """Update specific PV in cache.
        
        Args:
            pv_id: PV ID to update
            data: New data for the PV
        """
        pvs = self.load()
        
        # Find and update or append
        updated = False
        for i, pv in enumerate(pvs):
            if pv.get('id') == pv_id:
                pvs[i] = {**pv, **data}
                updated = True
                break
        
        if not updated:
            pvs.append(data)
        
        self.save(pvs)
    
    def remove(self, pv_id: int) -> None:
        """Remove PV from cache.
        
        Args:
            pv_id: PV ID to remove
        """
        pvs = self.load()
        pvs = [pv for pv in pvs if pv.get('id') != pv_id]
        self.save(pvs)


class GroupCacheManager:
    """Manages caching of Group data."""
    
    def __init__(self, cache_file: Path):
        """Initialize group cache manager.
        
        Args:
            cache_file: Path to group cache file
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> List[Dict[str, Any]]:
        """Load group cache from file.
        
        Returns:
            List of group data
        """
        if not self.cache_file.exists():
            return []
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading group cache: {e}")
            return []
    
    def save(self, groups: List[Dict[str, Any]]) -> None:
        """Save group data to cache file.
        
        Args:
            groups: List of group data
        """
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(groups, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving group cache: {e}")
    
    def update(self, group_id: int, data: Dict[str, Any]) -> None:
        """Update specific group in cache.
        
        Args:
            group_id: Group ID to update
            data: New data for the group
        """
        groups = self.load()
        
        # Find and update or append
        updated = False
        for i, group in enumerate(groups):
            if group.get('id') == group_id:
                groups[i] = {**group, **data}
                updated = True
                break
        
        if not updated:
            groups.append(data)
        
        self.save(groups)
    
    def remove(self, group_id: int) -> None:
        """Remove group from cache.
        
        Args:
            group_id: Group ID to remove
        """
        groups = self.load()
        groups = [g for g in groups if g.get('id') != group_id]
        self.save(groups)