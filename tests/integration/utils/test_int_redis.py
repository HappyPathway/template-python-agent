"""Integration tests for Redis messaging utilities.

This module contains integration tests for the Redis messaging utilities.
These tests require a running Redis server. If Redis is not available,
the tests will be skipped or use mock implementations.
"""
import json
import socket
import threading
import time
from typing import Any, Dict, List

import pytest

# Try to import mock implementations if available
try:
    from src.ailf.messaging.mock_redis import MockAsyncRedisClient, MockRedisClient
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False

from src.ailf.messaging.redis import (
    AsyncRedisClient,
    RedisClient,
    RedisConfig,
    RedisLock,
    RedisPubSub,
    RedisRateLimiter,
    RedisStream,
)


# Check if Redis is available
def is_redis_available():
    """Check if Redis server is available."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("localhost", 6379))
        s.close()
        return True
    except (socket.error, ConnectionRefusedError):
        return False


# Skip all Redis tests if Redis is not available
REDIS_AVAILABLE = is_redis_available()
SKIP_REASON = "Redis server is not available"


@pytest.fixture
def redis_config():
    """Redis configuration for tests."""
    return RedisConfig(
        host="localhost",
        port=6379,
        db=1,  # Use a different DB than default to avoid conflicts
        decode_responses=True
    )


@pytest.fixture
def redis_client(redis_config):
    """Redis client fixture.

    Returns a real Redis client if Redis is available, otherwise returns a mock.
    """
    if REDIS_AVAILABLE:
        client = RedisClient(redis_config)
        yield client
        client.close()
    elif MOCK_AVAILABLE:
        client = MockRedisClient(redis_config)
        yield client
    else:
        pytest.skip(SKIP_REASON)


@pytest.fixture
def clear_redis(redis_client):
    """Clear Redis database before and after tests."""
    redis_client.client.flushdb()
    yield
    redis_client.client.flushdb()


@pytest.fixture
def test_stream_name():
    """Test stream name for stream tests."""
    return "test_stream"


@pytest.fixture
def test_pubsub_channel():
    """Test channel name for pubsub tests."""
    return "test_channel"


@pytest.mark.integration
class TestRedisClient:
    """Integration tests for RedisClient."""

    def test_connection(self, redis_client):
        """Test Redis connection."""
        assert redis_client.health_check() is True

    def test_basic_operations(self, redis_client, clear_redis):
        """Test basic Redis operations."""
        # Set and get
        assert redis_client.set("test_key", "test_value") is True
        assert redis_client.get("test_key") == "test_value"

        # Exists
        assert redis_client.exists("test_key") is True
        assert redis_client.exists("nonexistent_key") is False

        # Delete
        assert redis_client.delete("test_key") is True
        assert redis_client.get("test_key") is None

    def test_json_operations(self, redis_client, clear_redis):
        """Test JSON Redis operations."""
        test_data = {"name": "test", "value": 42, "nested": {"key": "value"}}

        # Set and get JSON
        assert redis_client.set_json("test_json", test_data) is True
        result = redis_client.get_json("test_json")

        assert result == test_data
        assert result["nested"]["key"] == "value"


@pytest.mark.asyncio
@pytest.mark.integration
class TestAsyncRedisClient:
    """Integration tests for AsyncRedisClient."""

    async def test_connection(self, redis_config):
        """Test async Redis connection."""
        client = AsyncRedisClient(redis_config)
        assert await client.health_check() is True
        await client.close()

    async def test_basic_operations(self, redis_config, clear_redis):
        """Test basic async Redis operations."""
        client = AsyncRedisClient(redis_config)

        # Test setup is handled by clear_redis fixture

        # Set and get
        assert await client.set("test_key_async", "test_value") is True
        assert await client.get("test_key_async") == "test_value"

        # Exists
        assert await client.exists("test_key_async") is True
        assert await client.exists("nonexistent_key") is False

        # Delete
        assert await client.delete("test_key_async") is True
        assert await client.get("test_key_async") is None

        await client.close()


@pytest.mark.integration
class TestRedisPubSub:
    """Integration tests for RedisPubSub."""

    def test_publish_subscribe(self, redis_client, test_pubsub_channel, clear_redis):
        """Test publish and subscribe."""
        received_messages = []
        thread = None
        pubsub = None

        try:
            def message_handler(message):
                received_messages.append(message)

            # Create a PubSub instance
            pubsub = RedisPubSub(redis_client)
            pubsub.subscribe(test_pubsub_channel, message_handler)

            # Start listening in a background thread
            thread = pubsub.run_in_thread(daemon=True)

            # Give it a moment to subscribe
            time.sleep(0.5)

            # Publish some messages
            test_messages = [
                {"id": 1, "text": "Hello"},
                {"id": 2, "text": "World"}
            ]

            for message in test_messages:
                pubsub.publish(test_pubsub_channel, message)
                time.sleep(0.1)  # Give it time to process

            # Wait a bit for messages to be processed
            time.sleep(0.5)

            # Verify received messages
            assert len(received_messages) == len(test_messages)
            assert received_messages[0]["id"] == 1
            assert received_messages[1]["text"] == "World"
        finally:
            # Clean up resources properly
            if pubsub:
                pubsub.stop()
            if thread and thread.is_alive():
                thread.join(timeout=1)
                # Don't raise an exception if the thread doesn't exit cleanly
                # The Redis client may have already closed the connection


@pytest.mark.integration
class TestRedisStream:
    """Integration tests for RedisStream."""

    def test_add_and_read(self, redis_client, test_stream_name, clear_redis):
        """Test adding and reading from a stream."""
        stream = RedisStream(test_stream_name, redis_client)

        # Delete the stream if it exists (to start fresh)
        redis_client.client.delete(test_stream_name)

        # Add some messages
        message_id1 = stream.add({"key1": "value1", "number": "42"})
        message_id2 = stream.add({"key2": "value2", "boolean": "true"})

        # Read messages (using 0 to read from beginning of stream)
        messages = stream.read(count=10, last_id='0')

        # Verify messages
        assert len(messages) == 2
        assert messages[0]["id"] == message_id1
        assert messages[0]["data"]["key1"] == "value1"
        assert messages[1]["id"] == message_id2
        assert messages[1]["data"]["key2"] == "value2"

    def test_consumer_group(self, redis_client, test_stream_name, clear_redis):
        """Test consumer groups with streams."""
        # Delete the stream if it exists (to start fresh)
        redis_client.client.delete(test_stream_name)

        stream = RedisStream(test_stream_name, redis_client)

        # Create a consumer group
        assert stream.create_consumer_group(
            "test_group", "test_consumer", "0") is True

        # Add some messages
        stream.add({"task": "task1"})
        stream.add({"task": "task2"})

        # Read from the group
        messages = stream.read_group(count=10)

        # Filter out any messages that aren't our task messages
        task_messages = [m for m in messages if 'task' in m.get('data', {})]

        # Verify messages
        assert len(task_messages) == 2

        # Sort and verify task messages
        task_messages.sort(key=lambda x: x["data"]["task"])
        assert task_messages[0]["data"]["task"] == "task1"
        assert task_messages[1]["data"]["task"] == "task2"

        # Acknowledge a message
        assert stream.acknowledge(messages[0]["id"]) is True


@pytest.mark.integration
class TestRedisLock:
    """Integration tests for RedisLock."""

    def test_acquire_release(self, redis_client, clear_redis):
        """Test acquiring and releasing a lock."""
        lock = RedisLock("test_lock", expire=5, redis_client=redis_client)

        # Acquire the lock
        assert lock.acquire() is True

        # Try to acquire the same lock (should fail)
        lock2 = RedisLock("test_lock", expire=5, redis_client=redis_client)
        assert lock2.acquire(retry=1) is False

        # Release the lock
        assert lock.release() is True

        # Now lock2 should be able to acquire
        assert lock2.acquire() is True

        # Clean up
        lock2.release()

    def test_context_manager(self, redis_client, clear_redis):
        """Test lock as a context manager."""
        results = []

        def task1():
            with RedisLock("shared_lock", redis_client=redis_client).acquire_context() as acquired:
                if acquired:
                    results.append("task1")
                    time.sleep(0.2)

        def task2():
            # Wait a bit for task1 to acquire the lock
            time.sleep(0.1)
            with RedisLock("shared_lock", redis_client=redis_client).acquire_context() as acquired:
                if acquired:
                    results.append("task2")

        # Run the tasks in separate threads
        t1 = threading.Thread(target=task1)
        t2 = threading.Thread(target=task2)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # task1 should run first, followed by task2
        assert results == ["task1", "task2"]


@pytest.mark.integration
class TestRedisRateLimiter:
    """Integration tests for RedisRateLimiter."""

    def test_rate_limiting(self, redis_client, clear_redis):
        """Test rate limiting functionality."""
        # Clear rate limiter keys
        keys = redis_client.client.keys("rate:test_limiter:*")
        if keys:
            redis_client.client.delete(*keys)

        # Create a rate limiter with a very small limit to ensure it triggers
        limiter = RedisRateLimiter(
            "test_limiter", rate=1, period=1, redis_client=redis_client)

        # First request should be allowed
        assert limiter.is_allowed("user1") is True

        # Force the rate limiter to deny subsequent requests
        for _ in range(10):  # Make multiple requests to ensure we hit the limit
            limiter.is_allowed("user1")

        # Wait a tiny bit to ensure the rate counter is updated
        time.sleep(0.1)

        # Now check if the rate limiter correctly denies the request
        assert limiter.is_allowed("user1") is False

        # Different user should be allowed
        assert limiter.is_allowed("user2") is True

        # Wait for the rate limit to reset
        time.sleep(1.1)

        # Should be allowed again
        assert limiter.is_allowed("user1") is True
