"""Pydantic schemas for the Agent Communication Protocol (ACP)."""

import uuid
from datetime import datetime, timezone # Added timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter # Added TypeAdapter

class ACPMessageType(str, Enum):
    """Enumeration of ACP message types."""
    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    KNOWLEDGE_QUERY = "knowledge_query"
    KNOWLEDGE_RESPONSE = "knowledge_response" # Added for query/response pattern
    INFORMATION_SHARE = "information_share"
    USER_INTERVENTION_REQUEST = "user_intervention_request"
    UX_NEGOTIATION = "ux_negotiation" # Added for UX negotiation
    STATUS_UPDATE = "status_update" # General status or heartbeat
    ERROR_MESSAGE = "error_message" # For protocol or task-level errors
    AGENT_REGISTRATION = "agent_registration"
    AGENT_DEREGISTRATION = "agent_deregistration"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"

class ACPMessageHeader(BaseModel):
    """Header for all ACP messages."""
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this message.")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Identifier for an ongoing conversation or multi-message exchange.")
    sender_agent_id: str = Field(..., description="Unique identifier of the sending agent.")
    recipient_agent_id: Optional[str] = Field(None, description="Unique identifier of the recipient agent. Can be None for broadcast/multicast.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of when the message was created (UTC).") # Changed to timezone.utc
    message_type: ACPMessageType = Field(..., description="The type of ACP message.")
    version: str = Field("1.0", description="ACP version.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata for the message.")

class ACPMessage(BaseModel):
    """Base model for all ACP messages, including the header."""
    header: ACPMessageHeader
    payload: Dict[str, Any] = Field(..., description="The actual content of the message, specific to the message type.")

    class Config:
        validate_assignment = True

# --- Specific ACP Message Payloads and Full Messages ---

# TaskRequest
class TaskRequestPayload(BaseModel):
    task_name: str = Field(..., description="Name or type of the task to be performed.")
    task_input: Dict[str, Any] = Field(default_factory=dict, description="Input parameters for the task.")
    priority: int = Field(10, description="Task priority (lower value means higher priority).")
    deadline: Optional[datetime] = Field(None, description="Suggested deadline for task completion.")

class TaskRequestMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=TASK_REQUEST")
    payload: TaskRequestPayload

# TaskResult
class TaskResultPayload(BaseModel):
    original_message_id: uuid.UUID = Field(..., description="ID of the TaskRequestMessage this result corresponds to.")
    status: str = Field(..., description="Status of the task (e.g., success, failure, in_progress).")
    result: Optional[Any] = Field(None, description="The output or result of the task.")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Details if the task failed.")

class TaskResultMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=TASK_RESULT")
    payload: TaskResultPayload

# KnowledgeQuery
class KnowledgeQueryPayload(BaseModel):
    query_text: str = Field(..., description="The natural language or structured query.")
    query_type: Optional[str] = Field(None, description="Specific type of knowledge being sought (e.g., fact, procedure).")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Context relevant to the query.")

class KnowledgeQueryMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=KNOWLEDGE_QUERY")
    payload: KnowledgeQueryPayload

# KnowledgeResponse
class KnowledgeResponsePayload(BaseModel):
    original_message_id: uuid.UUID = Field(..., description="ID of the KnowledgeQueryMessage this response corresponds to.")
    response_data: Any = Field(..., description="The knowledge or answer being provided.")
    certainty_score: Optional[float] = Field(None, description="Confidence score for the provided response (0.0 to 1.0).")

class KnowledgeResponseMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=KNOWLEDGE_RESPONSE")
    payload: KnowledgeResponsePayload

# InformationShare
class InformationSharePayload(BaseModel):
    data_type: str = Field(..., description="Type or category of the information being shared.")
    data_content: Any = Field(..., description="The actual information content.")
    source_reliability: Optional[float] = Field(None, description="Reliability score of the information source (0.0 to 1.0).")

class InformationShareMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=INFORMATION_SHARE")
    payload: InformationSharePayload

# UserInterventionRequest
class UserInterventionRequestPayload(BaseModel):
    reason: str = Field(..., description="Reason why user intervention is required.")
    urgency: str = Field("medium", description="Urgency of the request (e.g., low, medium, high, critical).")
    required_input_schema: Optional[Dict[str, Any]] = Field(None, description="Schema of the input expected from the user.")

class UserInterventionRequestMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=USER_INTERVENTION_REQUEST")
    payload: UserInterventionRequestPayload

# UXNegotiation
class UXNegotiationPayload(BaseModel):
    """Payload for negotiating UX capabilities and session resumption."""
    session_id: Optional[str] = Field(None, description="Session ID to potentially resume.")
    supported_ux_elements: List[str] = Field(default_factory=list, description="List of UX element types supported by the sender (e.g., text, button, card, image_url).")
    requested_ux_elements: Optional[List[str]] = Field(None, description="Specific UX elements the sender wishes the recipient to use or confirm support for.")
    capabilities: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Key-value pairs describing other relevant capabilities or preferences.")
    negotiation_status: Optional[str] = Field(None, description="Status of the negotiation (e.g., request, response, confirm, reject).")

class UXNegotiationMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=UX_NEGOTIATION")
    payload: UXNegotiationPayload

# StatusUpdate
class StatusUpdatePayload(BaseModel):
    agent_status: str = Field(..., description="Current status of the agent (e.g., idle, busy, error, online, offline).")
    current_task_id: Optional[str] = Field(None, description="ID of the task the agent is currently processing, if any.")
    capabilities: Optional[List[str]] = Field(None, description="List of current capabilities or services offered.")

class StatusUpdateMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=STATUS_UPDATE")
    payload: StatusUpdatePayload

# ErrorMessage
class ErrorMessagePayload(BaseModel):
    """Payload for reporting errors within the ACP communication."""
    error_code: str = Field(..., description="A specific error code identifying the type of error.")
    message: str = Field(..., description="A human-readable message describing the error.")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional additional details or context about the error.")
    original_message_id: Optional[uuid.UUID] = Field(None, description="If the error is related to a specific message, its ID.")

class ErrorMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=ERROR_MESSAGE")
    payload: ErrorMessagePayload

# AgentRegistration
class AgentRegistrationPayload(BaseModel):
    """Payload for an agent to register its presence and capabilities."""
    agent_id: str = Field(..., description="Unique identifier of the agent registering.")
    agent_type: str = Field(..., description="Type or role of the agent (e.g., 'data_processor', 'user_interface').")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities or services the agent offers.")
    address: Optional[str] = Field(None, description="Network address or endpoint where the agent can be reached.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata about the agent.")

class AgentRegistrationMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=AGENT_REGISTRATION")
    payload: AgentRegistrationPayload

# AgentDeregistration
class AgentDeregistrationPayload(BaseModel):
    """Payload for an agent to signal it is going offline or unregistering."""
    agent_id: str = Field(..., description="Unique identifier of the agent deregistering.")
    reason: Optional[str] = Field(None, description="Optional reason for deregistration.")

class AgentDeregistrationMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=AGENT_DEREGISTRATION")
    payload: AgentDeregistrationPayload

# Heartbeat
class HeartbeatPayload(BaseModel):
    """Payload for a heartbeat message to indicate an agent is still active."""
    agent_id: str = Field(..., description="Identifier of the agent sending the heartbeat.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the heartbeat generation.") # Changed to timezone.utc
    load_indicator: Optional[float] = Field(None, description="Optional load indicator (e.g., CPU usage, queue length) from 0.0 to 1.0.")

class HeartbeatMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=HEARTBEAT")
    payload: HeartbeatPayload

# HeartbeatAck
class HeartbeatAckPayload(BaseModel):
    """Payload for acknowledging a heartbeat message."""
    original_message_id: uuid.UUID = Field(..., description="ID of the HeartbeatMessage this acknowledges.")
    responder_agent_id: str = Field(..., description="Identifier of the agent acknowledging the heartbeat.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the acknowledgment.") # Changed to timezone.utc

class HeartbeatAckMessage(ACPMessage):
    header: ACPMessageHeader = Field(..., description="Message header with message_type=HEARTBEAT_ACK")
    payload: HeartbeatAckPayload

# Union type for easy parsing of any ACP message
AnyACPMessage = Union[
    TaskRequestMessage,
    TaskResultMessage,
    KnowledgeQueryMessage,
    KnowledgeResponseMessage,
    InformationShareMessage,
    UserInterventionRequestMessage,
    UXNegotiationMessage,
    StatusUpdateMessage,
    ErrorMessage,
    AgentRegistrationMessage,
    AgentDeregistrationMessage,
    HeartbeatMessage,
    HeartbeatAckMessage
]

