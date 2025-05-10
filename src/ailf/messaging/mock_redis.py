"""Mock Redis Client for Testing.

This module provides mock implementations of Redis clients for testing environments
without a Redis server. It implements the same interfaces as the real clients but
uses in-memory storage instead of connecting to a Redis server.

Example:
    >>> from ailf.messaging.mock_redis import MockRedisClient
    >>> client = MockRedisClient()
    >>> client.set("key", "value")
    >>> value = client.get("key")
    >>> print(value)
    'value'
"""

import asyncio
import json
import time
from collections import defaultdict
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from ailf.messaging.redis import RedisConfig


class MockRedisClient:
    """Mock implementation of RedisClient for testing without a Redis server."""

    _storage: Dict[str, Dict[str, Any]] = {}
    _pubsub_channels: Dict[str, List[Callable]] = {}
    _streams: Dict[str, Dict[str, Any]] = defaultdict(dict)
    _stream_groups: Dict[str, Dict[str, Any]] = defaultdict(dict)
    _lock = Lock()

    def __init__(self, config: Optional[RedisConfig] = None):
        """Initialize the mock Redis client.

        Args:
            config: Redis configuration (ignored in mock implementation)
        """
        self._db_id = 0 if config is None else config.db
        # Initialize storage for this DB if needed
        with self._lock:
            if self._db_id not in self._storage:
                self._storage[self._db_id] = {}
        self.client = self  # For compatibility with RedisClient

        # Log the initialization to help with debugging
        print(f"MockRedisClient initialized with db={self._db_id}")

        # Track whether Redis would be available in a real environment
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("localhost", 6379))
            s.close()
            self._real_redis_available = True
            print("Note: Real Redis is actually available, but using mock implementation")
        except (socket.error, ConnectionRefusedError):
            self._real_redis_available = False
            print("Note: Real Redis is not available, mock implementation is appropriate")

    @property
    def _db(self) -> Dict[str, Any]:
        """Get the current database."""
        return self._storage[self._db_id]

    def get(self, key: str) -> Optional[str]:
        """Get a value from the mock Redis store."""
        with self._lock:
            return self._db.get(key)

    def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        """Set a value in the mock Redis store."""
        with self._lock:
            if nx and key in self._db:  # NX mode - only set if key does not exist
                return False
            self._db[key] = value
            return True

    def delete(self, key: str) -> bool:
        """Delete a key from the mock Redis store."""
        with self._lock:
            if key in self._db:
                del self._db[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists in the mock Redis store."""
        with self._lock:
            return key in self._db

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern from the mock Redis store."""
        import fnmatch
        with self._lock:
            return [k for k in self._db.keys() if fnmatch.fnmatch(k, pattern)]

    def flushdb(self) -> bool:
        """Clear the current database."""
        with self._lock:
            self._db.clear()
            return True

    def close(self) -> None:
        """Close the connection (no-op in mock)."""
        pass

    # JSON operations
    def json_set(self, key: str, path: str, obj: Any) -> bool:
        """Set a JSON value in the mock Redis store."""
        with self._lock:
            if path != ".":
                raise NotImplementedError("Only root path is supported in mock")
            self._db[key] = json.dumps(obj)
            return True

    def json_get(self, key: str, path: str = ".") -> Optional[Any]:
        """Get a JSON value from the mock Redis store."""
        with self._lock:
            if path != ".":
                raise NotImplementedError("Only root path is supported in mock")
            if key not in self._db:
                return None
            return json.loads(self._db[key])
            
    # Additional methods for compatibility with tests
    
    def set_json(self, key: str, obj: Any) -> bool:
        """Set a JSON value in the mock Redis store."""
        return self.json_set(key, ".", obj)
    
    def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON value from the mock Redis store."""
        return self.json_get(key)
        
    def pubsub(self):
        """Create a PubSub instance."""
        return MockPubSub(self)
        
    def health_check(self) -> bool:
        """Check connection to Redis."""
        return True
        
    def xadd(self, stream: str, fields: Dict[str, Any]):
        """Add entry to a stream."""
        with self._lock:
            id_str = f"{int(time.time() * 1000)}-0"
            if stream not in self._streams:
                self._streams[stream] = {}
            self._streams[stream][id_str] = fields
            return id_str
            
    def xgroup_create(self, stream: str, group_name: str, id: str = "$", mkstream: bool = False):
        """Create a consumer group."""
        with self._lock:
            if stream not in self._streams and mkstream:
                self._streams[stream] = {}
                
            if stream not in self._stream_groups:
                self._stream_groups[stream] = {}
                
            self._stream_groups[stream][group_name] = {
                "last_id": id,
                "consumers": {},
                "pending": {}
            }
            return True
    
    def xread(self, streams: Dict[str, str], count: int = None, block: int = None):
        """Read from streams.
        
        Returns a list of stream, message tuples to match Redis format.
        """
        with self._lock:
            result = []
            for stream_name, last_id in streams.items():
                if stream_name not in self._streams:
                    continue
                    
                messages = []
                for msg_id, fields in self._streams[stream_name].items():
                    if last_id == "0" or last_id == "0-0" or msg_id > last_id:
                        messages.append((msg_id, fields))
                        
                if messages:
                    result.append((stream_name, messages))
                    
            return result
    
    def xreadgroup(self, group_name: str, consumer_name: str, streams: Dict[str, str], 
                count: int = None, block: int = None, noack: bool = False):
        """Read from a consumer group.
        
        Returns a list of stream, message tuples to match Redis format.
        """
        with self._lock:
            result = []
            for stream_name, id_str in streams.items():
                if (stream_name not in self._streams or 
                    stream_name not in self._stream_groups or 
                    group_name not in self._stream_groups[stream_name]):
                    continue
                    
                group = self._stream_groups[stream_name][group_name]
                if consumer_name not in group["consumers"]:
                    group["consumers"][consumer_name] = {}
                    
                messages = []
                for msg_id, fields in self._streams[stream_name].items():
                    if (id_str == ">" and msg_id not in group["pending"]) or (id_str == "0" and msg_id > group["last_id"]):
                        messages.append((msg_id, fields))
                        if not noack:
                            if stream_name not in group["pending"]:
                                group["pending"][stream_name] = {}
                            group["pending"][stream_name][msg_id] = consumer_name
                        
                if messages:
                    result.append((stream_name, messages))
                    
            return result
    
    def xack(self, stream: str, group_name: str, *ids):
        """Acknowledge a message in a consumer group."""
        with self._lock:
            if (stream not in self._stream_groups or 
                group_name not in self._stream_groups[stream] or
                stream not in self._stream_groups[stream][group_name]["pending"]):
                return 0
                
            count = 0
            for id_str in ids:
                if id_str in self._stream_groups[stream][group_name]["pending"][stream]:
                    del self._stream_groups[stream][group_name]["pending"][stream][id_str]
                    count += 1
                    
            return count
    
    def pipeline(self):
        """Create a pipeline for batched operations."""
        return MockPipeline(self)


class MockPubSub:
    """Mock implementation of Redis PubSub."""
    
    def __init__(self, client):
        """Initialize the mock PubSub."""
        self.client = client
        self.channels = {}
        self.patterns = {}
        self._listeners = {}
        self._subscribed = set()
        
    def subscribe(self, *channels, **kwargs):
        """Subscribe to one or more channels.
        
        Handles both positional and keyword arguments.
        """
        # Handle positional arguments
        for channel in channels:
            self._subscribed.add(channel)
            self.channels[channel] = True
            
        # Handle keyword arguments (channel=handler format)
        for channel, handler in kwargs.items():
            self._subscribed.add(channel)
            self.channels[channel] = True
            
    def unsubscribe(self, *channels):
        """Unsubscribe from one or more channels."""
        for channel in channels:
            if channel in self.channels:
                self._subscribed.remove(channel)
                del self.channels[channel]
                
    def listen(self):
        """Listen for messages (generator)."""
        # This is a simplified version that would block forever in a real scenario
        # For testing, we just yield a sentinel message for each subscribed channel
        for channel in self._subscribed:
            yield {"type": "subscribe", "channel": channel, "data": 1}
            
        # Add a message to simulate received data
        yield {"type": "message", "channel": list(self._subscribed)[0] if self._subscribed else "test", 
               "data": json.dumps({"test": "data"})}
        
    def get_message(self, timeout=None):
        """Get a single message."""
        # For testing, return a test message for the first channel
        if self._subscribed:
            channel = list(self._subscribed)[0]
            return {"type": "message", "channel": channel, "data": json.dumps({"test": "data"})}
        return None
        
    def psubscribe(self, *patterns):
        """Subscribe to channel patterns."""
        for pattern in patterns:
            self.patterns[pattern] = True
            
    def punsubscribe(self, *patterns):
        """Unsubscribe from channel patterns."""
        for pattern in patterns:
            if pattern in self.patterns:
                del self.patterns[pattern]
                
    def run_in_thread(self, daemon=False):
        """Run the subscription in a thread (mock implementation)."""
        # Just return a mock thread object
        thread = Thread(target=lambda: None)
        thread.daemon = daemon
        thread.start()  # This won't actually run anything significant
        return thread


class MockPipeline:
    """Mock implementation of Redis Pipeline."""
    
    def __init__(self, client):
        """Initialize the mock pipeline."""
        self.client = client
        self.commands = []
        
    def __enter__(self):
        """Enter context manager."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and execute commands."""
        self.execute()
        
    def execute(self):
        """Execute all commands in the pipeline."""
        results = []
        for cmd, args, kwargs in self.commands:
            method = getattr(self.client, cmd)
            results.append(method(*args, **kwargs))
        self.commands = []
        return results
        
    # Add proxy methods for Redis operations
    def set(self, *args, **kwargs):
        """Add a SET command to the pipeline."""
        self.commands.append(("set", args, kwargs))
        return self
        
    def get(self, *args, **kwargs):
        """Add a GET command to the pipeline."""
        self.commands.append(("get", args, kwargs))
        return self
        
    def incr(self, *args, **kwargs):
        """Add an INCR command to the pipeline."""
        self.commands.append(("incr", args, kwargs))
        return self
        
    def exists(self, *args, **kwargs):
        """Add an EXISTS command to the pipeline."""
        self.commands.append(("exists", args, kwargs))
        return self


class MockAsyncRedisClient:
    """Mock implementation of AsyncRedisClient for testing without a Redis server."""

    _storage: Dict[str, Dict[str, Any]] = {}
    _lock = Lock()

    def __init__(self, config: Optional[RedisConfig] = None):
        """Initialize the mock async Redis client.

        Args:
            config: Redis configuration (ignored in mock implementation)
        """
        self._db_id = 0 if config is None else config.db
        # Initialize storage for this DB if needed
        with self._lock:
            if self._db_id not in self._storage:
                self._storage[self._db_id] = {}
        self.client = self  # For compatibility with AsyncRedisClient

    @property
    def _db(self) -> Dict[str, Any]:
        """Get the current database."""
        return self._storage[self._db_id]

    async def get(self, key: str) -> Optional[str]:
        """Get a value from the mock Redis store."""
        with self._lock:
            return self._db.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a value in the mock Redis store."""
        with self._lock:
            self._db[key] = value
            return True

    async def delete(self, key: str) -> int:
        """Delete a key from the mock Redis store."""
        with self._lock:
            if key in self._db:
                del self._db[key]
                return 1
            return 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the mock Redis store."""
        with self._lock:
            return key in self._db

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern from the mock Redis store."""
        import fnmatch
        with self._lock:
            return [k for k in self._db.keys() if fnmatch.fnmatch(k, pattern)]

    async def flushdb(self) -> bool:
        """Clear the current database."""
        with self._lock:
            self._db.clear()
            return True

    async def close(self) -> None:
        """Close the connection (no-op in mock)."""
        pass

    # JSON operations
    async def json_set(self, key: str, path: str, obj: Any) -> bool:
        """Set a JSON value in the mock Redis store."""
        with self._lock:
            if path != ".":
                raise NotImplementedError("Only root path is supported in mock")
            self._db[key] = json.dumps(obj)
            return True

    async def json_get(self, key: str, path: str = ".") -> Optional[Any]:
        """Get a JSON value from the mock Redis store."""
        with self._lock:
            if path != ".":
                raise NotImplementedError("Only root path is supported in mock")
            if key not in self._db:
                return None
            return json.loads(self._db[key])

    async def health_check(self) -> bool:
        """Check connection to Redis."""
        return True

    def is_connected(self) -> bool:
        """Check if the client is connected (always True for mock)."""
        return True
        
    async def set_json(self, key: str, obj: Any) -> bool:
        """Set a JSON value in the mock Redis store."""
        return await self.json_set(key, ".", obj)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON value from the mock Redis store."""
        return await self.json_get(key)
