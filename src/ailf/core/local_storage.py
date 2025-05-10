"""Local Storage Implementation.

This module provides a concrete implementation of the StorageBase interface
for local file system storage. It leverages all the extension points provided
by the base class for customization.
"""
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ailf.core.storage_base import StorageBase


class LocalStorage(StorageBase):
    """Local file system storage implementation.
    
    This class provides storage operations on the local file system
    with configurable options for compression, encryption, and caching.
    
    Example:
        >>> storage = LocalStorage("./data")
        >>> storage.save_json({"key": "value"}, "config/settings.json")
        '/path/to/data/config/settings.json'
        >>> data = storage.get_json("config/settings.json")
        >>> print(data)
        {'key': 'value'}
    """

    def __init__(self, base_path: Optional[Union[str, Path]] = None, 
                 config: Optional[Dict[str, Any]] = None):
        """Initialize local storage with base path and configuration.
        
        Args:
            base_path: Base directory for all storage operations. 
                      If None, uses './storage' as default
            config: Optional configuration dictionary
        """
        self.base_path = Path(base_path) if base_path else Path("./storage")
        super().__init__(config)

    def _initialize(self) -> None:
        """Initialize the storage system.
        
        Creates the base directory and default subdirectories if they don't exist.
        """
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create default subdirectories
        for directory in self._get_default_dirs():
            (self.base_path / directory).mkdir(exist_ok=True)
    
    def _get_default_dirs(self) -> List[str]:
        """Get default directories to create.
        
        Override this method to customize the default directory structure.
        
        Returns:
            List[str]: List of default directories to create
        """
        return ["config", "data", "cache", "tmp"]
    
    def _validate_path(self, path: str) -> str:
        """Validate and normalize the provided path.
        
        Ensures the path is valid and normalized for file system operations.
        
        Args:
            path: Path to validate
            
        Returns:
            str: Validated and normalized path
            
        Raises:
            ValueError: If path is invalid or contains dangerous patterns
        """
        path = super()._validate_path(path)
        
        # Security check: prevent path traversal attacks
        normalized = os.path.normpath(path)
        if normalized.startswith("..") or "/../" in normalized:
            raise ValueError(f"Path traversal attempt detected in: {path}")
            
        return path
    
    def _process_data_before_save(self, data: Dict) -> Dict:
        """Process data before saving to storage.
        
        Applies configured transformations like compression or encryption.
        
        Args:
            data: Data to process
            
        Returns:
            Dict: Processed data ready for saving
        """
        processed_data = super()._process_data_before_save(data)
        
        if self.config.get("compress", False):
            processed_data = self._compress_data(processed_data)
            
        if self.config.get("encrypt", False):
            processed_data = self._encrypt_data(processed_data)
            
        return processed_data
    
    def _process_data_after_load(self, data: Dict) -> Dict:
        """Process data after loading from storage.
        
        Reverses any transformations applied before saving.
        
        Args:
            data: Data to process
            
        Returns:
            Dict: Processed data ready for use
        """
        processed_data = data
        
        if self.config.get("encrypt", False):
            processed_data = self._decrypt_data(processed_data)
            
        if self.config.get("compress", False):
            processed_data = self._decompress_data(processed_data)
            
        return super()._process_data_after_load(processed_data)
    
    def _compress_data(self, data: Dict) -> Dict:
        """Compress data before saving.
        
        Note: This is a placeholder. In a real implementation, it would
        actually compress the data.
        
        Args:
            data: Data to compress
            
        Returns:
            Dict: Compressed data
        """
        # In a real implementation, this would use a compression algorithm
        # For now, we just mark it as compressed
        return {"__compressed": True, "data": data}
    
    def _decompress_data(self, data: Dict) -> Dict:
        """Decompress data after loading.
        
        Note: This is a placeholder. In a real implementation, it would
        actually decompress the data.
        
        Args:
            data: Data to decompress
            
        Returns:
            Dict: Decompressed data
        """
        # In a real implementation, this would use a decompression algorithm
        # For now, we just check the compression marker and return the original data
        if isinstance(data, dict) and data.get("__compressed") is True:
            return data.get("data", {})
        return data
    
    def _encrypt_data(self, data: Dict) -> Dict:
        """Encrypt data before saving.
        
        Note: This is a placeholder. In a real implementation, it would
        actually encrypt the data.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Dict: Encrypted data
        """
        # In a real implementation, this would use an encryption algorithm
        # For now, we just mark it as encrypted
        return {"__encrypted": True, "data": data}
    
    def _decrypt_data(self, data: Dict) -> Dict:
        """Decrypt data after loading.
        
        Note: This is a placeholder. In a real implementation, it would
        actually decrypt the data.
        
        Args:
            data: Data to decrypt
            
        Returns:
            Dict: Decrypted data
        """
        # In a real implementation, this would use a decryption algorithm
        # For now, we just check the encryption marker and return the original data
        if isinstance(data, dict) and data.get("__encrypted") is True:
            return data.get("data", {})
        return data

    def save_json(self, data: Dict, path: str) -> str:
        """Save data as JSON to the specified path.
        
        Args:
            data: Data to save
            path: Path where data should be saved

        Returns:
            str: Path where the data was saved
            
        Raises:
            ValueError: If path or data is invalid
            IOError: If saving fails due to file system issues
        """
        # Validate inputs using base class methods
        path = self._validate_path(path)
        data = self._validate_data(data)
        
        # Process data before saving
        processed_data = self._process_data_before_save(data)
        
        # Get full path and ensure parent directories exist
        full_path = self.get_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            return str(full_path)
        except IOError as e:
            raise IOError(f"Failed to save data to {path}: {str(e)}")

    def get_json(self, path: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Get JSON data from the specified path.
        
        Args:
            path: Path to get data from
            default: Default value to return if data not found

        Returns:
            Optional[Dict]: Loaded JSON data or default value
            
        Raises:
            ValueError: If path is invalid
            json.JSONDecodeError: If file contains invalid JSON
        """
        # Validate path
        path = self._validate_path(path)
        full_path = self.get_path(path)
        
        if not full_path.exists():
            return default
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Process data after loading
            return self._process_data_after_load(data)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {path}: {str(e)}", e.doc, e.pos
            )
        except IOError as e:
            return default

    def get_path(self, path: str) -> Path:
        """Get full path for the given relative path.

        Args:
            path: Relative path to resolve

        Returns:
            Path: Full resolved path
        """
        return self.base_path / path
        
    def exists(self, path: str) -> bool:
        """Check if a path exists in the storage.

        Args:
            path: Path to check

        Returns:
            bool: True if path exists, False otherwise
        """
        path = self._validate_path(path)
        return self.get_path(path).exists()
        
    def list_directory(self, path: str = "") -> List[str]:
        """List contents of a directory.

        Args:
            path: Directory path to list (empty for root)

        Returns:
            List[str]: List of items in the directory
            
        Raises:
            ValueError: If path is invalid
            NotADirectoryError: If path is not a directory
            FileNotFoundError: If path doesn't exist
        """
        path = self._validate_path(path) if path else ""
        dir_path = self.get_path(path)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
            
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")
            
        return [item.name for item in dir_path.iterdir()]
        
    def delete(self, path: str) -> bool:
        """Delete an item at the specified path.

        Args:
            path: Path to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        path = self._validate_path(path)
        full_path = self.get_path(path)
        
        if not full_path.exists():
            return False
            
        try:
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()
            return True
        except Exception:
            return False