"""Example MCP Server using BaseMCP

This module demonstrates how to build an MCP server using the BaseMCP class.
It includes examples of registering tools, resources, and prompts.
"""
import asyncio
from typing import List, Optional

from ailf.base_mcp import BaseMCP, Context
from ailf.schemas.mcp import AssistantMessage, UserMessage

# Create a simple MCP server
mcp = BaseMCP(
    name="DemoServer",
    instructions="This is a demonstration of the BaseMCP functionality."
)


# Register a simple tool
@mcp.tool(
    description="Add two numbers together",
    tags={"math", "basic"}
)
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


# Register a tool with context
@mcp.tool()
async def greet(ctx: Context, name: str) -> str:
    """Greet a user by name."""
    await ctx.info(f"Greeting {name}")
    return f"Hello, {name}!"


# Register a resource with static content
@mcp.resource("data://greeting-template")
def get_greeting_template() -> str:
    """Get a template for greeting messages."""
    return "Hello, {name}! Welcome to {service}."


# Register a resource template with parameters
@mcp.resource("user://{user_id}/profile")
def get_user_profile(user_id: int) -> dict:
    """Get a user's profile information."""
    # In a real implementation, this would query a database
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "joined": "2025-01-01"
    }


# Register a simple prompt
@mcp.prompt()
def customer_inquiry(topic: str) -> UserMessage:
    """Create a prompt for a customer inquiry on a specific topic."""
    return UserMessage(content=f"I have a question about {topic}. Can you help me?")


# Register a prompt that returns multiple messages
@mcp.prompt(name="help_request")
def create_help_request(
    product: str,
    issue: str,
    priority: str = "medium"
) -> List[UserMessage]:
    """Create a sequence of messages for a help request."""
    return [
        UserMessage(content=f"I need help with my {product}."),
        UserMessage(content=f"The issue I'm experiencing is: {issue}"),
        UserMessage(content=f"This is a {priority} priority request.")
    ]


async def list_components():
    """List all registered components."""
    print(f"\n{mcp.name} Components:")
    print("=" * 40)

    # List tools
    tools = await mcp.get_tools()
    print(f"\nTools ({len(tools)}):")
    for name, tool in tools.items():
        tags = ", ".join(tool.tags) if tool.tags else "none"
        print(f"  - {name}: {tool.description} (Tags: {tags})")

    # List resources
    resources = await mcp.get_resources()
    print(f"\nResources ({len(resources)}):")
    for uri, resource in resources.items():
        template_info = " (template)" if resource.is_template else ""
        print(f"  - {uri}{template_info}: {resource.description}")

    # List prompts
    prompts = await mcp.get_prompts()
    print(f"\nPrompts ({len(prompts)}):")
    for name, prompt in prompts.items():
        print(f"  - {name}: {prompt.description}")


# Run the server if executed as a script
if __name__ == "__main__":
    # Print all registered components
    asyncio.run(list_components())

    # Start the server
    mcp.run(transport="stdio")
