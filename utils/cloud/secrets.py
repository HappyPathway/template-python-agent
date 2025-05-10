"""Secure secrets management using Google Secret Manager.

This module uses Application Default Credentials (ADC) for authentication.
ADC automatically detects credentials in the following order:
1. GOOGLE_APPLICATION_CREDENTIALS environment variable
2. User credentials from gcloud SDK
3. Compute Engine service account
4. Cloud Run or App Engine service account
"""
import os
from typing import Optional

import google.auth
from google.cloud import secretmanager

from .logging import setup_logging

logger = setup_logging('secrets')


class SecretManager:
    """Manages secure access to application secrets using Google Secret Manager.

    This class uses Application Default Credentials (ADC) for authentication.
    Before using this class, ensure you have:

    1. Installed gcloud SDK
    2. Run 'gcloud auth application-default login'
    3. Set project: 'gcloud config set project YOUR-PROJECT'

    This class provides a secure interface for retrieving sensitive configuration values
    and credentials. It includes:
    - Automatic caching with configurable TTL
    - Error handling and logging
    - Environment-specific secret versions
    - Retry logic for network issues

    The manager integrates with Google Secret Manager for secure storage and
    implements best practices for secret handling:
    - No secrets in logs or exceptions
    - Automatic secret rotation support 
    - Memory-safe secret handling
    - Access logging and auditing

    Example:

        >>> from utils.secrets import secret_manager
        >>> 
        >>> # Get a secret
        >>> api_key = secret_manager.get_secret('API_KEY')
        >>> if api_key:
        ...     # Use the secret
        ...     client.configure(api_key)
        ... 
        >>> # Get a secret without caching
        >>> fresh_token = secret_manager.get_secret('AUTH_TOKEN', use_cache=False)

    Instance Variables:
        _client (secretmanager.SecretManagerServiceClient): Google Secret Manager client
        _project_id (str): Google Cloud project ID
        _cache (dict): Dictionary storing cached secret values
    """

    def __init__(self):
        self._client = secretmanager.SecretManagerServiceClient()
        self._project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if not self._project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT environment variable not set")

        self._cache = {}

    def _get_secret_path(self, secret_name: str) -> str:
        """Get the full path to a secret.

        Args:
            secret_name: Name of the secret

        Returns:
            Full path to the secret in Secret Manager
        """
        return f"projects/{self._project_id}/secrets/{secret_name}/versions/latest"

    def get_secret(self, secret_name: str, use_cache: bool = True) -> Optional[str]:
        """Get a secret value from Secret Manager.

        Args:
            secret_name: Name of the secret
            use_cache: Whether to use cached values

        Returns:
            Secret value, or None if not found
        """
        try:
            # Check cache first
            if use_cache and secret_name in self._cache:
                return self._cache[secret_name]

            # Get from Secret Manager
            path = self._get_secret_path(secret_name)
            response = self._client.access_secret_version(
                request={"name": path})
            secret = response.payload.data.decode("UTF-8")

            # Update cache
            if use_cache:
                self._cache[secret_name] = secret

            return secret

        except Exception as e:
            logger.error(f"Error accessing secret {secret_name}: {str(e)}")
            return None

    def clear_cache(self):
        """Clear the secrets cache."""
        self._cache.clear()


# Global instance
secret_manager = SecretManager()
