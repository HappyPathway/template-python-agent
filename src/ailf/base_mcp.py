# filepath: /workspaces/template-python-dev/ailf/base_mcp.py
"""MCP Server foundation for building AI agents with tools and resources.

This module provides the base MCP (Model Context Protocol) server implementation
for creating AI assistants with tools, resources, and prompts.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, Set, AsyncGenerator
from pydantic import BaseModel, Field
import inspect
import json
import logging
import asyncio
from uuid import uuid4

# Setup logging
logger = logging.getLogger(__name__)

class MCPError(Exception):
    """Base exception for MCP errors."""
    pass

class DuplicateComponentError(MCPError):
    """Raised when attempting to register a component with a duplicate name."""
    pass

class MCPComponentType(str, Enum):
    """Type of MCP component."""
    TOOL = "tool"
    RESOURCE = "resource" 
    PROMPT = "prompt"

class MCPComponent(BaseModel):
    """Base class for MCP components (tools, resources, prompts)."""
    name: str
    description: str
    component_type: MCPComponentType
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Tool(MCPComponent):
    """MCP tool registration."""
    component_type: MCPComponentType = MCPComponentType.TOOL
    function: Callable
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
class Resource(MCPComponent):
    """MCP resource registration."""
    component_type: MCPComponentType = MCPComponentType.RESOURCE
    content: Any
    
class Prompt(MCPComponent):
    """MCP prompt registration."""
    component_type: MCPComponentType = MCPComponentType.PROMPT
    template: str
    variables: Dict[str, str] = Field(default_factory=dict)

class MCPSettings(BaseModel):
    """Settings for the MCP server."""
    debug: bool = False
    log_level: str = "INFO"

class Context:
    """Request context for MCP operations."""
    
    def __init__(self, server, request_id=None):
        self.server = server
        self.request_id = request_id or str(uuid4())
        self.state = {}
    
    def error(self, message: str, code: str = "server_error") -> Exception:
        """Create an error response.
        
        Args:
            message: Error message
            code: Error code
            
        Returns:
            Exception to be raised
        """
        return MCPError(f"{code}: {message}")

class BaseMCP:
    """Base MCP server implementation."""
    
    def __init__(
        self,
        name: str,
        instructions: str,
        settings: Optional[MCPSettings] = None
    ):
        """Initialize MCP server.
        
        Args:
            name: Server name
            instructions: System instructions
            settings: Optional server settings
        """
        self.name = name
        self.instructions = instructions
        self.settings = settings or MCPSettings()
        
        # Component registries
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.prompts: Dict[str, Prompt] = {}
        
        # State
        self.state = {}
        
        logger.info(f"MCP Server '{name}' initialized")
    
    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """Register a function as a tool.
        
        Args:
            name: Optional tool name (defaults to function name)
            description: Optional tool description (defaults to function docstring)
            
        Returns:
            Decorator function
        """
        def decorator(func):
            nonlocal name, description
            
            # Use function info if not provided
            tool_name = name or func.__name__
            tool_description = description or (func.__doc__ or "").strip()
            
            # Get function signature for parameters
            sig = inspect.signature(func)
            params = {
                k: v.default if v.default is not inspect.Parameter.empty else None
                for k, v in sig.parameters.items()
                if k != "self" and k != "ctx"  # Skip self and ctx
            }
            
            # Register the tool
            self._register_tool(
                name=tool_name,
                description=tool_description,
                function=func,
                parameters=params
            )
            
            return func
        return decorator
    
    def _register_tool(self, name: str, description: str, function: Callable, parameters: Dict[str, Any] = None):
        """Register a tool with the server.
        
        Args:
            name: Tool name
            description: Tool description
            function: Tool function
            parameters: Tool parameters
        """
        if name in self.tools:
            raise DuplicateComponentError(f"Tool '{name}' already exists")
            
        tool = Tool(
            name=name,
            description=description,
            function=function,
            parameters=parameters or {}
        )
        
        self.tools[name] = tool
        logger.info(f"Registered tool: {name}")
    
    def resource(self, name: str, content: Any, description: str):
        """Register a resource with the server.
        
        Args:
            name: Resource name
            content: Resource content
            description: Resource description
        """
        if name in self.resources:
            raise DuplicateComponentError(f"Resource '{name}' already exists")
            
        resource = Resource(
            name=name,
            description=description,
            content=content
        )
        
        self.resources[name] = resource
        logger.info(f"Registered resource: {name}")
    
    def prompt(self, name: str, template: str, description: str, variables: Dict[str, str] = None):
        """Register a prompt template with the server.
        
        Args:
            name: Prompt name
            template: Prompt template
            description: Prompt description
            variables: Prompt variables with descriptions
        """
        if name in self.prompts:
            raise DuplicateComponentError(f"Prompt '{name}' already exists")
            
        prompt = Prompt(
            name=name,
            description=description,
            template=template,
            variables=variables or {}
        )
        
        self.prompts[name] = prompt
        logger.info(f"Registered prompt: {name}")
    
    async def invoke_tool(self, ctx: Context, tool_name: str, **kwargs) -> Any:
        """Invoke a tool by name.
        
        Args:
            ctx: Request context
            tool_name: Tool name
            kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        if tool_name not in self.tools:
            raise MCPError(f"Tool '{tool_name}' not found")
            
        tool = self.tools[tool_name]
        
        try:
            # Call the tool function
            if inspect.iscoroutinefunction(tool.function):
                if 'ctx' in inspect.signature(tool.function).parameters:
                    result = await tool.function(ctx=ctx, **kwargs)
                else:
                    result = await tool.function(**kwargs)
            else:
                if 'ctx' in inspect.signature(tool.function).parameters:
                    result = tool.function(ctx=ctx, **kwargs)
                else:
                    result = tool.function(**kwargs)
                    
            return result
        except Exception as e:
            logger.error(f"Error invoking tool '{tool_name}': {str(e)}")
            raise MCPError(f"Tool execution error: {str(e)}")
