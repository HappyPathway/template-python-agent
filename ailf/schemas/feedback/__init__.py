"""AILF Schemas for Feedback Systems.

This package contains Pydantic models used by the ailf.feedback module,
primarily for interaction logging and feedback data structures.

Key Schemas:
    LoggedInteraction: Defines the structure for a detailed log of an agent interaction.
"""

from .models import LoggedInteraction # Corrected: Import from .models

__all__ = [
    "LoggedInteraction",
]
