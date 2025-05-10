"""Mock Redis Streams implementation of the MessagingBackendBase."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from collections import defaultdict
import uuid

from ailf.messaging.base import MessagingBackendBase, MessageHandlerCallback

logger = logging.getLogger(__name__)

class MockRedisStreamsBackend(MessagingBackendBase):
    """
    An in-memory mock implementation of the Redis Streams messaging backend.

    This mock backend simulates the behavior of Redis Streams for testing purposes,
    allowing for message publishing and subscribing without a real Redis instance.
    It does not fully replicate all features of Redis Streams (e.g., consumer groups,
    message persistence beyond session, complex stream commands).
    """
    def __init__(self, 
                 redis_url: str,  # Kept for interface compatibility
                 consumer_group_prefix: str = "mock_ailf_group",
                 consumer_name_prefix: str = "mock_ailf_consumer"):
        self.redis_url = redis_url # Not actively used by mock
        self.consumer_group_prefix = consumer_group_prefix
        self.consumer_name_prefix = consumer_name_prefix
        
        self._is_connected: bool = False
        self._messages: Dict[str, List[Tuple[str, Dict[bytes, bytes]]]] = defaultdict(list) # topic -> list of (message_id, message_data)
        self._subscriptions: Dict[str, List[Tuple[MessageHandlerCallback, asyncio.Task]]] = defaultdict(list) # topic -> list of (callback, task)
        self._message_id_counter: int = 0

    async def connect(self) -> None:
        """Simulates establishing a connection."""
        logger.info(f"MockRedisStreamsBackend: Connecting to {self.redis_url} (simulated)")
        self._is_connected = True
        await asyncio.sleep(0) # Simulate async operation

    async def disconnect(self) -> None:
        """Simulates closing the connection and cancels subscription tasks."""
        logger.info("MockRedisStreamsBackend: Disconnecting (simulated)")
        self._is_connected = False
        for topic in list(self._subscriptions.keys()):
            await self.unsubscribe(topic)
        await asyncio.sleep(0) # Simulate async operation

    async def publish(self, topic: str, message: Union[str, bytes], **kwargs: Any) -> None:
        """
        Simulates publishing a message to a stream.

        The message is added to an in-memory list for the topic.
        If there are active subscriptions, their callbacks are invoked.
        """
        if not self._is_connected:
            raise ConnectionError("MockRedisStreamsBackend: Not connected.")

        if not isinstance(message, (str, bytes)):
            raise TypeError(f"Message must be str or bytes, got {type(message)}")
        
        message_data_bytes: bytes = message if isinstance(message, bytes) else message.encode('utf-8')
        
        # Simulate XADD behavior: message stored with a field name, e.g., 'message'
        # Redis Streams messages are dictionaries of field-value pairs.
        simulated_redis_message: Dict[bytes, bytes] = {b'message': message_data_bytes}
        
        self._message_id_counter += 1
        message_id = f"{self._message_id_counter}-0" # Simple mock message ID

        self._messages[topic].append((message_id, simulated_redis_message))
        logger.debug(f"MockRedisStreamsBackend: Published message {message_id} to topic '{topic}'. Content: {message_data_bytes[:50]}...")

        # Simulate message delivery to subscribers
        if topic in self._subscriptions:
            for callback, _ in self._subscriptions[topic]:
                try:
                    # Callback expects topic and the raw message payload (bytes)
                    # The real RedisStreamsBackend extracts this from the 'message' field.
                    asyncio.create_task(callback(topic, message_data_bytes))
                except Exception as e:
                    logger.error(f"MockRedisStreamsBackend: Error invoking callback for topic '{topic}': {e}", exc_info=True)
        await asyncio.sleep(0)

    async def subscribe(self, 
                        topic: str, 
                        callback: MessageHandlerCallback, 
                        consumer_name: Optional[str] = None, # Not strictly used by mock logic but part of interface
                        **kwargs: Any) -> None:
        """
        Simulates subscribing to a stream.

        The callback is stored and will be invoked when messages are published to the topic.
        A mock listener task is created.
        """
        if not self._is_connected:
            raise ConnectionError("MockRedisStreamsBackend: Not connected.")

        _consumer_name = consumer_name or f"{self.consumer_name_prefix}:{topic}:{uuid.uuid4().hex[:8]}"
        
        # Create a dummy task that doesn't do much for the mock,
        # as publish directly triggers callbacks.
        # In a more complex mock, this task could simulate polling.
        async def mock_listener():
            while self._is_connected:
                await asyncio.sleep(1) # Keep task alive

        listener_task = asyncio.create_task(mock_listener())
        self._subscriptions[topic].append((callback, listener_task))
        logger.info(f"MockRedisStreamsBackend: Subscribed to topic '{topic}' with consumer '{_consumer_name}' (simulated). Listener task started.")
        await asyncio.sleep(0)

    async def unsubscribe(self, topic: str, **kwargs: Any) -> None:
        """Simulates unsubscribing from a stream."""
        if topic in self._subscriptions:
            for _, task in self._subscriptions[topic]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.debug(f"MockRedisStreamsBackend: Listener task for topic '{topic}' cancelled.")
            del self._subscriptions[topic]
            logger.info(f"MockRedisStreamsBackend: Unsubscribed from topic '{topic}'.")
        else:
            logger.warning(f"MockRedisStreamsBackend: No active subscription found for topic '{topic}' to unsubscribe from.")
        await asyncio.sleep(0)

    # --- Mock-specific methods for testing ---
    async def get_messages(self, topic: str) -> List[Tuple[str, Dict[bytes, bytes]]]:
        """Returns all messages published to a topic (for test inspection)."""
        return self._messages.get(topic, [])

    async def clear_messages(self, topic: Optional[str] = None) -> None:
        """Clears messages for a specific topic or all topics if None."""
        if topic:
            if topic in self._messages:
                del self._messages[topic]
        else:
            self._messages.clear()
        logger.debug(f"MockRedisStreamsBackend: Cleared messages for {'topic ' + topic if topic else 'all topics'}.")
        await asyncio.sleep(0)

    async def clear_subscriptions(self, topic: Optional[str] = None) -> None:
        """Clears subscriptions for a specific topic or all topics if None."""
        if topic:
            if topic in self._subscriptions:
                await self.unsubscribe(topic) # Leverages existing cancellation logic
        else:
            for t in list(self._subscriptions.keys()):
                await self.unsubscribe(t)
        logger.debug(f"MockRedisStreamsBackend: Cleared subscriptions for {'topic ' + topic if topic else 'all topics'}.")

    async def clear_all_state(self) -> None:
        """Clears all messages and subscriptions from the mock backend."""
        await self.clear_messages()
        await self.clear_subscriptions()
        self._message_id_counter = 0
        logger.info("MockRedisStreamsBackend: All mock state cleared.")

    async def flushdb(self) -> None: # Mimics a redis client's flushdb for testing
        """Clears all data from the mock backend, similar to Redis FLUSHDB."""
        await self.clear_all_state()
