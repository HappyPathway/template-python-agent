# AI Module Reorganization Example

This document demonstrates how the AI engine module would be restructured as part of the repository cleanup plan.

## Current Structure

Currently, the AI-related code is contained primarily in:
- `/utils/ai_engine.py` - Main AI engine implementation
- `/utils/schemas/ai.py` - AI-related schemas

## Proposed Structure

```
/utils/ai/
  ├── __init__.py           # Exports key functionality
  ├── engine.py             # Core AI engine (refactored from ai_engine.py)
  ├── providers/            # Provider-specific implementations
  │   ├── __init__.py
  │   ├── openai.py         # OpenAI-specific functionality
  │   ├── gemini.py         # Gemini-specific functionality
  │   └── anthropic.py      # Anthropic-specific functionality
  └── tools/                # AI tools implementation
      ├── __init__.py
      ├── search.py         # Search tool implementation
      └── analysis.py       # Analysis tool implementation

/schemas/ai/
  ├── __init__.py           # Exports key schemas
  ├── core.py               # Core AI schemas
  ├── settings.py           # Provider settings schemas
  ├── responses.py          # Response schemas
  └── tools.py              # Tool-related schemas
```

## Implementation Example

### `/schemas/ai/core.py`

```python
"""Core AI schemas.

This module contains core schemas used by the AI engine.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class UsageLimits(BaseModel):
    """Usage limits for AI models.
    
    Attributes:
        max_requests_per_minute: Maximum requests per minute
        max_input_tokens: Maximum input tokens per request
        max_output_tokens: Maximum output tokens per request
        max_parallel_requests: Maximum parallel requests
    """
    max_requests_per_minute: int
    max_input_tokens: int
    max_output_tokens: int
    max_parallel_requests: int = 5

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
```

### `/schemas/ai/settings.py`

```python
"""AI provider settings schemas.

This module contains settings schemas for different AI providers.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .core import UsageLimits

class GeminiSafetySettings(BaseModel):
    """Safety settings for Gemini models."""
    category: str
    threshold: str

class GeminiSettings(BaseModel):
    """Configuration settings for Gemini models."""
    temperature: float = 0.7
    max_tokens: int = 1024
    safety_settings: Optional[List[GeminiSafetySettings]] = None
    generation_config: Optional[Dict[str, Any]] = None

class OpenAISettings(BaseModel):
    """Configuration settings for OpenAI models."""
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: Optional[float] = None
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
```

### `/utils/ai/__init__.py`

```python
"""AI module for working with large language models.

This module provides a unified interface for interacting with different 
AI providers like OpenAI, Google's Gemini, and Anthropic's Claude.

Example:
    >>> from ailf.ai import AIEngine
    >>> engine = AIEngine(feature_name="text_generator")
    >>> text = await engine.generate_text("Write a short story about AI")
"""

from .engine import AIEngine, AIEngineError, ModelError, ContentFilterError

__all__ = [
    "AIEngine", 
    "AIEngineError", 
    "ModelError", 
    "ContentFilterError"
]
```

### `/utils/ai/engine.py`

```python
"""AI Engine Module.

This module provides a comprehensive interface for AI and LLM interactions,
combining the capabilities of both AIEngine and BaseLLMAgent approaches.
It supports structured and unstructured outputs, with robust monitoring,
error handling, and type safety.

Key Components:
    AIEngine: Main class providing AI/LLM interaction interface
    AIEngineError: Base exception class for AI engine errors
    ModelError: Exception for model-specific errors
    ContentFilterError: Exception for content filtered by safety settings

Example:
    >>> from ailf.ai import AIEngine
    >>> from my_schemas import JobAnalysis
    >>> 
    >>> engine = AIEngine(
    ...     feature_name='job_analysis',
    ...     model_name='openai:gpt-4-turbo'
    ... )
    >>> 
    >>> result = await engine.generate(
    ...     prompt="Analyze this job description...",
    ...     output_schema=JobAnalysis
    ... )
"""

import asyncio
import os
from typing import (Any, AsyncIterator, Dict, Generic, List, Literal, Optional,
                    Type, TypeVar, Union)

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from schemas.ai.core import UsageLimits, AIResponse
from schemas.ai.settings import AnthropicSettings, GeminiSettings, OpenAISettings, GeminiSafetySettings
from ailf.core.logging import setup_logging
from ailf.core.monitoring import MetricsCollector, setup_monitoring
from ailf.cloud.secrets import secret_manager

# Initialize logging and monitoring
logger = setup_logging('ai_engine')
monitoring = setup_monitoring('ai_engine')

# Type variable for output types
T = TypeVar('T')

# AIEngine class would be implemented here with the same functionality
# but with updated imports and organization

# Exception classes
class AIEngineError(Exception):
    """Base exception for AI engine errors."""
    pass

class ModelError(AIEngineError):
    """Exception for model-specific errors."""
    pass

class ContentFilterError(AIEngineError):
    """Exception for content that was filtered by safety settings."""
    pass

# AIEngine class would continue here...
```

This example demonstrates how the reorganized code structure provides better organization, clearer separation of concerns, and improved modularity.

## Benefits of Reorganization

1. **Improved Modularity**: Each component has a clear responsibility.
2. **Better File Organization**: Related files are grouped together.
3. **Clearer Imports**: Import paths clearly indicate which component is being used.
4. **Easier Maintenance**: Smaller, more focused files are easier to maintain.
5. **Better Extensibility**: New provider implementations can be added without modifying the core engine.
6. **Enhanced Documentation**: Documentation is organized by component.
7. **Clearer Dependencies**: Dependencies between components are more explicit.

These principles can be applied across the entire repository to improve code organization and maintainability.
