# Redis Messaging with AILF

This guide provides an overview of the Redis messaging capabilities in the AILF package.

## Overview

AILF provides comprehensive Redis messaging utilities for distributed agent communication:

- **RedisClient**: Synchronous Redis client with error handling and convenience methods
- **AsyncRedisClient**: Asynchronous Redis client for async/await patterns
- **RedisPubSub**: Pub/Sub messaging for broadcast-style communication
- **RedisStream**: Reliable, ordered message delivery with consumer groups

## Basic Usage

### Configuration

```python
from ailf import RedisConfig, RedisClient

# Default configuration (localhost:6379)
client = RedisClient()

# Custom configuration
config = RedisConfig(
    host="redis.example.com",
    port=6380,
    password="secret",
    ssl=True
)
client = RedisClient(config)
```

### Simple Key-Value Operations

```python
from ailf import RedisClient

client = RedisClient()

# Set and get values
client.set("user:123:name", "Alice")
name = client.get("user:123:name")
print(name)  # 'Alice'

# JSON operations
user_data = {
    "name": "Alice",
    "role": "admin",
    "settings": {
        "theme": "dark",
        "notifications": True
    }
}
client.set_json("user:123", user_data)
retrieved = client.get_json("user:123")
```

## Pub/Sub Messaging

Pub/Sub is ideal for broadcast-style messaging where multiple subscribers receive all messages.

### Publisher

```python
from ailf import RedisPubSub

# Create publisher
publisher = RedisPubSub()

# Publish messages
publisher.publish("notifications", {
    "type": "alert",
    "message": "System maintenance scheduled",
    "level": "info",
    "timestamp": 1715026800
})
```

### Subscriber

```python
from ailf import RedisPubSub

# Create subscriber
subscriber = RedisPubSub()

# Define message handler
def handle_notification(data):
    print(f"Received notification: {data['message']}")
    
# Subscribe to channel
subscriber.subscribe("notifications", handle_notification)

# Start listening in background
thread = subscriber.run_in_thread()

# Or run in current thread (blocking)
# subscriber.run()

# Later, to stop listening
subscriber.stop()
```

## Streams

Redis Streams provide reliable, ordered message delivery with persistent storage and consumer groups.

### Producer

```python
from ailf import RedisStream

# Create stream
stream = RedisStream("tasks")

# Add messages to the stream
task_id = stream.add({
    "type": "analysis",
    "data": "Sample text to analyze",
    "priority": 1
})

print(f"Task added with ID: {task_id}")
```

### Consumer

```python
from ailf import RedisStream

# Create stream consumer
stream = RedisStream("tasks")

# Create consumer group
stream.create_consumer_group("workers", "worker-1")

# Read messages
messages = stream.read_group(count=10, block=2000)  # Block for 2 seconds

for message in messages:
    msg_id = message["id"]
    data = message["data"]
    
    print(f"Processing task: {data['type']}")
    
    # Process message...
    
    # Acknowledge message
    stream.acknowledge(msg_id)
```

## Error Handling

AILF's Redis components include built-in error handling:

```python
from ailf import RedisClient

client = RedisClient()

try:
    result = client.get("some-key")
    if result is None:
        print("Key not found")
    else:
        print(f"Value: {result}")
except Exception as e:
    print(f"Redis error: {str(e)}")
```

## Best Practices

1. **Connection Management**: Let AILF handle connection lifecycle - it manages connections efficiently
2. **Error Handling**: All Redis operations include error handling
3. **JSON Serialization**: Use the built-in JSON methods for structured data
4. **Long-Running Subscribers**: For long-running subscribers, use `run_in_thread()` with daemon=True
5. **Consumer Groups**: For work distribution, use stream consumer groups with explicit acknowledgment
