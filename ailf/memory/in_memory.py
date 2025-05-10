"""In-memory implementation of ShortTermMemory."""
from typing import List, Optional, Dict
import time

from ailf.memory.base import ShortTermMemory
from ailf.schemas.memory import MemoryItem

class InMemoryShortTermMemory(ShortTermMemory):
    """In-memory implementation of short-term memory."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize in-memory short-term memory.

        :param max_size: Maximum number of items to store.
        :type max_size: int
        """
        self._memory: Dict[str, MemoryItem] = {}
        self._timestamps: Dict[str, float] = {} # To track item recency
        self.max_size = max_size

    async def add_item(self, item: MemoryItem) -> None:
        """Add an item to short-term memory."""
        if len(self._memory) >= self.max_size:
            # Evict the oldest item if max_size is reached
            oldest_item_id = min(self._timestamps, key=self._timestamps.get)
            del self._memory[oldest_item_id]
            del self._timestamps[oldest_item_id]
        
        self._memory[item.item_id] = item
        self._timestamps[item.item_id] = time.time()

    async def get_item(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve an item from short-term memory by its ID."""
        return self._memory.get(item_id)

    async def get_recent_items(self, count: int) -> List[MemoryItem]:
        """Retrieve a list of the most recent items."""
        if count <= 0:
            return []
        # Sort items by timestamp in descending order (most recent first)
        sorted_item_ids = sorted(self._timestamps, key=self._timestamps.get, reverse=True)
        recent_ids = sorted_item_ids[:count]
        return [self._memory[id] for id in recent_ids if id in self._memory]

    async def clear(self) -> None:
        """Clear all items from short-term memory."""
        self._memory.clear()
        self._timestamps.clear()
