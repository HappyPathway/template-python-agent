"""Async Redis and Celery Example.

This example demonstrates how to use the AsyncRedisClient with 
Celery for background task processing.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List

from celery.result import AsyncResult

# Import AsyncIO task management
from ailf.async_tasks import TaskManager, TaskStatus
# Configure logging
from ailf.core.logging import setup_logging
from ailf.messaging.async_redis import AsyncRedisPubSub
# Import Redis components
from ailf.messaging.redis import AsyncRedisClient, RedisConfig
# Import Celery tasks
from ailf.workers.tasks import analyze_content, process_document

logger = setup_logging("async_redis_celery_example")
