"""Monitoring and instrumentation utilities.

This module provides tools for tracking metrics, performance, 
and health of agent systems.
"""

import time
import logging
import os
from typing import Any, Dict, Optional, Union, Callable

# Monitoring implementations
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collector for monitoring metrics."""
    
    def __init__(self, service_name: str):
        """Initialize metrics collector.
        
        Args:
            service_name: Name of the service being monitored
        """
        self.service_name = service_name
        self.metrics: Dict[str, Any] = {}
        self.latencies: Dict[str, float] = {}
        self.counters: Dict[str, int] = {}
        self.errors: Dict[str, int] = {}
        logger.info(f"Metrics collector initialized for {service_name}")
    
    def track_latency(self, operation: str, duration_ms: float):
        """Track operation latency.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
        """
        if operation not in self.latencies:
            self.latencies[operation] = []
        self.latencies[operation].append(duration_ms)
        logger.debug(f"Latency: {operation} = {duration_ms}ms")
    
    def increment(self, metric: str, value: int = 1):
        """Increment a counter metric.
        
        Args:
            metric: Metric name
            value: Increment value
        """
        if metric not in self.counters:
            self.counters[metric] = 0
        self.counters[metric] += value
        logger.debug(f"Counter: {metric} = {self.counters[metric]}")
    
    def track_error(self, operation: str, error_type: str):
        """Track operation errors.
        
        Args:
            operation: Operation name
            error_type: Type of error
        """
        key = f"{operation}:{error_type}"
        if key not in self.errors:
            self.errors[key] = 0
        self.errors[key] += 1
        logger.debug(f"Error: {key} count = {self.errors[key]}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.
        
        Returns:
            Dictionary containing all metrics
        """
        return {
            "service": self.service_name,
            "latencies": self.latencies,
            "counters": self.counters,
            "errors": self.errors
        }
        
def setup_monitoring(service_name: str) -> MetricsCollector:
    """Set up monitoring for a service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Configured metrics collector
    """
    return MetricsCollector(service_name)
    
def track_latency(operation: str, duration_ms: float):
    """Global latency tracking function.
    
    Args:
        operation: Operation name
        duration_ms: Duration in milliseconds
    """
    logger.debug(f"Latency: {operation} = {duration_ms}ms")
    
def track_error(operation: str, error_type: str):
    """Global error tracking function.
    
    Args:
        operation: Operation name
        error_type: Type of error
    """
    logger.error(f"Error in {operation}: {error_type}")
    
def increment(metric: str, value: int = 1):
    """Global counter increment function.
    
    Args:
        metric: Metric name
        value: Increment value
    """
    logger.debug(f"Metric {metric} incremented by {value}")
    class MetricsCollector:
        """Collects and optionally reports metrics."""
        
        def __init__(self, service_name: str):
            """Initialize the metrics collector."""
            self.service_name = service_name
            self.logger = logging.getLogger(f"{service_name}.metrics")
            
        def track_latency(self, operation: str, seconds: float, attributes: Optional[Dict[str, Any]] = None):
            """Track operation latency."""
            self.logger.debug(f"LATENCY: {operation}={seconds:.4f}s {attributes or ''}")
            
        def track_error(self, operation: str, error: Union[str, Exception], attributes: Optional[Dict[str, Any]] = None):
            """Track operation errors."""
            error_str = str(error)
            self.logger.debug(f"ERROR: {operation} - {error_str} {attributes or ''}")
            
        def increment(self, metric: str, value: int = 1, attributes: Optional[Dict[str, Any]] = None):
            """Increment a metric counter."""
            self.logger.debug(f"COUNT: {metric}+{value} {attributes or ''}")
            
    def setup_monitoring(service_name: str) -> MetricsCollector:
        """Set up monitoring for a service."""
        return MetricsCollector(service_name)
        
    def track_latency(operation: str, seconds: Optional[float] = None, start_time: Optional[float] = None) -> Optional[float]:
        """Track operation latency."""
        if seconds is not None:
            return seconds
        
        if start_time is not None:
            return time.time() - start_time
            
        return time.time()
        
    def track_error(operation: str, error: Union[str, Exception]) -> None:
        """Track an operation error."""
        logger = logging.getLogger("ailf.monitoring")
        logger.error(f"Operation '{operation}' failed: {str(error)}")
        
    def increment(metric: str, value: int = 1) -> None:
        """Increment a metric counter."""
        logger = logging.getLogger("ailf.monitoring")
        logger.debug(f"Metric '{metric}' incremented by {value}")

__all__ = [
    "MetricsCollector",
    "setup_monitoring",
    "track_latency",
    "track_error",
    "increment"
]
