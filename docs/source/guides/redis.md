# Redis Messaging for Agent Development

## Overview

This module provides Redis-based messaging utilities for agent communication, including:

- **Synchronous and asynchronous Redis clients** for basic operations
- **PubSub messaging** for simple, broadcast-style communication
- **Streams** for durable, ordered message passing and workflow processing
- **Distributed locks** for coordination between agents
- **Rate limiters** for controlling access to resources

## Installation

Redis support is included in the main `requirements.txt` file. To install dependencies:

```bash
pip install -r requirements.txt
```

## Using Redis Utilities

### Basic Redis Operations

```python
from ailf.messaging.redis import RedisClient

# Create a client
client = RedisClient()

# Basic operations
client.set("key", "value")
value = client.get("key")
client.delete("key")

# JSON operations
client.set_json("user:123", {"name": "Alice", "role": "admin"})
user = client.get_json("user:123")
```

### PubSub Messaging

```python
from ailf.messaging.redis import RedisPubSub

# Publisher
pubsub = RedisPubSub()
pubsub.publish("notifications", {"type": "alert", "message": "System update required"})

# Subscriber
def message_handler(data):
    print(f"Received: {data}")

subscriber = RedisPubSub()
subscriber.subscribe("notifications", message_handler)
subscriber.run_in_thread()  # Non-blocking
# or
subscriber.run()  # Blocking
```

### Stream Processing

```python
from ailf.messaging.redis import RedisStream

# Producer
stream = RedisStream("tasks")
task_id = stream.add({"type": "analysis", "data": "sample"})

# Consumer with consumer groups
stream.create_consumer_group("workers", "worker-1")
messages = stream.read_group(count=10)
for message in messages:
    # Process message
    stream.acknowledge(message["id"])
```

### Distributed Locks

```python
from ailf.messaging.redis import RedisLock

# Using a lock
lock = RedisLock("critical-section")
if lock.acquire():
    try:
        # Perform operations that require exclusive access
        pass
    finally:
        lock.release()

# Using lock as a context manager
with lock.acquire_context() as acquired:
    if acquired:
        # Exclusive access section
        pass
```

### Rate Limiting

```python
from ailf.messaging.redis import RedisRateLimiter

# Create a rate limiter (10 requests per second)
limiter = RedisRateLimiter("api-endpoint", rate=10, period=1)

# Check if action is allowed
user_id = "user-123"
if limiter.is_allowed(user_id):
    # Perform rate-limited action
    pass
else:
    # Handle rate limit exceeded
    pass
```

## Examples

See the example files for working code:

- `examples/redis_pubsub_example.py` - Demonstrates agent communication using Redis PubSub
- `examples/redis_stream_example.py` - Shows distributed agent workflows using Redis Streams

## Development

The dev container includes a Redis server that starts automatically. To manually start/stop Redis:

```bash
# Start Redis
sudo service redis-server start

# Stop Redis
sudo service redis-server stop

# Check Redis status
sudo service redis-server status
```
