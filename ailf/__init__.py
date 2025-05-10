# This file marks ailf as a package

# Import key components from submodules to make them available at the ailf level

# Cognition - Core AI reasoning and planning
from .cognition import ReActProcessor, TaskPlanner, IntentRefiner, PromptTemplateV1, PromptLibrary

# Communication - Agent Communication Protocol (ACP) related components
# from .communication import ACPHandler # Assuming ACPHandler will be the main export

# Feedback - Learning and adaptation mechanisms
from .feedback import InteractionLogger # Add PerformanceAnalyzer, AdaptiveLearningManager when ready

# Interaction - Managing agent's communication with the external world
from .interaction import BaseInputAdapter, BaseOutputAdapter, InteractionManager

# Memory - Short-term and long-term memory systems
from .memory import ShortTermMemory, LongTermMemory, ReflectionEngine

# Messaging - Low-level message queuing (ZMQ, Redis)
# from .messaging import ... # Specific classes if direct access is needed, often used by other components

# Registry Client - For interacting with agent/tool registries
# from .registry_client import HttpRegistryClient # Or other client implementations

# Routing - Task delegation and agent routing
# from .routing import TaskDelegator, AgentRouter # Assuming these will be main exports

# Schemas - Centralized Pydantic models
from . import schemas

# Tooling - Tool integration, selection, and execution
from .tooling import ToolSelector, ToolManager, ToolExecutionError


__all__ = [
    # Cognition
    "ReActProcessor",
    "TaskPlanner",
    "IntentRefiner",
    "PromptTemplateV1",
    "PromptLibrary",
    # Communication
    # "ACPHandler",
    # Feedback
    "InteractionLogger",
    # Interaction
    "BaseInputAdapter",
    "BaseOutputAdapter",
    "InteractionManager",
    # Memory
    "ShortTermMemory",
    "LongTermMemory",
    "ReflectionEngine",
    # Registry Client
    # "HttpRegistryClient",
    # Routing
    # "TaskDelegator",
    # "AgentRouter",
    # Schemas
    "schemas",
    # Tooling
    "ToolSelector",
    "ToolManager",
    "ToolExecutionError",
]