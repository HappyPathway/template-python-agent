"""Pydantic schemas for AILF interaction management."""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

class MessageModality(str, Enum):
    """Enumeration of possible message modalities."""
    TEXT = "text"
    STRUCTURED_DATA = "structured_data"
    BINARY = "binary"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTI_MODAL_CONTAINER = "multi_modal_container" # For messages that explicitly contain multiple modalities

class StandardMessageHeader(BaseModel):
    """
    A standard header for messages within the interaction module.
    This can be used by interaction managers and adapters.
    """
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for this message.")
    correlation_id: Optional[uuid.UUID] = Field(None, description="Identifier to correlate related messages, e.g., request-response.")
    session_id: Optional[str] = Field(None, description="Identifier for the session this message belongs to.")
    user_id: Optional[str] = Field(None, description="Identifier for the user involved, if applicable.")
    source_system: Optional[str] = Field(None, description="Identifier of the system/agent/component that originated the message.")
    target_system: Optional[str] = Field(None, description="Identifier of the intended recipient system/agent/component.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of message creation (UTC).")
    modality: MessageModality = Field(..., description="The primary modality of the message payload.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata for the message.")

class TextMessagePayload(BaseModel):
    """Payload for a simple text message."""
    text: str = Field(..., description="The text content of the message.")

class TextMessage(BaseModel):
    """A message primarily conveying text."""
    header: StandardMessageHeader = Field(..., default_factory=lambda: StandardMessageHeader(modality=MessageModality.TEXT))
    payload: TextMessagePayload

class StructuredDataMessagePayload(BaseModel):
    """Payload for a message carrying structured data."""
    data: Dict[str, Any] = Field(..., description="The structured data content, represented as a dictionary.")
    schema_identifier: Optional[str] = Field(None, description="Optional identifier for the schema of the data (e.g., Pydantic model name, URI).")

class StructuredDataMessage(BaseModel):
    """A message primarily conveying structured data."""
    header: StandardMessageHeader = Field(..., default_factory=lambda: StandardMessageHeader(modality=MessageModality.STRUCTURED_DATA))
    payload: StructuredDataMessagePayload

class BinaryMessagePayload(BaseModel):
    """Payload for a message carrying binary data."""
    content_type: str = Field(..., description="MIME type of the binary data (e.g., application/octet-stream, image/jpeg).")
    data: bytes = Field(..., description="The binary data.")
    filename: Optional[str] = Field(None, description="Optional filename associated with the binary data.")

class BinaryMessage(BaseModel):
    """A message primarily conveying binary data."""
    header: StandardMessageHeader = Field(..., default_factory=lambda: StandardMessageHeader(modality=MessageModality.BINARY))
    payload: BinaryMessagePayload

# Example for a multi-modal part, to be used within a container
class MultiModalPart(BaseModel):
    """Represents a single part of a multi-modal message."""
    part_id: str = Field(..., description="Identifier for this part within the multi-modal message.")
    modality: MessageModality = Field(..., description="Modality of this part.")
    content_type: Optional[str] = Field(None, description="MIME type if binary or specific text format (e.g., text/markdown).")
    data: Union[str, bytes, Dict[str, Any]] = Field(..., description="The actual content of this part.")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MultiModalMessagePayload(BaseModel):
    """Payload for a message composed of multiple parts with different modalities."""
    parts: List[MultiModalPart] = Field(..., description="A list of message parts.")
    primary_focus_part_id: Optional[str] = Field(None, description="Optional ID of the part that represents the primary focus or content.")

class MultiModalMessage(BaseModel):
    """A message explicitly designed to carry multiple modalities."""
    header: StandardMessageHeader = Field(..., default_factory=lambda: StandardMessageHeader(modality=MessageModality.MULTI_MODAL_CONTAINER))
    payload: MultiModalMessagePayload


# A generic message type that can be one of the above
# This is useful for interaction managers or handlers that can process various types.
AnyInteractionMessage = Union[
    TextMessage,
    StructuredDataMessage,
    BinaryMessage,
    MultiModalMessage
]
