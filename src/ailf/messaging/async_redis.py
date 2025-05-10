"""Async Redis Client Utilities.

This module provides asynchronous versions of Redis utility classes for use
with AsyncIO-based applications.

Key Components:
    AsyncRedisPubSub: Asynchronous wrapper for RedisPubSub functionality

Example:
    Async PubSub usage:
        >>> import asyncio
        >>> from ailf.messaging.async_redis import AsyncRedisPubSub
        >>> from ailf.messaging.redis import AsyncRedisClient
        >>> 
        >>> async def main():
        ...     client = AsyncRedisClient()
        ...     await client.connect()
        ...     pubsub = AsyncRedisPubSub(client=client)
        ...     
        ...     # Subscribe to a channel
        ...     async def message_handler(channel, message):
        ...         print(f"Received on {channel}: {message}")
        ...     
        ...     await pubsub.subscribe("my_channel", message_handler)
        ...     
        ...     # Publish a message
        ...     await pubsub.publish("my_channel", {"hello": "world"})
        ...     
        ...     # Wait for a while to receive messages
        ...     await asyncio.sleep(5)
        ...     
        ...     # Cleanup
        ...     await pubsub.unsubscribe_all()
        ...     await client.close()
        ... 
        >>> asyncio.run(main())
"""
import asyncio
import json
from typing import Any, Callable, Dict, Optional, Union

from ..logging import setup_logging
from .redis import AsyncRedisClient

logger = setup_logging(__name__)


class AsyncRedisPubSub:
    """Asynchronous Redis Pub/Sub interface.

    This class provides a simple async interface for Pub/Sub messaging patterns
    with automatic JSON serialization/deserialization.

    Attributes:
        client: AsyncRedisClient instance
        subscriptions: Dictionary of channel to handler mappings
    """

    def __init__(self, client: Optional[AsyncRedisClient] = None):
        """Initialize the async Redis Pub/Sub interface.

        Args:
            client: Optional AsyncRedisClient to use
        """
        self.client = client or AsyncRedisClient()
        self._pubsub = None
        self.subscriptions: Dict[str, Callable] = {}
        self._running = False
        self._task = None

    async def _get_pubsub(self):
        """Get or create the Redis pubsub object."""
        if self._pubsub is None:
            redis_client = await self.client.client
            self._pubsub = redis_client.pubsub()
        return self._pubsub

    async def publish(self, channel: str, message: Union[str, Dict[str, Any]]) -> int:
        """Publish a message to a channel asynchronously.

        Args:
            channel: Channel name to publish to
            message: Message data to publish (will be JSON encoded if dict)

        Returns:
            Number of clients that received the message
        """
        # Convert dict to JSON string if necessary
        if isinstance(message, dict):
            message = json.dumps(message)

        try:
            redis_client = await self.client.client
            return await redis_client.publish(channel, message)
        except Exception as e:
            logger.error(f"Error publishing to channel {channel}: {str(e)}")
            return 0

    async def subscribe(self, channel: str, handler: Callable[[str, Any], Any]) -> None:
        """Subscribe to a channel asynchronously.

        Args:
            channel: Channel name to subscribe to
            handler: Async function to call with received messages
        """
        self.subscriptions[channel] = handler
        pubsub = await self._get_pubsub()
        await pubsub.subscribe(channel)

        # Start message processing task if not already running
        if not self._running:
            self._start_message_processing()

        logger.info(f"Subscribed to Redis channel: {channel}")

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel asynchronously.

        Args:
            channel: Channel name to unsubscribe from
        """
        if channel in self.subscriptions:
            pubsub = await self._get_pubsub()
            await pubsub.unsubscribe(channel)
            del self.subscriptions[channel]
            logger.info(f"Unsubscribed from Redis channel: {channel}")

    async def unsubscribe_all(self) -> None:
        """Unsubscribe from all channels asynchronously."""
        if self.subscriptions:
            pubsub = await self._get_pubsub()
            # Get all channels
            channels = list(self.subscriptions.keys())
            # Unsubscribe from all channels
            await pubsub.unsubscribe(*channels)
            self.subscriptions.clear()
            logger.info("Unsubscribed from all Redis channels")

        # Stop the message processing task
        self._stop_message_processing()

    def _start_message_processing(self) -> None:
        """Start the message processing task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._process_messages())

    def _stop_message_processing(self) -> None:
        """Stop the message processing task."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _process_messages(self) -> None:
        """Process incoming messages asynchronously."""
        pubsub = await self._get_pubsub()

        while self._running:
            try:
                # Wait for a new message
                message = await pubsub.get_message(ignore_subscribe_messages=True)

                if message is not None and message['type'] == 'message':
                    channel = message['channel']
                    if isinstance(channel, bytes):
                        channel = channel.decode('utf-8')

                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')

                    # Try to parse as JSON
                    try:
                        if isinstance(data, str):
                            data = json.loads(data)
                    except json.JSONDecodeError:
                        # Not JSON, leave as is
                        pass

                    # Call the appropriate handler
                    if channel in self.subscriptions:
                        handler = self.subscriptions[channel]
                        try:
                            await handler(channel, data)
                        except Exception as e:
                            logger.error(
                                f"Error in message handler for channel {channel}: {str(e)}")

                # Small sleep to avoid tight loop
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing Redis messages: {str(e)}")
                await asyncio.sleep(1)  # Delay before retrying

    async def close(self) -> None:
        """Close the pubsub connection and clean up resources."""
        await self.unsubscribe_all()
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
