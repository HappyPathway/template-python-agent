"""Example of an integrated system using AsyncIO, Celery, and Redis.

This example demonstrates a more realistic use case where:
1. An MCP-style server receives requests
2. Tasks are scheduled with the AsyncIO TaskManager
3. Heavy processing is offloaded to Celery 
4. Redis PubSub and Streams are used for inter-component messaging

To run this example:
1. Make sure Redis is running (`redis-server`)
2. Start a Celery worker in a separate terminal:
   `celery -A utils.workers.celery_app worker --loglevel=INFO`
3. Run this script: `python examples/integrated_agent_system.py`
"""

import asyncio
import json
import time
import traceback
import uuid
from typing import Any, Dict, List, Optional

from celery.result import AsyncResult

# Import AsyncIO task management
from ailf.async_tasks import TaskManager, TaskStatus
# Configure logging
from ailf.core.logging import setup_logging  # Changed from ailf.logging
# Import Redis components
from ailf.messaging.redis import (AsyncRedisClient, RedisLock, RedisPubSub,
                                   RedisStream)
# Import Celery tasks
from ailf.workers.tasks import analyze_content, process_document

logger = setup_logging("integrated_agent")


class AgentServer:
    """Agent server that integrates AsyncIO, Redis and Celery.

    This server demonstrates:
    1. Using an MCP-like structure to handle requests
    2. AsyncIO task management for concurrency
    3. Redis for pub/sub and inter-agent communication
    4. Redis Streams for reliable event logging
    5. Redis locks for coordination
    6. Celery for heavy backend processing
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize the agent server.

        Args:
            redis_url: Redis connection URL
        """
        # Create Redis clients
        self.redis = AsyncRedisClient(url=redis_url)
        self.pubsub = RedisPubSub(client=self.redis)
        self.event_stream = None  # Will be initialized in start()

        # Create task manager
        self.task_manager = TaskManager()

        # State tracking
        self.running = False
        self.tasks: Dict[str, Dict[str, Any]] = {}
        # Short ID for this agent instance
        self.agent_id = str(uuid.uuid4())[:8]

        # For example exit after handling a few requests
        self.request_count = 0
        self.max_requests = 5  # Process 5 requests then exit

    async def start(self):
        """Start the agent server."""
        if self.running:
            return

        self.running = True
        logger.info(f"Starting agent server (ID: {self.agent_id})")

        # Start task manager
        await self.task_manager.start()

        # Initialize Redis connection
        await self.redis.connect()

        # Initialize event stream
        self.event_stream = RedisStream(
            client=self.redis,
            stream_name="agent:events"
        )

        # Try to create consumer group (ignore if already exists)
        try:
            await self.event_stream.create_group(f"agent:{self.agent_id}")
        except Exception:
            logger.info("Consumer group already exists or couldn't be created")

        # Subscribe to Redis channels
        await self.pubsub.subscribe("agent:requests", self._handle_pubsub_request)
        await self.pubsub.subscribe("agent:control", self._handle_control)

        # Submit background tasks
        await self.task_manager.submit(
            self._process_stream_events(),
            task_id="stream_processor"
        )

        # Log startup event
        await self._log_event("agent_started", {"agent_id": self.agent_id})

        logger.info(f"Agent server started (ID: {self.agent_id})")

    async def stop(self):
        """Stop the agent server."""
        if not self.running:
            return

        self.running = False
        logger.info(f"Stopping agent server (ID: {self.agent_id})")

        # Log shutdown event
        await self._log_event("agent_stopping", {"agent_id": self.agent_id})

        # Unsubscribe from Redis channels
        await self.pubsub.unsubscribe_all()

        # Stop task manager (will cancel background tasks)
        await self.task_manager.stop()

        # Close Redis connection
        await self.redis.disconnect()

        logger.info(f"Agent server stopped (ID: {self.agent_id})")

    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request.

        Args:
            request_data: Request data dictionary

        Returns:
            Response dictionary
        """
        # Generate a request ID if not provided
        request_id = request_data.get("request_id", str(uuid.uuid4()))

        # Increment request counter
        self.request_count += 1

        logger.info(
            f"Processing request {request_id} ({self.request_count}/{self.max_requests})")

        # Store task info
        self.tasks[request_id] = {
            "status": "pending",
            "started_at": time.time(),
            "request": request_data
        }

        # Log request received event
        await self._log_event(
            "request_received",
            {
                "request_id": request_id,
                "agent_id": self.agent_id,
                "request_type": request_data.get("type", "unknown")
            }
        )

        # Submit to task manager for async processing
        task_id = await self.task_manager.submit(
            self._process_request(request_id, request_data),
            task_id=f"request:{request_id}",
            metadata={
                "request_id": request_id,
                "type": request_data.get("type")
            }
        )

        # Return immediate acknowledgment
        return {
            "request_id": request_id,
            "agent_id": self.agent_id,
            "status": "processing",
            "task_id": task_id,
            "estimated_completion": time.time() + 5  # Estimate 5 seconds
        }

    async def _process_request(self, request_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request asynchronously.

        Args:
            request_id: Request ID
            request_data: Request data

        Returns:
            Processing result
        """
        try:
            # Update status
            self.tasks[request_id]["status"] = "processing"

            # Log processing started
            await self._log_event("processing_started", {"request_id": request_id})

            # Get request parameters
            request_type = request_data.get("type", "unknown")

            # Simulate different processing based on request type
            if request_type == "document_processing":
                result = await self._process_document_request(request_id, request_data)
            elif request_type == "analysis":
                result = await self._process_analysis_request(request_id, request_data)
            else:
                result = await self._process_generic_request(request_id, request_data)

            # Update status to completed
            self.tasks[request_id]["status"] = "completed"
            self.tasks[request_id]["result"] = result
            self.tasks[request_id]["completed_at"] = time.time()

            # Log request completed
            await self._log_event("request_completed", {
                "request_id": request_id,
                "processing_time": time.time() - self.tasks[request_id]["started_at"]
            })

            # Publish result to Redis
            await self.pubsub.publish(
                f"agent:results:{request_id}",
                json.dumps({
                    "request_id": request_id,
                    "agent_id": self.agent_id,
                    "status": "completed",
                    "result": result
                })
            )

            return result

        except Exception as e:
            logger.error(f"Error processing request {request_id}: {str(e)}")
            logger.error(traceback.format_exc())

            # Update status to failed
            self.tasks[request_id]["status"] = "failed"
            self.tasks[request_id]["error"] = str(e)
            self.tasks[request_id]["completed_at"] = time.time()

            # Log request failed
            await self._log_event("request_failed", {
                "request_id": request_id,
                "error": str(e)
            })

            # Publish error to Redis
            await self.pubsub.publish(
                f"agent:results:{request_id}",
                json.dumps({
                    "request_id": request_id,
                    "agent_id": self.agent_id,
                    "status": "failed",
                    "error": str(e)
                })
            )

            raise

    async def _process_document_request(
        self, request_id: str, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a document request using Celery.

        Args:
            request_id: Request ID
            request_data: Request data

        Returns:
            Processing result
        """
        # Extract document information
        document_ids = request_data.get("document_ids", [])
        if not document_ids:
            raise ValueError("No document IDs provided")

        logger.info(
            f"Processing {len(document_ids)} documents for request {request_id}")

        # Process documents in parallel using Celery
        tasks = []
        for doc_id in document_ids:
            # Submit to Celery
            celery_task = process_document.delay(
                doc_id,
                {"request_id": request_id}
            )
            tasks.append(celery_task)

        # Wait for all tasks to complete
        results = []
        for task in tasks:
            # Poll until complete with timeout
            max_time = 30  # 30 second timeout
            start_time = time.time()

            while not task.ready() and time.time() - start_time < max_time:
                await asyncio.sleep(0.5)

            if task.ready():
                try:
                    result = task.get()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Task {task.id} failed: {str(e)}")
                    results.append({"status": "error", "error": str(e)})
            else:
                logger.warning(f"Task {task.id} timed out")
                results.append({"status": "timeout"})

        return {
            "document_count": len(document_ids),
            "successful": len([r for r in results if r.get("status") == "success"]),
            "failed": len([r for r in results if r.get("status") != "success"]),
            "results": results
        }

    async def _process_analysis_request(
        self, request_id: str, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process an analysis request using Celery.

        Args:
            request_id: Request ID
            request_data: Request data

        Returns:
            Analysis result
        """
        # Extract content to analyze
        content = request_data.get("content")
        analysis_type = request_data.get("analysis_type", "general")

        if not content:
            raise ValueError("No content provided for analysis")

        logger.info(
            f"Running {analysis_type} analysis for request {request_id}")

        # Submit to Celery
        task = analyze_content.delay(content, analysis_type)

        # Wait for task to complete with timeout
        max_time = 30  # 30 second timeout
        start_time = time.time()

        while not task.ready() and time.time() - start_time < max_time:
            await asyncio.sleep(0.5)

            # Check task status every second
            if int(time.time() - start_time) % 5 == 0:
                logger.info(f"Analysis task {task.id} still running...")

        if task.ready():
            try:
                result = task.get()
                logger.info(f"Analysis task {task.id} completed")
                return result
            except Exception as e:
                logger.error(f"Analysis task {task.id} failed: {str(e)}")
                raise
        else:
            logger.warning(f"Analysis task {task.id} timed out")
            raise TimeoutError("Analysis task timed out")

    async def _process_generic_request(
        self, request_id: str, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a generic request.

        Args:
            request_id: Request ID
            request_data: Request data

        Returns:
            Processing result
        """
        # Simulate processing time
        await asyncio.sleep(1)

        # Return generic response
        return {
            "request_id": request_id,
            "status": "success",
            "message": "Request processed successfully",
            "timestamp": time.time()
        }

    async def _handle_pubsub_request(self, channel: str, message: str):
        """Handle request message from Redis PubSub.

        Args:
            channel: Channel name
            message: Message content
        """
        try:
            # Parse request data
            request_data = json.loads(message)
            logger.info(f"Received request via PubSub: {request_data}")

            # Process request
            await self.handle_request(request_data)

        except Exception as e:
            logger.error(f"Error handling PubSub request: {str(e)}")

    async def _handle_control(self, channel: str, message: str):
        """Handle control message from Redis PubSub.

        Args:
            channel: Channel name
            message: Message content
        """
        try:
            # Parse control data
            control_data = json.loads(message)
            command = control_data.get("command")

            logger.info(f"Received control command: {command}")

            # Handle different commands
            if command == "shutdown":
                logger.info("Received shutdown command")
                await self.stop()
            elif command == "status":
                # Publish status report
                await self.pubsub.publish(
                    "agent:status",
                    json.dumps({
                        "agent_id": self.agent_id,
                        "status": "running",
                        "task_count": len(self.tasks),
                        "request_count": self.request_count,
                        "timestamp": time.time()
                    })
                )
            elif command == "ping":
                # Respond to ping
                await self.pubsub.publish(
                    "agent:pong",
                    json.dumps({
                        "agent_id": self.agent_id,
                        "timestamp": time.time()
                    })
                )
        except Exception as e:
            logger.error(f"Error handling control message: {str(e)}")

    async def _process_stream_events(self):
        """Process events from Redis Stream.

        This demonstrates consuming from a Redis Stream with a consumer group.
        """
        logger.info("Starting stream event processor")

        try:
            while self.running:
                try:
                    # Read events from stream
                    events = await self.event_stream.read_group(
                        group_name=f"agent:{self.agent_id}",
                        consumer_name=f"consumer:{self.agent_id}",
                        count=10,
                        block=1000  # Block for 1 second if no messages
                    )

                    # Process events
                    for msg_id, data in events:
                        try:
                            # Process the event
                            await self._handle_stream_event(msg_id, data)

                            # Acknowledge successful processing
                            await self.event_stream.acknowledge(
                                group_name=f"agent:{self.agent_id}",
                                message_id=msg_id
                            )
                        except Exception as e:
                            logger.error(
                                f"Error processing event {msg_id}: {str(e)}")
                except Exception as e:
                    if self.running:  # Only log if still running
                        logger.error(f"Stream reading error: {str(e)}")
                        # Small delay before retry
                        await asyncio.sleep(1)

                # Exit after max requests processed
                if self.request_count >= self.max_requests:
                    logger.info(
                        f"Processed {self.request_count} requests, exiting")
                    await self.stop()
                    break

                # Short sleep to avoid busy loop
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Stream event processor cancelled")
        except Exception as e:
            logger.error(f"Stream processor error: {str(e)}")
            logger.error(traceback.format_exc())

    async def _handle_stream_event(self, msg_id: str, data: Dict[str, str]):
        """Handle an event from the Redis Stream.

        Args:
            msg_id: Message ID
            data: Event data
        """
        try:
            # Parse event data (keys and values are strings in Redis streams)
            event_type = data.get("event_type", "unknown")
            event_data = json.loads(data.get("data", "{}"))
            timestamp = float(data.get("timestamp", "0"))

            logger.debug(
                f"Processing stream event: {event_type} from {timestamp}")

            # Handle different event types
            if event_type == "request_received":
                request_id = event_data.get("request_id")
                source_agent = event_data.get("agent_id")

                # Only log events from other agents
                if source_agent != self.agent_id:
                    logger.info(
                        f"Another agent ({source_agent}) received request {request_id}")

            elif event_type == "request_completed":
                request_id = event_data.get("request_id")
                processing_time = event_data.get("processing_time", 0)

                logger.debug(
                    f"Request {request_id} completed in {processing_time:.2f}s")

            # Here you would add handling for other event types

        except Exception as e:
            logger.error(f"Error handling event {msg_id}: {str(e)}")

    async def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event to the Redis Stream.

        Args:
            event_type: Event type
            data: Event data
        """
        if not self.event_stream:
            return

        try:
            # Add event to stream
            await self.event_stream.add({
                "event_type": event_type,
                "data": json.dumps(data),
                "timestamp": str(time.time()),
                "agent_id": self.agent_id
            })
        except Exception as e:
            logger.error(f"Error logging event {event_type}: {str(e)}")


async def run_example():
    """Run the integrated agent system example."""
    # Create agent server
    agent = AgentServer()

    try:
        # Start the agent
        await agent.start()

        # Submit some test requests
        requests = [
            {
                "type": "document_processing",
                "document_ids": ["doc-1", "doc-2"],
                "request_id": f"req-doc-{uuid.uuid4()}"
            },
            {
                "type": "analysis",
                "content": "This is a sample text to analyze. It contains multiple sentences and ideas that can be processed.",
                "analysis_type": "sentiment",
                "request_id": f"req-analysis-{uuid.uuid4()}"
            },
            {
                "type": "generic",
                "data": {"param1": "value1", "param2": "value2"},
                "request_id": f"req-generic-{uuid.uuid4()}"
            }
        ]

        # Send requests with small delay between them
        for req in requests:
            logger.info(f"Sending request: {req['type']}")
            response = await agent.handle_request(req)
            logger.info(f"Response: {response}")
            await asyncio.sleep(2)  # Wait a bit between requests

        # Now demonstrate the PubSub interface by publishing a request
        logger.info("Publishing request via Redis PubSub")
        pubsub = RedisPubSub(client=AsyncRedisClient())
        await pubsub.connect()

        await pubsub.publish("agent:requests", json.dumps({
            "type": "generic",
            "data": {"source": "pubsub", "timestamp": time.time()},
            "request_id": f"req-pubsub-{uuid.uuid4()}"
        }))

        # Also demonstrate the control channel
        await pubsub.publish("agent:control", json.dumps({
            "command": "status"
        }))

        # Wait for things to finish
        logger.info("Waiting for all tasks to complete...")
        await asyncio.sleep(15)

    finally:
        # Clean up
        if agent.running:
            await agent.stop()


if __name__ == "__main__":
    # Run the example
    try:
        asyncio.run(run_example())
    except KeyboardInterrupt:
        logger.info("Example interrupted")
    except Exception as e:
        logger.error(f"Example error: {str(e)}")
        logger.error(traceback.format_exc())
