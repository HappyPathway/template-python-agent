"""
AILF Tooling Subsystem.

This package includes components for tool integration, selection, and execution
within the AILF framework.

Key Components:
    ToolSelector: Selects appropriate tools based on queries or tasks.
    ToolManager: Manages the registration and execution of tools.
    ToolExecutionError: Custom exception for errors during tool execution.
"""

from .selector import ToolSelector
from .manager import ToolManager, ToolExecutionError # Consolidated ToolManager

__all__ = [
    "ToolSelector",
    "ToolManager",
    "ToolExecutionError",
]