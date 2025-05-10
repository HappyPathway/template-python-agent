"""Google Cloud Storage Implementation.

This module provides a concrete implementation of the StorageBase interface
for Google Cloud Storage (GCS). It leverages all the extension points provided
by the base class for customization.
"""
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound
except ImportError:
    raise ImportError(
        "Google Cloud Storage dependencies not installed. "
        "Install them with: pip install google-cloud-storage"
    )

from ailf.core.storage_base import StorageBase


class GCSStorage(StorageBase):
    """Google Cloud Storage implementation.
    
    This class provides storage operations using Google Cloud Storage
    with configurable options for prefixes and authentication.
    
    Example:
        >>> storage = GCSStorage(bucket_name="my-app-data")
        >>> storage.save_json({"key": "value"}, "config/settings.json")
        'gs://my-app-data/config/settings.json'
        >>> data = storage.get_json("config/settings.json")
        >>> print(data)
        {'key': 'value'}
    """

    def __init__(self, bucket_name: str, 
                 prefix: str = "", 
                 project_id: Optional[str] = None,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize Google Cloud Storage.
        
        Args:
            bucket_name: Name of the GCS bucket
            prefix: Optional prefix for all object paths (default: "")
            project_id: Optional Google Cloud project ID
            config: Optional configuration dictionary
        
        Note:
            This implementation uses Application Default Credentials (ADC).
            Ensure you have run `gcloud auth application-default login`
            or have set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
        """
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip("/") if prefix else ""
        self.project_id = project_id
        
        # Initialize client
        self.client = storage.Client(project=project_id)
        
        # Initialize the base class (which will call _initialize)
        super().__init__(config)

    def _initialize(self) -> None:
        """Initialize the GCS storage.
        
        Validates the bucket exists and is accessible.
        """
        try:
            self.bucket = self.client.get_bucket(self.bucket_name)
        except NotFound:
            if self.config.get("auto_create_bucket", False):
                self.bucket = self.client.create_bucket(self.bucket_name)
            else:
                raise ValueError(
                    f"Bucket '{self.bucket_name}' not found. "
                    f"Set config['auto_create_bucket']=True to create it automatically."
                )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values for GCS.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        config = super()._get_default_config()
        config.update({
            "auto_create_bucket": False,
            "cache_control": None,
            "content_type": "application/json",
        })
        return config
    
    def _validate_path(self, path: str) -> str:
        """Validate and normalize the provided path.
        
        Ensures the path is valid for GCS operations.
        
        Args:
            path: Path to validate
            
        Returns:
            str: Validated and normalized path
            
        Raises:
            ValueError: If path is invalid
        """
        path = super()._validate_path(path)
        
        # Remove leading slashes for GCS paths
        return path.lstrip("/")
    
    def _get_full_path(self, path: str) -> str:
        """Get the full path including prefix.
        
        Args:
            path: Relative path
            
        Returns:
            str: Full path including prefix
        """
        path = self._validate_path(path)
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path
        
    def save_json(self, data: Dict, path: str) -> str:
        """Save data as JSON to the specified GCS path.
        
        Args:
            data: Data to save
            path: Path where data should be saved

        Returns:
            str: GCS URI where the data was saved
            
        Raises:
            ValueError: If path or data is invalid
            Exception: If saving to GCS fails
        """
        # Validate inputs using base class methods
        path = self._validate_path(path)
        data = self._validate_data(data)
        
        # Process data before saving
        processed_data = self._process_data_before_save(data)
        
        # Get full path
        full_path = self._get_full_path(path)
        
        # Create a blob reference
        blob = self.bucket.blob(full_path)
        
        # Set metadata if provided in config
        if self.config.get("cache_control"):
            blob.cache_control = self.config["cache_control"]
        
        # Convert to JSON string
        json_data = json.dumps(processed_data, ensure_ascii=False, indent=2)
        
        # Upload to GCS
        content_type = self.config.get("content_type", "application/json")
        blob.upload_from_string(json_data, content_type=content_type)
        
        # Return the GCS URI
        return f"gs://{self.bucket_name}/{full_path}"

    def get_json(self, path: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Get JSON data from the specified GCS path.
        
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
        full_path = self._get_full_path(path)
        
        # Create a blob reference
        blob = self.bucket.blob(full_path)
        
        # Check if exists
        if not blob.exists():
            return default
        
        try:
            # Download as string
            content = blob.download_as_text()
            
            # Parse JSON
            data = json.loads(content)
            
            # Process data after loading
            return self._process_data_after_load(data)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in gs://{self.bucket_name}/{full_path}: {str(e)}",
                e.doc,
                e.pos
            )
        except Exception as e:
            # Log the error and return default
            print(f"Error loading from GCS: {str(e)}")
            return default

    def get_path(self, path: str) -> str:
        """Get full GCS URI for the given path.

        Args:
            path: Relative path to resolve

        Returns:
            str: Full GCS URI
        """
        path = self._validate_path(path)
        full_path = self._get_full_path(path)
        return f"gs://{self.bucket_name}/{full_path}"
        
    def exists(self, path: str) -> bool:
        """Check if a path exists in GCS.

        Args:
            path: Path to check

        Returns:
            bool: True if path exists, False otherwise
        """
        path = self._validate_path(path)
        full_path = self._get_full_path(path)
        blob = self.bucket.blob(full_path)
        return blob.exists()
        
    def list_directory(self, path: str = "") -> List[str]:
        """List contents of a directory in GCS.

        Args:
            path: Directory path to list (empty for root)

        Returns:
            List[str]: List of items in the directory
        """
        path = self._validate_path(path)
        prefix = self._get_full_path(path)
        
        if prefix and not prefix.endswith('/'):
            prefix += '/'
            
        # List blobs with the prefix
        blobs = self.client.list_blobs(
            self.bucket_name, 
            prefix=prefix, 
            delimiter="/"
        )
        
        # Get files and directories
        result = []
        
        # Add files (direct blobs)
        for blob in blobs:
            # Skip the directory prefix itself
            if blob.name == prefix:
                continue
                
            # Get relative name (strip prefix)
            relative_name = blob.name[len(prefix):] if prefix else blob.name
            if relative_name:
                result.append(relative_name)
                
        # Add directories (prefixes)
        for prefix in blobs.prefixes:
            # Get relative name (strip directory prefix and trailing slash)
            relative_name = prefix[len(prefix):-1] if prefix else prefix[:-1]
            if relative_name:
                result.append(f"{relative_name}/")
                
        return result
        
    def delete(self, path: str) -> bool:
        """Delete an item in GCS.

        Args:
            path: Path to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        path = self._validate_path(path)
        full_path = self._get_full_path(path)
        blob = self.bucket.blob(full_path)
        
        if not blob.exists():
            return False
            
        try:
            blob.delete()
            return True
        except Exception:
            return False
            
    def download_to_file(self, gcs_path: str, local_path: str) -> bool:
        """Download a file from GCS to local path.
        
        Args:
            gcs_path: GCS path to download
            local_path: Local path to save to
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        gcs_path = self._validate_path(gcs_path)
        full_path = self._get_full_path(gcs_path)
        blob = self.bucket.blob(full_path)
        
        if not blob.exists():
            return False
            
        try:
            # Ensure local directory exists
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the blob to the file
            blob.download_to_filename(str(local_path))
            return True
        except Exception as e:
            print(f"Error downloading from GCS: {str(e)}")
            return False
            
    def upload_from_file(self, local_path: str, gcs_path: str) -> bool:
        """Upload a file from local path to GCS.
        
        Args:
            local_path: Local path to upload
            gcs_path: GCS path to save to
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        local_path = Path(local_path)
        if not local_path.exists():
            return False
            
        gcs_path = self._validate_path(gcs_path)
        full_path = self._get_full_path(gcs_path)
        blob = self.bucket.blob(full_path)
        
        try:
            # Upload the file to the blob
            blob.upload_from_filename(str(local_path))
            return True
        except Exception as e:
            print(f"Error uploading to GCS: {str(e)}")
            return False