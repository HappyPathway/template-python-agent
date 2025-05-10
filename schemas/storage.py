"""Storage Schema Models

This module defines data models related to storage operations.
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class StorageConfig(BaseModel):
    """Configuration for storage operations.

    Attributes:
        base_path: Base directory for storage operations
        create_if_missing: Whether to create directories if they don't exist
        compress: Whether to compress stored files
        file_permissions: Unix file permissions to apply to new files
        additional_options: Additional storage-specific configuration options
    """
    base_path: str
    create_if_missing: bool = True
    compress: bool = False
    file_permissions: Optional[int] = None
    additional_options: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        'validate_assignment': True,
        'extra': 'forbid'
    }
