# ruff: noqa: F401
# pylint: disable=broad-except,no-member,too-many-instance-attributes
"""ZMQ Device Management Module.

This module provides high-level abstractions for ZMQ devices with proper resource
management, monitoring, and error handling.

Key Components:
    DeviceManager: Factory for creating and managing ZMQ devices
    ThreadDevice: Device implementation running in a background thread
    ProcessDevice: Device implementation running in a separate process
"""
from contextlib import contextmanager
from multiprocessing import Event, Process
from threading import Thread
from typing import Any, List, Optional, Sequence

import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator

from utils.logging import setup_logging
from utils.monitoring import setup_monitoring

from .schemas.zmq_devices import AuthConfig, DeviceConfig, DeviceType

# Initialize logging and metrics
logger = setup_logging(__name__)
metrics = setup_monitoring(__name__)

# Constants
DEFAULT_LINGER = 0  # Default socket linger time in ms
DEFAULT_POLL_TIMEOUT = 100  # Default poll timeout in ms
DEFAULT_JOIN_TIMEOUT = 1.0  # Default thread/process join timeout in seconds


class DeviceError(Exception):
    """Base exception for device operations."""


class BaseDevice:
    """Base class for ZMQ devices.

    Implements common functionality for device management including:
    - Socket setup and configuration
    - Authentication and security
    - Monitoring and error handling
    - Resource cleanup
    """

    def __init__(
        self,
        config: DeviceConfig,
        *,
        context: Optional[zmq.Context] = None
    ):
        """Initialize base device.

        Args:
            config: Device configuration
            context: Optional ZMQ context
        """
        self.config = config
        self._context = context or zmq.Context.instance()
        self._frontend: Optional[zmq.Socket] = None
        self._backend: Optional[zmq.Socket] = None
        self._running = False
        self._poller = zmq.Poller()
        self._should_stop = None
        self._auth: Optional[ThreadAuthenticator] = None

    def _setup_sockets(self) -> None:
        """Set up frontend and backend sockets with proper configuration."""
        # Create sockets
        self._frontend = self._context.socket(
            self.config.device_type.frontend_type)
        self._backend = self._context.socket(
            self.config.device_type.backend_type)

        # Configure socket options
        for socket in (self._frontend, self._backend):
            # Ensure clean shutdown
            socket.setsockopt(zmq.LINGER, DEFAULT_LINGER)
            if hasattr(socket, 'RCVTIMEO'):
                socket.setsockopt(zmq.RCVTIMEO, DEFAULT_POLL_TIMEOUT)
            if hasattr(socket, 'SNDTIMEO'):
                socket.setsockopt(zmq.SNDTIMEO, DEFAULT_POLL_TIMEOUT)

        # Set up authentication if configured
        if self.config.auth_config:
            self._setup_auth(self.config.auth_config)

        # Bind sockets
        try:
            self._frontend.bind(self.config.frontend_addr)
            self._backend.bind(self.config.backend_addr)
        except zmq.ZMQError as e:
            self._cleanup()
            raise DeviceError(f"Failed to bind sockets: {e}") from e

        # Set up monitoring
        self._poller.register(self._frontend, zmq.POLLIN)
        self._poller.register(self._backend, zmq.POLLIN)

    def _setup_auth(self, auth_config: AuthConfig) -> None:
        """Configure CURVE authentication for the device sockets.

        Args:
            auth_config: Authentication configuration containing keys and certificates

        Raises:
            DeviceError: If authentication setup fails
        """
        try:
            auth = ThreadAuthenticator(self._context)
            auth.start()
            auth.configure_curve(
                domain='*', location=auth_config.certificates_dir)

            # Set up server authentication
            for socket in (self._frontend, self._backend):
                socket.curve_server = True
                socket.curve_secretkey = auth_config.server_secret_key
                socket.curve_publickey = auth_config.server_public_key

            self._auth = auth
        except Exception as e:
            raise DeviceError(f"Failed to setup authentication: {e}") from e

    def _cleanup_auth(self) -> None:
        """Clean up authentication resources."""
        if hasattr(self, '_auth') and self._auth is not None:
            self._auth.stop()

    def _cleanup(self) -> None:
        """Clean up resources."""
        # Close sockets
        if self._frontend:
            self._frontend.close()
            self._frontend = None
        if self._backend:
            self._backend.close()
            self._backend = None

        # Clean up authentication if configured
        if hasattr(self, '_auth'):
            self._auth = None

        # Clean up context if we created it
        if not self._context.closed and self._context is not zmq.Context.instance():
            self._context.term()

    def _forward_message(
        self,
        recv_socket: zmq.Socket,
        send_socket: zmq.Socket
    ) -> bool:
        """Forward a message between sockets.

        Args:
            recv_socket: Socket to receive from
            send_socket: Socket to send to

        Returns:
            True if message was forwarded successfully
        """
        try:
            message = recv_socket.recv_multipart(zmq.NOBLOCK)
            send_socket.send_multipart(message)
            metrics.increment("messages_forwarded")
            return True
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                # No message available
                return False
            logger.error(f"Error forwarding message: {e}")
            metrics.increment("message_errors")
            return False

    def _device_loop(self) -> None:
        """Main device loop for message forwarding.

        This method handles message forwarding between frontend and backend sockets
        with proper error handling and metrics collection.
        """
        while not self._should_stop.is_set():
            try:
                # Wait for messages on either socket
                events = dict(self._poller.poll(DEFAULT_POLL_TIMEOUT))

                # Forward frontend -> backend
                if events.get(self._frontend) == zmq.POLLIN:
                    message = self._frontend.recv_multipart()
                    self._backend.send_multipart(message)
                    metrics.increment('messages_forwarded_frontend')

                # Forward backend -> frontend
                if events.get(self._backend) == zmq.POLLIN:
                    message = self._backend.recv_multipart()
                    self._frontend.send_multipart(message)
                    metrics.increment('messages_forwarded_backend')

            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:  # Timeout, normal for polling
                    continue
                elif e.errno == zmq.ETERM:  # Context terminated
                    break
                else:
                    metrics.increment('device_errors')
                    logger.error("ZMQ error in device loop: %s", e)
                    if not self.config.ignore_errors:
                        raise DeviceError("Device loop failed") from e

            except Exception as e:
                metrics.increment('device_errors')
                logger.error("Unexpected error in device loop: %s", e)
                if not self.config.ignore_errors:
                    raise DeviceError("Device loop failed") from e

        logger.info("Device loop terminated")

    def start(self) -> None:
        """Start the device."""
        raise NotImplementedError("Subclasses must implement start()")

    def stop(self) -> None:
        """Stop the device."""
        self._running = False


class ThreadDevice(BaseDevice):
    """Thread-based ZMQ device implementation."""

    def __init__(self, config: DeviceConfig, *, context: Optional[zmq.Context] = None):
        """Initialize thread device.

        Args:
            config: Device configuration
            context: Optional ZMQ context
        """
        super().__init__(config, context=context)
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        """Start the device in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Device thread already running")
            return

        self._thread = Thread(
            target=self._device_loop,
            name=f"ZMQDevice-{self.config.device_type.name}",
            daemon=True
        )
        self._thread.start()
        metrics.increment("thread_device_starts")

    def stop(self) -> None:
        """Stop the device thread."""
        if not self._thread:
            return

        super().stop()
        if self._thread.is_alive():
            self._thread.join(DEFAULT_JOIN_TIMEOUT)
            if self._thread.is_alive():
                logger.warning("Device thread did not stop cleanly")
                metrics.increment("thread_device_timeout")
            else:
                metrics.increment("thread_device_stops")
        self._thread = None

    def __enter__(self) -> "ThreadDevice":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()


class ProcessDevice(BaseDevice):
    """Process-based ZMQ device implementation.

    This implementation runs the device in a separate process for better isolation
    and parallel processing capabilities.
    """

    def __init__(self, config: DeviceConfig):
        """Initialize ProcessDevice with configuration.

        Args:
            config: Device configuration
        """
        super().__init__(config)
        self._process: Optional[Process] = None
        self._should_stop: Optional[Event] = None

    def start(self) -> None:
        """Start the device in a separate process."""
        if self._process and self._process.is_alive():
            raise DeviceError("Device already running")

        self._should_stop = Event()
        self._process = Process(
            target=self._run_device_process,
            name=f"DeviceProcess-{self.config.device_type.name}"
        )
        self._process.start()
        metrics.increment("process_device_starts")

    def stop(self) -> None:
        """Stop the device process."""
        if self._should_stop:
            self._should_stop.set()

    def join(self, timeout: Optional[float] = None) -> None:
        """Wait for the device process to terminate.

        Args:
            timeout: Maximum time to wait for process termination
        """
        if self._process:
            self._process.join(timeout)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(DEFAULT_JOIN_TIMEOUT)

    def is_alive(self) -> bool:
        """Check if the device process is running.

        Returns:
            bool: True if process is alive, False otherwise
        """
        return bool(self._process and self._process.is_alive())

    def _run_device_process(self) -> None:
        """Main process function that sets up and runs the device loop."""
        try:
            self._context = zmq.Context()
            self._poller = zmq.Poller()
            self._setup_sockets()
            self._device_loop()
        except Exception as e:
            self._logger.error(f"Error in device process: {e}")
            raise
        finally:
            self._cleanup()

    def __enter__(self) -> "ProcessDevice":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()


class DeviceManager:
    """Manager for ZMQ devices."""

    def __init__(self):
        """Initialize device manager."""
        self._devices: List[BaseDevice] = []
        self._context = zmq.Context.instance()

    def create_device(
        self,
        device_type: DeviceType,
        frontend: str,
        backend: str,
        *,
        monitor: Optional[str] = None,
        auth_config: Optional[AuthConfig] = None,
        use_process: bool = False
    ) -> BaseDevice:
        """Create a new device with the specified configuration.

        Args:
            device_type: Type of device to create
            frontend: Frontend socket address
            backend: Backend socket address
            monitor: Optional monitor socket address
            auth_config: Optional authentication configuration
            use_process: Whether to use process-based device

        Returns:
            BaseDevice: Configured device instance
        """
        config = DeviceConfig(
            device_type=device_type,
            frontend_addr=frontend,
            backend_addr=backend,
            monitor_addr=monitor,
            auth_config=auth_config
        )

        device_class = ProcessDevice if use_process else ThreadDevice
        device = device_class(config)
        self._devices.append(device)
        return device

    def create_queue(
        self,
        frontend: str,
        backend: str,
        monitor: Optional[str] = None,
        **kwargs: Any
    ) -> BaseDevice:
        """Create a QUEUE device."""
        return self.create_device(
            DeviceType.QUEUE,
            frontend,
            backend,
            monitor=monitor,
            **kwargs
        )

    def create_forwarder(
        self,
        frontend: str,
        backend: str,
        monitor: Optional[str] = None,
        **kwargs: Any
    ) -> BaseDevice:
        """Create a FORWARDER device."""
        return self.create_device(
            DeviceType.FORWARDER,
            frontend,
            backend,
            monitor=monitor,
            **kwargs
        )

    def create_streamer(
        self,
        frontend: str,
        backend: str,
        monitor: Optional[str] = None,
        **kwargs: Any
    ) -> BaseDevice:
        """Create a STREAMER device."""
        return self.create_device(
            DeviceType.STREAMER,
            frontend,
            backend,
            monitor=monitor,
            **kwargs
        )

    def start_device(self, config: DeviceConfig) -> BaseDevice:
        """Start a device with the provided configuration.

        Args:
            config: Device configuration

        Returns:
            BaseDevice: Started device instance
        """
        device = ThreadDevice(config, context=self._context)
        device.start()
        self._devices.append(device)
        return device

    def stop_all(self) -> None:
        """Stop all managed devices."""
        for device in self._devices:
            try:
                device.stop()
            except Exception as e:
                logger.error("Error stopping device: %s", e)
            metrics.increment("device_stop_errors")
        self._devices.clear()

    @property
    def active_devices(self) -> List[BaseDevice]:
        """Get list of currently active devices."""
        return [d for d in self._devices if d.is_alive()]

    def __enter__(self) -> "DeviceManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop_all()


@contextmanager
def create_device(
    device_type: DeviceType,
    frontend: str,
    backend: str,
    **kwargs
) -> Any:
    """Context manager for creating and managing a ZMQ device.

    Args:
        device_type: The type of device to create
        frontend: Frontend socket address
        backend: Backend socket address
        **kwargs: Additional arguments passed to create_device

    Example:
        with create_device(DeviceType.QUEUE, "tcp://*:5555", "tcp://*:5556") as device:
            # Device is running
            ...
        # Device is stopped and cleaned up
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


class ZmqDevice:
    """ZMQ Device for managing message flow between sockets."""

    def __init__(self, context):
        """Initialize the ZMQ Device.

        Args:
            context: The ZMQ context to use.
        """
        self.context = context

    def start(self, sender, receiver):
        """Start the ZMQ device to forward messages.

        Args:
            sender: The sending socket.
            receiver: The receiving socket.
        """
        while True:
            message = sender.recv()
            receiver.send(message)

    def close(self):
        """Close the ZMQ device."""
        self.context.term()
