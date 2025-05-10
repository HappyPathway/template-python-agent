"""Base classes for AILF cognition components.

This module defines the core abstract base classes for agents, their state,
and cognitive processes within the AILF framework.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Generic, TypeVar
from pydantic import BaseModel

# Forward declaration for type hinting if BaseAgent uses BaseAgentState
# and BaseAgentState might reference BaseAgent (though less common for state)
class BaseAgent:
    pass

S = TypeVar('S', bound='BaseAgentState') # TypeVar for generic state

class BaseAgentState(BaseModel, ABC, Generic[S]):
    """
    Abstract base class for an agent's internal state.
    Pydantic BaseModel is used for validation and serialization.
    Subclasses should define specific state variables.
    """
    agent_id: str = Field(description="The unique identifier of the agent this state belongs to.")
    # current_mode: Optional[str] = Field(default=None, description="Current operational mode of the agent.")
    # last_error: Optional[str] = Field(default=None, description="Last error encountered by the agent.")

    # class Config:
    #     arbitrary_types_allowed = True # If state needs to hold complex non-Pydantic objects

    @abstractmethod
    async def load_state(self, state_id: Optional[str] = None) -> S:
        """Loads the agent's state, potentially from a persistent store."""
        pass

    @abstractmethod
    async def save_state(self) -> bool:
        """Saves the agent's current state, potentially to a persistent store."""
        pass

    def update_state(self, new_data: Dict[str, Any]):
        """
        Updates the state with new data.
        Pydantic will handle validation if fields are defined.
        """
        for key, value in new_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                # Or handle dynamic attributes if your state model allows for it (e.g. via extra='allow')
                print(f"Warning: Attempted to set unknown state attribute '{key}'")
        return self

class BaseCognitiveProcess(ABC):
    """
    Abstract base class for a single step or component in an agent's thought process.
    Cognitive processes operate on the agent's state and may produce output or side effects.
    """

    def __init__(self, agent_context: Optional[BaseAgent] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the cognitive process.

        :param agent_context: A reference to the parent agent, providing access to its state, tools, etc.
        :type agent_context: Optional[BaseAgent]
        :param config: Configuration for this cognitive process.
        :type config: Optional[Dict[str, Any]]
        """
        self.agent_context = agent_context
        self.config = config or {}

    @abstractmethod
    async def execute(self, input_data: Any, current_state: BaseAgentState) -> Any:
        """
        Executes the cognitive process.

        :param input_data: The primary input for this cognitive step.
        :type input_data: Any
        :param current_state: The current state of the agent.
        :type current_state: BaseAgentState
        :return: The result of the cognitive process. This could be data to update state,
                 an action to perform, or input for the next process.
        :rtype: Any
        """
        pass

class BaseAgent(ABC):
    """
    Abstract base class for an AILF agent.
    Defines the lifecycle and core methods for agent operation.
    """

    def __init__(self, agent_id: str, initial_state: Optional[BaseAgentState] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the agent.

        :param agent_id: A unique identifier for this agent.
        :type agent_id: str
        :param initial_state: An initial state object for the agent. If None, a default state might be created or loaded.
        :type initial_state: Optional[BaseAgentState]
        :param config: Configuration dictionary for the agent.
        :type config: Optional[Dict[str, Any]]
        """
        self.agent_id = agent_id
        self.state: BaseAgentState = initial_state # type: ignore # Initial state will be set in subclasses or load
        self.config = config or {}
        self.is_running = False
        self._cognitive_processes: Dict[str, BaseCognitiveProcess] = {}

    @abstractmethod
    async def initialize(self):
        """Initializes agent resources, loads state, sets up connections, etc."""
        pass

    @abstractmethod
    async def start(self):
        """Starts the agent's main processing loop or makes it ready to receive messages/events."""
        self.is_running = True
        pass

    @abstractmethod
    async def stop(self):
        """Stops the agent's processing and cleans up resources."""
        self.is_running = False
        pass

    @abstractmethod
    async def process_message(self, message: Any, sender_info: Optional[Dict[str, Any]] = None) -> Any:
        """
        Processes an incoming message or event.
        This is a primary entry point for external interaction or internal event handling.

        :param message: The message/event data to process.
        :type message: Any
        :param sender_info: Optional information about the sender or source of the message.
        :type sender_info: Optional[Dict[str, Any]]
        :return: A response or result of processing, if applicable.
        :rtype: Any
        """
        pass

    def add_cognitive_process(self, name: str, process: BaseCognitiveProcess):
        """Registers a cognitive process with the agent."""
        self._cognitive_processes[name] = process

    def get_cognitive_process(self, name: str) -> Optional[BaseCognitiveProcess]:
        """Retrieves a registered cognitive process."""
        return self._cognitive_processes.get(name)

    async def run_cognitive_cycle(self, initial_input: Any) -> Any:
        """
        A conceptual method representing a full cognitive cycle.
        The actual implementation will vary greatly based on agent design.
        This might involve a sequence of cognitive processes.
        Subclasses should override this with their specific logic.

        :param initial_input: The initial input to start the cycle (e.g., a user query, a sensor reading).
        :type initial_input: Any
        :return: The final output of the cognitive cycle.
        :rtype: Any
        """
        if not self._cognitive_processes:
            print(f"Warning: Agent {self.agent_id} has no cognitive processes defined for run_cognitive_cycle.")
            return None
        
        # Example: a simple sequential execution if processes are ordered or a primary one exists
        # This is highly dependent on the agent's architecture.
        # For instance, a 'main_process' or a chain could be invoked here.
        # current_data = initial_input
        # for process_name, process_obj in self._cognitive_processes.items():
        #     print(f"Executing process: {process_name}")
        #     current_data = await process_obj.execute(current_data, self.state)
        # return current_data
        raise NotImplementedError("Subclasses must implement their own cognitive cycle logic.")

    async def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the agent."""
        return {
            "agent_id": self.agent_id,
            "is_running": self.is_running,
            "state_summary": self.state.model_dump(exclude_none=True) if self.state else None,
            "cognitive_processes": list(self._cognitive_processes.keys())
        }
