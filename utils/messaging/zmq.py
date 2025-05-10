"""ZeroMQ Utilities Module.

This module provides a unified interface for ZMQ operations with proper resource
management, error handling, and common messaging patterns.

Key Components:
    ZMQManager: Central manager for ZMQ contexts and socket creation
    ZMQSocket: Context-managed wrapper for ZMQ sockets
    ZMQError: Custom exception type for ZMQ-specific errors

Example:
    >>> from utils.zmq import ZMQManager
    >>> from utils.schemas.zmq import SocketType
    >>> 
    >>> # Publisher example
    >>> with ZMQManager() as zmq:
    ...     with zmq.socket(SocketType.PUB, "tcp://*:5555") as pub:
    ...         pub.send_message("Hello", topic="greetings")
    ...
    >>> # Subscriber example
    >>> with ZMQManager() as zmq:
    ...     with zmq.socket(SocketType.SUB, "tcp://localhost:5555", topics=["greetings"]) as sub:
    ...         message = sub.receive()
    ...         print(message.payload.decode())
    ...         'Hello'

Note:
    All sockets are automatically managed using context managers to ensure proper cleanup.
"""

import json
import time
from contextlib import contextmanager
from typing import Any, Optional, Union

import zmq

from .logging import setup_logging
from .monitoring import MetricsCollector, setup_monitoring
from .schemas.zmq import MessageEnvelope, SocketType, ZMQConfig

logger = setup_logging(__name__)
metrics = setup_monitoring(__name__)


class ZMQError(Exception):
    """Base exception for ZMQ operations.

    This exception wraps ZMQ-specific errors and provides additional context.

    :param message: The error message
    :type message: str
    :param original_error: The original exception that caused this error
    :type original_error: Optional[Exception]
    """
    pass


class ZMQSocket:
    """Wrapper for ZMQ socket with context management.

    This class provides a high-level interface for ZMQ socket operations with
    automatic resource management, error handling, and metrics collection.

    :param config: Socket configuration parameters
    :type config: ZMQConfig
    :param context: ZMQ context to use for socket creation
    :type context: zmq.Context
    :param metrics: Optional metrics collector
    :type metrics: Optional[MetricsCollector]

    Example:
        >>> config = ZMQConfig(socket_type=SocketType.PUB, address="tcp://*:5555")
        >>> with ZMQSocket(config, context) as socket:
        ...     socket.send_message("Hello", topic="greetings")
    """

    def __init__(self, config: ZMQConfig, context: zmq.Context, metrics: Optional[MetricsCollector] = None):
        """Initialize ZMQ socket wrapper.

        :param config: Socket configuration parameters
        :type config: ZMQConfig
        :param context: ZMQ context to use for socket creation
        :type context: zmq.Context
        :param metrics: Optional metrics collector
        :type metrics: Optional[MetricsCollector]
        :raises ZMQError: If socket initialization fails
        """
        self.config = config
        self.context = context
        self.metrics = metrics or setup_monitoring(__name__)
        self.socket = None

    def __enter__(self):
        """Configure and return socket.

        This method initializes the socket by:
        1. Creating the socket with the configured type
        2. Applying socket options
        3. Binding or connecting the socket
        4. Setting up subscriptions if needed

        Override the _create_socket, _configure_socket_options, _connect_socket,
        or _setup_subscriptions methods to customize socket behavior.
        """
        try:
            logger.info(
                "Creating socket of type %s", self.config.socket_type.value)
            self.socket = self._create_socket()
            logger.info("Socket created successfully")

            # Configure socket options
            self._configure_socket_options()

            # Connect or bind
            try:
                self._connect_socket()
            except zmq.ZMQError as e:
                logger.error(
                    f"ZMQ Error during {'bind' if self.config.bind else 'connect'}: {e}")
                raise ZMQError(
                    f"Failed to {self.config.bind and 'bind' or 'connect'}: {str(e)}")

            # Set up subscriptions if needed
            self._setup_subscriptions()

            return self

        except Exception as e:
            logger.error("Failed to initialize ZMQ socket: %s", str(e))
            self.metrics.increment("socket.init.error")
            raise ZMQError(f"Socket initialization failed: {str(e)}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up socket resources."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error("Error closing socket: %s", str(e))
                self.metrics.increment("socket.close.error")

    def send_message(
        self,
        data: Union[str, bytes, dict],
        topic: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Send a message through the socket.

        Sends data through the socket with optional topic and metadata. The data
        is automatically serialized and wrapped in a MessageEnvelope.

        :param data: The message payload to send
        :type data: Union[str, bytes, dict]
        :param topic: Optional topic for pub/sub messaging
        :type topic: Optional[str]
        :param metadata: Optional metadata to include with the message
        :type metadata: Optional[dict]
        :return: True if sent successfully, False otherwise
        :rtype: bool
        :raises ZMQError: If sending fails

        Example:
            >>> socket.send_message({"key": "value"}, topic="updates")
            True
            >>> socket.send_message("Hello", metadata={"priority": "high"})
            True
        """
        start_time = time.time()
        try:
            start_time = time.time()
            if isinstance(data, dict):
                payload = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                payload = data.encode('utf-8')
            else:
                payload = data

            try:
                envelope = MessageEnvelope(
                    topic=topic,
                    payload=payload,
                    metadata=metadata or {}
                )
            except Exception as e:
                logger.error(
                    f"Failed to create MessageEnvelope: {e}, payload type: {type(payload)}")
                return False

            # Prepare message for sending
            logger.debug("Preparing message with topic: %s", topic)
            try:
                message_json = envelope.model_dump_json().encode('utf-8')
            except Exception as e:
                logger.error("Failed to serialize message: %s", e)
                return False

            # Send the message
            try:
                if self.config.socket_type == SocketType.PUB:
                    if not topic:
                        logger.error("Topic is required for PUB sockets")
                        return False
                    logger.debug("Sending PUB message: topic=%s", topic)
                    self.socket.send_multipart(
                        [topic.encode('utf-8'), message_json])
                else:
                    logger.debug("Sending single part message")
                    self.socket.send(message_json)

                self.metrics.timing("message.send", time.time() - start_time)
                return True

            except zmq.ZMQError as e:
                logger.error("ZMQ error while sending: %s", e)
                raise ZMQError(f"Failed to send message: {e}") from e

        except zmq.ZMQError as e:
            logger.error(
                "ZMQ Error sending message: %s (errno: %s)", e, e.errno)
            self.metrics.increment("message.send.error")
            raise ZMQError(f"Failed to send message: {str(e)}") from e
        except Exception as e:
            logger.error("Failed to send message: %s", str(e))
            self.metrics.increment("message.send.error")
            return False

    def receive(self, timeout: Optional[int] = None) -> Optional[MessageEnvelope]:
        """Receive a message from the socket.

        Receives and deserializes a message from the socket. For SUB sockets,
        handles multipart messages with topics correctly.

        :param timeout: Override receive timeout for this call (milliseconds)
        :type timeout: Optional[int]
        :return: Received message envelope or None if no message available
        :rtype: Optional[MessageEnvelope]
        :raises ZMQError: If receive operation fails

        Example:
            >>> message = socket.receive()
            >>> if message:
            ...     print(message.payload.decode())
        """
        start_time = time.time()
        try:
            if timeout is not None:
                old_timeout = self.socket.getsockopt(zmq.RCVTIMEO)
                self.socket.setsockopt(zmq.RCVTIMEO, timeout)

            try:
                if self.config.socket_type == SocketType.SUB:
                    logger.debug("Receiving multipart message on SUB socket")
                    parts = self.socket.recv_multipart()
                    if len(parts) != 2:
                        raise ZMQError(
                            f"Expected 2 message parts for SUB socket, got {len(parts)}")

                    topic = parts[0].decode('utf-8')
                    logger.debug("Received message with topic: %s", topic)
                    try:
                        data = json.loads(parts[1].decode('utf-8'))
                        # Ensure topic is included in envelope
                        data['topic'] = topic
                    except json.JSONDecodeError as e:
                        raise ZMQError(f"Failed to decode message JSON: {e}")
                else:
                    logger.debug("Receiving single part message")
                    try:
                        data = json.loads(self.socket.recv().decode('utf-8'))
                    except json.JSONDecodeError as e:
                        raise ZMQError(f"Failed to decode message JSON: {e}")

                try:
                    envelope = MessageEnvelope.model_validate(data)
                    logger.debug("Message envelope validated successfully")
                    self.metrics.timing("message.receive",
                                        time.time() - start_time)
                    return envelope
                except Exception as e:
                    raise ZMQError(f"Failed to validate message envelope: {e}")

            finally:
                if timeout is not None:
                    self.socket.setsockopt(zmq.RCVTIMEO, old_timeout)

        except zmq.Again:
            # Timeout occurred
            logger.debug(
                "Receive timeout after %sms", timeout or self.config.receive_timeout)
            self.metrics.increment("message.receive.timeout")
            return None
        except zmq.ZMQError as e:
            error_msg = "ZMQ error receiving message: %s (errno: %s)" % (
                str(e), e.errno)
            logger.error(error_msg)
            self.metrics.track_error("message.receive", error_msg)
            raise ZMQError(error_msg) from e
        except Exception as e:
            error_msg = "Failed to receive message: %s" % str(e)
            logger.error(error_msg)
            self.metrics.track_error("message.receive", error_msg)
            raise ZMQError(error_msg) from e

    def _create_socket(self):
        """Create the ZMQ socket based on configuration.

        Override this method in subclasses to customize socket creation.

        Returns:
            socket: ZMQ socket object
        """
        socket_type = self.config.socket_type.get_zmq_type()
        return self.context.socket(socket_type)

    def _configure_socket_options(self):
        """Configure socket options based on configuration.

        Override this method in subclasses to customize socket options.
        """
        if self.config.receive_timeout:
            self.socket.setsockopt(zmq.RCVTIMEO, self.config.receive_timeout)
        if self.config.send_timeout:
            self.socket.setsockopt(zmq.SNDTIMEO, self.config.send_timeout)
        if self.config.identity:
            self.socket.setsockopt(zmq.IDENTITY, self.config.identity)

        # Ensure we set HWM (High Water Mark) to prevent buffering issues
        self.socket.setsockopt(zmq.SNDHWM, 1000)
        self.socket.setsockopt(zmq.RCVHWM, 1000)

    def _connect_socket(self):
        """Connect or bind the socket based on configuration.

        Override this method in subclasses to customize connection behavior.

        Raises:
            zmq.ZMQError: If connection or binding fails
        """
        connection_type = "binding to" if self.config.bind else "connecting to"
        logger.info(
            "Socket %s %s", connection_type, self.config.address)
        if self.config.bind:
            self.socket.bind(self.config.address)
            logger.info("Bind successful")
        else:
            self.socket.connect(self.config.address)
            logger.info("Connect successful")

    def _setup_subscriptions(self):
        """Set up subscriptions for SUB sockets.

        Override this method in subclasses to customize subscription behavior.
        """
        if self.config.socket_type == SocketType.SUB:
            logger.info(
                "Setting up SUB socket with topics: %s", self.config.topics)
            for topic in (self.config.topics or [""]):
                logger.info("Subscribing to topic: %s", topic)
                self.socket.setsockopt_string(zmq.SUBSCRIBE, topic)


class ZMQManager:
    """Manager for ZMQ operations.

    This class manages ZMQ contexts and provides factory methods for creating
    configured sockets. It ensures proper resource cleanup and consistent
    socket configuration.

    :param metrics: Optional metrics collector
    :type metrics: Optional[MetricsCollector]

    Example:
        >>> with ZMQManager() as zmq:
        ...     with zmq.socket(SocketType.REQ, "tcp://localhost:5555") as sock:
        ...         sock.send_message({"request": "data"})
        ...         response = sock.receive()
    """

    def __init__(self, metrics: Optional[MetricsCollector] = None):
        """Initialize the ZMQ manager.

        :param metrics: Optional metrics collector
        :type metrics: Optional[MetricsCollector]
        """
        self.context = self._create_context()
        self.metrics = metrics or self._create_metrics()

    def _create_context(self) -> zmq.Context:
        """Create a ZMQ context.

        Override this method in subclasses to customize context creation.

        Returns:
            zmq.Context: ZMQ context
        """
        return zmq.Context()

    def _create_metrics(self) -> MetricsCollector:
        """Create a metrics collector.

        Override this method in subclasses to customize metrics collection.

        Returns:
            MetricsCollector: Metrics collector
        """
        return setup_monitoring(__name__)

    def __enter__(self):
        """Return manager instance."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up ZMQ context."""
        self._cleanup_context()

    def _cleanup_context(self) -> None:
        """Cleanup the ZMQ context.

        Returns:
            None
        """
        if self.context:
            logger.info("Terminating ZMQ context")
            try:
                self.context.term()
                logger.info("ZMQ context terminated")
            except Exception as e:
                logger.error("Error terminating ZMQ context: %s", str(e))
                self.metrics.increment("context.term.error")

    @contextmanager
    def socket(self, socket_type: SocketType, address: str, **kwargs) -> ZMQSocket:
        """Create a configured socket.

        Creates and configures a ZMQ socket with the specified type and address.
        Additional configuration can be provided through kwargs.

        :param socket_type: Type of socket to create (PUB, SUB, REQ, etc.)
        :type socket_type: SocketType
        :param address: Socket address (e.g., "tcp://localhost:5555")
        :type address: str
        :param kwargs: Additional socket configuration options
        :type kwargs: dict
        :return: Configured socket wrapper
        :rtype: ZMQSocket
        :raises ZMQError: If socket creation or configuration fails

        Example:
            >>> with zmq.socket(SocketType.PUB, "tcp://*:5555", bind=True) as pub:
            ...     pub.send_message("Hello", topic="greetings")
        """
        try:
            # Set reasonable defaults for socket configuration
            defaults = {
                'receive_timeout': 1000,  # 1 second timeout
                'send_timeout': 1000,     # 1 second timeout
            }
            # Override defaults with provided kwargs
            config_kwargs = {**defaults, **kwargs}

            # Create configuration
            config = self._create_config(socket_type, address, config_kwargs)

            logger.debug("Creating socket with config: %s",
                         config.model_dump())

            with self._create_socket_instance(config) as socket:
                yield socket
        except Exception as e:
            logger.error("Socket creation failed: %s", str(e))
            raise ZMQError(f"Failed to create socket: {str(e)}") from e

    def _create_config(self, socket_type: SocketType, address: str, config_kwargs: dict) -> ZMQConfig:
        """Create a socket configuration.

        Override this method in subclasses to customize configuration creation.

        Args:
            socket_type: The type of socket to create
            address: The address to bind/connect to
            config_kwargs: Additional configuration options

        Returns:
            ZMQConfig: Socket configuration
        """
        return ZMQConfig(
            socket_type=socket_type,
            address=address,
            **config_kwargs
        )

    def _create_socket_instance(self, config: ZMQConfig) -> ZMQSocket:
        """Create a socket instance.

        Override this method in subclasses to customize socket instance creation.

        Args:
            config: Socket configuration

        Returns:
            ZMQSocket: Socket instance

        Raises:
            ZMQError: If socket creation fails
        """
        try:
            return ZMQSocket(config, self.context, self.metrics)
        except ValueError as e:
            raise ZMQError(f"Invalid socket configuration: {str(e)}") from e
        except Exception as e:
            raise ZMQError(f"Failed to create socket: {str(e)}") from e

    def _create_context(self) -> zmq.Context:
        """Create a ZMQ context.

        Override this method in subclasses to customize context creation.

        Returns:
            zmq.Context: ZMQ context
        """
        return zmq.Context()

    def _create_metrics(self) -> MetricsCollector:
        """Create a metrics collector.

        Override this method in subclasses to customize metrics collection.

        Returns:
            MetricsCollector: Metrics collector
        """
        return setup_monitoring(__name__)
