# Messaging with Redis

## Overview

This project includes built-in Redis messaging utilities for agent communication. Redis provides lightweight, fast messaging patterns for distributed systems.

## Key Components

- **RedisClient/AsyncRedisClient**: Base clients with error handling and convenience methods
- **RedisPubSub**: Publish-subscribe messaging for broadcasting messages
- **RedisStream**: Reliable, ordered message delivery with consumer groups
- **RedisLock**: Distributed locks for coordinating critical operations
- **RedisRateLimiter**: Rate limiting for resource protection

## Common Patterns

### Agent-to-Agent Communication

```python
# Publisher agent
from ailf.messaging.redis import RedisPubSub

pubsub = RedisPubSub()
pubsub.publish("agent-commands", {
    "command": "analyze", 
    "data": "content to analyze"
})

# Subscriber agent
def handle_command(message):
    if message["command"] == "analyze":
        # Process the command
        result = analyze_content(message["data"])
        # Publish the result
        pubsub.publish("agent-results", {"result": result})

pubsub = RedisPubSub()
pubsub.subscribe("agent-commands", handle_command)
pubsub.run()  # Blocking call
```

### Workflow Processing

```python
from ailf.messaging.redis import RedisStream

# Task producer
task_stream = RedisStream("tasks")
task_stream.add({
    "task_id": "123",
    "type": "document_processing",
    "content": "Document content"
})

# Task worker
worker_stream = RedisStream("tasks")
worker_stream.create_consumer_group("workers", "worker-1")

def process_task(task):
    # Process the task
    if task["type"] == "document_processing":
        process_document(task["content"])
    return True  # Mark as processed successfully

worker_stream.process_messages(process_task)
```

For more details and examples, see:

- [Redis messaging guide](docs/source/guides/redis.md)
- [Redis PubSub example](examples/redis_pubsub_example.py)
- [Redis Stream example](examples/redis_stream_example.py)
