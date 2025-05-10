"""Handles sending and receiving of Agent Communication Protocol (ACP) messages."""
import json
import uuid
from typing import Callable, Dict, Optional, Type, Union, Any, Awaitable

from pydantic import BaseModel, TypeAdapter, ValidationError

from ailf.messaging.base import BaseMessageClient
from ailf.schemas.acp import (
    ACPMessage, 
    AnyACPMessage, 
    ACPMessageType,
    ACPMessageHeader,
    TaskRequestMessage, TaskRequestPayload,
    KnowledgeQueryMessage, KnowledgeQueryPayload,
)

# Initialize a TypeAdapter for parsing any valid ACP message
AnyACPMessageAdapter = TypeAdapter(AnyACPMessage)

class ACPHandler:
    """
    Manages the serialization, deserialization, sending, and receiving of ACP messages
    over a provided messaging client.
    """

    def __init__(self, message_client: BaseMessageClient, agent_id: str):
        """
        Initializes the ACPHandler.

        :param message_client: An instance of a class derived from BaseMessageClient,
                               used for the actual message transport.
        :type message_client: BaseMessageClient
        :param agent_id: The unique identifier of the agent using this handler.
                         This will be used as the sender_agent_id in outgoing messages.
        :type agent_id: str
        """
        self.message_client = message_client
        self.agent_id = agent_id
        self.pending_requests: Dict[uuid.UUID, Callable[[AnyACPMessage], None]] = {}

    async def send_message(
        self,
        payload_model: BaseModel, 
        message_type: ACPMessageType,
        recipient_agent_id: Optional[str] = None,
        conversation_id: Optional[uuid.UUID] = None,
        target_destination: Optional[str] = None, 
        custom_header_fields: Optional[Dict[str, Any]] = None,
        specific_message_class: Optional[Type[AnyACPMessage]] = None 
    ) -> uuid.UUID:
        """
        Constructs, serializes, and sends an ACP message.

        :param payload_model: The Pydantic model instance representing the message payload.
        :param message_type: The type of ACP message to send.
        :param recipient_agent_id: The ID of the recipient agent, if known.
        :param conversation_id: Optional ID to group related messages.
        :param target_destination: The destination for the message (e.g., a topic or queue).
        :param custom_header_fields: Optional dictionary to add/override fields in the ACPMessageHeader.
        :param specific_message_class: Optional specific ACP message class (e.g., TaskRequestMessage)
                                     for stricter validation before sending. If None, a generic
                                     ACPMessage structure is used for serialization.
        :return: The UUID of the sent message.
        :raises ValueError: If target_destination is not provided and message_client requires it.
        :raises ValidationError: If specific_message_class is provided and validation fails.
        """
        header_data = {
            "sender_agent_id": self.agent_id,
            "message_type": message_type,
            "recipient_agent_id": recipient_agent_id,
            "conversation_id": conversation_id,
            **(custom_header_fields or {})
        }
        header = ACPMessageHeader(**header_data)

        if specific_message_class:
            try:
                message_to_send = specific_message_class(header=header, payload=payload_model)
                message_json = message_to_send.model_dump_json().encode('utf-8')
            except ValidationError as e:
                print(f"[ACPHandler] ERROR: Validation failed for {specific_message_class.__name__}: {e}")
                raise
        else:
            acp_message_data = {
                "header": header.model_dump(),
                "payload": payload_model.model_dump()
            }
            message_json = json.dumps(acp_message_data).encode('utf-8')

        if target_destination is None:
            print(f"[ACPHandler] Warning: target_destination is None. Sending might rely on message_client's default behavior.")

        await self.message_client.publish(message_json, destination_topic=target_destination)
        return header.message_id

    async def send_request_and_await_response(
        self,
        payload_model: BaseModel,
        message_type: ACPMessageType,
        recipient_agent_id: str,
        target_destination: str,
        timeout_seconds: float = 30.0,
        specific_message_class: Optional[Type[AnyACPMessage]] = None
    ) -> AnyACPMessage:
        """
        Sends a request message and waits for a corresponding response.

        :param payload_model: The Pydantic model for the request payload.
        :param message_type: The ACPMessageType of the request.
        :param recipient_agent_id: The ID of the recipient agent.
        :param target_destination: The messaging topic/queue for the recipient.
        :param timeout_seconds: How long to wait for a response.
        :param specific_message_class: Optional specific ACP message class for the request.
        :return: The response ACP message.
        :raises asyncio.TimeoutError: If the response is not received within the timeout.
        """
        import asyncio

        conversation_id = uuid.uuid4()
        future = asyncio.Future()
        self.pending_requests[conversation_id] = lambda response_msg: future.set_result(response_msg)

        try:
            await self.send_message(
                payload_model=payload_model,
                message_type=message_type,
                recipient_agent_id=recipient_agent_id,
                conversation_id=conversation_id,
                target_destination=target_destination,
                specific_message_class=specific_message_class
            )
            
            return await asyncio.wait_for(future, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            print(f"[ACPHandler] Timeout waiting for response to conversation {conversation_id}")
            raise
        finally:
            self.pending_requests.pop(conversation_id, None)

    def process_incoming_message(self, raw_message_data: bytes) -> Optional[AnyACPMessage]:
        """
        Deserializes and validates an incoming raw message.
        If the message is a response to a pending request, it resolves the future.
        """
        try:
            parsed_message = AnyACPMessageAdapter.validate_json(raw_message_data)
            
            if parsed_message.header.conversation_id and parsed_message.header.conversation_id in self.pending_requests:
                callback = self.pending_requests.pop(parsed_message.header.conversation_id)
                callback(parsed_message)
            
            return parsed_message
        except ValidationError as e:
            print(f"[ACPHandler] ERROR: Failed to validate incoming ACP message: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[ACPHandler] ERROR: Failed to decode incoming JSON message: {e}")
            return None
