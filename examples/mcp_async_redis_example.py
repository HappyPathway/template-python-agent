"""Example MCP Server with AsyncIO and Redis integration.

This example demonstrates how to:
1. Create an MCP server with FastMCP
2. Use AsyncIO task management for background tasks
3. Use Redis for messaging between components
4. Coordinate between MCP context and background tasks

To run this example:
1. Make sure Redis is running
2. Run this script: `python examples/mcp_async_redis_example.py`
3. Connect with a compatible MCP client
"""

import asyncio
import json
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel, Field

# Import our utils
from ailf.base_mcp import Context, BaseMCP as FastMCP
from ailf.async_tasks import TaskManager
# Configure logging
from ailf.core.logging import setup_logging
from ailf.messaging.redis import AsyncRedisClient, RedisPubSub

logger = setup_logging("mcp_async_redis")


# Define schemas for our MCP tools
class DocumentProcessRequest(BaseModel):
    """Request to process a document."""
    document_id: str = Field(description="The ID of the document to process")
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional processing options"
    )


class DocumentProcessResponse(BaseModel):
    """Response from document processing."""
    document_id: str = Field(
        description="The ID of the document that was processed")
    status: str = Field(description="Processing status (success or error)")
    processing_time: float = Field(
        description="Time taken to process the document in seconds")
    word_count: Optional[int] = Field(
        default=None,
        description="Number of words in the document if available"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )


class AgentState:
    """Agent state shared across MCP contexts."""

    def __init__(self):
        """Initialize agent state."""
        self.task_manager = TaskManager()
        self.redis = AsyncRedisClient()
        self.pubsub = None  # Will be initialized during startup
        self.request_results: Dict[str, Any] = {}

    async def initialize(self):
        """Initialize agent components."""
        await self.task_manager.start()
        await self.redis.connect()
        self.pubsub = RedisPubSub(client=self.redis)

        # Subscribe to result channel
        await self.pubsub.subscribe(
            "agent:mcp:results",
            self._handle_results
        )

        logger.info("Agent state initialized")

    async def shutdown(self):
        """Clean up agent resources."""
        if self.pubsub:
            await self.pubsub.unsubscribe_all()

        await self.task_manager.stop()

        if self.redis:
            await self.redis.disconnect()

        logger.info("Agent state cleaned up")

    async def _handle_results(self, channel: str, message: str):
        """Handle results coming from Redis."""
        try:
            data = json.loads(message)
            request_id = data.get("request_id")
            if request_id:
                self.request_results[request_id] = data
                logger.info(f"Received result for request {request_id}")
        except Exception as e:
            logger.error(f"Error handling result: {str(e)}")


@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[None]:
    """Manage the lifecycle of the MCP server."""
    # Initialize state
    state = AgentState()
    mcp.state.agent = state

    try:
        # Initialize components
        await state.initialize()
        yield
    finally:
        # Clean up
        await state.shutdown()


# Create MCP server
mcp = FastMCP(
    name="Async Redis MCP Agent",
    instructions="A document processing agent that handles requests asynchronously",
    lifespan=lifespan
)


@mcp.tool()
async def process_document(
    ctx: Context,
    document_id: str,
    options: Optional[Dict[str, Any]] = None
) -> DocumentProcessResponse:
    """Process a document asynchronously.

    Args:
        document_id: The ID of the document to process
        options: Optional processing options

    Returns:
        Document processing response
    """
    logger.info(f"Received request to process document {document_id}")

    # Get agent state from context
    agent = ctx.server.state.agent

    # Generate request ID
    request_id = str(uuid.uuid4())

    # Prepare data
    request_data = {
        "request_id": request_id,
        "document_id": document_id,
        "options": options or {},
        "timestamp": time.time()
    }

    try:
        # Submit background task
        task_id = await agent.task_manager.submit(
            _process_document_async(agent, request_id, document_id, options),
            task_id=f"doc:{request_id}"
        )

        logger.info(f"Submitted document processing task {task_id}")

        # Wait for result with timeout
        result = None
        timeout = 10  # 10 second timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            if request_id in agent.request_results:
                result = agent.request_results[request_id]
                break
            await asyncio.sleep(0.2)

        # Check if we got a result
        if result:
            # Clean up result
            del agent.request_results[request_id]

            # Return document process response
            return DocumentProcessResponse(
                document_id=document_id,
                status=result.get("status", "unknown"),
                processing_time=result.get("processing_time", 0),
                word_count=result.get("word_count"),
                error=result.get("error")
            )
        else:
            # Timeout
            return DocumentProcessResponse(
                document_id=document_id,
                status="timeout",
                processing_time=time.time() - start_time,
                error="Request processing timed out"
            )

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        logger.error(traceback.format_exc())

        return DocumentProcessResponse(
            document_id=document_id,
            status="error",
            processing_time=0,
            error=str(e)
        )


async def _process_document_async(
    agent: AgentState,
    request_id: str,
    document_id: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Background task to process a document.

    Args:
        agent: Agent state
        request_id: Request ID
        document_id: Document ID
        options: Processing options

    Returns:
        Processing result
    """
    start_time = time.time()

    try:
        logger.info(f"Processing document {document_id}")

        # Simulate processing time
        await asyncio.sleep(2)

        # Simulate document processing
        word_count = len(document_id) * 100  # Fake word count

        result = {
            "request_id": request_id,
            "document_id": document_id,
            "status": "success",
            "processing_time": time.time() - start_time,
            "word_count": word_count,
            "timestamp": time.time()
        }

        # Publish result to Redis
        await agent.pubsub.publish(
            "agent:mcp:results",
            json.dumps(result)
        )

        return result

    except Exception as e:
        logger.error(
            f"Error in background processing for {document_id}: {str(e)}")
        error_result = {
            "request_id": request_id,
            "document_id": document_id,
            "status": "error",
            "error": str(e),
            "processing_time": time.time() - start_time,
            "timestamp": time.time()
        }

        # Publish error to Redis
        await agent.pubsub.publish(
            "agent:mcp:results",
            json.dumps(error_result)
        )

        return error_result


@mcp.tool()
async def get_server_status(ctx: Context) -> Dict[str, Any]:
    """Get the current server status.

    Returns:
        Server status information
    """
    agent = ctx.server.state.agent

    # Get task manager statistics
    running_tasks = agent.task_manager.list_tasks(status="RUNNING")
    completed_tasks = agent.task_manager.list_tasks(status="COMPLETED")
    failed_tasks = agent.task_manager.list_tasks(status="FAILED")

    return {
        "server": "Async Redis MCP Agent",
        "status": "running",
        "uptime": "N/A",  # Would track uptime in a real implementation
        "tasks": {
            "running": len(running_tasks),
            "completed": len(completed_tasks),
            "failed": len(failed_tasks),
            "total": len(agent.task_manager.task_info)
        },
        "pending_results": len(agent.request_results),
        "timestamp": time.time()
    }


# Main entry point
async def main():
    """Run the MCP server."""
    host = "localhost"
    port = 8080

    # Start the server
    await mcp.run(host=host, port=port)


if __name__ == "__main__":
    try:
        # Run the server
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(traceback.format_exc())
