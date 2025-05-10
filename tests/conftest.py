"""
Global pytest configuration for the project.
"""

import os
import sys
import pytest
import asyncio
import redis.asyncio as aioredis  # For type hinting and checking availability

# Add the project root to the path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ailf.messaging import RedisStreamsBackend, MockRedisStreamsBackend

# Default Redis connection URL for tests
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")  # Use DB 1 for tests


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running test")
    config.addinivalue_line(
        "markers", "requires_redis: mark test as requiring a real Redis server"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir(tmpdir_factory):
    """Create a temporary directory for the test session."""
    return tmpdir_factory.mktemp("test_data")


@pytest.fixture(scope="session")
def test_env():
    """Return environment variables needed for tests."""
    return {
        "has_openai": "OPENAI_API_KEY" in os.environ and os.environ["OPENAI_API_KEY"],
        "has_gemini": "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"],
        "has_anthropic": "ANTHROPIC_API_KEY" in os.environ and os.environ["ANTHROPIC_API_KEY"],
        "has_gcp": "GOOGLE_APPLICATION_CREDENTIALS" in os.environ and os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        "has_github": "GITHUB_TOKEN" in os.environ and os.environ["GITHUB_TOKEN"],
    }


async def is_redis_available(redis_url: str) -> bool:
    """Check if Redis server is available at the given URL."""
    try:
        r = await aioredis.from_url(redis_url, socket_connect_timeout=1)
        pong = await r.ping()
        await r.close()
        return pong
    except (OSError, aioredis.RedisError) as e:  # OSError for connection refused
        print(f"Redis connection failed for check: {e}")
        return False


@pytest.fixture(scope="function")  # Changed to function scope for cleaner state per test
async def redis_messaging_backend(request):
    """Yields a RedisStreamsBackend or MockRedisStreamsBackend instance.
    
    If FORCE_MOCK_REDIS is set or a real Redis is not available (and not skipped),
    it provides a MockRedisStreamsBackend. Otherwise, it provides a real RedisStreamsBackend.
    The backend is connected and disconnected automatically.
    The real Redis database (DB 1) is flushed before yielding to ensure a clean state.
    """
    force_mock = os.environ.get('FORCE_MOCK_REDIS', 'false').lower() == 'true'
    use_mock = force_mock

    # Check if test requires real redis and skip if not available
    if hasattr(request, "node") and request.node.get_closest_marker("requires_redis"):
        if not await is_redis_available(TEST_REDIS_URL):
            pytest.skip("Test requires a real Redis server, but it's not available.")
        elif force_mock:
            print("Warning: Test is marked with 'requires_redis' but FORCE_MOCK_REDIS is true. Using mock.")
        else:
            use_mock = False  # Definitely use real Redis
    elif not force_mock and not await is_redis_available(TEST_REDIS_URL):
        print("Real Redis not available, falling back to mock for non-marked test.")
        use_mock = True

    if use_mock:
        print("Using MockRedisStreamsBackend")
        backend = MockRedisStreamsBackend(redis_url=TEST_REDIS_URL)
    else:
        print(f"Using RedisStreamsBackend with URL: {TEST_REDIS_URL}")
        backend = RedisStreamsBackend(redis_url=TEST_REDIS_URL)
        # Clean the test database before the test runs for real Redis
        try:
            r = await aioredis.from_url(TEST_REDIS_URL)
            await r.flushdb()
            await r.close()
            print(f"Flushed Redis DB for {TEST_REDIS_URL}")
        except Exception as e:
            pytest.skip(f"Could not connect to or flush Redis DB {TEST_REDIS_URL}: {e}")

    await backend.connect()
    yield backend
    await backend.disconnect()


@pytest.fixture(scope="function")
async def clear_redis_db(redis_messaging_backend):
    """Fixture to ensure the Redis database (or mock state) is clean.
    
    This is useful if a test needs to explicitly clear state mid-test or ensure
    it's clean after specific operations, beyond the automatic per-test flush.
    """
    if isinstance(redis_messaging_backend, MockRedisStreamsBackend):
        await redis_messaging_backend.clear_all_state()
    elif isinstance(redis_messaging_backend, RedisStreamsBackend):
        # For real Redis, connect and flush the specific test DB
        try:
            r = await aioredis.from_url(TEST_REDIS_URL)
            await r.flushdb()
            await r.close()
            print(f"Flushed Redis DB for {TEST_REDIS_URL} via clear_redis_db fixture.")
        except Exception as e:
            print(f"Warning: Could not flush Redis DB via clear_redis_db: {e}")


@pytest.fixture(scope="function")
async def requires_real_redis_backend(redis_messaging_backend):
    """Skips test if the provided backend is not a real RedisStreamsBackend.
    
    Use this fixture when a test specifically needs to interact with features
    of the real RedisStreamsBackend that the mock might not fully implement.
    """
    if not isinstance(redis_messaging_backend, RedisStreamsBackend):
        pytest.skip("This test requires the real RedisStreamsBackend.")
    yield redis_messaging_backend  # Provide the backend to the test
