"""Anthropic Claude Engine Implementation.

This module provides a concrete implementation of the AIEngineBase interface
for Anthropic Claude API integration. It leverages all the extension points provided
by the base class for customization.
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

try:
    import anthropic
    from anthropic import AsyncAnthropic
    from anthropic.types import Message, MessageParam
except ImportError:
    raise ImportError(
        "Anthropic dependencies not installed. "
        "Install them with: pip install anthropic"
    )

try:
    from pydantic import BaseModel, ValidationError
except ImportError:
    raise ImportError(
        "Pydantic dependencies not installed. "
        "Install them with: pip install pydantic"
    )

from ailf.core.ai_engine_base import AIEngineBase


T = TypeVar('T', bound=BaseModel)


class AnthropicError(Exception):
    """Exception raised for Anthropic-specific errors."""
    pass


class AnthropicEngine(AIEngineBase):
    """Anthropic Claude API integration for AI Engine.
    
    This class provides a concrete implementation of AIEngineBase for
    interacting with Anthropic Claude models.
    
    Example:
        >>> engine = AnthropicEngine(
        ...     api_key="your-api-key",
        ...     model="claude-3-opus-20240229",
        ...     config={"temperature": 0.5}
        ... )
        >>> response = await engine.generate("Write a poem about AI")
        >>> print(response)
        
        >>> # Generate structured data
        >>> class Person(BaseModel):
        ...     name: str
        ...     age: int
        ...     bio: str
        >>> person = await engine.generate_with_schema(
        ...     "Create a fictional character profile", 
        ...     Person
        ... )
        >>> print(f"{person.name}, {person.age} years old")
    """

    def __init__(self, 
                 api_key: Optional[str] = None, 
                 model: str = "claude-3-opus-20240229",
                 config: Optional[Dict[str, Any]] = None):
        """Initialize Anthropic engine.
        
        Args:
            api_key: Anthropic API key (if None, uses ANTHROPIC_API_KEY environment variable)
            model: Anthropic model to use (default: "claude-3-opus-20240229")
            config: Optional configuration dictionary
        """
        self.model = model
        self.api_key = api_key
        self.client = None  # Initialized in _initialize
        super().__init__(config)
        
    def _initialize(self) -> None:
        """Initialize the Anthropic client."""
        self.client = AsyncAnthropic(api_key=self.api_key)
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values for Anthropic.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        config = super()._get_default_config()
        config.update({
            "system_message": "You are Claude, a helpful AI assistant.",
            "stream": False,
            "token_counter": None,  # Custom token counting function
            "metadata": {}  # Custom metadata to include with messages
        })
        return config
        
    def _preprocess_prompt(self, 
                           prompt: str, 
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process prompt into Anthropic message format.
        
        Args:
            prompt: Prompt to process
            context: Optional context information
            
        Returns:
            Dict[str, Any]: Parameters for Anthropic API
        """
        # Validate the prompt using the base class method
        prompt = super()._validate_prompt(prompt)
        
        # Build the base parameters
        params = {
            "model": self.model,
            "system": self.config.get("system_message"),
            "messages": [],
            "max_tokens": self.config.get("max_tokens", 1000),
            "metadata": self.config.get("metadata", {})
        }
        
        # Add conversation history from context
        if context and "history" in context and isinstance(context["history"], list):
            params["messages"] = context["history"]
        
        # Add the user's prompt as the latest message
        params["messages"].append({
            "role": "user",
            "content": prompt
        })
        
        return params
        
    def _extract_response_text(self, message: Message) -> str:
        """Extract text from Anthropic message.
        
        Args:
            message: Anthropic message object
            
        Returns:
            str: Extracted response text
        """
        try:
            return message.content[0].text
        except (AttributeError, IndexError):
            return ""
            
    def _count_tokens(self, params: Dict[str, Any]) -> Optional[int]:
        """Count tokens in the messages.
        
        Args:
            params: Anthropic API parameters
            
        Returns:
            Optional[int]: Token count or None if counter not available
        """
        counter = self.config.get("token_counter")
        if callable(counter):
            return counter(params, self.model)
        return None
        
    def _handle_response(self, response: Any) -> str:
        """Process response from Anthropic API.
        
        Args:
            response: Response from Anthropic API
            
        Returns:
            str: Processed response text
        """
        if isinstance(response, Message):
            return self._extract_response_text(response)
        return super()._handle_response(response)
        
    def _handle_error(self, error: Exception, prompt: str) -> None:
        """Handle Anthropic-specific errors.
        
        Args:
            error: Exception that occurred
            prompt: Original prompt that caused the error
            
        Raises:
            AnthropicError: Wrapped Anthropic exception with context
        """
        # Update metrics
        super()._handle_error(error, prompt)
        
        # Check for common Anthropic errors and provide more context
        if hasattr(error, "status_code"):
            if error.status_code == 429:
                raise AnthropicError("Rate limit exceeded. Consider implementing backoff strategy.") from error
            elif error.status_code == 401:
                raise AnthropicError("Invalid API key or authentication error.") from error
            elif error.status_code == 500:
                raise AnthropicError("Anthropic server error. Consider retrying after a delay.") from error
                
        # For other errors, wrap in AnthropicError
        raise AnthropicError(f"Anthropic API error: {str(error)}") from error
        
    async def _retry_with_exponential_backoff(self, func, max_retries: int) -> Any:
        """Execute function with exponential backoff retry strategy.
        
        Args:
            func: Async function to execute
            max_retries: Maximum number of retries
            
        Returns:
            Any: Function result
        
        Raises:
            Exception: Last exception if all retries fail
        """
        retries = 0
        retry_delay = self.config.get("retry_delay", 1.0)
        
        while True:
            try:
                return await func()
            except Exception as e:
                retries += 1
                if retries > max_retries:
                    raise
                
                # Calculate delay with exponential backoff
                delay = retry_delay * (2 ** (retries - 1))
                
                # Wait before retrying
                await asyncio.sleep(delay)

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response using Anthropic API.
        
        Args:
            prompt: The prompt to generate a response for
            **kwargs: Additional keyword arguments for the API

        Returns:
            str: Generated response text
            
        Raises:
            AnthropicError: On API errors
            ValueError: On invalid input
        """
        if not self.client:
            self._initialize()
            
        try:
            # Prepare parameters
            context = kwargs.pop("context", None)
            params = self._preprocess_prompt(prompt, context)
            
            # Override defaults with any provided kwargs
            for key, value in kwargs.items():
                if key in params:
                    params[key] = value
            
            # Set temperature if provided
            if "temperature" in kwargs or "temperature" in self.config:
                params["temperature"] = kwargs.get("temperature", self.config.get("temperature"))
                
            # Count tokens if a counter is available
            input_tokens = self._count_tokens(params)
            
            # Configure streaming if requested
            stream = kwargs.get("stream", self.config.get("stream", False))
            params["stream"] = stream
            
            # Record start time for latency tracking
            start_time = time.time()
            
            # Execute with retry
            max_retries = self.config.get("retry_count", 3)
            if stream:
                # Handle streaming responses
                response_text = ""
                stream_resp = await self._retry_with_exponential_backoff(
                    lambda: self.client.messages.create(**params),
                    max_retries
                )
                async for chunk in stream_resp:
                    if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                        response_text += chunk.delta.text
                response = response_text
            else:
                # Handle non-streaming responses
                response = await self._retry_with_exponential_backoff(
                    lambda: self.client.messages.create(**params),
                    max_retries
                )
            
            # Process response
            response_text = self._handle_response(response)
            
            # Calculate metrics
            metrics = {
                "latency": time.time() - start_time,
                "model": params["model"]
            }
            
            # Add token counts if available
            if hasattr(response, "usage"):
                metrics["tokens"] = response.usage.input_tokens + response.usage.output_tokens
                metrics["prompt_tokens"] = response.usage.input_tokens
                metrics["completion_tokens"] = response.usage.output_tokens
            elif input_tokens:
                metrics["prompt_tokens"] = input_tokens
            
            # Log the request
            self._log_request(prompt, response_text, metrics)
            
            return response_text
            
        except Exception as e:
            return self._handle_error(e, prompt)
            
    async def generate_with_schema(self, 
                                  prompt: str, 
                                  output_schema: Type[T],
                                  **kwargs) -> T:
        """Generate a structured response matching the provided schema.
        
        Args:
            prompt: The prompt to generate a response for
            output_schema: Pydantic model class for response validation
            **kwargs: Additional keyword arguments

        Returns:
            T: Generated response as a validated instance of output_schema
            
        Raises:
            AnthropicError: On API errors
            ValidationError: When response doesn't match the schema
            ValueError: On invalid input
        """
        if not self.client:
            self._initialize()
            
        try:
            # Enhance the prompt with schema information
            schema_info = output_schema.schema()
            schema_prompt = (
                f"{prompt}\n\n"
                f"Respond with a valid JSON object matching this schema:\n"
                f"{json.dumps(schema_info, indent=2)}\n\n"
                f"Important: Your response must be valid JSON that matches the schema exactly. "
                f"Ensure all required fields are included with the correct types."
            )
            
            # Generate the JSON response
            json_response = await self.generate(schema_prompt, **kwargs)
            
            try:
                # Extract JSON from response (Claude might wrap the JSON in markdown code blocks)
                json_matches = self._extract_json_from_text(json_response)
                if json_matches:
                    json_response = json_matches[0]
                
                # Parse and validate with the schema
                parsed_data = json.loads(json_response)
                return output_schema.parse_obj(parsed_data)
            except (json.JSONDecodeError, ValidationError) as e:
                # If validation fails, try one more time with error feedback
                retry_prompt = (
                    f"{schema_prompt}\n\n"
                    f"Previous attempt failed with error: {str(e)}\n"
                    f"Respond ONLY with the JSON object that matches the schema. "
                    f"Don't include any explanations, just the JSON object itself."
                )
                
                json_response = await self.generate(retry_prompt, **kwargs)
                
                # Extract JSON again
                json_matches = self._extract_json_from_text(json_response)
                if json_matches:
                    json_response = json_matches[0]
                    
                parsed_data = json.loads(json_response)
                return output_schema.parse_obj(parsed_data)
                
        except json.JSONDecodeError as e:
            raise AnthropicError(f"Failed to parse JSON response: {str(e)}")
        except ValidationError as e:
            raise AnthropicError(f"Response validation failed: {str(e)}")
        except Exception as e:
            return self._handle_error(e, prompt)
            
    def _extract_json_from_text(self, text: str) -> List[str]:
        """Extract JSON objects from a text string.
        
        Handles cases where the model wraps JSON in markdown code blocks.
        
        Args:
            text: Text that may contain JSON objects
            
        Returns:
            List[str]: Extracted JSON strings
        """
        import re
        
        # First, try to find JSON in code blocks
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        code_blocks = re.findall(code_block_pattern, text)
        
        if code_blocks:
            return code_blocks
            
        # If no code blocks, try to find JSON-like content
        # This is a simple heuristic and may need improvement
        json_pattern = r"(\{[\s\S]*\})"
        json_blocks = re.findall(json_pattern, text)
        
        return json_blocks if json_blocks else [text]