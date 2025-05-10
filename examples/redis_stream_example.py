"""Redis Streams for Agent Workflow Example.

This example demonstrates how to use Redis Streams for implementing
distributed agent workflows. It shows how multiple agents can collaborate
on tasks using Redis Streams for durable, ordered message passing.

Example:
    Run the dispatcher in one terminal:
    $ python -m examples.redis_stream_example --role dispatcher

    Run multiple workers in other terminals:
    $ python -m examples.redis_stream_example --role worker --id worker1
    $ python -m examples.redis_stream_example --role worker --id worker2
"""

import argparse
import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ailf.messaging.redis import RedisClient, RedisConfig, RedisStream

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("redis_streams")

# Define stream names
TASKS_STREAM = "agent:tasks"
RESULTS_STREAM = "agent:results"
EVENTS_STREAM = "agent:events"

# Define consumer groups
WORKERS_GROUP = "workers"
ANALYTICS_GROUP = "analytics"


class TaskGenerator:
    """Generates sample tasks for the workflow."""

    def __init__(self):
        """Initialize task generator."""
        self.task_types = ["text_analysis",
                           "image_processing", "data_extraction"]
        self.priorities = ["low", "medium", "high", "critical"]
        self.counter = 0

    def generate_task(self) -> Dict[str, Any]:
        """Generate a sample task.

        Returns:
            Task dictionary
        """
        import random

        self.counter += 1
        task_id = f"task-{self.counter}"

        task_type = random.choice(self.task_types)
        priority = random.choice(self.priorities)

        # Generate task-specific parameters
        if task_type == "text_analysis":
            params = {
                "text": f"Sample text for analysis {task_id}",
                "analysis_type": random.choice(["sentiment", "classification", "extraction"]),
                "max_tokens": random.randint(50, 200)
            }
        elif task_type == "image_processing":
            params = {
                "image_url": f"https://example.com/images/{task_id}.jpg",
                "processing_type": random.choice(["resize", "filter", "detect_objects"]),
                "quality": random.randint(75, 100)
            }
        else:  # data_extraction
            params = {
                "source_url": f"https://example.com/data/{task_id}",
                "format": random.choice(["json", "csv", "xml"]),
                "fields": ["id", "name", "value", "timestamp"]
            }

        # Create the task object
        task = {
            "task_id": task_id,
            "type": task_type,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "parameters": params,
            "timeout": 60
        }

        return task


class TaskDispatcher:
    """Dispatches tasks to workers using Redis Streams."""

    def __init__(self, redis_config: Optional[RedisConfig] = None):
        """Initialize the task dispatcher.

        Args:
            redis_config: Optional Redis configuration
        """
        self.redis_config = redis_config or RedisConfig()
        self.task_stream = RedisStream(TASKS_STREAM)
        self.result_stream = RedisStream(RESULTS_STREAM)
        self.event_stream = RedisStream(EVENTS_STREAM)
        self.task_generator = TaskGenerator()
        self.running = False
        self._setup_signal_handlers()

        # Initialize Redis client for monitoring
        self.redis = RedisClient(self.redis_config)

    def _setup_signal_handlers(self):
        """Set up handlers for termination signals."""
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down dispatcher...")
        self.running = False
        # Give the background threads time to complete
        time.sleep(0.5)
        sys.exit(0)

    def monitor_workers(self):
        """Monitor worker status and activity."""
        # Get information about consumer groups
        try:
            info = self.redis.client.xinfo_groups(TASKS_STREAM)
            worker_count = 0
            pending_tasks = 0

            for group_info in info:
                if group_info['name'] == WORKERS_GROUP:
                    worker_count = group_info['consumers']
                    pending_tasks = group_info['pending']

            logger.info(
                f"Active workers: {worker_count}, Pending tasks: {pending_tasks}")

            # Record this information as an event
            if worker_count > 0:
                self.event_stream.add({
                    "event_type": "monitoring",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "worker_count": str(worker_count),
                        "pending_tasks": str(pending_tasks)
                    }
                })

        except Exception as e:
            logger.error(f"Error monitoring workers: {str(e)}")

    def process_results(self):
        """Process and log task results."""
        results = self.result_stream.read(count=10, block=500)

        for result in results:
            result_data = result["data"]
            task_id = result_data.get("task_id", "unknown")
            status = result_data.get("status", "unknown")
            worker_id = result_data.get("worker_id", "unknown")

            logger.info(
                f"Task {task_id} completed by {worker_id} with status {status}")

    def start(self):
        """Start the task dispatcher."""
        self.running = True
        logger.info("Task dispatcher started")

        # Create consumer groups if they don't exist
        self.task_stream.create_consumer_group(
            WORKERS_GROUP, "dispatcher", "0")
        self.result_stream.create_consumer_group(
            ANALYTICS_GROUP, "dispatcher", "0")

        # Main dispatch loop
        try:
            while self.running:
                # Generate and dispatch a new task
                task = self.task_generator.generate_task()
                task_id = task["task_id"]

                logger.info(
                    f"Dispatching task {task_id} of type {task['type']}")
                self.task_stream.add(task)

                # Record task dispatch as an event
                self.event_stream.add({
                    "event_type": "task_dispatched",
                    "timestamp": datetime.now().isoformat(),
                    "task_id": task_id,
                    "task_type": task["type"],
                    "priority": task["priority"]
                })

                # Process any completed task results
                self.process_results()

                # Monitor worker state
                self.monitor_workers()

                # Pause between tasks
                time.sleep(5)

        except KeyboardInterrupt:
            self.running = False

        logger.info("Task dispatcher stopped")


class TaskWorker:
    """Processes tasks from Redis Streams."""

    def __init__(self, worker_id: str, redis_config: Optional[RedisConfig] = None):
        """Initialize the task worker.

        Args:
            worker_id: Unique worker identifier
            redis_config: Optional Redis configuration
        """
        self.worker_id = worker_id
        self.redis_config = redis_config or RedisConfig()
        self.task_stream = RedisStream(TASKS_STREAM)
        self.result_stream = RedisStream(RESULTS_STREAM)
        self.event_stream = RedisStream(EVENTS_STREAM)
        self.running = False
        self._setup_signal_handlers()

        # Task processors mapped by task type
        self.task_processors = {
            "text_analysis": self._process_text_analysis,
            "image_processing": self._process_image_processing,
            "data_extraction": self._process_data_extraction
        }

    def _setup_signal_handlers(self):
        """Set up handlers for termination signals."""
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down worker...")
        self.running = False
        # Give the background threads time to complete
        time.sleep(0.5)
        sys.exit(0)

    def _process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task based on its type.

        Args:
            task_data: Task data dictionary

        Returns:
            Task result dictionary
        """
        task_id = task_data.get("task_id", "unknown")
        task_type = task_data.get("type", "unknown")

        logger.info(
            f"Worker {self.worker_id} processing task {task_id} of type {task_type}")

        # Record task start event
        self.event_stream.add({
            "event_type": "task_started",
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "worker_id": self.worker_id
        })

        # Find the appropriate processor
        processor = self.task_processors.get(task_type)
        if processor:
            try:
                start_time = time.time()
                result = processor(task_data)
                processing_time = time.time() - start_time

                # Add processing metadata
                result.update({
                    "task_id": task_id,
                    "worker_id": self.worker_id,
                    "processing_time": str(processing_time),
                    "completed_at": datetime.now().isoformat(),
                    "status": "completed"
                })

                return result

            except Exception as e:
                logger.error(f"Error processing task {task_id}: {str(e)}")
                return {
                    "task_id": task_id,
                    "worker_id": self.worker_id,
                    "status": "error",
                    "error": str(e),
                    "completed_at": datetime.now().isoformat()
                }
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {
                "task_id": task_id,
                "worker_id": self.worker_id,
                "status": "error",
                "error": f"Unknown task type: {task_type}",
                "completed_at": datetime.now().isoformat()
            }

    def _process_text_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a text analysis task.

        Args:
            task_data: Task data

        Returns:
            Task result
        """
        params = task_data.get("parameters", {})
        text = params.get("text", "")
        analysis_type = params.get("analysis_type", "sentiment")

        # Simulate processing time based on text length and analysis type
        processing_time = len(text) * 0.01
        time.sleep(min(processing_time, 2))

        # Generate a simple result
        if analysis_type == "sentiment":
            import random
            sentiment = random.choice(["positive", "negative", "neutral"])
            score = round(random.random(), 2)
            return {
                "result_type": "sentiment_analysis",
                "sentiment": sentiment,
                "score": str(score),
                "confidence": str(round(random.random(), 2))
            }
        elif analysis_type == "classification":
            categories = ["business", "technology", "health", "entertainment"]
            import random
            return {
                "result_type": "classification",
                "category": random.choice(categories),
                "confidence": str(round(random.random(), 2))
            }
        else:  # extraction
            return {
                "result_type": "extraction",
                "entities": [
                    {"type": "person", "text": "John Doe"},
                    {"type": "organization", "text": "ACME Corp"}
                ],
                "keywords": ["sample", "analysis", "text"]
            }

    def _process_image_processing(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an image processing task.

        Args:
            task_data: Task data

        Returns:
            Task result
        """
        params = task_data.get("parameters", {})
        processing_type = params.get("processing_type", "resize")

        # Simulate processing time
        time.sleep(1.5)

        # Generate a result based on processing type
        if processing_type == "resize":
            return {
                "result_type": "image_resize",
                "dimensions": "800x600",
                "original_size": "1024x768",
                "format": "jpg"
            }
        elif processing_type == "filter":
            return {
                "result_type": "image_filter",
                "filter": "grayscale",
                "applied": True
            }
        else:  # detect_objects
            return {
                "result_type": "object_detection",
                "objects": [
                    {"type": "person", "confidence": "0.95",
                        "bounds": "0,0,100,200"},
                    {"type": "car", "confidence": "0.87",
                        "bounds": "300,400,200,100"}
                ],
                "count": "2"
            }

    def _process_data_extraction(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a data extraction task.

        Args:
            task_data: Task data

        Returns:
            Task result
        """
        params = task_data.get("parameters", {})
        format_type = params.get("format", "json")

        # Simulate processing time
        time.sleep(0.8)

        # Generate a result based on format
        return {
            "result_type": "data_extraction",
            "format": format_type,
            "record_count": str(10),
            "fields": str(params.get("fields", [])),
            "sample": json.dumps({"id": "123", "name": "Sample", "value": "42"})
        }

    def start(self):
        """Start the task worker."""
        self.running = True
        logger.info(f"Task worker {self.worker_id} started")

        # Create or join the consumer group
        self.task_stream.create_consumer_group(
            WORKERS_GROUP, self.worker_id, "0")

        # Process tasks from the stream
        try:
            while self.running:
                # Read new tasks from the stream
                tasks = self.task_stream.read_group(count=1, block=1000)

                for task in tasks:
                    task_id = task["id"]
                    task_data = task["data"]

                    # Process the task
                    result = self._process_task(task_data)

                    # Send the result to the result stream
                    self.result_stream.add(result)

                    # Record task completion event
                    self.event_stream.add({
                        "event_type": "task_completed",
                        "timestamp": datetime.now().isoformat(),
                        "task_id": task_data.get("task_id", "unknown"),
                        "worker_id": self.worker_id,
                        "status": result.get("status", "completed")
                    })

                    # Acknowledge task completion
                    self.task_stream.acknowledge(task_id)

                # Small sleep to prevent tight loop if no tasks
                if not tasks:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            self.running = False

        logger.info(f"Task worker {self.worker_id} stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Redis Streams Agent Workflow Example")
    parser.add_argument("--role", choices=["dispatcher", "worker"], required=True,
                        help="Agent role (dispatcher or worker)")
    parser.add_argument("--id", default=None,
                        help="Worker ID (required for worker role)")
    args = parser.parse_args()

    if args.role == "worker" and not args.id:
        # Generate a default worker ID if not provided
        import socket
        import uuid
        args.id = f"worker-{socket.gethostname()}-{str(uuid.uuid4())[:8]}"

    # Create and start the appropriate agent
    if args.role == "dispatcher":
        agent = TaskDispatcher()
    else:
        agent = TaskWorker(args.id)

    try:
        agent.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
