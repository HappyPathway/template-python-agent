"""Google Cloud Storage Config Stash

This module provides a Python equivalent to the Terraform Clover Config Stash,
allowing storage and retrieval of arbitrary configuration data in GCS buckets.
It supports:

- Storing arbitrary JSON data in GCS
- Reading and merging configuration data
- Path-based organization
- Initialization with default values
- Refresh/update capabilities
- Data versioning (through GCS versioning)

Example:
    ```python
    from ailf.gcs_config_stash import ConfigStash
    
    # Initialize stash
    stash = ConfigStash(bucket_name="my-config-bucket")
    
    # Store configuration
    await stash.set_config(
        path="services/auth/config.json",
        data={"api_url": "https://auth.example.com", "timeout": 30}
    )
    
    # Get configuration
    config = await stash.get_config("services/auth/config.json")
    print(config["api_url"])
    
    # Update specific fields
    await stash.update_config(
        path="services/auth/config.json",
        updates={"timeout": 60}
    )
    
    # Initialize with defaults
    await stash.initialize_config(
        path="services/new/config.json",
        defaults={"setting1": "default1"},
        keys_to_manage=["setting1"]  # Only manage these keys
    )
    ```
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.api_core import retry

from .logging import setup_logging

logger = setup_logging(__name__)

class ConfigStash:
    """Google Cloud Storage based configuration management.
    
    This class provides functionality similar to terraform-clover-config-stash,
    allowing storage and management of arbitrary configuration data in GCS buckets.
    """
    
    def __init__(
        self,
        bucket_name: str,
        client: Optional[storage.Client] = None,
        retry_config: Optional[retry.Retry] = None
    ):
        """Initialize the config stash.
        
        Args:
            bucket_name: Name of the GCS bucket to use
            client: Optional pre-configured storage client
            retry_config: Optional retry configuration for GCS operations
        """
        self.bucket_name = bucket_name
        self.client = client or storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.retry = retry_config or retry.Retry(predicate=retry.if_exception_type(Exception))
        
    @retry.Retry(predicate=retry.if_exception_type(Exception))
    async def get_config(
        self,
        path: str,
        default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get configuration data from GCS.
        
        Args:
            path: Path to the configuration file in GCS
            default: Default data to return if file doesn't exist
            
        Returns:
            Configuration data as dictionary
        """
        try:
            blob = self.bucket.blob(path)
            content = blob.download_as_text()
            return json.loads(content)
        except NotFound:
            if default is not None:
                return default.copy()
            return {}
        except Exception as e:
            logger.error(f"Error reading config from {path}: {str(e)}")
            raise
            
    @retry.Retry(predicate=retry.if_exception_type(Exception))
    async def set_config(
        self,
        path: str,
        data: Dict[str, Any],
        merge: bool = False
    ) -> bool:
        """Store configuration data in GCS.
        
        Args:
            path: Path where to store the configuration
            data: Configuration data to store
            merge: Whether to merge with existing data
            
        Returns:
            True if successful
        """
        try:
            if merge:
                existing = await self.get_config(path, {})
                data = {**existing, **data}
            
            blob = self.bucket.blob(path)
            blob.upload_from_string(
                json.dumps(data, indent=2),
                content_type='application/json'
            )
            return True
            
        except Exception as e:
            logger.error(f"Error writing config to {path}: {str(e)}")
            raise
            
    @retry.Retry(predicate=retry.if_exception_type(Exception))
    async def update_config(
        self,
        path: str,
        updates: Dict[str, Any],
        create: bool = True
    ) -> bool:
        """Update specific fields in configuration.
        
        Args:
            path: Path to the configuration file
            updates: Dictionary of updates to apply
            create: Whether to create if doesn't exist
            
        Returns:
            True if successful
        """
        try:
            existing = await self.get_config(path)
            if not existing and not create:
                raise ValueError(f"Config at {path} does not exist")
                
            merged = {**existing, **updates}
            return await self.set_config(path, merged)
            
        except Exception as e:
            logger.error(f"Error updating config at {path}: {str(e)}")
            raise
            
    async def initialize_config(
        self,
        path: str,
        defaults: Dict[str, Any],
        keys_to_manage: Optional[List[str]] = None,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """Initialize configuration with defaults.
        
        Similar to Terraform module's initialization, this:
        1. Creates the config if it doesn't exist
        2. Optionally manages only specific keys
        3. Can refresh/overwrite managed keys
        
        Args:
            path: Path to the configuration file
            defaults: Default configuration values
            keys_to_manage: List of keys to manage (others preserved)
            refresh: Whether to refresh managed keys
            
        Returns:
            The resulting configuration
        """
        try:
            existing = await self.get_config(path, {})
            
            if keys_to_manage:
                # Filter defaults to only managed keys
                defaults = {k: v for k, v in defaults.items() if k in keys_to_manage}
                
                if refresh:
                    # Update only managed keys
                    merged = {**existing}
                    for key in keys_to_manage:
                        if key in defaults:
                            merged[key] = defaults[key]
                else:
                    # Preserve existing managed keys
                    merged = {
                        **defaults,
                        **{k: v for k, v in existing.items() if k in keys_to_manage}
                    }
                
                # Preserve unmanaged keys
                final = {
                    **existing,
                    **{k: v for k, v in merged.items() if k in keys_to_manage}
                }
            else:
                if refresh or not existing:
                    final = defaults
                else:
                    final = {**defaults, **existing}
                    
            await self.set_config(path, final)
            return final
            
        except Exception as e:
            logger.error(f"Error initializing config at {path}: {str(e)}")
            raise
            
    async def list_configs(
        self,
        prefix: Optional[str] = None
    ) -> List[str]:
        """List available configurations.
        
        Args:
            prefix: Optional prefix to filter by
            
        Returns:
            List of configuration paths
        """
        try:
            blobs = self.client.list_blobs(self.bucket, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing configs: {str(e)}")
            raise
            
    async def delete_config(self, path: str) -> bool:
        """Delete a configuration.
        
        Args:
            path: Path to the configuration to delete
            
        Returns:
            True if successful
        """
        try:
            blob = self.bucket.blob(path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting config at {path}: {str(e)}")
            raise
