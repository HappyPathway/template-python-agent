"""Redis messaging utilities.

This module provides Redis-based messaging patterns for distributed systems.
It includes both synchronous and asynchronous clients, as well as higher-level
abstractions for common messaging patterns such as pub/sub and streams.

Key Components:
    RedisClient: Synchronous Redis client implementation
    AsyncRedisClient: Asynchronous Redis client implementation
    RedisPubSub: Higher-level pub/sub implementation
    RedisStream: Stream-based messaging implementation

Example:
    Basic Redis operations:
        >>> from ailf.messaging import RedisClient
        >>> client = RedisClient()
        >>> client.set("key", "value")
        >>> value = client.get("key")
        >>> print(value)
        'value'
    
    PubSub messaging:
        >>> from ailf.messaging import RedisPubSub
        >>> 
        >>> # Publisher
        >>> pubsub = RedisPubSub()
        >>> pubsub.publish("channel", {"message": "hello"})
        >>> 
        >>> # Subscriber
        >>> def message_handler(data):
        ...     print(f"Received: {data}")
        >>> 
        >>> subscriber = RedisPubSub()
        >>> subscriber.subscribe("channel", message_handler)
        >>> subscriber.run_in_thread()  # Non-blocking subscription
"""

import json
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Union

# Try to import from utils if available (for development)
try:
    from utils.messaging.redis import (
        RedisClient,
        AsyncRedisClient,
        RedisPubSub,
        RedisStream,
        RedisLock,
        RedisRateLimiter,
        RedisConfig
    )
except ImportError:
    # Fallback implementations for standalone package
    import logging
    from ailf.schemas.redis import RedisConfig
    
    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)
    
    try:
        import redis
        from redis.exceptions import RedisError
    except ImportError:
        logger.warning("Redis package not installed. Using stub implementation.")
        
        # Create stub implementations for testing without Redis
        class RedisError(Exception):
            """Redis error exception."""
            pass
            
        class redis:
            """Stub Redis implementation."""
            @staticmethod
            def Redis(*args, **kwargs):
                logger.error("Attempted to use Redis but the package is not installed.")
                raise ImportError("Required package not found: redis. Install with: pip install redis")
        
        # Stub implementation if redis package is not available
        class RedisError(Exception):
            """Redis error exception."""
            pass
        
        class redis:
            """Stub Redis implementation."""
            @staticmethod
            def Redis(*args, **kwargs):
                logger.warning("Using stub Redis implementation. Install redis package for full functionality.")
                return StubRedisClient()
            
            class ConnectionPool:
                """Stub connection pool."""
                def __init__(self, *args, **kwargs):
                    pass
        
        class StubRedisClient:
            """Stub Redis client for when redis package is not available."""
            def __init__(self, *args, **kwargs):
                self._data = {}
            
            def ping(self):
                return "PONG"
            
            def get(self, key):
                logger.warning("Stub Redis: get(%s)", key)
                return self._data.get(key)
            
            def set(self, key, value, ex=None):
                logger.warning("Stub Redis: set(%s, %s)", key, value)
                self._data[key] = value
                return True
            
            def delete(self, key):
                logger.warning("Stub Redis: delete(%s)", key)
                if key in self._data:
                    del self._data[key]
                    return 1
                return 0
            
            def exists(self, key):
                return key in self._data
            
            def pipeline(self):
                return self
            
            def execute(self):
                return []
            
            def pubsub(self):
                return StubPubSub()
            
            def publish(self, channel, message):
                logger.warning("Stub Redis: publish(%s, %s)", channel, message)
                return 0
            
            def xadd(self, *args, **kwargs):
                logger.warning("Stub Redis: xadd(%s, %s)", args, kwargs)
                return "0-0"
            
            def xread(self, *args, **kwargs):
                logger.warning("Stub Redis: xread(%s, %s)", args, kwargs)
                return []
            
            def xreadgroup(self, *args, **kwargs):
                logger.warning("Stub Redis: xreadgroup(%s, %s)", args, kwargs)
                return []
        
        class StubPubSub:
            """Stub PubSub client."""
            def __init__(self):
                self.subscribed = {}
            
            def subscribe(self, *args):
                for channel in args:
                    self.subscribed[channel] = True
            
            def psubscribe(self, *args):
                for pattern in args:
                    self.subscribed[pattern] = True
            
            def unsubscribe(self, *args):
                for channel in args:
                    if channel in self.subscribed:
                        del self.subscribed[channel]
            
            def punsubscribe(self, *args):
                for pattern in args:
                    if pattern in self.subscribed:
                        del self.subscribed[pattern]
            
            def get_message(self, *args, **kwargs):
                return None

    class RedisClient:
        """Synchronous Redis client for agent communication.
        
        This class provides a simplified interface to Redis operations with
        error handling, logging, and convenience methods for common operations.
        
        Attributes:
            config: Redis connection configuration
            client: Raw Redis client instance
        """
        
        def __init__(self, config: Optional[RedisConfig] = None):
            """Initialize the Redis client.
            
            Args:
                config: Redis connection configuration (optional)
            """
            self.config = config or RedisConfig()
            self._client = None
            self.connect()
        
        def connect(self) -> None:
            """Connect to Redis server."""
            try:
                self._client = redis.Redis(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    ssl=self.config.ssl,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    socket_keepalive=self.config.socket_keepalive,
                    decode_responses=self.config.decode_responses,
                    max_connections=self.config.max_connections
                )
                # Test the connection
                self._client.ping()
                logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                raise
        
        @property
        def client(self) -> redis.Redis:
            """Get the raw Redis client.
            
            Returns:
                The underlying Redis client instance
            """
            if self._client is None:
                self.connect()
            return self._client
        
        def close(self) -> None:
            """Close the Redis connection."""
            if self._client:
                self._client.close()
                self._client = None
        
        @contextmanager
        def pipeline(self):
            """Get a Redis pipeline for batch operations.
            
            Example:
                >>> with redis_client.pipeline() as pipe:
                ...     pipe.set("key1", "value1")
                ...     pipe.set("key2", "value2")
                ...     pipe.execute()
            """
            pipe = self.client.pipeline()
            try:
                yield pipe
            finally:
                pipe.execute()
        
        def get(self, key: str) -> Optional[str]:
            """Get a value from Redis.
            
            Args:
                key: Key to get
                
            Returns:
                The value if found, None otherwise
            """
            try:
                return self.client.get(key)
            except RedisError as e:
                logger.error(f"Redis error in get({key}): {str(e)}")
                return None
        
        def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
            """Set a value in Redis.
            
            Args:
                key: Key to set
                value: Value to set
                expire: Optional expiration time in seconds
                
            Returns:
                True if successful, False otherwise
            """
            try:
                return bool(self.client.set(key, value, ex=expire))
            except RedisError as e:
                logger.error(f"Redis error in set({key}): {str(e)}")
                return False
        
        def delete(self, key: str) -> bool:
            """Delete a key from Redis.
            
            Args:
                key: Key to delete
                
            Returns:
                True if the key was deleted, False otherwise
            """
            try:
                return bool(self.client.delete(key))
            except RedisError as e:
                logger.error(f"Redis error in delete({key}): {str(e)}")
                return False
        
        def exists(self, key: str) -> bool:
            """Check if a key exists in Redis.
            
            Args:
                key: Key to check
                
            Returns:
                True if the key exists, False otherwise
            """
            try:
                return bool(self.client.exists(key))
            except RedisError as e:
                logger.error(f"Redis error in exists({key}): {str(e)}")
                return False
        
        def set_json(self, key: str, value: Dict[str, Any], expire: Optional[int] = None) -> bool:
            """Set a JSON value in Redis.
            
            Args:
                key: Key to set
                value: Dictionary to store as JSON
                expire: Optional expiration time in seconds
                
            Returns:
                True if successful, False otherwise
            """
            try:
                serialized = json.dumps(value)
                return bool(self.client.set(key, serialized, ex=expire))
            except (RedisError, TypeError) as e:
                logger.error(f"Error in set_json({key}): {str(e)}")
                return False
        
        def get_json(self, key: str) -> Optional[Dict[str, Any]]:
            """Get a JSON value from Redis.
            
            Args:
                key: Key to get
                
            Returns:
                The deserialized JSON object if found, None otherwise
            """
            try:
                value = self.client.get(key)
                if value:
                    return json.loads(value)
                return None
            except (RedisError, json.JSONDecodeError) as e:
                logger.error(f"Error in get_json({key}): {str(e)}")
                return None
        
        def publish(self, channel: str, message: Union[str, Dict[str, Any]]) -> int:
            """Publish a message to a Redis channel.
            
            Args:
                channel: Channel to publish to
                message: Message to publish (string or dict)
                
            Returns:
                Number of clients that received the message
            """
            try:
                # Convert dict to JSON string if necessary
                if isinstance(message, dict):
                    message = json.dumps(message)
                
                return self.client.publish(channel, message)
            except RedisError as e:
                logger.error(f"Redis error in publish({channel}): {str(e)}")
                return 0
        
        def health_check(self) -> bool:
            """Check if Redis is healthy.
            
            Returns:
                True if healthy, False otherwise
            """
            try:
                return self.client.ping() == "PONG"
            except RedisError:
                return False
    
    class AsyncRedisClient:
        """Placeholder for AsyncRedisClient.
        
        This class provides a minimal async Redis client placeholder.
        For a full implementation, please install the redis package.
        """
        
        def __init__(self, config: Optional[RedisConfig] = None):
            """Initialize the async Redis client.
            
            Args:
                config: Redis connection configuration (optional)
            """
            self.config = config or RedisConfig()
            logger.warning(
                "AsyncRedisClient requires redis[hiredis] package with async support. "
                "This is a placeholder implementation."
            )
    
    class RedisPubSub:
        """High-level Redis Pub/Sub interface.
        
        This class provides a simple interface for Pub/Sub messaging patterns
        with automatic JSON serialization/deserialization.
        
        Attributes:
            client: Redis client instance
            subscriptions: Dictionary of channel to handler mappings
        """
        
        def __init__(self, redis_client: Optional[RedisClient] = None):
            """Initialize the Redis Pub/Sub interface.
            
            Args:
                redis_client: Optional RedisClient to use
            """
            self.client = redis_client or RedisClient()
            self.subscriptions = {}
            self._pubsub = None
            self._running = False
            self._thread = None
        
        def publish(self, channel: str, message: Dict[str, Any]) -> int:
            """Publish a message to a channel.
            
            Args:
                channel: Channel to publish to
                message: Message to publish (will be serialized to JSON)
                
            Returns:
                Number of clients that received the message
            """
            try:
                serialized = json.dumps(message)
                return self.client.client.publish(channel, serialized)
            except Exception as e:
                logger.error(f"Error publishing to {channel}: {str(e)}")
                return 0
        
        def subscribe(self, channel: str, handler: Callable[[Dict[str, Any]], None]) -> None:
            """Subscribe to a channel.
            
            Args:
                channel: Channel to subscribe to
                handler: Function to call when a message is received
            """
            if self._pubsub is None:
                self._pubsub = self.client.client.pubsub()
            
            # Store the handler
            self.subscriptions[channel] = handler
            
            # Subscribe to the channel
            self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")
        
        def unsubscribe(self, channel: str) -> None:
            """Unsubscribe from a channel.
            
            Args:
                channel: Channel to unsubscribe from
            """
            if channel in self.subscriptions:
                del self.subscriptions[channel]
            
            if self._pubsub:
                self._pubsub.unsubscribe(channel)
                logger.info(f"Unsubscribed from channel: {channel}")
        
        def _message_handler(self, message: Dict[str, Any]) -> None:
            """Handle incoming messages and route to appropriate handlers."""
            if message['type'] != 'message':
                return
            
            channel = message['channel']
            if isinstance(channel, bytes):
                channel = channel.decode('utf-8')
            
            data = message['data']
            if channel in self.subscriptions:
                handler = self.subscriptions[channel]
                try:
                    # Parse JSON data
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    
                    parsed_data = json.loads(data)
                    handler(parsed_data)
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON data on {channel}: {data}")
                    # Pass the raw data to the handler
                    handler(data)
                except Exception as e:
                    logger.error(f"Error in handler for {channel}: {str(e)}")
        
        def run(self) -> None:
            """Run the subscription loop in the current thread (blocking)."""
            if not self._pubsub:
                logger.error("No subscriptions to run")
                return
            
            self._running = True
            logger.info("Starting Redis PubSub listener")
            
            try:
                while self._running:
                    message = self._pubsub.get_message(timeout=0.1)
                    if message:
                        self._message_handler(message)
                    time.sleep(0.01)  # Small sleep to prevent CPU hogging
            except Exception as e:
                logger.error(f"Error in subscription loop: {str(e)}")
            finally:
                self._running = False
                logger.info("Redis PubSub listener stopped")
        
        def run_in_thread(self, daemon: bool = True) -> threading.Thread:
            """Run the subscription loop in a background thread.
            
            Args:
                daemon: Whether the thread should be a daemon thread
                
            Returns:
                The created thread
            """
            if self._thread and self._thread.is_alive():
                logger.warning("Listener thread is already running")
                return self._thread
            
            self._thread = threading.Thread(target=self.run, daemon=daemon)
            self._thread.start()
            return self._thread
        
        def stop(self) -> None:
            """Stop listening for messages."""
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
                self._thread = None
        
        def __del__(self):
            """Clean up resources."""
            self.stop()
            if self._pubsub:
                try:
                    self._pubsub.close()
                except Exception:
                    pass
    
    class RedisStream:
        """High-level Redis Stream interface.
        
        Redis Streams are an append-only data structure that can be used for
        message brokers, event sourcing, and time-series data.
        
        Attributes:
            client: Redis client instance
            stream_name: Name of the stream
        """
        
        def __init__(self, stream_name: str, redis_client: Optional[RedisClient] = None):
            """Initialize the Redis Stream interface.
            
            Args:
                stream_name: Name of the stream
                redis_client: Optional Redis client to use
            """
            self.client = redis_client or RedisClient()
            self.stream_name = stream_name
            self._consumer_group = None
            self._consumer_name = None
            self._running = False
            self._thread = None
        
        def add(self, data: Dict[str, Any]) -> str:
            """Add a message to the stream.
            
            Args:
                data: Data to add to the stream
                
            Returns:
                ID of the added message
            """
            try:
                # Convert values to strings as required by Redis
                fields = {}
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        fields[k] = json.dumps(v)
                    else:
                        fields[k] = str(v)
                
                return self.client.client.xadd(
                    name=self.stream_name,
                    fields=fields,
                    maxlen=10000,  # Limit stream size
                    approximate=True
                )
            except RedisError as e:
                logger.error(f"Error adding to stream {self.stream_name}: {str(e)}")
                return ""
        
        def read(self, count: int = 10, block: Optional[int] = None, 
                last_id: str = "$") -> List[Dict[str, Any]]:
            """Read messages from the stream.
            
            Args:
                count: Maximum number of messages to read
                block: If set, block for this many milliseconds
                last_id: Start reading from this ID
                
            Returns:
                List of messages
            """
            try:
                streams = {self.stream_name: last_id}
                response = self.client.client.xread(
                    streams=streams,
                    count=count,
                    block=block
                )
                
                if not response:
                    return []
                
                messages = []
                for stream_name, stream_messages in response:
                    for message_id, fields in stream_messages:
                        # Decode the message ID if it's bytes
                        if isinstance(message_id, bytes):
                            message_id = message_id.decode('utf-8')
                        
                        # Convert values back from strings where possible
                        decoded_fields = {}
                        for k, v in fields.items():
                            # Decode key if needed
                            if isinstance(k, bytes):
                                k = k.decode('utf-8')
                                
                            # Decode value if needed
                            if isinstance(v, bytes):
                                v = v.decode('utf-8')
                                
                            # Try to parse JSON
                            try:
                                if v.startswith('{') or v.startswith('['):
                                    decoded_fields[k] = json.loads(v)
                                    continue
                            except (json.JSONDecodeError, AttributeError):
                                pass
                                
                            decoded_fields[k] = v
                        
                        messages.append({
                            "id": message_id,
                            "data": decoded_fields
                        })
                
                return messages
            except RedisError as e:
                logger.error(f"Error reading from stream {self.stream_name}: {str(e)}")
                return []
        
        def create_consumer_group(self, group_name: str, consumer_name: str, 
                                start_id: str = "$") -> bool:
            """Create a consumer group for the stream.
            
            Args:
                group_name: Name of the consumer group
                consumer_name: Name of the consumer
                start_id: ID to start consuming from
                
            Returns:
                True if successful, False otherwise
            """
            try:
                # Check if the stream exists
                if not self.client.client.exists(self.stream_name):
                    # Create the stream with an empty message
                    self.client.client.xadd(self.stream_name, {"create": "group"})
                
                # Create the consumer group
                self.client.client.xgroup_create(
                    name=self.stream_name,
                    groupname=group_name,
                    id=start_id,
                    mkstream=True
                )
                
                self._consumer_group = group_name
                self._consumer_name = consumer_name
                return True
            except RedisError as e:
                logger.error(
                    f"Error creating consumer group for stream {self.stream_name}: {str(e)}"
                )
                return False
        
        def read_group(self, count: int = 10, block: Optional[int] = None, 
                    last_id: str = ">") -> List[Dict[str, Any]]:
            """Read messages from the stream using a consumer group.
            
            Args:
                count: Maximum number of messages to read
                block: If set, block for this many milliseconds
                last_id: Start reading from this ID
                
            Returns:
                List of messages
            """
            if not self._consumer_group or not self._consumer_name:
                logger.error("Consumer group and name must be set before reading")
                return []
            
            try:
                streams = {self.stream_name: last_id}
                response = self.client.client.xreadgroup(
                    groupname=self._consumer_group,
                    consumername=self._consumer_name,
                    streams=streams,
                    count=count,
                    block=block,
                    noack=False  # Require explicit acknowledgment
                )
                
                if not response:
                    return []
                
                messages = []
                for stream_name, stream_messages in response:
                    for message_id, fields in stream_messages:
                        # Decode the message ID if it's bytes
                        if isinstance(message_id, bytes):
                            message_id = message_id.decode('utf-8')
                        
                        # Convert values back from strings where possible
                        decoded_fields = {}
                        for k, v in fields.items():
                            # Decode key if needed
                            if isinstance(k, bytes):
                                k = k.decode('utf-8')
                                
                            # Decode value if needed
                            if isinstance(v, bytes):
                                v = v.decode('utf-8')
                                
                            # Try to parse JSON
                            try:
                                if v.startswith('{') or v.startswith('['):
                                    decoded_fields[k] = json.loads(v)
                                    continue
                            except (json.JSONDecodeError, AttributeError):
                                pass
                                
                            decoded_fields[k] = v
                        
                        messages.append({
                            "id": message_id,
                            "data": decoded_fields
                        })
                
                return messages
            except RedisError as e:
                logger.error(f"Error reading from group {self._consumer_group}: {str(e)}")
                return []
        
        def acknowledge(self, message_id: str) -> bool:
            """Acknowledge processing of a message in a consumer group.
            
            Args:
                message_id: ID of the message to acknowledge
                
            Returns:
                True if successful, False otherwise
            """
            if not self._consumer_group:
                logger.error("Consumer group must be set before acknowledging")
                return False
            
            try:
                self.client.client.xack(
                    name=self.stream_name,
                    groupname=self._consumer_group,
                    id=message_id
                )
                return True
            except RedisError as e:
                logger.error(f"Error acknowledging message {message_id}: {str(e)}")
                return False


# Export public symbols
__all__ = [
    "RedisConfig",
    "RedisClient",
    "AsyncRedisClient",
    "RedisPubSub",
    "RedisStream",
    "RedisLock",
    "RedisRateLimiter"
]
