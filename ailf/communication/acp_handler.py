"""ACP (Agent Communication Protocol) Handler.

This module will be responsible for managing the sending and receiving of
structured ACP messages, leveraging underlying messaging components from
ailf.messaging (e.g., ZMQ, Redis) for transport.
"""

import logging
import uuid
import json
import asyncio
from typing import Any, Dict, Optional, Union, Callable, Awaitable

from ailf.messaging.base import MessagingBackendBase
from ailf.schemas.acp import (
    ACPMessage, 
    ACPMessageType, 
    ACPMessageHeader,
    StatusUpdatePayload, # Added import
    TaskRequestPayload   # Added import
)
from pydantic import BaseModel, ValidationError # Added ValidationError

logger = logging.getLogger(__name__)

DEFAULT_BROADCAST_TOPIC = "ailf.broadcast"

class ACPHandler:
    """
    Handles the serialization, deserialization, sending, and receiving of ACP messages.
    It acts as a layer on top of a specific messaging backend.
    """

    def __init__(self,
                 agent_id: str,
                 messaging_backend: MessagingBackendBase,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the ACPHandler.

        :param agent_id: The unique identifier of the agent this handler belongs to.
        :type agent_id: str
        :param messaging_backend: An instance of a messaging backend (e.g., RedisStreamsBackend).
        :type messaging_backend: MessagingBackendBase
        :param config: Optional configuration for the ACPHandler.
        :type config: Optional[Dict[str, Any]]
        """
        self.agent_id = agent_id
        self.messaging_backend = messaging_backend
        self.config = config or {}
        self.broadcast_topic = self.config.get("broadcast_topic", DEFAULT_BROADCAST_TOPIC)
        self._message_handlers: Dict[ACPMessageType, Callable[[ACPMessage], Awaitable[None]]] = {}
        self._register_default_handlers()
        logger.info(f"ACPHandler initialized for agent_id: {self.agent_id} using {type(messaging_backend).__name__}")

    def _register_default_handlers(self):
        """Registers default handlers for known message types."""
        self.register_handler(ACPMessageType.STATUS_UPDATE)(self._handle_status_update)
        self.register_handler(ACPMessageType.TASK_REQUEST)(self._handle_task_request)
        logger.debug("Default ACP message handlers for STATUS_UPDATE and TASK_REQUEST registered.")

    def register_handler(self, message_type: ACPMessageType) -> Callable[[Callable[[ACPMessage], Awaitable[None]]], Callable[[ACPMessage], Awaitable[None]]]:
        """
        Decorator to register a handler function for a specific ACPMessageType.

        :param message_type: The ACPMessageType to register the handler for.
        :type message_type: ACPMessageType
        :raises TypeError: If the registered handler is not a coroutine function.
        :raises ValueError: If a handler for the message_type is already registered.

        Example:
            acp_handler = ACPHandler(...)

            @acp_handler.register_handler(ACPMessageType.TASK_REQUEST)
            async def my_task_request_handler(message: ACPMessage):
                # process task request
                pass
        """
        def decorator(handler_func: Callable[[ACPMessage], Awaitable[None]]) -> Callable[[ACPMessage], Awaitable[None]]:
            if not asyncio.iscoroutinefunction(handler_func):
                raise TypeError(f"Handler for {message_type.value} must be an async function (coroutine).")
            if message_type in self._message_handlers:
                raise ValueError(f"Handler for message type {message_type.value} is already registered with {self._message_handlers[message_type].__name__}.")
            
            self._message_handlers[message_type] = handler_func
            logger.info(f"Handler registered for ACPMessageType: {message_type.value} -> {handler_func.__name__}")
            return handler_func
        return decorator

    async def send_message(self,
                           message_type: ACPMessageType,
                           payload_model: BaseModel,
                           recipient_agent_id: Optional[str] = None,
                           conversation_id: Optional[uuid.UUID] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> ACPMessage:
        """
        Constructs and sends an ACP message using the configured messaging backend.

        :param message_type: The type of ACP message to send.
        :type message_type: ACPMessageType
        :param payload_model: The Pydantic model instance for the message payload.
        :type payload_model: BaseModel
        :param recipient_agent_id: The ID of the recipient agent. If None, sends to broadcast topic.
        :type recipient_agent_id: Optional[str]
        :param conversation_id: Optional ID for an ongoing conversation.
        :type conversation_id: Optional[uuid.UUID]
        :param metadata: Optional metadata for the message header.
        :type metadata: Optional[Dict[str, Any]]
        :return: The constructed ACPMessage that was sent.
        :rtype: ACPMessage
        :raises ConnectionError: If the messaging backend is not connected.
        """
        if not self.messaging_backend:
            raise ConnectionError("Messaging backend not configured.")

        header = ACPMessageHeader(
            sender_agent_id=self.agent_id,
            recipient_agent_id=recipient_agent_id,
            message_type=message_type,
            conversation_id=conversation_id,
            metadata=metadata or {}
        )
        acp_message = ACPMessage(header=header, payload=payload_model.model_dump(mode='json'))

        serialized_message = acp_message.model_dump_json()
        
        target_topic = recipient_agent_id if recipient_agent_id else self.broadcast_topic
        
        logger.debug(f"Sending ACP message (ID: {header.message_id}) of type '{message_type.value}' to topic '{target_topic}': {serialized_message[:200]}...")
        
        await self.messaging_backend.publish(topic=target_topic, message=serialized_message)
        logger.info(f"ACP message (ID: {header.message_id}) sent to topic '{target_topic}'.")
        return acp_message

    async def receive_message(self, raw_message: Union[str, bytes]) -> Optional[ACPMessage]:
        """
        Deserializes a raw message (str or bytes) into an ACPMessage object.
        This method would typically be called by a callback from the messaging backend.

        :param raw_message: The raw message received from the transport layer.
        :type raw_message: Union[str, bytes]
        :return: An ACPMessage object if deserialization is successful, None otherwise.
        :rtype: Optional[ACPMessage]
        """
        try:
            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode('utf-8')
            
            acp_message = ACPMessage.model_validate_json(raw_message)
            logger.debug(f"Received and parsed ACP message: {acp_message.header.message_id}")
            return acp_message
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from raw message: {e}. Raw: {raw_message[:200]}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse raw message into ACPMessage: {e}\nRaw message snippet: {str(raw_message)[:500]}")
            return None

    async def setup(self):
        """Set up the ACP handler and its underlying messaging backend."""
        if not self.messaging_backend:
            logger.error("Cannot setup ACPHandler: Messaging backend not provided.")
            return

        await self.messaging_backend.connect()
        logger.info(f"ACPHandler for agent {self.agent_id} connected to messaging backend.")
        
        await self.messaging_backend.subscribe(topic=self.agent_id, callback=self.handle_incoming_raw_message)
        logger.info(f"ACPHandler subscribed to direct topic: {self.agent_id}")
        
        await self.messaging_backend.subscribe(topic=self.broadcast_topic, callback=self.handle_incoming_raw_message)
        logger.info(f"ACPHandler subscribed to broadcast topic: {self.broadcast_topic}")
        logger.info(f"ACPHandler for agent {self.agent_id} setup complete.")

    async def teardown(self):
        """Clean up resources used by the ACP handler."""
        if self.messaging_backend:
            try:
                await self.messaging_backend.unsubscribe(topic=self.agent_id)
                logger.info(f"ACPHandler unsubscribed from direct topic: {self.agent_id}")
                await self.messaging_backend.unsubscribe(topic=self.broadcast_topic)
                logger.info(f"ACPHandler unsubscribed from broadcast topic: {self.broadcast_topic}")
            except Exception as e:
                logger.error(f"Error during unsubscribe for agent {self.agent_id}: {e}")

            await self.messaging_backend.disconnect()
            logger.info(f"ACPHandler for agent {self.agent_id} disconnected from messaging backend.")
        logger.info(f"ACPHandler for agent {self.agent_id} torn down.")

    async def handle_incoming_raw_message(self, topic: str, message_data: Union[str, bytes]):
        """
        Callback for the messaging backend to pass raw messages.
        It deserializes and then dispatches the message.
        """
        logger.debug(f"ACPHandler ({self.agent_id}) received raw message on topic '{topic}'. Type: {type(message_data)}")
        acp_message = await self.receive_message(message_data)
        
        if acp_message:
            if acp_message.header.recipient_agent_id and acp_message.header.recipient_agent_id != self.agent_id:
                logger.debug(f"Message ID {acp_message.header.message_id} on topic '{topic}' is for recipient "
                             f"{acp_message.header.recipient_agent_id}, not this agent ({self.agent_id}). Ignoring.")
                return

            await self.dispatch_message(acp_message)
        else:
            logger.warning(f"Could not parse ACP message received on topic '{topic}'. Data snippet: {str(message_data)[:200]}")

    async def dispatch_message(self, message: ACPMessage) -> None:
        """
        Dispatches a deserialized ACPMessage to the appropriate registered handler method
        based on its type.

        :param message: The ACPMessage to dispatch.
        :type message: ACPMessage
        """
        logger.info(f"Dispatching message type: {message.header.message_type} (ID: {message.header.message_id}) for agent {self.agent_id}")
        handler = self._message_handlers.get(message.header.message_type)

        if handler:
            try:
                logger.debug(f"Found handler {handler.__name__} for message type {message.header.message_type.value}")
                await handler(message)
            except Exception as e:
                logger.error(f"Error executing handler {handler.__name__} for message {message.header.message_id}: {e}", exc_info=True)
        else:
            logger.warning(f"No handler registered for message type: {message.header.message_type.value} (ID: {message.header.message_id}). Message will be ignored by {self.agent_id}.")
            # Optionally, could implement a default handler for unhandled message types.
            # print(f"ACPHandler ({self.agent_id}) no handler for: {message.model_dump_json(indent=2)}")

    # --- Default Message Handler Implementations ---

    async def _handle_status_update(self, message: ACPMessage) -> None:
        """Handles incoming StatusUpdate messages."""
        logger.info(f"Agent {self.agent_id} received StatusUpdate: {message.header.message_id}")
        try:
            # The payload in ACPMessage is a dict, parse it into the specific Pydantic model
            status_payload = StatusUpdatePayload(**message.payload)
            logger.debug(f"StatusUpdate payload parsed: Agent Status - {status_payload.agent_status}, Task ID - {status_payload.current_task_id}")
            # ... further processing with status_payload ...
            print(f"[{self.agent_id}] Received Status Update: Agent is {status_payload.agent_status}")
        except ValidationError as e:
            logger.error(f"Pydantic validation error processing StatusUpdate payload for message {message.header.message_id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error processing StatusUpdate payload for message {message.header.message_id}: {e}", exc_info=True)

    async def _handle_task_request(self, message: ACPMessage) -> None:
        """Handles incoming TaskRequest messages."""
        logger.info(f"Agent {self.agent_id} received TaskRequest: {message.header.message_id}")
        try:
            # The payload in ACPMessage is a dict, parse it into the specific Pydantic model
            task_payload = TaskRequestPayload(**message.payload)
            logger.debug(f"TaskRequest payload parsed: Task Name - {task_payload.task_name}, Priority - {task_payload.priority}")
            # ... further processing, e.g., adding to a task queue ...
            print(f"[{self.agent_id}] Received Task Request: Name - {task_payload.task_name}, Input - {task_payload.task_input}")
        except ValidationError as e:
            logger.error(f"Pydantic validation error processing TaskRequest payload for message {message.header.message_id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error processing TaskRequest payload for message {message.header.message_id}: {e}", exc_info=True)

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown()
