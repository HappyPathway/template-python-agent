"""Pydantic schemas for AILF memory systems."""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
import time

class MemoryItem(BaseModel):
    """
    Represents a single item stored in memory.
    """
    item_id: str = Field(..., description="Unique identifier for the memory item.")
    data: Any = Field(..., description="The actual data stored.")
    timestamp: float = Field(default_factory=time.time, description="Timestamp of when the item was created or last updated.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata associated with the item.")
    # ttl: Optional[int] = Field(None, description="Time-to-live for this item in seconds from creation.") # TTL managed by store

class UserProfile(BaseModel):
    """
    Schema for storing user profile information, potentially in long-term memory.
    """
    user_id: str = Field(..., description="Unique identifier for the user.")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User-specific preferences.")
    history_summary: Optional[str] = Field(None, description="A summary of past interactions or key information related to the user.")
    # Add other relevant fields like interaction_timestamps, key_entities, etc.

class KnowledgeFact(BaseModel):
    """
    Schema for storing a piece of knowledge or a fact, typically in long-term memory.
    """
    fact_id: str = Field(..., description="Unique identifier for the knowledge fact.")
    content: str = Field(..., description="The content of the fact.")
    source: Optional[str] = Field(None, description="Source of the knowledge (e.g., document ID, user input session).")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing or retrieving the fact.")
    confidence_score: Optional[float] = Field(None, description="A score indicating the confidence in this fact's accuracy.")
    created_at: float = Field(default_factory=time.time)
    last_accessed_at: Optional[float] = None
