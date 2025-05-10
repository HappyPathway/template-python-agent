"""Client for interacting with Agent and Tool Registries.

This package provides clients to connect to and interact with external
registries that store descriptions of agents and tools.

Key Components:
    BaseRegistryClient: Abstract base class for registry clients.
    HTTPRegistryClient: A client implementation for registries that expose an HTTP/S API.
    RegistryError: Custom exception for registry client operations.
"""

from .base import BaseRegistryClient, RegistryError
from .http_client import HTTPRegistryClient

__all__ = [
    "BaseRegistryClient",
    "HTTPRegistryClient",
    "RegistryError",
]