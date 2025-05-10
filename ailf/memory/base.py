"""Core memory system classes for ailf."""
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from ailf.schemas.memory import MemoryItem

class ShortTermMemory(ABC):
    """Abstract base class for short-term memory storage."""

    @abstractmethod
    async def add_item(self, item: MemoryItem) -> None:
        """Add an item to short-term memory."""
        raise NotImplementedError

    @abstractmethod
    async def get_item(self, item_id: str) -> Optional[MemoryItem]:
        """Retrieve an item from short-term memory by its ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_recent_items(self, count: int) -> List[MemoryItem]:
        """Retrieve a list of the most recent items."""
        raise NotImplementedError

    @abstractmethod
    async def clear(self) -> None:
        """Clear all items from short-term memory."""
        raise NotImplementedError

class LongTermMemory(ABC):
    """Abstract base class for long-term memory storage."""

    @abstractmethod
    async def store_knowledge(self, fact: Any) -> str:
        """Store a piece of knowledge (e.g., UserProfile, KnowledgeFact) and return its ID."""
        raise NotImplementedError

    @abstractmethod
    async def retrieve_knowledge(self, query: str, top_k: int = 5) -> List[Any]:
        """Retrieve relevant knowledge based on a query."""
        raise NotImplementedError

    @abstractmethod
    async def get_knowledge_by_id(self, fact_id: str) -> Optional[Any]:
        """Retrieve a specific piece of knowledge by its ID."""
        raise NotImplementedError
