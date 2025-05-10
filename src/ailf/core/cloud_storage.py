"""Google Cloud Storage Implementation.

This module provides an implementation of the StorageBase interface for Google Cloud Storage.
It uses Application Default Credentials for authentication and provides methods for
storing and retrieving JSON data from GCS.
"""
import json
from typing import Dict, Optional

from ailf.core.storage_base import StorageBase
from ailf.core.logging import setup_logging

# Initialize logger
logger = setup_logging('cloud_storage')


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
            
            return f"gs://{self.bucket_name}/{blob_path}"
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
    
    def save_text(self, content: str, path: str) -> str:
        """Save text content to the specified path in GCS.
        
        Args:
            content: Text content to save
            path: Path where content should be saved
            
        Returns:
            str: Cloud Storage path where the content was saved
            
        Raises:
            Exception: If the save operation fails
        """
        try:
            blob_path = self.get_path(path)
            blob = self.bucket.blob(blob_path)
            
            # Save to GCS
            blob.upload_from_string(content, content_type='text/plain')
            logger.info(f"Saved text content to gs://{self.bucket_name}/{blob_path}")
            
            return f"gs://{self.bucket_name}/{blob_path}"
        except Exception as e:
            logger.error(f"Error saving text to GCS path {path}: {str(e)}")
            raise