"""MCP Schema Models

This module defines data models for MCP server configurations, components, and metadata.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, ConfigDict, Field


class DuplicateHandling(str, Enum):
    """How to handle duplicate component registrations."""
    WARN = "warn"      # Log a warning and replace existing component
    ERROR = "error"    # Raise an error
    REPLACE = "replace"  # Silently replace existing component
    IGNORE = "ignore"  # Keep existing component, ignore new one


class MCPSettings(BaseModel):
    """MCP server configuration settings.

    Attributes:
        host: Host address for SSE transport
        port: Port number for SSE transport
        log_level: Logging level
        on_duplicate_tools: How to handle duplicate tool registrations
        on_duplicate_resources: How to handle duplicate resource registrations
        on_duplicate_prompts: How to handle duplicate prompt registrations
        tool_serializer: Custom serialization function for tool return values
    """
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    on_duplicate_tools: DuplicateHandling = DuplicateHandling.WARN
    on_duplicate_resources: DuplicateHandling = DuplicateHandling.WARN
    on_duplicate_prompts: DuplicateHandling = DuplicateHandling.WARN
    # Function to serialize tool return values
    tool_serializer: Optional[Any] = None

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )


class ToolAnnotations(BaseModel):
    """Annotations for tools that communicate behavior to client applications.

    Attributes:
        title: Display name for user interfaces
        readOnlyHint: Indicates if the tool only reads without making changes
        destructiveHint: For non-readonly tools, signals if changes are destructive
        idempotentHint: Indicates if repeated identical calls have the same effect
        openWorldHint: Specifies if the tool interacts with external systems
    """
    title: Optional[str] = None
    readOnlyHint: Optional[bool] = None
    destructiveHint: Optional[bool] = None
    idempotentHint: Optional[bool] = None
    openWorldHint: Optional[bool] = None

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow"  # Allow custom annotations
    )


class ToolMetadata(BaseModel):
    """Metadata for a registered tool.

    Attributes:
        name: Name of the tool
        description: Human-readable description of the tool
        tags: List of tags for categorizing the tool
        annotations: Additional information about the tool's behavior
        schema: JSON schema for the tool's parameters (derived from function signature)
    """
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    annotations: Dict[str, Any] = Field(default_factory=dict)
    schema: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )


class ResourceMetadata(BaseModel):
    """Metadata for a registered resource.

    Attributes:
        uri: URI for accessing this resource
        description: Human-readable description of the resource
        tags: List of tags for categorizing the resource
        is_template: Whether this resource is a template with parameters
        parameters: List of parameters for template resources
    """
    uri: str
    description: str
    tags: List[str] = Field(default_factory=list)
    is_template: bool = False
    parameters: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )


class PromptMetadata(BaseModel):
    """Metadata for a registered prompt.

    Attributes:
        name: Name of the prompt
        description: Human-readable description of the prompt
        tags: List of tags for categorizing the prompt
        schema: JSON schema for the prompt's parameters (derived from function signature)
    """
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    schema: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )


class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A message in a conversation.

    Attributes:
        role: Role of the message sender (user, assistant, system)
        content: Text content of the message
    """
    role: MessageRole
    content: str

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )


class UserMessage(Message):
    """A message from the user."""
    role: MessageRole = MessageRole.USER


class AssistantMessage(Message):
    """A message from the assistant."""
    role: MessageRole = MessageRole.ASSISTANT


class SystemMessage(Message):
    """A system message providing instructions or context."""
    role: MessageRole = MessageRole.SYSTEM
