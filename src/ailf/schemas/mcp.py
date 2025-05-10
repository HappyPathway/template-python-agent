"""MCP schema models.

This module provides Pydantic models for MCP server configurations and interactions.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, ConfigDict, Field

from ailf.base_mcp import (
    MCPSettings,
    MCPComponent,
    MCPComponentType,
    Tool,
    Resource, 
    Prompt,
    Context
)

class DuplicateHandling(str, Enum):
    """How to handle duplicate component registrations."""
    WARN = "warn"      # Log a warning and replace existing component
    ERROR = "error"    # Raise an error
    REPLACE = "replace"  # Silently replace existing component
    IGNORE = "ignore"  # Keep existing component, ignore new one


class ToolAnnotations(BaseModel):
    """Annotations for tools that communicate behavior to client applications."""
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
    """Metadata for a registered tool."""
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
    """Metadata for a registered resource."""
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
    """Metadata for a registered prompt."""
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
    """A message in a conversation."""
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


__all__ = [
    # From base_mcp
    "MCPSettings",
    "MCPComponent",
    "MCPComponentType",
    "Tool",
    "Resource",
    "Prompt",
    "Context",
    
    # MCP schema classes
    "DuplicateHandling",
    "ToolAnnotations",
    "ToolMetadata",
    "ResourceMetadata",
    "PromptMetadata",
    "MessageRole",
    "Message",
    "UserMessage",
    "AssistantMessage",
    "SystemMessage"
]
