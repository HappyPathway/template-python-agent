# filepath: /workspaces/template-python-dev/ailf/core/secrets.py
"""Secrets management utilities.

This module provides secure handling of credentials and secrets.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class SecretManager(ABC):
    """Base class for secret management."""
    
    @abstractmethod
    def get_secret(self, secret_id: str) -> str:
        """Get a secret by ID.
        
        Args:
            secret_id: ID of the secret
            
        Returns:
            Secret value
        """
        pass
    
class LocalSecretManager(SecretManager):
    """Local secret manager that uses environment variables or a local file."""
    
    def __init__(self, secrets_file: Optional[str] = None):
        """Initialize local secret manager.
        
        Args:
            secrets_file: Optional path to secrets file
        """
        self.secrets_file = secrets_file
        self._secrets = {}
        
        # Load secrets from file if specified
        if secrets_file and os.path.exists(secrets_file):
            try:
                with open(secrets_file, 'r') as f:
                    self._secrets = json.load(f)
                logger.info(f"Loaded secrets from {secrets_file}")
            except Exception as e:
                logger.error(f"Failed to load secrets from {secrets_file}: {e}")
    
    def get_secret(self, secret_id: str) -> str:
        """Get a secret by ID.
        
        Args:
            secret_id: ID of the secret
            
        Returns:
            Secret value
        """
        # Try environment variable first
        env_var = os.environ.get(secret_id)
        if env_var:
            return env_var
        
        # Then try secrets file
        if secret_id in self._secrets:
            return self._secrets[secret_id]
        
        raise KeyError(f"Secret {secret_id} not found")

class CloudSecretManager(SecretManager):
    """Google Cloud Secret Manager implementation."""
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize cloud secret manager.
        
        Args:
            project_id: Google Cloud project ID
        """
        self.project_id = project_id
        self._client = None
        logger.info(f"Initialized Cloud Secret Manager for project {project_id}")
    
    @property
    def client(self):
        """Get Secret Manager client.
        
        Returns:
            Secret Manager client
        """
        try:
            from google.cloud import secretmanager
            if self._client is None:
                self._client = secretmanager.SecretManagerServiceClient()
            return self._client
        except ImportError:
            raise ImportError("google-cloud-secret-manager is required for CloudSecretManager")
    
    def get_secret(self, secret_id: str) -> str:
        """Get a secret by ID from Google Cloud Secret Manager.
        
        Args:
            secret_id: ID of the secret
            
        Returns:
            Secret value
        """
        try:
            # Access the secret version
            project_id = self.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
            if not project_id:
                raise ValueError("Project ID is required")
                
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = self.client.access_secret_version(name=name)
            
            # Return the secret payload
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to access secret {secret_id}: {e}")
            raise

# Default secret manager instance
secret_manager = LocalSecretManager()

def get_secret(secret_id: str) -> str:
    """Get a secret using the default secret manager.
    
    Args:
        secret_id: ID of the secret
        
    Returns:
        Secret value
    """
    return secret_manager.get_secret(secret_id)

__all__ = [
    "SecretManager",
    "LocalSecretManager",
    "CloudSecretManager",
    "secret_manager",
    "get_secret"
]
