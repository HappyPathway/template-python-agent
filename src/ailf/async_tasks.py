"""AsyncIO Task Management.

This module provides utilities for managing asynchronous tasks within a Python process.
It allows for scheduling, monitoring, and coordinating multiple asynchronous tasks.

Example:
    ```python
    import asyncio
    from ailf.async_tasks import TaskManager
    
    async def main():
        # Create and start the task manager
        manager = TaskManager()
        await manager.start()
        
        # Submit some tasks
        async def example_task(name):
            print(f"Task {name} started")
            await asyncio.sleep(2)
            print(f"Task {name} completed")
            return f"Result from {name}"
        
        task_id = await manager.submit(example_task("task1"))
        
        # Check task status
        info = manager.get_task_info(task_id)
        print(f"Task status: {info.status}")
        
        # Wait for task to complete
        await asyncio.sleep(3)
        info = manager.get_task_info(task_id)
        print(f"Task result: {info.result}")
        
        # Clean up
        await manager.stop()
    
    asyncio.run(main())
    ```
"""

import asyncio
import logging
import time
import traceback
import uuid
from enum import Enum
from typing import (Any, Awaitable, Callable, Dict, List, Optional, TypeVar,
                    Union)

from pydantic import BaseModel, Field

from ailf.core.logging import setup_logging

logger = setup_logging(__name__)

# Type variable for task result
T = TypeVar('T')


class TaskStatus(str, Enum):
    """Task status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo(BaseModel):
    """Information about a task.

    Attributes:
        id: Unique task identifier
        status: Current task status
        created_at: Timestamp when task was created
        started_at: Timestamp when task started running
        completed_at: Timestamp when task completed (success or failure)
        result: Task result (if completed successfully)
        error: Error message (if task failed)
        progress: Optional progress percentage (0-100)
        metadata: Optional additional task metadata
    """
    id: str
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    progress: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskManager:
    """Manages asynchronous tasks within a process.

    This class provides utilities for submitting, tracking, and managing
    asynchronous tasks using asyncio. It maintains a registry of tasks
    and their current status.
    """

    def __init__(self, task_timeout: Optional[int] = None):
        """Initialize the task manager.

        Args:
            task_timeout: Default timeout for tasks in seconds (None for no timeout)
        """
        self.tasks: Dict[str, asyncio.Task] = {}
        self.task_info: Dict[str, TaskInfo] = {}
        self.task_timeout = task_timeout
        self._cleanup_task = None
        self._running = False

    async def start(self) -> None:
        """Start the task manager."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_completed())
        logger.info("Task manager started")

    async def stop(self) -> None:
        """Stop the task manager and cancel all running tasks."""
        if not self._running:
            return

        self._running = False

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel all running tasks
        for task_id, task in list(self.tasks.items()):
            if not task.done():
                logger.info(f"Cancelling task {task_id}")
                task.cancel()
                self.task_info[task_id].status = TaskStatus.CANCELLED

        logger.info("Task manager stopped")

    async def submit(
        self,
        coroutine: Awaitable[T],
        task_id: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit a task for execution.

        Args:
            coroutine: The coroutine to execute
            task_id: Optional task ID (generated if not provided)
            timeout: Optional timeout in seconds
            metadata: Optional task metadata

        Returns:
            Task ID for tracking the task
        """
        if not self._running:
            await self.start()

        task_id = task_id or str(uuid.uuid4())
        timeout = timeout or self.task_timeout
        metadata = metadata or {}

        self.task_info[task_id] = TaskInfo(
            id=task_id,
            status=TaskStatus.PENDING,
            created_at=time.time(),
            metadata=metadata
        )

        # Create a wrapper to update task status
        async def task_wrapper():
            self.task_info[task_id].status = TaskStatus.RUNNING
            self.task_info[task_id].started_at = time.time()

            try:
                if timeout:
                    # Run with timeout
                    result = await asyncio.wait_for(coroutine, timeout)
                else:
                    # Run without timeout
                    result = await coroutine

                self.task_info[task_id].result = result
                self.task_info[task_id].status = TaskStatus.COMPLETED
                logger.debug(f"Task {task_id} completed successfully")
            except asyncio.TimeoutError:
                logger.warning(
                    f"Task {task_id} timed out after {timeout} seconds")
                self.task_info[task_id].error = f"Task timed out after {timeout} seconds"
                self.task_info[task_id].status = TaskStatus.FAILED
            except asyncio.CancelledError:
                logger.info(f"Task {task_id} was cancelled")
                self.task_info[task_id].status = TaskStatus.CANCELLED
                raise  # Re-raise to properly cancel the task
            except Exception as e:
                logger.error(f"Task {task_id} failed with error: {str(e)}")
                logger.error(traceback.format_exc())
                self.task_info[task_id].error = str(e)
                self.task_info[task_id].status = TaskStatus.FAILED
            finally:
                self.task_info[task_id].completed_at = time.time()

        # Create and start the task
        task = asyncio.create_task(task_wrapper())
        self.tasks[task_id] = task

        logger.debug(f"Submitted task {task_id}")
        return task_id

    def update_progress(self, task_id: str, progress: int) -> bool:
        """Update the progress of a task.

        Args:
            task_id: The ID of the task to update
            progress: Progress percentage (0-100)

        Returns:
            True if the task exists and was updated, False otherwise
        """
        if task_id in self.task_info:
            # Ensure progress is between 0 and 100
            progress = max(0, min(100, progress))
            self.task_info[task_id].progress = progress
            return True
        return False

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get information about a task.

        Args:
            task_id: The ID of the task to retrieve

        Returns:
            Task information or None if not found
        """
        return self.task_info.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[TaskInfo]:
        """List all tasks, optionally filtered by status.

        Args:
            status: Optional status to filter by

        Returns:
            List of task information
        """
        if status is None:
            return list(self.task_info.values())
        return [info for info in self.task_info.values() if info.status == status]

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: The ID of the task to cancel

        Returns:
            True if the task was found and cancelled, False otherwise
        """
        if task_id in self.tasks and not self.tasks[task_id].done():
            self.tasks[task_id].cancel()
            self.task_info[task_id].status = TaskStatus.CANCELLED
            return True
        return False

    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Any]:
        """Wait for a task to complete.

        Args:
            task_id: The ID of the task to wait for
            timeout: Optional timeout in seconds

        Returns:
            Task result or None if task failed, was cancelled, or doesn't exist
        """
        if task_id not in self.tasks:
            return None

        try:
            if timeout:
                await asyncio.wait_for(self.tasks[task_id], timeout)
            else:
                await self.tasks[task_id]

            return self.task_info[task_id].result
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return None

    async def _cleanup_completed(self) -> None:
        """Clean up completed tasks periodically."""
        try:
            while self._running:
                await asyncio.sleep(60)  # Clean up every minute

                # Remove tasks completed more than an hour ago
                cutoff = time.time() - 3600
                for task_id in list(self.task_info.keys()):
                    info = self.task_info[task_id]
                    if (info.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED) and
                            info.completed_at is not None and
                            info.completed_at < cutoff):
                        if task_id in self.tasks and self.tasks[task_id].done():
                            del self.tasks[task_id]
                        del self.task_info[task_id]
                        logger.debug(f"Cleaned up completed task {task_id}")
        except asyncio.CancelledError:
            # Expected when shutting down
            logger.debug("Task cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in task cleanup: {str(e)}")
            logger.error(traceback.format_exc())
