"""Redis Streams implementation of the MessagingBackendBase.

This module provides a concrete implementation of the messaging backend interface
using Redis Streams for durable message queuing and asynchronous communication.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Union, List

import redis.asyncio as redis
from redis.exceptions import RedisError

from ailf.messaging.base import MessagingBackendBase, MessageHandlerCallback

logger = logging.getLogger(__name__)

class RedisStreamsBackend(MessagingBackendBase):
    """
    A messaging backend that uses Redis Streams for message persistence and delivery.

    This backend supports durable message queuing, consumer groups, and asynchronous
    message handling, making it suitable for robust inter-agent communication.

    :param redis_url: URL for the Redis server (e.g., "redis://localhost:6379/0").
    :type redis_url: str
    :param consumer_group_prefix: Prefix for consumer group names. Defaults to "ailf_group".
    :type consumer_group_prefix: str, optional
    :param consumer_name_prefix: Prefix for consumer names within groups. Defaults to "ailf_consumer".
    :type consumer_name_prefix: str, optional
    :param default_block_ms: Default blocking time in milliseconds for stream reads. Defaults to 1000.
    :type default_block_ms: int, optional
    :param default_count: Default number of messages to fetch per read. Defaults to 10.
    :type default_count: int, optional
    """
    def __init__(self, 
                 redis_url: str,
                 consumer_group_prefix: str = "ailf_group",
                 consumer_name_prefix: str = "ailf_consumer",
                 default_block_ms: int = 1000,
                 default_count: int = 10):
        self.redis_url = redis_url
        self._redis_client: Optional[redis.Redis] = None
        self.consumer_group_prefix = consumer_group_prefix
        self.consumer_name_prefix = consumer_name_prefix
        self.default_block_ms = default_block_ms
        self.default_count = default_count
        self._subscription_tasks: Dict[str, asyncio.Task] = {}
        self._is_connecting = False
        self._is_connected = False

    async def connect(self) -> None:
        """Establishes a connection to the Redis server."""
        if self._is_connected or self._is_connecting:
            logger.debug(f"Redis connection already established or in progress for {self.redis_url}")
            return
        
        self._is_connecting = True
        try:
            logger.info(f"Connecting to Redis at {self.redis_url}...")
            self._redis_client = redis.from_url(self.redis_url)
            await self._redis_client.ping() # type: ignore
            self._is_connected = True
            logger.info(f"Successfully connected to Redis at {self.redis_url}.")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis at {self.redis_url}: {e}")
            self._redis_client = None
            self._is_connected = False
            raise # Re-raise the exception to signal connection failure
        finally:
            self._is_connecting = False

    async def disconnect(self) -> None:
        """Closes the connection to the Redis server and cancels subscription tasks."""
        logger.info("Disconnecting from Redis...")
        for topic, task in self._subscription_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled subscription task for topic: {topic}")
        self._subscription_tasks.clear()

        if self._redis_client:
            try:
                await self._redis_client.close()
                logger.info("Redis connection closed.")
            except RedisError as e:
                logger.error(f"Error while closing Redis connection: {e}")
            finally:
                self._redis_client = None
                self._is_connected = False
        else:
            logger.info("No active Redis connection to close.")
        self._is_connected = False

    async def publish(self, topic: str, message: Union[str, bytes], **kwargs: Any) -> None:
        """
        Publishes a message to a Redis Stream.

        The message is added to the stream specified by the topic.
        kwargs can include `message_id` (str, e.g. '*') or `maxlen` (int).

        :param topic: The name of the Redis Stream (used as the topic).
        :type topic: str
        :param message: The message content. If str, it will be utf-8 encoded.
                      It's expected to be a single value for the 'message' field.
        :type message: Union[str, bytes]
        :param kwargs: Supports `message_id` (e.g. '*') and `maxlen` for XADD.
        :type kwargs: Any
        :raises ConnectionError: If not connected to Redis.
        :raises TypeError: If message is not str or bytes.
        """
        if not self._redis_client or not self._is_connected:
            raise ConnectionError("Not connected to Redis. Call connect() first.")

        if not isinstance(message, (str, bytes)):
            raise TypeError(f"Message must be str or bytes, got {type(message)}")
        
        message_data: bytes = message if isinstance(message, bytes) else message.encode('utf-8')
        fields = {'message': message_data} # Store message under a 'message' field
        
        message_id = kwargs.get('message_id', '*')
        maxlen = kwargs.get('maxlen')

        try:
            msg_id = await self._redis_client.xadd(name=topic, fields=fields, id=message_id, maxlen=maxlen) # type: ignore
            logger.debug(f"Published message {msg_id} to stream '{topic}'.")
        except RedisError as e:
            logger.error(f"Failed to publish message to stream '{topic}': {e}")
            raise

    async def subscribe(self, 
                        topic: str, 
                        callback: MessageHandlerCallback, 
                        consumer_name: Optional[str] = None,
                        create_group: bool = True,
                        block_ms: Optional[int] = None,
                        count: Optional[int] = None,
                        **kwargs: Any) -> None:
        """
        Subscribes to a Redis Stream using a consumer group.

        This method creates a consumer group (if it doesn't exist and `create_group` is True)
        and starts a task to listen for new messages on the stream.

        :param topic: The name of the Redis Stream.
        :type topic: str
        :param callback: The async callback function to handle incoming messages.
        :type callback: MessageHandlerCallback
        :param consumer_name: Unique name for this consumer. Defaults to `consumer_name_prefix` + topic.
        :type consumer_name: Optional[str]
        :param create_group: Whether to create the consumer group if it doesn't exist. Defaults to True.
        :type create_group: bool
        :param block_ms: How long to block (in ms) waiting for messages. Defaults to `self.default_block_ms`.
        :type block_ms: Optional[int]
        :param count: Max number of messages to fetch per read. Defaults to `self.default_count`.
        :type count: Optional[int]
        :param kwargs: Additional arguments (not currently used by this backend for subscribe).
        :type kwargs: Any
        :raises ConnectionError: If not connected to Redis.
        :raises RuntimeError: If already subscribed to this topic with an active task.
        """
        if not self._redis_client or not self._is_connected:
            raise ConnectionError("Not connected to Redis. Call connect() first.")
        
        if topic in self._subscription_tasks and not self._subscription_tasks[topic].done():
            raise RuntimeError(f"Already subscribed to topic '{topic}' with an active task.")

        group_name = f"{self.consumer_group_prefix}:{topic}"
        _consumer_name = consumer_name or f"{self.consumer_name_prefix}:{topic}:{uuid.uuid4().hex[:8]}"
        _block_ms = block_ms if block_ms is not None else self.default_block_ms
        _count = count if count is not None else self.default_count

        if create_group:
            try:
                await self._redis_client.xgroup_create(name=topic, groupname=group_name, id='0', mkstream=True) # type: ignore
                logger.info(f"Consumer group '{group_name}' created for stream '{topic}' or already exists.")
            except RedisError as e:
                if 'BUSYGROUP' in str(e):
                    logger.info(f"Consumer group '{group_name}' already exists for stream '{topic}'.")
                else:
                    logger.error(f"Failed to create consumer group '{group_name}' for stream '{topic}': {e}")
                    raise
        
        # Start a background task to listen for messages
        task = asyncio.create_task(self._listen_for_messages(topic, group_name, _consumer_name, callback, _block_ms, _count))
        self._subscription_tasks[topic] = task
        logger.info(f"Subscribed to stream '{topic}' with consumer '{_consumer_name}' in group '{group_name}'. Listening task started.")

    async def _listen_for_messages(self, 
                                   stream_name: str, 
                                   group_name: str, 
                                   consumer_name: str, 
                                   callback: MessageHandlerCallback, 
                                   block_ms: int, 
                                   count: int):
        """Internal method to continuously listen for messages on a stream."""
        if not self._redis_client or not self._is_connected:
            logger.error(f"Redis client not available for listening on {stream_name}. Exiting listener.")
            return

        logger.info(f"Listener started for {stream_name} / {group_name} / {consumer_name}")
        while self._is_connected: # Loop while connected
            try:
                # '>' means get new messages not yet delivered to other consumers in this group
                messages = await self._redis_client.xreadgroup( # type: ignore
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: '>'},
                    count=count,
                    block=block_ms
                )

                if not messages:
                    await asyncio.sleep(0.01) # Short sleep if no messages to prevent tight loop if block_ms is very low
                    continue

                message_ids_to_ack = []
                for stream_key, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            # Assuming message is stored in a field named 'message'
                            payload = message_data.get(b'message') 
                            if payload is None:
                                logger.warning(f"Message {message_id.decode()} in stream {stream_key.decode()} has no 'message' field. Data: {message_data}")
                                # Still ACK it to remove from PEL
                                message_ids_to_ack.append(message_id)
                                continue
                            
                            # The callback expects topic (stream_name) and the raw message (bytes or str)
                            # Here, we pass the stream_name as topic and payload as message
                            await callback(stream_key.decode('utf-8'), payload) # Payload is already bytes
                            message_ids_to_ack.append(message_id)
                        except Exception as e:
                            logger.error(f"Error processing message {message_id.decode()} from stream {stream_key.decode()}: {e}", exc_info=True)
                            # Decide on error handling: NACK, requeue, or simply log and move on.
                            # For now, we will still ACK to prevent reprocessing loop for poison pills.
                            # A dead-letter queue mechanism would be better for production.
                            message_ids_to_ack.append(message_id)
                
                if message_ids_to_ack and self._redis_client and self._is_connected:
                    await self._redis_client.xack(stream_name, group_name, *message_ids_to_ack) # type: ignore
                    logger.debug(f"Acknowledged {len(message_ids_to_ack)} messages from stream '{stream_name}'.")

            except asyncio.CancelledError:
                logger.info(f"Listener task for stream '{stream_name}' cancelled.")
                break # Exit loop if task is cancelled
            except RedisError as e:
                logger.error(f"Redis error while listening to stream '{stream_name}': {e}")
                if not self._is_connected: # If connection lost, break
                    logger.warning(f"Redis connection lost. Stopping listener for {stream_name}.")
                    break
                await asyncio.sleep(5) # Wait before retrying on other Redis errors
            except Exception as e:
                logger.error(f"Unexpected error in listener for stream '{stream_name}': {e}", exc_info=True)
                await asyncio.sleep(5) # Wait before retrying
        
        logger.info(f"Listener stopped for {stream_name} / {group_name} / {consumer_name}")

    async def unsubscribe(self, topic: str, **kwargs: Any) -> None:
        """
        Unsubscribes from a Redis Stream by cancelling the listening task.

        Note: This does not remove the consumer from the group or delete the group itself.
        Further cleanup might be needed depending on the application's lifecycle.

        :param topic: The name of the Redis Stream (topic) to unsubscribe from.
        :type topic: str
        :param kwargs: Additional arguments (not currently used by this backend).
        :type kwargs: Any
        """
        if topic in self._subscription_tasks:
            task = self._subscription_tasks.pop(topic)
            if not task.done():
                task.cancel()
                try:
                    await task # Wait for the task to actually cancel
                except asyncio.CancelledError:
                    logger.info(f"Subscription task for topic '{topic}' successfully cancelled and cleaned up.")
                except Exception as e:
                    logger.error(f"Error during cancellation of subscription task for topic '{topic}': {e}")
            else:
                logger.info(f"Subscription task for topic '{topic}' was already done.")
            logger.info(f"Unsubscribed from stream '{topic}'.")
        else:
            logger.warning(f"No active subscription found for topic '{topic}' to unsubscribe from.")

# Need to import uuid for consumer_name generation
import uuid
