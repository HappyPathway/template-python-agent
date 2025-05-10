"""Celery configuration module.

This module configures a Celery application for distributed task processing.
It reads configuration from environment variables and provides a base
Celery instance that can be used to define tasks.

Usage:
    # Import the app instance
    from ailf.workers.celery_app import app
    
    # Define a task
    @app.task
    def process_data(data_id):
        # Process data...
        return result
"""

import os

from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Celery
app = Celery(
    "agent_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

# Configure Celery settings
app.conf.update(
    # Serialization settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Time settings
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "2")),
    worker_prefetch_multiplier=1,

    # Task execution settings
    task_acks_late=True,  # Tasks are acknowledged after completion
    task_reject_on_worker_lost=True,  # Tasks are rejected if worker is lost
    task_time_limit=600,  # 10 minutes max task execution time
    task_soft_time_limit=540,  # 9 minutes soft limit (warning)

    # Result settings
    result_expires=3600,  # Results expire after 1 hour
)

# Optional autodiscover tasks
# app.autodiscover_tasks(['utils.workers.tasks'])
