"""Base class and common utilities for registry clients."""
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict

from ailf.schemas.agent import AgentDescription
from ailf.schemas.tooling import ToolDescription

class RegistryError(Exception):
    """Custom exception for registry client errors."""
    pass

class BaseRegistryClient(ABC):
    """
    Abstract base class for an agent and tool registry client.
    Defines the interface for registering, discovering, and managing
    agent and tool descriptions in a registry.
    """

    def __init__(self, registry_url: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the base registry client.

        :param registry_url: The base URL or connection string for the registry service.
        :type registry_url: Optional[str]
        :param config: Optional configuration dictionary for the client.
        :type config: Optional[Dict[str, Any]]
        """
        self.registry_url = registry_url
        self.config = config or {}

    # --- Agent Registry Methods ---

    @abstractmethod
    async def register_agent(self, agent_description: AgentDescription) -> str:
        """
        Registers an agent with the registry.

        :param agent_description: The description of the agent to register.
        :type agent_description: AgentDescription
        :return: The unique ID assigned to the agent by the registry.
        :rtype: str
        :raises RegistryError: If registration fails.
        """
        pass

    @abstractmethod
    async def discover_agents(
        self,
        query: Optional[str] = None,
        capability_names: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentDescription]:
        """
        Discovers agents based on various criteria.

        :param query: A natural language query to search for agents (e.g., by name, description).
        :type query: Optional[str]
        :param capability_names: A list of capability names the agent must possess.
        :type capability_names: Optional[List[str]]
        :param agent_type: Filter by a specific agent type.
        :type agent_type: Optional[str]
        :param limit: Maximum number of agent descriptions to return.
        :type limit: int
        :return: A list of matching agent descriptions.
        :rtype: List[AgentDescription]
        :raises RegistryError: If discovery fails.
        """
        pass

    @abstractmethod
    async def get_agent_description(self, agent_id: str) -> Optional[AgentDescription]:
        """
        Retrieves the description of a specific agent by its ID.

        :param agent_id: The unique ID of the agent.
        :type agent_id: str
        :return: The agent description if found, else None.
        :rtype: Optional[AgentDescription]
        :raises RegistryError: If retrieval fails for reasons other than not found.
        """
        pass

    @abstractmethod
    async def update_agent_description(self, agent_id: str, agent_description: AgentDescription) -> bool:
        """
        Updates the description of an existing agent.

        :param agent_id: The ID of the agent to update.
        :type agent_id: str
        :param agent_description: The new description for the agent.
        :type agent_description: AgentDescription
        :return: True if the update was successful, False otherwise.
        :rtype: bool
        :raises RegistryError: If the update fails.
        """
        pass

    @abstractmethod
    async def deregister_agent(self, agent_id: str) -> bool:
        """
        Removes an agent from the registry.

        :param agent_id: The ID of the agent to deregister.
        :type agent_id: str
        :return: True if deregistration was successful, False otherwise.
        :rtype: bool
        :raises RegistryError: If deregistration fails.
        """
        pass

    # --- Tool Registry Methods ---

    @abstractmethod
    async def register_tool(self, tool_description: ToolDescription) -> str:
        """
        Registers a tool with the registry.

        :param tool_description: The description of the tool to register.
        :type tool_description: ToolDescription
        :return: The unique ID or name assigned to the tool by the registry.
        :rtype: str
        :raises RegistryError: If registration fails.
        """
        pass

    @abstractmethod
    async def discover_tools(
        self,
        query: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[ToolDescription]:
        """
        Discovers tools based on various criteria.

        :param query: A natural language query to search for tools (e.g., by name, description, keywords).
        :type query: Optional[str]
        :param tool_names: A list of specific tool names to retrieve.
        :type tool_names: Optional[List[str]]
        :param categories: A list of categories the tool must belong to.
        :type categories: Optional[List[str]]
        :param limit: Maximum number of tool descriptions to return.
        :type limit: int
        :return: A list of matching tool descriptions.
        :rtype: List[ToolDescription]
        :raises RegistryError: If discovery fails.
        """
        pass

    @abstractmethod
    async def get_tool_description(self, tool_name_or_id: str) -> Optional[ToolDescription]:
        """
        Retrieves the description of a specific tool by its name or ID.

        :param tool_name_or_id: The unique name or ID of the tool.
        :type tool_name_or_id: str
        :return: The tool description if found, else None.
        :rtype: Optional[ToolDescription]
        :raises RegistryError: If retrieval fails for reasons other than not found.
        """
        pass

    @abstractmethod
    async def update_tool_description(self, tool_name_or_id: str, tool_description: ToolDescription) -> bool:
        """
        Updates the description of an existing tool.

        :param tool_name_or_id: The name or ID of the tool to update.
        :type tool_name_or_id: str
        :param tool_description: The new description for the tool.
        :type tool_description: ToolDescription
        :return: True if the update was successful, False otherwise.
        :rtype: bool
        :raises RegistryError: If the update fails.
        """
        pass

    @abstractmethod
    async def deregister_tool(self, tool_name_or_id: str) -> bool:
        """
        Removes a tool from the registry.

        :param tool_name_or_id: The name or ID of the tool to deregister.
        :type tool_name_or_id: str
        :return: True if deregistration was successful, False otherwise.
        :rtype: bool
        :raises RegistryError: If deregistration fails.
        """
        pass

    # --- Health/Status Method (Optional but Recommended) ---
    async def check_health(self) -> Dict[str, Any]:
        """
        Checks the health or status of the registry service.
        Default implementation, can be overridden by subclasses.

        :return: A dictionary containing health status information.
        :rtype: Dict[str, Any]
        """
        return {"status": "unknown", "message": "Health check not implemented by this client."}
