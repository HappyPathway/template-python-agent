"""Base Storage Interface.

This module defines the base storage interface that all storage implementations
should follow. It provides an abstract base class with required methods and
clear extension points for customization.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class StorageBase(ABC):
    """Base class for storage implementations.

    This abstract base class defines the interface for all storage implementations.
    Subclasses should implement the required methods to provide concrete storage functionality.
    The class provides clear extension points prefixed with underscore for customization.

    Extension Points:
        - _get_default_config: Override to customize default configuration
        - _initialize: Override to customize initialization logic
        - _validate_path: Override to customize path validation
        - _validate_data: Override to customize data validation before saving
        - _process_data_before_save: Override to customize data processing before saving
        - _process_data_after_load: Override to customize data processing after loading

    Example:
        ```python
        class CustomStorage(StorageBase):
            def __init__(self, base_path=None, config=None):
                super().__init__(config)
                self.base_path = base_path or Path("./data")
                
            def _get_default_config(self):
                config = super()._get_default_config()
                config.update({"compress": True})
                return config
                
            def _process_data_before_save(self, data):
                # Add custom compression if enabled
                data = super()._process_data_before_save(data)
                if self.config.get("compress", False):
                    return self._compress_data(data)
                return data
                
            def save_json(self, data, path):
                # Implement required method
                processed_data = self._process_data_before_save(data)
                full_path = self.get_path(path)
                # Save logic here...
                return str(full_path)
        ```
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize storage with optional configuration.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._get_default_config()
        self._initialize()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Override this method to provide custom default configuration settings.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        return {
            "compress": False,
            "encrypt": False,
            "cache_enabled": True,
            "max_cache_size": 100
        }
        
    def _initialize(self) -> None:
        """Perform initialization after config is set.
        
        Override this method to add custom initialization logic.
        This is called at the end of __init__.
        """
        pass
        
    def _validate_path(self, path: str) -> str:
        """Validate and normalize the provided path.
        
        Override this method to customize path validation or normalization.
        
        Args:
            path: Path to validate
            
        Returns:
            str: Validated and normalized path
            
        Raises:
            ValueError: If path is invalid
        """
        if not path:
            raise ValueError("Path cannot be empty")
        return path.strip()
        
    def _validate_data(self, data: Dict) -> Dict:
        """Validate the provided data before saving.
        
        Override this method to customize data validation logic.
        
        Args:
            data: Data to validate
            
        Returns:
            Dict: Validated data
            
        Raises:
            ValueError: If data is invalid
        """
        if data is None:
            raise ValueError("Data cannot be None")
        return data
        
    def _process_data_before_save(self, data: Dict) -> Dict:
        """Process data before saving to storage.
        
        Override this method to customize data processing before saving.
        
        Args:
            data: Data to process
            
        Returns:
            Dict: Processed data ready for saving
        """
        return data
        
    def _process_data_after_load(self, data: Dict) -> Dict:
        """Process data after loading from storage.
        
        Override this method to customize data processing after loading.
        
        Args:
            data: Data to process
            
        Returns:
            Dict: Processed data ready for use
        """
        return data

    @abstractmethod
    def save_json(self, data: Dict, path: str) -> str:
        """Save data as JSON to the specified path.
        
        This is a template method that should use the following workflow:
        1. Validate the path using _validate_path
        2. Validate the data using _validate_data
        3. Process the data using _process_data_before_save
        4. Perform the actual save operation
        
        Args:
            data: Data to save
            path: Path where data should be saved

        Returns:
            str: Path where the data was saved

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass

    @abstractmethod
    def get_json(self, path: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Get JSON data from the specified path.
        
        This is a template method that should use the following workflow:
        1. Validate the path using _validate_path
        2. Attempt to load the data
        3. If successful, process the data using _process_data_after_load
        4. If unsuccessful, return the default value
        
        Args:
            path: Path to get data from
            default: Default value to return if data not found

        Returns:
            Optional[Dict]: Loaded JSON data or default value

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass

    @abstractmethod
    def get_path(self, path: str) -> Union[Path, str]:
        """Get full path for the given relative path.

        Args:
            path: Relative path to resolve

        Returns:
            Union[Path, str]: Full resolved path

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        pass
        
    def exists(self, path: str) -> bool:
        """Check if a path exists in the storage.

        Args:
            path: Path to check

        Returns:
            bool: True if path exists, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement exists")
        
    def list_directory(self, path: str = "") -> List[str]:
        """List contents of a directory.

        Args:
            path: Directory path to list (empty for root)

        Returns:
            List[str]: List of items in the directory
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement list_directory")
        
    def delete(self, path: str) -> bool:
        """Delete an item at the specified path.

        Args:
            path: Path to delete

        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement delete")