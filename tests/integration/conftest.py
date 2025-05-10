"""Configuration for integration tests.

This module contains configuration and common fixtures for integration tests.
"""
import os
import socket

import pytest


def is_service_available(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a service is available at host:port.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        True if the service is available, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (socket.error, ConnectionRefusedError):
        return False


# Set environment variables for test configuration
def pytest_configure(config):
    """Configure pytest environment."""
    # Check for Redis availability
    if not is_service_available("localhost", 6379):
        os.environ["USE_MOCK_REDIS"] = "true"
        print("\nRedis server not available. Using mock implementation.")
    else:
        print("\nRedis server available. Using real implementation.")


# Register custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: marks tests that require external services")
    config.addinivalue_line("markers", "unit: marks unit tests")


# Integration test specific fixtures
