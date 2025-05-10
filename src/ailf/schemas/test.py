"""Test Schema Models

This module defines data models used in tests.
"""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BestPractice(BaseModel):
    """Represents a software development best practice.

    Attributes:
        name: Name of the best practice
        description: Detailed description of the practice
        importance: Importance rating from 1-10
    """
    name: str
    description: str
    importance: int

    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid'
    )

    @field_validator('importance')
    def validate_importance(self, v):
        """Validate importance is between 1 and 10."""
        if not 1 <= v <= 10:
            raise ValueError("Importance must be between 1 and 10")
        return v


class BestPracticesResponse(BaseModel):
    """Response containing software development best practices.

    Attributes:
        practices: List of best practices
        count: Number of practices returned
        source: Source of the best practices information
    """
    practices: List[BestPractice]
    count: int
    source: Optional[str] = None

    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid'
    )
