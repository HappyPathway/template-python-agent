"""HTTP-based client for interacting with an Agent and Tool Registry."""
import httpx # Using httpx for async requests
from typing import List, Optional, Any, Dict

from ailf.schemas.agent import AgentDescription
from ailf.schemas.tooling import ToolDescription
from .base import BaseRegistryClient, RegistryError

class HTTPRegistryClient(BaseRegistryClient):
    """
    An HTTP-based client for an agent and tool registry.
    Assumes a RESTful API for the registry service.
    """

    def __init__(self, registry_url: str, api_key: Optional[str] = None, timeout: float = 10.0, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the HTTPRegistryClient.

        :param registry_url: The base URL of the registry service (e.g., "http://localhost:8000/registry").
        :type registry_url: str
        :param api_key: Optional API key for authentication with the registry.
        :type api_key: Optional[str]
        :param timeout: Timeout in seconds for HTTP requests.
        :type timeout: float
        :param config: Optional additional configuration for the client or httpx.AsyncClient.
        :type config: Optional[Dict[str, Any]]
        """
        super().__init__(registry_url, config)
        self.api_key = api_key
        self.timeout = timeout
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        client_config = self.config.get("httpx_client_config", {})
        self.http_client = httpx.AsyncClient(base_url=self.registry_url, headers=headers, timeout=self.timeout, **client_config)

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> httpx.Response:
        """
        Helper method to make HTTP requests to the registry.
        """
        try:
            response = await self.http_client.request(method, endpoint, params=params, json=json_data)
            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses
            return response
        except httpx.HTTPStatusError as e:
            # Log error: print(f"HTTP error {e.response.status_code} for {e.request.url}: {e.response.text}")
            raise RegistryError(f"Registry API error: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            # Log error: print(f"Request error for {e.request.url}: {str(e)}")
            raise RegistryError(f"Registry request failed: {str(e)}") from e

    # --- Agent Registry Methods ---

    async def register_agent(self, agent_description: AgentDescription) -> str:
        response = await self._request("POST", "/agents", json_data=agent_description.model_dump(exclude_none=True))
        # Assuming the registry returns a JSON with {"agent_id": "new_id"}
        return response.json().get("agent_id", agent_description.agent_id) 

    async def discover_agents(
        self,
        query: Optional[str] = None,
        capability_names: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentDescription]:
        params = {"limit": limit}
        if query: params["query"] = query
        if capability_names: params["capabilities"] = ",".join(capability_names) # Assuming CSV for list params
        if agent_type: params["agent_type"] = agent_type
        
        response = await self._request("GET", "/agents", params=params)
        return [AgentDescription(**item) for item in response.json().get("agents", [])]

    async def get_agent_description(self, agent_id: str) -> Optional[AgentDescription]:
        try:
            response = await self._request("GET", f"/agents/{agent_id}")
            return AgentDescription(**response.json())
        except RegistryError as e:
            if "404" in str(e): # Basic check for 404 Not Found
                return None
            raise

    async def update_agent_description(self, agent_id: str, agent_description: AgentDescription) -> bool:
        await self._request("PUT", f"/agents/{agent_id}", json_data=agent_description.model_dump(exclude_none=True))
        return True # Assumes 200/204 on success, error raised otherwise

    async def deregister_agent(self, agent_id: str) -> bool:
        await self._request("DELETE", f"/agents/{agent_id}")
        return True # Assumes 204 on success

    # --- Tool Registry Methods ---

    async def register_tool(self, tool_description: ToolDescription) -> str:
        response = await self._request("POST", "/tools", json_data=tool_description.model_dump(exclude_none=True))
        # Assuming the registry returns a JSON with {"tool_id": "new_id"} or {"name": "tool_name"}
        return response.json().get("tool_id", tool_description.name)

    async def discover_tools(
        self,
        query: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[ToolDescription]:
        params = {"limit": limit}
        if query: params["query"] = query
        if tool_names: params["names"] = ",".join(tool_names)
        if categories: params["categories"] = ",".join(categories)
        
        response = await self._request("GET", "/tools", params=params)
        return [ToolDescription(**item) for item in response.json().get("tools", [])]

    async def get_tool_description(self, tool_name_or_id: str) -> Optional[ToolDescription]:
        try:
            response = await self._request("GET", f"/tools/{tool_name_or_id}")
            return ToolDescription(**response.json())
        except RegistryError as e:
            if "404" in str(e): # Basic check for 404 Not Found
                return None
            raise

    async def update_tool_description(self, tool_name_or_id: str, tool_description: ToolDescription) -> bool:
        await self._request("PUT", f"/tools/{tool_name_or_id}", json_data=tool_description.model_dump(exclude_none=True))
        return True

    async def deregister_tool(self, tool_name_or_id: str) -> bool:
        await self._request("DELETE", f"/tools/{tool_name_or_id}")
        return True

    # --- Health/Status Method ---
    async def check_health(self) -> Dict[str, Any]:
        """
        Checks the health of the HTTP registry service.
        Assumes a /health endpoint on the registry.
        """
        try:
            response = await self.http_client.get("/health") # Use http_client directly for health, might not need auth
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "details": f"HTTP error {e.response.status_code}: {e.response.text}"}
        except httpx.RequestError as e:
            return {"status": "unreachable", "details": str(e)}
        except Exception as e:
            return {"status": "error", "details": f"Unexpected error: {str(e)}"}

    async def close(self):
        """Closes the underlying HTTP client session."""
        await self.http_client.aclose()
