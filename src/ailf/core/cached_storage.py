"""Cached Local Storage Implementation.

This module provides an extension of the LocalStorage class with
in-memory caching functionality for improved performance.
"""
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from ailf.core.local_storage import LocalStorage


class CachedLocalStorage(LocalStorage):
    """LocalStorage with in-memory caching.
    
    This class extends LocalStorage to provide in-memory caching for
    frequently accessed files, reducing disk I/O operations.
    
    Example:
        >>> storage = CachedLocalStorage("./data", config={"max_cache_size": 50})
        >>> storage.save_json({"key": "value"}, "config/settings.json")
        >>> # First access reads from disk
        >>> data1 = storage.get_json("config/settings.json")
        >>> # Second access retrieves from cache
        >>> data2 = storage.get_json("config/settings.json")
    """

    def __init__(self, base_path: Optional[Union[str, Path]] = None, 
                 config: Optional[Dict[str, Any]] = None):
        """Initialize cached storage.
        
        Args:
            base_path: Base directory for all storage operations
            config: Optional configuration dictionary with cache settings
        """
        super().__init__(base_path, config)
        self._cache = OrderedDict()  # LRU cache {path: (data, timestamp)}
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values including cache settings.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        config = super()._get_default_config()
        config.update({
            "cache_enabled": True,
            "max_cache_size": 100,
            "cache_ttl": 300  # 5 minutes in seconds
        })
        return config
        
    def _initialize(self) -> None:
        """Initialize the storage system with cache setup.
        
        Creates necessary directories and initializes the cache.
        """
        super()._initialize()
        self._cache = OrderedDict()
        
    def _is_cache_enabled(self) -> bool:
        """Check if caching is enabled.
        
        Returns:
            bool: True if caching is enabled, False otherwise
        """
        return self.config.get("cache_enabled", True)
        
    def _get_from_cache(self, path: str) -> Optional[Dict]:
        """Get data from cache if it exists and is not expired.
        
        Args:
            path: Cache key (path)
            
        Returns:
            Optional[Dict]: Cached data or None if not found
        """
        if not self._is_cache_enabled() or path not in self._cache:
            return None
            
        data, timestamp = self._cache[path]
        ttl = self.config.get("cache_ttl", 300)
        
        # Check if cache entry has expired
        if ttl > 0 and time.time() - timestamp > ttl:
            # Remove expired cache entry
            del self._cache[path]
            return None
            
        # Move to end for LRU ordering
        self._cache.move_to_end(path)
        return data
        
    def _add_to_cache(self, path: str, data: Dict) -> None:
        """Add data to cache with current timestamp.
        
        Implements LRU (Least Recently Used) caching strategy.
        
        Args:
            path: Cache key (path)
            data: Data to cache
        """
        if not self._is_cache_enabled():
            return
            
        # Check if we need to make room in the cache
        max_size = self.config.get("max_cache_size", 100)
        while len(self._cache) >= max_size and self._cache:
            # Remove least recently used item
            self._cache.popitem(last=False)
            
        # Add new item to cache with current timestamp
        self._cache[path] = (data, time.time())
        
    def _invalidate_cache(self, path: str = None) -> None:
        """Invalidate cache for a specific path or all paths.
        
        Args:
            path: Path to invalidate, or None to invalidate all
        """
        if path is None:
            self._cache.clear()
        elif path in self._cache:
            del self._cache[path]
            
    def get_json(self, path: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Get JSON data from cache or file system.
        
        Attempts to get data from cache first, falls back to file system.
        
        Args:
            path: Path to get data from
            default: Default value to return if data not found

        Returns:
            Optional[Dict]: Loaded JSON data or default value
        """
        path = self._validate_path(path)
        
        # Try to get from cache first
        cached_data = self._get_from_cache(path)
        if cached_data is not None:
            return cached_data
            
        # Get from file system
        data = super().get_json(path, default)
        
        # Add to cache if data was found
        if data is not default:
            self._add_to_cache(path, data)
            
        return data
        
    def save_json(self, data: Dict, path: str) -> str:
        """Save data to file system and update cache.
        
        Args:
            data: Data to save
            path: Path where data should be saved

        Returns:
            str: Path where the data was saved
        """
        path = self._validate_path(path)
        
        # Save to file system
        result = super().save_json(data, path)
        
        # Update cache with processed data
        processed_data = self._process_data_after_load(
            self._process_data_before_save(data)
        )
        self._add_to_cache(path, processed_data)
        
        return result
        
    def delete(self, path: str) -> bool:
        """Delete an item and invalidate its cache entry.

        Args:
            path: Path to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        path = self._validate_path(path)
        
        # Invalidate cache
        self._invalidate_cache(path)
        
        # Delete from file system
        return super().delete(path)
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the current cache state.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return {
            "enabled": self._is_cache_enabled(),
            "size": len(self._cache),
            "max_size": self.config.get("max_cache_size", 100),
            "ttl": self.config.get("cache_ttl", 300),
            "paths": list(self._cache.keys())
        }
        
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._invalidate_cache()
        
    def refresh_cache(self, path: str) -> None:
        """Refresh a specific cache entry.
        
        Args:
            path: Path to refresh
            
        Returns:
            None
        """
        path = self._validate_path(path)
        self._invalidate_cache(path)
        
        # If file exists, load it into cache
        if self.exists(path):
            data = super().get_json(path)
            if data:
                self._add_to_cache(path, data)