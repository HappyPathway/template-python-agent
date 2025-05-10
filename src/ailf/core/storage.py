"""Storage abstraction layer.

This module provides a unified interface for storage operations,
supporting local and cloud storage backends.
"""

# Import storage functionality directly from core
from ailf.core.storage_base import StorageBase
from ailf.core.local_storage import LocalStorage
from ailf.core.cloud_storage import CloudStorage

__all__ = [
    "StorageBase",
    "LocalStorage",
    "CloudStorage"
]
