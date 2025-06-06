"""AI-related schema models.

This module provides Pydantic models for AI interactions.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

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

class AIRequest(BaseModel):
    """Request to AI models.
    
    Attributes:
        prompt: The input prompt or message
        system: Optional system message/instruction
        temperature: The sampling temperature
        max_tokens: The maximum number of tokens to generate
        stream: Whether to stream the response
        tools: Optional list of tools available to the model
    """
    prompt: str
    system: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None

class AIEngineConfig(BaseModel):
    """Configuration for AIEngine.
    
    Attributes:
        model_name: The name of the model to use
        feature_name: Name of the feature using the engine (for monitoring)
        api_key: Optional API key (defaults to environment variable)
        base_url: Optional base URL for API
        timeout: Request timeout in seconds
        usage_limits: Optional usage limits
    """
    model_name: str
    feature_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    usage_limits: Optional[UsageLimits] = None

class GeminiSafetySettings(BaseModel):
    """Safety settings for Gemini models.
    
    Attributes:
        category: The harm category
        threshold: The blocking threshold
    """
    category: str
    threshold: str

class GeminiSettings(BaseModel):
    """Settings for Gemini models.
    
    Attributes:
        temperature: The sampling temperature
        max_tokens: The maximum number of tokens to generate
        safety_settings: List of safety settings
        generation_config: Additional generation config
    """
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    safety_settings: List[GeminiSafetySettings] = []
    generation_config: Dict[str, Any] = {}

class OpenAISettings(BaseModel):
    """Settings for OpenAI models.
    
    Attributes:
        temperature: The sampling temperature
        max_tokens: The maximum number of tokens to generate
        top_p: Top p sampling parameter
        frequency_penalty: Frequency penalty parameter
        presence_penalty: Presence penalty parameter
        stop: Optional stop sequences
    """
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None

class AnthropicSettings(BaseModel):
    """Settings for Anthropic models.
    
    Attributes:
        temperature: The sampling temperature
        max_tokens: The maximum number of tokens to generate
        top_p: Top p sampling parameter
        top_k: Top k sampling parameter
    """
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    top_k: Optional[int] = None

class AIResponse(BaseModel):
    """Response from AI models.
    
    Attributes:
        content: The generated content
        usage: Usage statistics
        model: The model used
        finish_reason: Reason for completion
    """
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None

__all__ = [
    "AIRequest",
    "AIResponse",
    "AIEngineConfig",
    "GeminiSettings",
    "GeminiSafetySettings",
    "OpenAISettings",
    "AnthropicSettings",
    "UsageLimits"
]
