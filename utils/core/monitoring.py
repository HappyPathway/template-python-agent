"""Performance Monitoring and Metrics Collection

This module provides centralized monitoring configuration with built-in support for:
- Metrics collection
- Performance tracking
- Error monitoring
- Success rate tracking
- Custom dimensions

Example Usage:
    ```python
    from core.monitoring import setup_monitoring

    monitoring = setup_monitoring('my_feature')

    monitoring.increment('api_calls')
    with monitoring.timer('request_duration'):
        result = make_request()
    monitoring.track_success('api_call', {'status': 200})
    ```

Use this module to implement systematic monitoring across your application.
"""
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .logging import setup_logging

logger = setup_logging('monitoring')


@dataclass
class MetricsCollector:
    """Collector for tracking various metrics."""
    name: str
    counters: Dict[str, int] = field(default_factory=dict)
    timers: Dict[str, float] = field(default_factory=dict)
    success_counts: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def increment(self, metric: str, value: int = 1) -> None:
        """Increment a counter metric."""
        if metric not in self.counters:
            self.counters[metric] = 0
        self.counters[metric] += value
        logger.debug(f"{self.name} - {metric}: {self.counters[metric]}")

    def increment_success(self, operation: str) -> None:
        """Increment success counter for an operation."""
        if operation not in self.success_counts:
            self.success_counts[operation] = 0
        self.success_counts[operation] += 1
        logger.debug(
            f"{self.name} - Success {operation}: {self.success_counts[operation]}")

    def track_success(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Track a successful operation."""
        if operation not in self.success_counts:
            self.success_counts[operation] = 0
        self.success_counts[operation] += 1
        if metadata:
            logger.info(f"{self.name} - Success {operation}: {metadata}")

    def track_error(self, operation: str, error: str) -> None:
        """Track an operation error."""
        if operation not in self.error_counts:
            self.error_counts[operation] = {}
        if error not in self.error_counts[operation]:
            self.error_counts[operation][error] = 0
        self.error_counts[operation][error] += 1
        logger.error(f"{self.name} - Error in {operation}: {error}")

    @contextmanager
    def timer(self, metric: str):
        """Time an operation.

        Example:
            ```python
            with monitoring.timer('request_duration'):
                result = make_request()
            ```
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if metric not in self.timers:
                self.timers[metric] = 0
            self.timers[metric] = duration
            logger.debug(f"{self.name} - {metric} duration: {duration:.2f}s")

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return {
            'counters': self.counters,
            'timers': self.timers,
            'success_counts': self.success_counts,
            'error_counts': self.error_counts
        }


# Alias for backward compatibility with existing code
Metrics = MetricsCollector


def setup_monitoring(
    component_name: str,
    enable_debug: bool = False
) -> MetricsCollector:
    """Set up monitoring for a component.

    Args:
        component_name: Name of the component being monitored
        enable_debug: Whether to enable debug logging

    Returns:
        MetricsCollector instance
    """
    if enable_debug:
        logger.setLevel('DEBUG')
    return MetricsCollector(name=component_name)
