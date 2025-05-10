"""Redis Schema Definitions.

This module defines the data models and configuration schemas for Redis connections
and operations.

Key Components:
    RedisConfig: Configuration for Redis connections
"""

from typing import Optional

from pydantic import BaseModel, Field


class RedisConfig(BaseModel):
    """Redis connection configuration.

    Attributes:
        host: Redis server hostname
        port: Redis server port
        db: Redis database number
        password: Optional Redis password
        ssl: Whether to use SSL for the connection
        socket_timeout: Socket timeout in seconds
        socket_connect_timeout: Socket connection timeout in seconds
        socket_keepalive: Whether to enable TCP keepalive
        max_connections: Maximum number of connections in the connection pool
        decode_responses: Whether to decode byte responses to strings
    """
    host: str = Field(default="localhost", description="Redis server hostname")
    port: int = Field(default=6379, description="Redis server port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Optional Redis password")
    ssl: bool = Field(default=False, description="Whether to use SSL for the connection")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(default=5, description="Socket connection timeout in seconds")
    socket_keepalive: bool = Field(default=True, description="Whether to enable TCP keepalive")
    max_connections: int = Field(default=10, description="Maximum number of connections in the pool")
    decode_responses: bool = Field(default=True, description="Whether to decode byte responses to strings")

    model_config = {
        "frozen": True,
        "validate_assignment": True,
        "extra": "forbid"
    }
