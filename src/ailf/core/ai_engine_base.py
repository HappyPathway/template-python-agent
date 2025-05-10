"""AI Engine Base Module.

This module provides the base class for all AI engine implementations,
defining a common interface and extension points.
"""
import logging
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

try:
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "Pydantic is required for this module. "
        "Install it with: pip install pydantic"
    )

from ailf.core.logging import setup_logging


T = TypeVar('T', bound=BaseModel)


class AIEngineBase(ABC):
    """Base class for AI engine implementations.
    
    This abstract base class defines a common interface and extension points
    for all AI engine implementations, enabling consistent usage patterns
    across different providers while allowing for provider-specific features.
    
    To implement a new AI engine:
    1. Create a new class that inherits from AIEngineBase
    2. Override the required methods (_initialize, generate, generate_with_schema)
    3. Override extension points (_get_default_config, etc.) as needed
    
    Example implementation:
    ```python
    class CustomEngine(AIEngineBase):
        def __init__(self, api_key: str, model: str = "default", config: Optional[Dict[str, Any]] = None):
            self.api_key = api_key
            self.model = model
            super().__init__(config)
        
        def _initialize(self) -> None:
            self.client = CustomClient(api_key=self.api_key)
            
        async def generate(self, prompt: str, **kwargs) -> str:
            # Implementation of text generation
            response = await self.client.complete(prompt)
            return response.text
            
        async def generate_with_schema(self, prompt: str, output_schema: Type[T], **kwargs) -> T:
            # Implementation of schema-based generation
            json_response = await self.client.complete_as_json(prompt)
            return output_schema.parse_obj(json_response)
    ```
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the AI engine.
        
        Args:
            config: Optional configuration dictionary
        """
        self.logger = setup_logging(f"ai.{self.__class__.__name__}")
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
        self._initialize()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Override this method to provide default configuration values
        specific to your engine implementation.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        return {
            "retry_count": 3,
            "retry_delay": 1.0,
            "timeout": 60.0,
            "fail_on_error": True,
            "log_requests": True,
            "log_level": logging.INFO,
        }
        
    @abstractmethod
    def _initialize(self) -> None:
        """Initialize the engine.
        
        Override this method to perform any necessary initialization,
        such as setting up API clients or loading resources.
        """
        pass
        
    def _validate_prompt(self, prompt: str) -> str:
        """Validate and preprocess the prompt.
        
        Override this method to implement custom prompt validation
        or preprocessing logic.
        
        Args:
            prompt: The prompt to validate
            
        Returns:
            str: The validated/preprocessed prompt
            
        Raises:
            ValueError: If the prompt is invalid
        """
        if not prompt or not isinstance(prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        return prompt
        
    def _log_request(self, 
                   prompt: str, 
                   response: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log request and response information.
        
        Override this method to customize logging behavior.
        
        Args:
            prompt: The prompt sent to the engine
            response: The response received
            metadata: Optional metadata about the request/response
        """
        if not self.config.get("log_requests", True):
            return
            
        metadata = metadata or {}
        truncated_prompt = (prompt[:100] + "...") if len(prompt) > 100 else prompt
        truncated_response = (response[:100] + "...") if len(response) > 100 else response
        
        self.logger.info(
            "AI request: %s -> %s %s",
            truncated_prompt,
            truncated_response,
            metadata
        )
        
    def _handle_error(self, error: Exception, prompt: str) -> None:
        """Handle errors from the AI engine.
        
        Override this method to customize error handling behavior.
        
        Args:
            error: The exception that occurred
            prompt: The prompt that caused the error
            
        Raises:
            Exception: If fail_on_error is True
        """
        # Log the error
        self.logger.error(
            "AI engine error: %s\nPrompt: %s\nTraceback: %s",
            str(error),
            prompt,
            traceback.format_exc()
        )
        
        # Raise if fail_on_error is True
        if self.config.get("fail_on_error", True):
            raise error
            
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response for the given prompt.
        
        Args:
            prompt: The prompt to send to the model
            **kwargs: Additional parameters for generation
            
        Returns:
            str: The generated response
            
        Raises:
            Exception: On API or validation errors
        """
        pass
        
    @abstractmethod
    async def generate_with_schema(self, 
                               prompt: str, 
                               output_schema: Type[T],
                               **kwargs) -> T:
        """Generate a structured response based on the provided schema.
        
        Args:
            prompt: The prompt to send to the model
            output_schema: Pydantic model class for response validation
            **kwargs: Additional parameters for generation
            
        Returns:
            T: The structured response as a Pydantic model instance
            
        Raises:
            ValidationError: If the response cannot be parsed into the schema
            Exception: On other API or validation errors
        """
        pass