"""ZeroMQ Device Manager.

This module provides a manager for creating and controlling ZMQ devices
in a centralized way.

Key Components:
    DeviceManager: Factory for creating and managing ZMQ devices
    create_device: Context manager for simplified device creation
"""

import threading
from contextlib import contextmanager
from typing import Any, List, Optional, Union

import zmq

from ailf.schemas.zmq_devices import AuthConfig, DeviceConfig, DeviceType
from .zmq_devices import ZMQDevice, ZMQForwarder, ZMQStreamer, ZMQProxy

# Try to import from utils if available for more advanced functionality
try:
    from utils.logging import setup_logging
    logger = setup_logging(__name__)
except ImportError:
    # Fallback to standard logging
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)

try:
    from utils.monitoring import setup_monitoring
    metrics = setup_monitoring(__name__)
except ImportError:
    # No-op metrics as fallback
    class NoopMetrics:
        def __getattr__(self, name):
            return self.noop
            
        def noop(self, *args, **kwargs):
            pass
    
    metrics = NoopMetrics()


class DeviceError(Exception):
    """Base exception for device operations."""
    pass


class DeviceManager:
    """Manager for ZMQ devices.
    
    This class provides a centralized way to create, configure, and manage
    ZeroMQ devices for distributed messaging patterns.
    """

    def __init__(self, context: Optional[zmq.Context] = None):
        """Initialize device manager.
        
        Args:
            context: ZMQ context to use (creates one if None)
        """
        self._devices: List[ZMQDevice] = []
        self._context = context or zmq.Context.instance()
    
    def create_device(
        self,
        device_type: Union[DeviceType, str],
        frontend: str,
        backend: str,
        *,
        monitor: Optional[str] = None,
        auth_config: Optional[AuthConfig] = None,
    ) -> ZMQDevice:
        """Create a new device with the specified configuration.

        Args:
            device_type: Type of device to create
            frontend: Frontend socket address
            backend: Backend socket address
            monitor: Optional monitor socket address
            auth_config: Optional authentication configuration

        Returns:
            ZMQDevice: Configured device instance
        """
        # Convert string to DeviceType if needed
        if isinstance(device_type, str):
            device_type = DeviceType(device_type)
            
        # Create appropriate device based on type
        if device_type == DeviceType.QUEUE:
            device = ZMQProxy(frontend, backend, self._context)
        elif device_type == DeviceType.FORWARDER:
            device = ZMQForwarder(frontend, backend, self._context)
        elif device_type == DeviceType.STREAMER:
            device = ZMQStreamer(frontend, backend, self._context)
        else:
            raise DeviceError(f"Unsupported device type: {device_type}")
            
        # Add to managed devices
        self._devices.append(device)
        
        # Return the configured device
        return device
    
    def create_queue(
        self,
        frontend: str,
        backend: str,
        **kwargs: Any
    ) -> ZMQDevice:
        """Create a QUEUE device (ROUTER-DEALER proxy).
        
        Args:
            frontend: Frontend address
            backend: Backend address
            **kwargs: Additional configuration options
            
        Returns:
            ZMQDevice: Configured queue device
        """
        return self.create_device(
            DeviceType.QUEUE,
            frontend,
            backend,
            **kwargs
        )
    
    def create_forwarder(
        self,
        frontend: str,
        backend: str,
        **kwargs: Any
    ) -> ZMQDevice:
        """Create a FORWARDER device (SUB-PUB proxy).
        
        Args:
            frontend: Frontend address
            backend: Backend address
            **kwargs: Additional configuration options
            
        Returns:
            ZMQDevice: Configured forwarder device
        """
        return self.create_device(
            DeviceType.FORWARDER,
            frontend,
            backend,
            **kwargs
        )
    
    def create_streamer(
        self,
        frontend: str,
        backend: str,
        **kwargs: Any
    ) -> ZMQDevice:
        """Create a STREAMER device (PULL-PUSH proxy).
        
        Args:
            frontend: Frontend address
            backend: Backend address
            **kwargs: Additional configuration options
            
        Returns:
            ZMQDevice: Configured streamer device
        """
        return self.create_device(
            DeviceType.STREAMER,
            frontend,
            backend,
            **kwargs
        )
    
    def start_device(self, device: ZMQDevice) -> ZMQDevice:
        """Start a device and add it to managed devices.
        
        Args:
            device: Device to start
            
        Returns:
            ZMQDevice: Started device instance
        """
        device.start()
        if device not in self._devices:
            self._devices.append(device)
        metrics.increment("device_starts")
        return device
    
    def stop_all(self) -> None:
        """Stop all managed devices."""
        for device in self._devices:
            try:
                device.stop()
                metrics.increment("device_stops")
            except Exception as e:
                logger.error("Error stopping device: %s", e)
                metrics.increment("device_stop_errors")
        self._devices.clear()
    
    @property
    def active_devices(self) -> List[ZMQDevice]:
        """Get list of currently active devices.
        
        Returns:
            List[ZMQDevice]: List of active device instances
        """
        # For our implementation, we don't have an is_alive method,
        # so we just return all devices - in a real implementation
        # you might filter based on running state
        return list(self._devices)
    
    def __enter__(self) -> "DeviceManager":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop_all()


@contextmanager
def create_device(
    device_type: Union[DeviceType, str],
    frontend: str,
    backend: str,
    **kwargs
) -> Any:
    """Context manager for creating and managing a ZMQ device.

    Args:
        device_type: The type of device to create
        frontend: Frontend socket address
        backend: Backend socket address
        **kwargs: Additional arguments for device configuration

    Example:
        ```python
        with create_device(DeviceType.QUEUE, "tcp://*:5555", "tcp://*:5556") as device:
            # Device is running
            # Do other work...
        # Device is automatically stopped and cleaned up
        ```
    """
    manager = DeviceManager()
    device = manager.create_device(
        device_type,
        frontend,
        backend,
        **kwargs
    )
    try:
        device.start()
        yield device
    finally:
        device.stop()


__all__ = [
    "DeviceManager",
    "DeviceError",
    "create_device"
]
