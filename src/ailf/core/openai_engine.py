"""OpenAI Engine Module.

This module provides an implementation of AIEngineBase for OpenAI's API,
supporting text generation and structured output generation with schema validation.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from ailf.core.ai_engine_base import AIEngineBase

# Type variable for generic structured output
T = TypeVar('T', bound=BaseModel)

class OpenAIEngine(AIEngineBase):
    """OpenAI implementation of AIEngineBase.
    
    This class provides access to OpenAI's models for text generation and
    structured output generation with Pydantic schema validation.
    
    Example:
        ```python
        # Initialize the engine
        engine = OpenAIEngine(
            api_key="your-openai-key",
            model="gpt-4-turbo"
        )
        
        # Generate a text response
        response = await engine.generate("What is the capital of France?")
        
        # Generate a structured response
        class City(BaseModel):
            name: str
            country: str
            population: int
            
        city_info = await engine.generate_with_schema(
            "Provide information about Paris.",
            output_schema=City
        )
        ```
    """
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-3.5-turbo",
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the OpenAI engine.
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use (default: gpt-3.5-turbo)
            config: Optional configuration dictionary
        """
        self.api_key = api_key
        self.model = model
        super().__init__(config)
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values for OpenAI.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        config = super()._get_default_config()
        config.update({
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "schema_instructions": "You must respond with a valid JSON object that conforms to the required schema.",
            "structured_output_format": "json_object",
        })
        return config
        
    def _initialize(self) -> None:
        """Initialize the OpenAI client.
        
        Raises:
            ImportError: If OpenAI Python package is not installed
        """
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            self.logger.info(f"OpenAIEngine initialized with model {self.model}")
        except ImportError:
            raise ImportError(
                "OpenAI Python package is required. "
                "Install it with: pip install openai"
            )
            
    def _format_system_message(self, system_prompt: Optional[str] = None) -> Dict[str, str]:
        """Format the system message for OpenAI.
        
        Args:
            system_prompt: Optional system prompt
            
        Returns:
            Dict[str, str]: Formatted system message
        """
        default_system = "You are a helpful, precise assistant."
        content = system_prompt or default_system
        return {"role": "system", "content": content}
        
    def _format_user_message(self, prompt: str) -> Dict[str, str]:
        """Format the user message for OpenAI.
        
        Args:
            prompt: User prompt
            
        Returns:
            Dict[str, str]: Formatted user message
        """
        return {"role": "user", "content": prompt}
        
    def _prepare_messages(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages for OpenAI API.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            history: Optional conversation history
            
        Returns:
            List[Dict[str, str]]: Formatted messages
        """
        messages = [self._format_system_message(system_prompt)]
        
        if history:
            messages.extend(history)
            
        messages.append(self._format_user_message(prompt))
        return messages
        
    def _extract_response_content(self, response: Any) -> str:
        """Extract content from OpenAI response.
        
        Args:
            response: OpenAI API response
            
        Returns:
            str: Extracted content
        """
        return response.choices[0].message.content
        
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """Generate a response for the given prompt.
        
        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system prompt to guide model behavior
            history: Optional conversation history
            **kwargs: Additional parameters for generation
            
        Returns:
            str: The generated response
            
        Raises:
            Exception: On API or validation errors
        """
        try:
            validated_prompt = self._validate_prompt(prompt)
            messages = self._prepare_messages(validated_prompt, system_prompt, history)
            
            # Merge config with kwargs, with kwargs taking precedence
            params = {**self.config, **kwargs}
            
            # Remove keys that are not relevant to the API call
            for key in ['retry_count', 'retry_delay', 'timeout', 'fail_on_error', 
                        'log_requests', 'log_level', 'schema_instructions',
                        'structured_output_format']:
                params.pop(key, None)
                
            # Extract parameters that don't belong in the API call
            retry_count = self.config.get('retry_count', 3)
            retry_delay = self.config.get('retry_delay', 1.0)
            
            # Make the API call with retries
            response = None
            last_error = None
            
            for attempt in range(retry_count):
                try:
                    start_time = time.time()
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        **params
                    )
                    elapsed = time.time() - start_time
                    break
                except Exception as e:
                    last_error = e
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{retry_count} failed: {str(e)}. "
                        f"Retrying in {retry_delay} seconds..."
                    )
                    time.sleep(retry_delay)
                    
            if response is None:
                raise last_error or Exception("All retry attempts failed")
                
            content = self._extract_response_content(response)
            
            # Log the request and response
            self._log_request(
                prompt, 
                content, 
                {
                    "model": self.model,
                    "elapsed_time": elapsed
                }
            )
            
            return content
            
        except Exception as e:
            self._handle_error(e, prompt)
            return ""  # Only reached if fail_on_error is False
            
    async def generate_with_schema(
        self, 
        prompt: str, 
        output_schema: Type[T],
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> T:
        """Generate a structured response based on the provided schema.
        
        Args:
            prompt: The prompt to send to the model
            output_schema: Pydantic model class for response validation
            system_prompt: Optional system prompt to guide model behavior
            history: Optional conversation history
            **kwargs: Additional parameters for generation
            
        Returns:
            T: The structured response as a Pydantic model instance
            
        Raises:
            ValidationError: If the response cannot be parsed into the schema
            Exception: On other API or validation errors
        """
        # Build a custom system prompt that includes schema instructions
        schema_description = output_schema.schema_json(indent=2)
        schema_instructions = self.config.get("schema_instructions", 
            "You must respond with a valid JSON object that conforms to the required schema.")
            
        custom_system_prompt = (
            f"{system_prompt or 'You are a helpful, precise assistant.'}\n\n"
            f"{schema_instructions}\n\n"
            f"Required JSON Schema:\n{schema_description}"
        )
        
        # Override config to use lower temperature for structured output
        structured_params = kwargs.copy()
        structured_params["temperature"] = kwargs.get("temperature", 0.2)
        
        for _ in range(self.config.get("retry_count", 3)):
            try:
                response_text = await self.generate(
                    prompt=prompt,
                    system_prompt=custom_system_prompt, 
                    history=history,
                    **structured_params
                )
                
                # Try to extract JSON from the response
                json_str = self._extract_json(response_text)
                
                # Parse the response into the schema
                result = output_schema.parse_raw(json_str)
                return result
                
            except ValidationError as e:
                self.logger.warning(
                    f"Validation error in schema parsing: {str(e)}. Retrying..."
                )
                continue
                
            except Exception as e:
                self._handle_error(e, prompt)
                raise
                
        # If we get here, all retries failed
        error_msg = f"Failed to generate valid response matching schema after {self.config['retry_count']} attempts"
        self.logger.error(error_msg)
        raise ValidationError(error_msg, model=output_schema)
        
    def _extract_json(self, text: str) -> str:
        """Extract JSON from a text response.
        
        Args:
            text: Text response that may contain JSON
            
        Returns:
            str: Extracted JSON string
            
        Raises:
            ValueError: If no valid JSON is found
        """
        # First, try to parse the entire response as JSON
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
            
        # Try to extract JSON from markdown code blocks
        import re
        json_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(json_block_pattern, text)
        
        for match in matches:
            try:
                # Validate that this is parseable JSON
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
                
        # Try to find anything that looks like a JSON object
        curly_brace_pattern = r"\{[\s\S]*\}"
        matches = re.findall(curly_brace_pattern, text)
        
        for match in matches:
            try:
                # Validate that this is parseable JSON
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
                
        # If we got here, no valid JSON was found
        raise ValueError(f"No valid JSON found in response: {text}")