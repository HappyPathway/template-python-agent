"""Short-term memory implementation for AILF agents."""

from typing import Any, Dict, List, Optional
import time

from ailf.schemas.memory import MemoryItem # Import MemoryItem

class ShortTermMemory:
    """
    Manages short-term memory for an agent, using a simple in-memory dictionary.
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initializes the short-term memory store.

        :param default_ttl: Default time-to-live for memory items in seconds.
        :type default_ttl: int
        """
        self._memory: Dict[str, Dict[str, Any]] = {} # Stores MemoryItem and expiration
        self.default_ttl = default_ttl

    async def add_item(self, item_id: str, data: Any, ttl: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds an item to the short-term memory.

        :param item_id: Unique identifier for the memory item.
        :type item_id: str
        :param data: The data to store.
        :type data: Any
        :param ttl: Time-to-live for this item in seconds. Uses default_ttl if None.
        :type ttl: Optional[int]
        :param metadata: Optional metadata associated with the item.
        :type metadata: Optional[Dict[str, Any]]
        """
        if ttl is None:
            ttl = self.default_ttl
        
        expires_at = time.time() + ttl if ttl > 0 else None
        
        memory_item_obj = MemoryItem(
            item_id=item_id,
            data=data,
            timestamp=time.time(), # Timestamp of creation/update
            metadata=metadata or {}
        )
        
        self._memory[item_id] = {
            "item": memory_item_obj,
            "expires_at": expires_at
        }

    async def get_item(self, item_id: str) -> Optional[MemoryItem]:
        """
        Retrieves an item from short-term memory.

        Removes the item if it has expired.

        :param item_id: The ID of the item to retrieve.
        :type item_id: str
        :return: The MemoryItem if found and not expired, else None.
        :rtype: Optional[MemoryItem]
        """
        item_entry = self._memory.get(item_id)
        if not item_entry:
            return None

        if item_entry["expires_at"] is not None and item_entry["expires_at"] < time.time():
            del self._memory[item_id]
            return None
        
        # Update last_accessed_at if we add it to MemoryItem
        # item_entry["item"].metadata["last_accessed_at"] = time.time() 
        return item_entry["item"]

    async def remove_item(self, item_id: str) -> bool:
        """
        Removes an item from short-term memory.

        :param item_id: The ID of the item to remove.
        :type item_id: str
        :return: True if the item was removed, False if not found.
        :rtype: bool
        """
        if item_id in self._memory:
            del self._memory[item_id]
            return True
        return False

    async def list_items(self) -> List[str]:
        """
        Lists all non-expired item IDs in short-term memory.
        
        This method also cleans up any expired items it encounters.

        :return: A list of item IDs.
        :rtype: List[str]
        """
        current_time = time.time()
        # Iterate safely if modification during iteration is a concern, though current ops are safe
        # For complex scenarios, consider iterating over a copy of keys: list(self._memory.keys())
        expired_keys = [
            key for key, item_entry in self._memory.items() 
            if item_entry["expires_at"] is not None and item_entry["expires_at"] < current_time
        ]
        for key in expired_keys:
            # Ensure key still exists, in case of concurrent access (though less likely in typical async patterns without explicit task switching)
            if key in self._memory: 
                del self._memory[key]
        
        return list(self._memory.keys())

    async def clear(self) -> None:
        """Clears all items from short-term memory."""
        self._memory.clear()

    def _cleanup_expired_items(self) -> None: # This method might be better as async if it grows
        """Internal method to remove all expired items. Can be called periodically if needed."""
        current_time = time.time()
        expired_keys = [
            key for key, item_entry in self._memory.items()
            if item_entry["expires_at"] is not None and item_entry["expires_at"] < current_time
        ]
        for key in expired_keys:
            if key in self._memory: # Check if key still exists
                del self._memory[key]
