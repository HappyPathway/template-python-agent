"""AILF Interaction Module.

This module provides components for managing agent interactions with users or other systems,
including input/output adaptation and interaction flow management.
"""

from .adapters import BaseInputAdapter, BaseOutputAdapter
from .manager import InteractionManager

__all__ = [
    "BaseInputAdapter",
    "BaseOutputAdapter",
    "InteractionManager",
]