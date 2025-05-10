"""Base classes for messaging backends in AILF.

This module defines the abstract interface that all messaging backend
implementations (e.g., Redis Streams, ZeroMQ) should adhere to.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Union, Awaitable

logger = logging.getLogger(__name__)

# Type alias for a message handling callback
# It takes a topic (str) and message data (Union[str, bytes]) and returns an Awaitable
MessageHandlerCallback = Callable[[str, Union[str, bytes]], Awaitable[None]]

class MessagingBackendBase(ABC):
    """
    Abstract base class for a messaging backend.

    This class defines the common interface for connecting to, publishing messages to,
    and subscribing to messages from a messaging system.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish a connection to the messaging system.
        This method should handle any necessary setup for the connection.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the messaging system.
        This method should handle graceful shutdown and cleanup of resources.
        """
        pass

    @abstractmethod
    async def publish(self, topic: str, message: Union[str, bytes], **kwargs: Any) -> None:
        """
        Publish a message to a specific topic or channel.

        :param topic: The topic or channel to publish the message to.
        :type topic: str
        :param message: The message content to publish (string or bytes).
        :type message: Union[str, bytes]
        :param kwargs: Additional keyword arguments specific to the backend (e.g., message TTL, headers).
        :type kwargs: Any
        """
        pass

    @abstractmethod
    async def subscribe(self, topic: str, callback: MessageHandlerCallback, **kwargs: Any) -> None:
        """
        Subscribe to a topic or channel to receive messages.

        When a message is received on the subscribed topic, the provided callback
        function will be invoked with the topic and the message content.

        :param topic: The topic or channel to subscribe to.
        :type topic: str
        :param callback: The asynchronous function to call when a message is received.
                         It should accept `topic: str` and `message: Union[str, bytes]` as arguments.
        :type callback: MessageHandlerCallback
        :param kwargs: Additional keyword arguments specific to the backend (e.g., group name for streams).
        :type kwargs: Any
        """
        pass

    @abstractmethod
    async def unsubscribe(self, topic: str, **kwargs: Any) -> None:
        """
        Unsubscribe from a topic or channel.

        :param topic: The topic or channel to unsubscribe from.
        :type topic: str
        :param kwargs: Additional keyword arguments specific to the backend.
        :type kwargs: Any
        """
        pass

    async def __aenter__(self):
        """Enter the runtime context related to this object."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context related to this object."""
        await self.disconnect()
