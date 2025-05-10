"""Redis-backed distributed cache implementation for AILF agents."""

import json
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis # type: ignore

from ailf.schemas.memory import MemoryItem

class RedisDistributedCache:
    """
    Manages a distributed cache using Redis, storing MemoryItem objects.
    """

    def __init__(self, redis_url: str, default_ttl: int = 3600, key_prefix: str = "ailf:cache:"):
        """
        Initializes the Redis distributed cache.

        :param redis_url: URL for the Redis server (e.g., "redis://localhost:6379/0").
        :type redis_url: str
        :param default_ttl: Default time-to-live for cache items in seconds.
        :type default_ttl: int
        :param key_prefix: Prefix for all keys stored in Redis to avoid collisions.
        :type key_prefix: str
        """
        self.redis_client = redis.from_url(redis_url)
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

    def _get_redis_key(self, item_id: str) -> str:
        """Constructs the full Redis key with the prefix."""
        return f"{self.key_prefix}{item_id}"

    async def add_item(self, item_id: str, data: Any, ttl: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds an item to the Redis cache.

        The item is stored as a JSON serialized MemoryItem.

        :param item_id: Unique identifier for the memory item.
        :type item_id: str
        :param data: The data to store.
        :type data: Any
        :param ttl: Time-to-live for this item in seconds. Uses default_ttl if None.
                            A TTL of 0 or less means the item will not expire (persistent).
        :type ttl: Optional[int]
        :param metadata: Optional metadata associated with the item.
        :type metadata: Optional[Dict[str, Any]]
        """
        actual_ttl = ttl if ttl is not None else self.default_ttl
        redis_key = self._get_redis_key(item_id)
        
        memory_item_obj = MemoryItem(
            item_id=item_id,
            data=data,
            metadata=metadata or {}
        )
        # Pydantic v2 uses model_dump_json, v1 uses json()
        serialized_item = memory_item_obj.model_dump_json() if hasattr(memory_item_obj, 'model_dump_json') else memory_item_obj.json()

        if actual_ttl > 0:
            await self.redis_client.setex(redis_key, actual_ttl, serialized_item)
        else:
            await self.redis_client.set(redis_key, serialized_item) # Persist if ttl <= 0

    async def get_item(self, item_id: str) -> Optional[MemoryItem]:
        """
        Retrieves an item from the Redis cache.

        :param item_id: The ID of the item to retrieve.
        :type item_id: str
        :return: The MemoryItem if found, else None.
        :rtype: Optional[MemoryItem]
        """
        redis_key = self._get_redis_key(item_id)
        serialized_item = await self.redis_client.get(redis_key)
        if serialized_item:
            # Pydantic v2 uses model_validate_json, v1 uses parse_raw
            item_dict = json.loads(serialized_item)
            return MemoryItem(**item_dict)
        return None

    async def remove_item(self, item_id: str) -> bool:
        """
        Removes an item from the Redis cache.

        :param item_id: The ID of the item to remove.
        :type item_id: str
        :return: True if the item was removed (or didn't exist), False on error.
        :rtype: bool
        """
        redis_key = self._get_redis_key(item_id)
        deleted_count = await self.redis_client.delete(redis_key)
        return deleted_count >= 0 # delete returns num keys deleted, 0 if key doesn't exist

    async def list_item_ids(self, pattern: str = "*") -> List[str]:
        """
        Lists item IDs in the cache matching a pattern (relative to the key_prefix).
        Warning: `KEYS` can be slow in production Redis environments. Use with caution.

        :param pattern: The pattern to match item IDs (e.g., "user:*").
        :type pattern: str
        :return: A list of item IDs (without the global prefix).
        :rtype: List[str]
        """
        full_pattern = f"{self.key_prefix}{pattern}"
        keys_as_bytes = await self.redis_client.keys(full_pattern)
        # Decode and strip prefix
        return [key.decode('utf-8').replace(self.key_prefix, "", 1) for key in keys_as_bytes]

    async def clear_all(self, pattern: str = "*") -> int:
        """
        Clears items from the cache matching a pattern (relative to the key_prefix).
        If pattern is "*", it clears all keys managed by this cache instance (with its prefix).
        Warning: `KEYS` can be slow. For full flush, consider `FLUSHDB` or `FLUSHALL` if appropriate
        and if this client is the only user or specific to a DB.
        This method only deletes keys matching the prefix + pattern.

        :param pattern: The pattern to match item IDs for clearing.
        :type pattern: str
        :return: The number of keys deleted.
        :rtype: int
        """
        keys_to_delete = await self.list_item_ids(pattern) # This already uses the prefix
        if not keys_to_delete:
            return 0
        
        # Need to re-add prefix for deletion if list_item_ids strips it
        full_keys_to_delete = [self._get_redis_key(key_id) for key_id in keys_to_delete]
        return await self.redis_client.delete(*full_keys_to_delete)

    async def ping(self) -> bool:
        """Checks the connection to Redis."""
        return await self.redis_client.ping()

    async def close(self) -> None:
        """Closes the Redis connection."""
        await self.redis_client.close()
        await self.redis_client.connection_pool.disconnect()
