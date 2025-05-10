"""AI Engine Schema Models

This module defines data models for AI operations and configurations.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class UsageLimits(BaseModel):
    """Usage limits for AI operations.

    Attributes:
        max_input_tokens: Maximum number of input tokens allowed per request
        max_output_tokens: Maximum number of output tokens allowed per request
        max_requests_per_minute: Maximum number of API requests allowed per minute
        max_parallel_requests: Maximum number of parallel requests allowed
    """
    max_input_tokens: int = 8000
    max_output_tokens: int = 1024
    max_requests_per_minute: int = 60
    max_parallel_requests: int = 5

    model_config = {
        'validate_assignment': True,
        'extra': 'forbid'
    }


class GeminiSafetySettings(BaseModel):
    """Safety settings for Gemini AI models."""
    harm_category: str
    threshold: str


class GeminiSettings(BaseModel):
    """Configuration settings for Gemini AI models."""
    temperature: float = 0.7
    max_tokens: int = 1024
    safety_settings: Optional[List[GeminiSafetySettings]] = None
    generation_config: Optional[Dict[str, Any]] = None


class OpenAISettings(BaseModel):
    """Configuration settings for OpenAI models."""
    temperature: float = 0.7
    max_tokens: int = 1024
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    stop: Optional[List[str]] = None


class AnthropicSettings(BaseModel):
    """Configuration settings for Anthropic models."""
    temperature: float = 0.7
    max_tokens: int = 1024
    top_k: Optional[int] = None
    top_p: Optional[float] = None


class AIResponse(BaseModel):
    """Response from AI operation.

    Attributes:
        content: The generated content from the AI model
        usage: Information about token usage
        model: The model that generated the response
        finish_reason: The reason why generation stopped
    """
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: Optional[str] = None

    model_config = {
        'validate_assignment': True,
        'extra': 'forbid'
    }
