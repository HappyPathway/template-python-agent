"""Messaging infrastructure for distributed agent systems.

This package provides utilities for agent communication and coordination,
including ZeroMQ and Redis-based implementations.

Key components:
    - ZeroMQ patterns: Publisher/subscriber, client/server, push/pull
    - ZeroMQ devices: Forwarder, streamer, queue devices with device manager
    - Redis clients: Synchronous and asynchronous Redis clients
    - Redis patterns: PubSub and Streams for reliable messaging
"""

# Import ZMQ base patterns
from .zmq import (
    ZMQBase,
    ZMQPublisher,
    ZMQSubscriber,
    ZMQClient,
    ZMQServer
)

# Import ZMQ device patterns
from .zmq_devices import (
    ZMQDevice,
    ZMQForwarder,
    ZMQStreamer,
    ZMQProxy
)

# Import device management
from .zmq_device_manager import (
    DeviceManager,
    DeviceError,
    create_device
)

# Import Redis components
from .redis import (
    RedisClient,
    AsyncRedisClient,
    RedisPubSub,
    RedisStream
)

__all__ = [
    # ZMQ base patterns
    "ZMQBase",
    "ZMQPublisher", 
    "ZMQSubscriber",
    "ZMQClient",
    "ZMQServer",
    
    # ZMQ devices
    "ZMQDevice",
    "ZMQForwarder",
    "ZMQStreamer",
    "ZMQProxy",
    
    # Device management
    "DeviceManager",
    "DeviceError",
    "create_device",
    
    # Redis components
    "RedisClient",
    "AsyncRedisClient",
    "RedisPubSub",
    "RedisStream"
]
