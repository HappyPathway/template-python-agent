"""ZMQ Schema Definitions

This module defines the data models and configuration schemas for ZMQ operations.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SocketType(str, Enum):
    """ZMQ socket types."""
    PUB = "PUB"  # zmq.PUB
    SUB = "SUB"  # zmq.SUB
    REQ = "REQ"  # zmq.REQ
    REP = "REP"  # zmq.REP
    PUSH = "PUSH"  # zmq.PUSH
    PULL = "PULL"  # zmq.PULL

    def get_zmq_type(self) -> int:
        """Get the ZMQ socket type constant for this enum value."""
        import zmq
        socket_type_map = {
            self.PUB: zmq.PUB,
            self.SUB: zmq.SUB,
            self.REQ: zmq.REQ,
            self.REP: zmq.REP,
            self.PUSH: zmq.PUSH,
            self.PULL: zmq.PULL
        }
        return socket_type_map[self]


class ZMQConfig(BaseModel):
    """ZMQ connection configuration."""
    socket_type: SocketType
    address: str
    bind: bool = False
    topics: List[str] = Field(default_factory=list)
    receive_timeout: Optional[int] = None
    send_timeout: Optional[int] = None
    identity: Optional[bytes] = None

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate ZMQ address format."""
        if not v.startswith(('tcp://', 'ipc://')):
            raise ValueError("Address must start with tcp:// or ipc://")
        return v

    model_config = {
        'validate_assignment': True,
        'extra': 'forbid'
    }


class MessageEnvelope(BaseModel):
    """Message envelope for ZMQ communications."""
    topic: Optional[str] = None
    payload: bytes
    metadata: dict = Field(default_factory=dict)
