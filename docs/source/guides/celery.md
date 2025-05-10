# Distributed Task Processing with Celery

This guide covers how to use Celery for distributed task processing in your agent applications using the utilities provided in the `ailf.workers` module.

## Overview

Celery is a distributed task queue that allows you to run tasks asynchronously across multiple workers. The `ailf.workers` module provides pre-configured Celery integration for:

- Processing CPU or memory-intensive tasks
- Running background operations
- Scheduling periodic tasks
- Distributing work across multiple machines

## Getting Started

### Installation

Celery is included in the main requirements file. Install it with:

```bash
pip install -r requirements.txt
```

Redis is used as the default broker and result backend for Celery. Make sure Redis is running:

```bash
redis-server
```

### Starting a Worker

To start a Celery worker:

```bash
celery -A utils.workers.celery_app worker --loglevel=INFO
```

For development with auto-reloading:

```bash
watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A utils.workers.celery_app worker --loglevel=INFO
```

## Using Predefined Tasks

The template includes several predefined tasks in `ailf.workers.tasks`:

```python
from ailf.workers.tasks import process_document, analyze_content

# Process a document asynchronously
result = process_document.delay("document-123", {"format": "json"})

# Check task status
print(f"Task ID: {result.id}")
print(f"Task status: {result.status}")

# Get the result when ready
if result.ready():
    output = result.get()
    print(f"Result: {output}")
```

## Defining Custom Tasks

You can define your own tasks in `ailf.workers.tasks` or in your application code:

```python
from ailf.workers.celery_app import app

@app.task(bind=True, name="tasks.custom_task")
def custom_task(self, arg1, arg2=None):
    """A custom task.
    
    Args:
        arg1: First argument
        arg2: Optional second argument
    
    Returns:
        Task result
    """
    # Task implementation
    result = f"Processed {arg1} with {arg2}"
    
    # Optionally update task state
    self.update_state(state="PROGRESS", meta={"progress": 50})
    
    return result
```

## Task Execution Options

You can provide various options when executing tasks:

```python
# Basic execution
result = custom_task.delay(arg1="value", arg2="option")

# With more options
result = custom_task.apply_async(
    args=["value"], 
    kwargs={"arg2": "option"},
    countdown=10,  # Wait 10 seconds before executing
    expires=300,   # Task expires after 300 seconds
    retry=True,    # Retry on failure
    retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    }
)
```

## Handling Task Results

You can check and process task results:

```python
from celery.result import AsyncResult

# Get task by ID
task_id = "task-uuid-here"
result = AsyncResult(task_id)

# Check status
if result.status == 'SUCCESS':
    output = result.get()  # Get the return value
elif result.status == 'FAILURE':
    error = result.get(propagate=False)  # Get the exception
    print(f"Task failed: {error}")
elif result.status == 'PENDING':
    print("Task is still queued")
elif result.status == 'STARTED':
    print("Task has been started")
else:
    print(f"Task status: {result.status}")
```

## Task Progress and State Updates

Long-running tasks can report progress:

```python
@app.task(bind=True)
def long_process(self, items):
    total = len(items)
    for i, item in enumerate(items):
        # Process item...
        
        # Update progress
        progress = int((i + 1) / total * 100)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": progress,
                "current": i + 1,
                "total": total,
                "status": f"Processing item {i+1}/{total}"
            }
        )
    
    return {"status": "completed", "processed": total}
```

Tracking progress from the client:

```python
def check_task_progress(task_id):
    result = AsyncResult(task_id)
    if result.state == 'PROGRESS':
        progress = result.info.get('progress', 0)
        status = result.info.get('status', '')
        print(f"Progress: {progress}% - {status}")
        return False
    elif result.state == 'SUCCESS':
        print("Task completed!")
        return True
    else:
        print(f"Task state: {result.state}")
        return False
```

## Error Handling

Handle task failures appropriately:

```python
@app.task(bind=True, max_retries=3)
def risky_task(self, arg):
    try:
        # Task that might fail
        result = some_operation(arg)
        return result
    except TemporaryError as exc:
        # Retry with exponential backoff
        countdown = 2 ** self.request.retries
        self.retry(exc=exc, countdown=countdown)
    except Exception as exc:
        # Log and capture permanent errors
        logger.error(f"Task failed: {exc}")
        self.update_state(
            state="FAILURE",
            meta={
                "exc_type": type(exc).__name__,
                "exc_message": str(exc),
                "custom_error": "Task encountered an error"
            }
        )
        raise
```

## Integration with AsyncIO

Combine Celery with AsyncIO for hybrid task processing:

```python
import asyncio
from ailf.async_tasks import TaskManager
from ailf.workers.tasks import process_document
from celery.result import AsyncResult

async def process_documents(document_ids):
    """Process documents using Celery from AsyncIO."""
    # Submit tasks to Celery
    tasks = []
    for doc_id in document_ids:
        task = process_document.delay(doc_id)
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = []
    for task in tasks:
        # Wait for task to complete
        while not task.ready():
            await asyncio.sleep(0.5)
        
        # Get result
        result = task.get()
        results.append(result)
    
    return results

async def main():
    # Create task manager
    task_manager = TaskManager()
    await task_manager.start()
    
    try:
        # Submit async task that coordinates with Celery
        task_id = await task_manager.submit(
            process_documents(["doc1", "doc2", "doc3"])
        )
        
        # Wait for task to complete
        result = await task_manager.wait_for_task(task_id)
        print(f"All documents processed: {result}")
    finally:
        await task_manager.stop()

# Run the main function
asyncio.run(main())
```

## Scheduling Periodic Tasks

Configure periodic tasks (like cron jobs) in the Celery app:

```python
# In utils/workers/celery_app.py
app.conf.beat_schedule = {
    'cleanup-every-hour': {
        'task': 'tasks.cleanup',
        'schedule': 3600.0,  # Run every hour
        'args': (),
    },
    'daily-report': {
        'task': 'tasks.generate_report',
        'schedule': crontab(hour=7, minute=30),  # Run at 7:30 AM
        'args': ('daily',),
    },
}
```

To run the scheduler:

```bash
celery -A utils.workers.celery_app beat
```

## Integration with Redis Messaging

Combine Celery with Redis messaging for a complete system:

```python
import json
from ailf.messaging.redis import AsyncRedisClient, RedisPubSub
from ailf.workers.tasks import process_document
from celery.result import AsyncResult

async def redis_celery_bridge():
    """Bridge between Redis messages and Celery tasks."""
    # Set up Redis
    redis = AsyncRedisClient()
    await redis.connect()
    pubsub = RedisPubSub(client=redis)
    
    # Handle incoming requests
    async def message_handler(channel, message):
        try:
            data = json.loads(message)
            document_id = data.get("document_id")
            options = data.get("options", {})
            
            # Submit to Celery
            task = process_document.delay(document_id, options)
            
            # Acknowledge receipt
            await pubsub.publish(
                "processing:ack",
                json.dumps({
                    "document_id": document_id,
                    "task_id": task.id,
                    "status": "processing"
                })
            )
            
            # Monitor task completion (in a real app, use a separate monitoring task)
            while not task.ready():
                await asyncio.sleep(1)
            
            # Get result and publish
            try:
                result = task.get()
                await pubsub.publish(
                    "processing:results",
                    json.dumps({
                        "document_id": document_id,
                        "task_id": task.id,
                        "status": "completed",
                        "result": result
                    })
                )
            except Exception as e:
                await pubsub.publish(
                    "processing:results",
                    json.dumps({
                        "document_id": document_id,
                        "task_id": task.id,
                        "status": "failed",
                        "error": str(e)
                    })
                )
                
        except Exception as e:
            print(f"Error processing message: {e}")
    
    # Subscribe to request channel
    await pubsub.subscribe("processing:requests", message_handler)
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(10)
    finally:
        await pubsub.unsubscribe_all()
        await redis.disconnect()
```

## Production Configuration

For production environments, consider the following settings:

1. **Worker Concurrency**:
   ```bash
   celery -A utils.workers.celery_app worker --loglevel=INFO --concurrency=8
   ```

2. **Worker Pools**:
   ```bash
   # For CPU-bound tasks
   celery -A utils.workers.celery_app worker --pool=prefork
   
   # For I/O-bound tasks
   celery -A utils.workers.celery_app worker --pool=eventlet
   ```

3. **Multiple Queues**:
   ```python
   # Define a task with a specific queue
   @app.task(bind=True, queue='high-priority')
   def urgent_task(self):
       # ...
   ```
   
   ```bash
   # Start worker for specific queues
   celery -A utils.workers.celery_app worker --queues=high-priority,default
   ```

4. **Monitoring with Flower**:
   ```bash
   pip install flower
   celery -A utils.workers.celery_app flower
   ```

## Best Practices

1. **Keep tasks idempotent** - they should produce the same result if executed multiple times with the same input.

2. **Task serialization** - ensure all task arguments and results can be properly serialized.

3. **Handle task timeouts** - set reasonable time limits to prevent worker blocking.

4. **Avoid shared state** - tasks should be self-contained and not rely on shared memory.

5. **Task granularity** - make tasks neither too small (overhead) nor too large (hard to distribute).

6. **Error handling** - implement proper error handling and reporting.

7. **Monitoring** - set up monitoring for task queues, worker health, and resource usage.

8. **Resource cleanup** - ensure tasks clean up resources regardless of success or failure.

## Example Supervisord Configuration

For production deployment, you can use Supervisord to manage Celery workers:

```ini
[program:celery_worker]
command=/path/to/venv/bin/celery -A utils.workers.celery_app worker --loglevel=INFO
directory=/path/to/project
user=celery_user
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=30
priority=998

[program:celery_beat]
command=/path/to/venv/bin/celery -A utils.workers.celery_app beat --loglevel=INFO
directory=/path/to/project
user=celery_user
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=30
priority=999
```
