"""Pydantic schemas for ailf.routing."""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# Assuming StandardMessage might be similar to BaseMessage from ailf.schemas.interaction
# If a specific StandardMessage is needed, it should be defined, possibly importing BaseMessage
from ailf.schemas.interaction import AnyInteractionMessage # Changed from BaseMessage

class DelegatedTaskMessage(BaseModel):
    """Message for delegating a task to another agent or worker."""
    task_id: str = Field(description="Unique ID for the delegated task.")
    target_agent_id: Optional[str] = Field(default=None, description="ID of the target agent/worker.")
    task_name: str = Field(description="Name or type of the task to be performed.")
    task_input: Dict[str, Any] = Field(default_factory=dict, description="Input parameters for the task.")
    # callback_info: Optional[Dict[str, Any]] = Field(default=None, description="Information for callback if needed.")
    source_agent_id: Optional[str] = Field(default=None, description="ID of the agent delegating the task.")

class TaskResultMessage(BaseModel):
    """Message containing the result of a delegated task."""
    task_id: str = Field(description="Unique ID of the task this result corresponds to.")
    status: str = Field(description="Status of the task (e.g., completed, failed, in_progress).")
    result: Optional[Any] = Field(default=None, description="The output or result of the task.")
    error_message: Optional[str] = Field(default=None, description="Error message if the task failed.")

class RouteDecision(BaseModel):
    """Represents a decision made by the AgentRouter."""
    target_handler: Optional[str] = Field(default=None, description="Name of the internal handler or function to route to.")
    target_agent_id: Optional[str] = Field(default=None, description="ID of another agent to delegate/forward the request to.")
    # action: str # e.g., "handle_internally", "delegate_externally", "reject"
    confidence: float = Field(default=1.0, description="Confidence score for this routing decision.")
    reasoning: Optional[str] = Field(default=None, description="Explanation for the routing decision (if LLM-driven).")

class RouteDecisionContext(BaseModel):
    """Context provided to an LLM for making a routing decision."""
    incoming_message: AnyInteractionMessage # Changed from StandardMessage (which was BaseMessage)
    available_internal_handlers: List[str] = Field(default_factory=list)
    known_external_agents: List[Dict[str, Any]] = Field(default_factory=list, description="List of known external agents and their capabilities.")
    routing_rules: Optional[Dict[str, Any]] = Field(default=None, description="Predefined routing rules.")
    historical_context: Optional[List[Dict]] = Field(default_factory=list, description="Recent interaction history.")
