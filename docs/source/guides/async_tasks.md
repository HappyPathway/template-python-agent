# AsyncIO Task Management

This guide covers the AsyncIO task management utilities provided in the `ailf.async_tasks` module. These utilities help you manage and coordinate asynchronous tasks within your Python applications.

## Overview

The AsyncIO task management module provides a structured way to:

- Submit and track asynchronous tasks
- Monitor task progress and status
- Handle timeouts and failures gracefully
- Coordinate multiple concurrent tasks

## Task Manager Class

The `TaskManager` class is the central component for managing asynchronous tasks:

```python
import asyncio
from ailf.async_tasks import TaskManager

# Create and start a task manager
task_manager = TaskManager()
await task_manager.start()

# Submit a task for execution
async def my_task():
    print("Task running")
    await asyncio.sleep(2)
    return "Task completed"

task_id = await task_manager.submit(my_task())

# Get task information
task_info = task_manager.get_task_info(task_id)
print(f"Task status: {task_info.status}")

# Wait for the task to complete
await asyncio.sleep(3)
task_info = task_manager.get_task_info(task_id)
print(f"Task result: {task_info.result}")

# Clean up
await task_manager.stop()
```

## Task Status Tracking

Tasks can be in one of the following states:

- `PENDING`: Task has been created but not yet started
- `RUNNING`: Task is currently executing
- `COMPLETED`: Task has completed successfully
- `FAILED`: Task encountered an error during execution
- `CANCELLED`: Task was cancelled before completion

You can check a task's status:

```python
task_info = task_manager.get_task_info(task_id)
if task_info.status == TaskStatus.COMPLETED:
    print(f"Result: {task_info.result}")
elif task_info.status == TaskStatus.FAILED:
    print(f"Error: {task_info.error}")
```

## Task Timeouts

You can specify timeouts when submitting tasks:

```python
async def long_running_task():
    await asyncio.sleep(10)
    return "Done"

# Task will time out after 5 seconds
task_id = await task_manager.submit(
    long_running_task(), 
    timeout=5
)

# Wait and check the status
await asyncio.sleep(6)
task_info = task_manager.get_task_info(task_id)
# This will show FAILED status with a timeout error
print(f"Status: {task_info.status}, Error: {task_info.error}")
```

## Progress Tracking

Long-running tasks can report progress:

```python
async def task_with_progress():
    for i in range(10):
        # Do work...
        await asyncio.sleep(0.5)
        # Update progress (0-100)
        task_manager.update_progress(task_id, (i+1) * 10)
    return "Complete"

task_id = await task_manager.submit(task_with_progress())

# Poll for progress
for _ in range(5):
    await asyncio.sleep(1)
    info = task_manager.get_task_info(task_id)
    print(f"Progress: {info.progress}%")
```

## Task Cancellation

You can cancel running tasks:

```python
async def long_task():
    try:
        await asyncio.sleep(30)
        return "Completed"
    except asyncio.CancelledError:
        # Clean up resources if needed
        raise  # Re-raise to properly handle cancellation

task_id = await task_manager.submit(long_task())
await asyncio.sleep(2)  # Let the task start

# Cancel the task
success = await task_manager.cancel_task(task_id)
if success:
    print("Task was cancelled")
```

## Waiting for Tasks

Wait for a task to complete with an optional timeout:

```python
task_id = await task_manager.submit(some_task())

# Wait for up to 5 seconds
result = await task_manager.wait_for_task(task_id, timeout=5)
if result is not None:
    print(f"Task completed with result: {result}")
else:
    print("Task timed out or failed")
```

## Task Metadata

You can attach metadata to tasks to help track their purpose or context:

```python
metadata = {
    "user_id": "user-123",
    "priority": "high",
    "description": "Process user data"
}

task_id = await task_manager.submit(
    process_user_task("user-123"),
    metadata=metadata
)
```

## Listing Tasks

You can list all tasks or filter by status:

```python
# Get all tasks
all_tasks = task_manager.list_tasks()

# Get only running tasks
running_tasks = task_manager.list_tasks(status=TaskStatus.RUNNING)

# Show pending and running task count
pending = task_manager.list_tasks(status=TaskStatus.PENDING)
running = task_manager.list_tasks(status=TaskStatus.RUNNING)
print(f"Pending: {len(pending)}, Running: {len(running)}")
```

## Error Handling

The task manager handles errors within tasks and captures the exceptions:

```python
async def failing_task():
    await asyncio.sleep(1)
    raise ValueError("Something went wrong")

task_id = await task_manager.submit(failing_task())
await asyncio.sleep(2)  # Wait for task to fail

info = task_manager.get_task_info(task_id)
if info.status == TaskStatus.FAILED:
    print(f"Task failed with error: {info.error}")
```

## Task Cleanup

The task manager automatically cleans up completed, failed, and cancelled tasks after a period of time (default: 1 hour). You don't need to manually remove old tasks.

## Integration with Redis Messaging

The AsyncIO task manager works well with Redis messaging for building distributed systems:

```python
from ailf.messaging.redis import AsyncRedisClient, RedisPubSub
from ailf.async_tasks import TaskManager
import json

async def setup_agent():
    # Create components
    redis = AsyncRedisClient()
    pubsub = RedisPubSub(client=redis)
    task_manager = TaskManager()
    
    # Start components
    await redis.connect()
    await task_manager.start()
    
    # Subscribe to messages
    async def message_handler(channel, message):
        try:
            data = json.loads(message)
            # Process each message in a separate task
            await task_manager.submit(
                process_message(data),
                metadata={"message_source": channel}
            )
        except Exception as e:
            print(f"Error handling message: {e}")
    
    await pubsub.subscribe("agent:requests", message_handler)
    
    async def process_message(data):
        # Process message...
        result = {"status": "completed", "data": "processed"}
        # Publish result
        await pubsub.publish("agent:results", json.dumps(result))
    
    return redis, pubsub, task_manager

# Main application
async def main():
    redis, pubsub, task_manager = await setup_agent()
    try:
        # Keep agent running
        while True:
            await asyncio.sleep(1)
    finally:
        # Clean up
        await pubsub.unsubscribe_all()
        await task_manager.stop()
        await redis.disconnect()
```

## Integration with Celery

You can combine AsyncIO task management with Celery for hybrid task processing:

```python
from ailf.async_tasks import TaskManager
from ailf.workers.tasks import process_document
from celery.result import AsyncResult

async def hybrid_processing():
    task_manager = TaskManager()
    await task_manager.start()
    
    async def coordinate_processing(document_ids):
        # Submit to Celery
        celery_tasks = []
        for doc_id in document_ids:
            task = process_document.delay(doc_id)
            celery_tasks.append(task)
        
        # Monitor Celery tasks from AsyncIO
        results = []
        for task in celery_tasks:
            # Poll until complete
            while not task.ready():
                await asyncio.sleep(0.5)
            
            # Get result when ready
            result = task.get()
            results.append(result)
        
        return results
    
    # Process multiple documents
    task_id = await task_manager.submit(
        coordinate_processing(["doc1", "doc2", "doc3"])
    )
    
    # Wait for all processing to complete
    result = await task_manager.wait_for_task(task_id)
    print(f"All documents processed: {result}")
    
    await task_manager.stop()
```

## Best Practices

1. **Always start and stop the TaskManager properly**:
   ```python
   await task_manager.start()
   # ...use the task manager...
   await task_manager.stop()
   ```

2. **Use try/finally for clean shutdown**:
   ```python
   try:
       # Use task manager
   finally:
       await task_manager.stop()
   ```

3. **Set appropriate timeouts** for tasks to avoid indefinite hanging.

4. **Handle task exceptions** in long-running tasks:
   ```python
   async def robust_task():
       try:
           # Task logic
       except asyncio.CancelledError:
           # Handle cancellation gracefully
           raise  # Re-raise to signal cancellation
       except Exception as e:
           # Log and handle other exceptions
           print(f"Task error: {e}")
           raise  # Re-raise to mark task as failed
   ```

5. **Monitor task status** regularly to detect stalled or failed tasks.

6. **Use metadata** to track context for each task.

7. **Consider memory usage** - don't keep too many large results in memory.
