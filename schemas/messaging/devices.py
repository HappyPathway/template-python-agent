"""ZMQ Device Schema Definitions.

This module defines the data models and configuration schemas for ZMQ devices
and authentication mechanisms.

Key Components:
    DeviceType: Enum for ZMQ device types
    DeviceConfig: Base configuration for ZMQ devices
    AuthConfig: Configuration for ZMQ authentication
"""

from enum import Enum, auto
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    """ZMQ device types.

    Each device type defines its frontend and backend socket types based on 
    standard ZMQ device configurations:
    - QUEUE: REP frontend, REQ backend
    - FORWARDER: SUB frontend, PUB backend
    - STREAMER: PULL frontend, PUSH backend
    """
    QUEUE = "QUEUE"
    FORWARDER = "FORWARDER"
    STREAMER = "STREAMER"

    @property
    def frontend_type(self) -> str:
        """Get frontend socket type."""
        type_map = {
            self.QUEUE: "REP",
            self.FORWARDER: "SUB",
            self.STREAMER: "PULL"
        }
        return type_map[self]

    @property
    def backend_type(self) -> str:
        """Get backend socket type."""
        type_map = {
            self.QUEUE: "REQ",
            self.FORWARDER: "PUB",
            self.STREAMER: "PUSH"
        }
        return type_map[self]

    @property
    def monitor_type(self) -> str:
        """Get monitor socket type."""
        return "PUB"


class DeviceConfig(BaseModel):
    """Base configuration for ZMQ devices."""
    device_type: DeviceType
    frontend_addr: str
    backend_addr: str
    monitor_addr: Optional[str] = None
    bind_frontend: bool = True
    bind_backend: bool = True
    bind_monitor: bool = True
    ignore_errors: bool = False
    auth_config: Optional["AuthConfig"] = None

    @property
    def frontend_type(self) -> str:
        """Get frontend socket type."""
        return self.device_type.frontend_type

    @property
    def backend_type(self) -> str:
        """Get backend socket type."""
        return self.device_type.backend_type

    @property
    def monitor_type(self) -> Optional[str]:
        """Get monitor socket type if monitor is configured."""
        return self.device_type.monitor_type if self.monitor_addr else None

    model_config = {
        'validate_assignment': True,
        'extra': 'forbid',
        'use_enum_values': True
    }


class AuthConfig(BaseModel):
    """Authentication configuration."""
    require_auth: bool = False
    allow_ips: List[str] = Field(default_factory=list)
    deny_ips: List[str] = Field(default_factory=list)
    certificates_dir: Optional[str] = None
    passwords: Dict[str, str] = Field(default_factory=dict)
    server_public_key: Optional[bytes] = None
    server_secret_key: Optional[bytes] = None

    model_config = {
        'validate_assignment': True,
        'extra': 'forbid'
    }
