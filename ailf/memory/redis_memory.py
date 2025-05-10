"""Redis-backed implementation of ShortTermMemory."""
import json
from typing import List, Optional, Any

import redis.asyncio as aioredis # type: ignore

from ailf.memory.base import ShortTermMemory
from ailf.schemas.memory import MemoryItem

class RedisShortTermMemory(ShortTermMemory):
    """Redis-backed implementation of short-term memory."""

    def __init__(
        self, 
        redis_client: aioredis.Redis,
        prefix: str = "stm",
        max_size: Optional[int] = 10000 # Max number of items in the sorted set
    ):
        """
        Initialize Redis-backed short-term memory.

        :param redis_client: An instance of redis.asyncio.Redis.
        :type redis_client: aioredis.Redis
        :param prefix: Prefix for Redis keys to avoid collisions.
        :type prefix: str
        :param max_size: Optional maximum number of items to keep in memory (LRU).
        :type max_size: Optional[int]
        """
        self.redis = redis_client
        self.prefix = prefix
        self.max_size = max_size
        self._items_key = f"{self.prefix}:items" # Hash to store actual items
        self._timestamps_key = f"{self.prefix}:timestamps" # Sorted set for recency (score is timestamp)

    async def add_item(self, item: MemoryItem) -> None:
        """Add an item to short-term memory using Redis.
        Stores item in a HASH and its timestamp in a SORTED SET for recency tracking.
        Implements LRU eviction if max_size is set.
        """
        item_json = item.model_dump_json()
        timestamp = item.metadata.get("timestamp", self.redis.time()[0]) # Use item timestamp or current Redis time

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.hset(self._items_key, item.item_id, item_json)
            pipe.zadd(self._timestamps_key, {item.item_id: float(timestamp)})

            if self.max_size is not None and self.max_size > 0:
                # Trim the sorted set to maintain max_size (oldest items are removed)
                pipe.zremrangebyrank(self._timestamps_key, 0, -(self.max_size + 1))
                # Potentially remove corresponding items from hash (more complex, requires Lua or checking)
                # For simplicity here, we only trim the sorted set. A separate cleanup might be needed for orphaned hash items
                # or use ZREMRANGEBYSCORE and then remove from HASH.
                # A more robust LRU would involve removing from hash as well.
                # Let's try to remove items that are no longer in the sorted set (after trimming).
                # This is illustrative; for high performance, a Lua script is better.

            await pipe.execute()
        
        # LRU Part 2: Remove items from hash that are no longer in the timestamp sorted set (if trimmed)
        if self.max_size is not None and self.max_size > 0:
            current_size = await self.redis.zcard(self._timestamps_key)
            if current_size > self.max_size:
                num_to_remove = current_size - self.max_size
                ids_to_remove = await self.redis.zrange(self._timestamps_key, 0, num_to_remove -1)
                if ids_to_remove:
                    async with self.redis.pipeline(transaction=True) as pipe:
                        pipe.zrem(self._timestamps_key, *ids_to_remove)
                        pipe.hdel(self._items_key, *ids_to_remove)
                        await pipe.execute()


    async def get_item(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve an item from short-term memory by its ID using Redis HGET."""
        item_json = await self.redis.hget(self._items_key, item_id)
        if item_json:
            return MemoryItem.model_validate_json(item_json)
        return None

    async def get_recent_items(self, count: int) -> List[MemoryItem]:
        """Retrieve a list of the most recent items using Redis ZREVRANGE and HMGET."""
        if count <= 0:
            return []
        
        # Get recent item IDs from the sorted set (highest scores are newest)
        recent_ids = await self.redis.zrevrange(self._timestamps_key, 0, count - 1)
        if not recent_ids:
            return []

        # Fetch actual items from the hash
        # Ensure IDs are strings for hmget
        str_recent_ids = [rid.decode('utf-8') if isinstance(rid, bytes) else str(rid) for rid in recent_ids]
        items_json = await self.redis.hmget(self._items_key, *str_recent_ids)
        
        items: List[MemoryItem] = []
        for item_j in items_json:
            if item_j:
                items.append(MemoryItem.model_validate_json(item_j))
        return items

    async def clear(self) -> None:
        """Clear all items related to this memory store from Redis."""
        await self.redis.delete(self._items_key, self._timestamps_key)
