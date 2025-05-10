"""Local File Storage Manager for Development

This module provides a simple interface for managing local file storage during
development. It includes utilities for creating directories, saving and loading
JSON files, and managing file paths.

Use this module to handle file storage needs in a local development environment.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles # type: ignore
import aiofiles.os as aios # type: ignore
from pydantic import BaseModel

from utils.core.logging import setup_logging # Corrected import

# Initialize logger
logger = setup_logging('storage')

# Initialize module-level variables
_DEFAULT_STORAGE = None
_get_path = None
_get_json = None
_save_json = None


def get_default_storage_path() -> Path:
    """Get the default storage path.

    Tries to use ~/.template-python-dev, falls back to tempdir if needed.
    """
    try:
        path = Path.home() / '.template-python-dev'
        # Test if we can create/write to this directory
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            # Try writing a test file
            test_file = path / '.test'
            test_file.write_text('')
            test_file.unlink()
        return path
    except (OSError, PermissionError):
        # Fall back to a temporary directory
        temp_dir = Path(tempfile.gettempdir()) / 'template-python-dev'
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir


class StorageBase:
    """Base class for storage implementations.

    This abstract base class defines the interface for all storage implementations.
    Subclasses should implement the required methods to provide concrete storage functionality.

    Example:
        ```python
        class CustomStorage(StorageBase):
            def __init__(self, config=None):
                super().__init__(config)
                # Custom initialization

            def save_json(self, data, path):
                # Custom implementation
                pass

            def get_json(self, path, default=None):
                # Custom implementation
                pass
        ```
    """

    def __init__(self, config=None):
        """Initialize storage with optional configuration.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

    def save_json(self, data: Dict, path: str) -> str:
        """Save data as JSON to the specified path.

        Args:
            data: Data to save
            path: Path where data should be saved

        Returns:
            str: Path where the data was saved

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement save_json")

    def get_json(self, path: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Get JSON data from the specified path.

        Args:
            path: Path to get data from
            default: Default value to return if data not found

        Returns:
            Optional[Dict]: Loaded JSON data or default value

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_json")

    def get_path(self, path: str) -> Path:
        """Get full path for the given relative path.

        Args:
            path: Relative path to resolve

        Returns:
            Path: Full resolved path

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement get_path")


class LocalStorage(StorageBase):
    """Local File Storage Manager

The `LocalStorage` class simplifies file storage operations in a local
development environment. It provides methods for:

- Ensuring necessary directories exist.
- Saving and loading JSON files.
- Managing file paths.

This class is designed to be inherited from for custom storage implementations.
Override the appropriate methods to customize behavior.

Example:
    ```python
    class MyCustomStorage(LocalStorage):
        def __init__(self, custom_config):
            super().__init__(custom_config.path)
            self.custom_setting = custom_config.setting

        def _get_default_dirs(self):
            # Add custom directories
            dirs = super()._get_default_dirs()
            dirs.extend(['custom_dir', 'another_dir'])
            return dirs
    ```
"""

    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        """Initialize local storage paths.

        Args:
            base_path: Optional base path for storage. If not provided,
                      tries user's home directory, falls back to temp dir.
        """
        if base_path is None:
            base_path = self._get_default_base_path()
        self.base_path = Path(base_path)
        self.ensure_directories()

    def _get_default_base_path(self) -> Path:
        """Get the default base path for storage.

        Override this method in subclasses to customize the default base path.

        Returns:
            Path: Default base path
        """
        return get_default_storage_path()

    def _get_default_dirs(self) -> List[str]:
        """Get the list of default directories to create.

        Override this method in subclasses to customize directory structure.

        Returns:
            List[str]: List of directory names to create
        """
        return ['data', 'documents', 'config', 'cache']

    def ensure_directories(self):
        """Initialize and ensure existence of required storage directories.

        Creates a standardized directory structure for storing different types
        of data based on the directories returned by _get_default_dirs().

        This method is called automatically during initialization but can
        be called again to repair the directory structure if needed.

        Example:
            ```python
            storage = LocalStorage()
            storage.ensure_directories()  # Recreate any missing directories
            ```

        Note:
            All directories are created with exist_ok=True to prevent race conditions

        Override _get_default_dirs() instead of this method to customize directories.
        """
        dirs = self._get_default_dirs()
        for d in dirs:
            path = self.base_path / d
            path.mkdir(exist_ok=True)

    def get_path(self, filename: str) -> Path:
        """Get full path for a file in the storage directory.

        Args:
            filename: Name of the file to get path for

        Returns:
            Path: The full absolute path to the file

        Example:
            ```python
            storage = LocalStorage()
            path = storage.get_path("config.json")
            print(path)  # /path/to/base/config.json
            ```

        Note:
            The path is always relative to the base storage directory
        """
        return self.base_path / filename

    def save_json(self, data: Union[Dict, List], filename: str) -> bool:
        """Save Data as JSON File

        This method saves a dictionary as a JSON file in the specified location.

        Args:
            data (Dict): The data to save.
            filename (str): The name of the JSON file.

        Returns:
            bool: True if the file was saved successfully, False otherwise.

        Example:
            ```python
            storage = LocalStorage()
            success = storage.save_json({"key": "value"}, "data.json")
            print(success)  # Outputs: True
            ```
        """
        try:
            path = self.get_path(filename)
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Saved JSON to %s", filename)
            return True
        except Exception as e:
            logger.error("Error saving JSON %s: %s", filename, str(e))
            return False

    def load_json(self, filename: str) -> Optional[Dict]:
        """Load JSON Data from File

This method loads data from a JSON file if it exists.

Args:
    filename (str): The name of the JSON file.

Returns:
    Optional[Dict]: The loaded data as a dictionary, or None if the file does not exist.

Example:
    ```python
    storage = LocalStorage()
    data = storage.load_json("data.json")
    print(data)  # Outputs: {"key": "value"}
    ```
"""
        return self.get_json(filename)

    def save_text(self, content: str, filename: str) -> bool:
        """Save text content to file."""
        try:
            path = self.get_path(filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("Saved text to %s", filename)
            return True
        except Exception as e:
            logger.error("Error saving text %s: %s", filename, str(e))
            return False

    def get_json(self, filename: str) -> Optional[dict]:
        """Load JSON data from file.

        Args:
            filename: Name of the file to load

        Returns:
            Optional[dict]: The loaded JSON data, or None if loading fails
        """
        try:
            path = self.get_path(filename)
            if not path.exists():
                logger.warning("File not found: %s", filename)
                return None

            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading JSON %s: %s", filename, str(e))
            return None

# Initialize default storage after class definition


def get_default_storage() -> 'LocalStorage':
    """Get or create the default storage instance."""
    global _DEFAULT_STORAGE, _get_path, _get_json, _save_json
    if _DEFAULT_STORAGE is None:
        _DEFAULT_STORAGE = LocalStorage()
        _get_path = _DEFAULT_STORAGE.get_path
        _get_json = _DEFAULT_STORAGE.get_json
        _save_json = _DEFAULT_STORAGE.save_json
    return _DEFAULT_STORAGE


# Create the default storage instance
_DEFAULT_STORAGE = get_default_storage()

# Make helper functions available at module level
get_path = _get_path
get_json = _get_json
save_json = _save_json


class CloudStorage(StorageBase):
    """Google Cloud Storage implementation.
    
    This class provides an interface to Google Cloud Storage for storing and retrieving data.
    It implements the StorageBase interface and uses Application Default Credentials for authentication.
    
    Example:
        ```python
        storage = CloudStorage(bucket_name="my-bucket")
        storage.save_json({"key": "value"}, "data/config.json")
        data = storage.get_json("data/config.json")
        ```
        
    Note:
        This implementation requires the Google Cloud Storage client library and
        properly configured Application Default Credentials (ADC).
        Run `gcloud auth application-default login` to set up credentials.
    """
    
    def __init__(self, bucket_name: str, prefix: str = ""):
        """Initialize cloud storage with bucket name and optional prefix.
        
        Args:
            bucket_name: Name of the Google Cloud Storage bucket
            prefix: Optional prefix to prepend to all paths (default: "")
        """
        super().__init__({"bucket": bucket_name, "prefix": prefix})
        self.bucket_name = bucket_name
        self.prefix = prefix
        self._init_client()
        
    def _init_client(self):
        """Initialize the GCS client.
        
        Raises:
            ImportError: If the Google Cloud Storage library is not installed
        """
        try:
            from google.cloud import storage
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"Initialized Cloud Storage client for bucket {self.bucket_name}")
        except ImportError:
            logger.error("Google Cloud Storage library not installed. Install with: pip install google-cloud-storage")
            raise ImportError("Required package not found: google-cloud-storage")
        
    def get_path(self, path: str) -> str:
        """Get full path for the given path in the bucket.
        
        Args:
            path: Path to resolve
            
        Returns:
            str: Full blob path including prefix
        """
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
        
    def save_json(self, data: Dict, path: str) -> str:
        """Save data as JSON to the specified path in GCS.
        
        Args:
            data: Data to save
            path: Path where data should be saved
            
        Returns:
            str: Cloud Storage path where the data was saved
            
        Raises:
            Exception: If the save operation fails
        """
        try:
            blob_path = self.get_path(path)
            blob = self.bucket.blob(blob_path)
            
            # Convert data to JSON string
            content = json.dumps(data, indent=2)
            
            # Save to GCS
            blob.upload_from_string(content, content_type='application/json')
            logger.info(f"Saved JSON data to gs://{self.bucket_name}/{blob_path}")
            
            return blob_path
        except Exception as e:
            logger.error(f"Error saving JSON to GCS path {path}: {str(e)}")
            raise
            
    def get_json(self, path: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Get JSON data from the specified path in GCS.
        
        Args:
            path: Path to get data from
            default: Default value to return if data not found
            
        Returns:
            Optional[Dict]: Loaded JSON data or default value
        """
        try:
            blob_path = self.get_path(path)
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                logger.warning(f"File not found in GCS: {blob_path}")
                return default
                
            # Download and parse JSON
            content = blob.download_as_text()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading JSON from GCS path {path}: {str(e)}")
            return default
