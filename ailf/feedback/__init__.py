"""AILF Feedback Package.

This package provides components for collecting, storing, and analyzing feedback
related to agent interactions and performance. It aims to support:
    - Interaction Logging: Capturing detailed records of agent-user or agent-system exchanges.
    - Performance Monitoring: Tracking key metrics about agent behavior and efficiency.
    - Adaptive Learning: (Future) Mechanisms for agents to learn from feedback.
"""

from .interaction_logger import InteractionLogger, BaseLogStorage, ConsoleLogStorage
from .performance_analyzer import PerformanceAnalyzer
from .adaptive_learning_manager import AdaptiveLearningManager

__all__ = [
    "InteractionLogger",
    "BaseLogStorage",
    "ConsoleLogStorage",
    "PerformanceAnalyzer",
    "AdaptiveLearningManager",
]
