"""OpenAI Engine Implementation.

This module provides a concrete implementation of the AIEngineBase interface
for the OpenAI API, supporting GPT models.
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

try:
    import httpx
    from openai import AsyncOpenAI, BadRequestError, APIError, RateLimitError
    from pydantic import BaseModel, ValidationError, Field
except ImportError:
    raise ImportError(
        "OpenAI dependencies not installed. "
        "Install them with: pip install openai httpx pydantic"
    )

from ailf.core.ai_engine_base import AIEngineBase


T = TypeVar('T', bound=BaseModel)


class OpenAIEngine(AIEngineBase):
    """OpenAI implementation of AIEngineBase.
    
    This class provides a concrete implementation of AIEngineBase for OpenAI's GPT models,
    using the official OpenAI Python client.
    
    Example:
        ```python
        engine = OpenAIEngine(
            api_key="your_api_key",
            model="gpt-4",
            config={"temperature": 0.2}
        )
        
        # Simple text generation
        response = await engine.generate("Explain quantum computing")
        
        # Schema-based generation
        class Person(BaseModel):
            name: str
            age: int
            bio: str
            
        person = await engine.generate_with_schema(
            "Generate a fictional character",
            Person
        )
        print(f"{person.name}, {person.age} years old")
        print(person.bio)
        ```
    """
    
    def __init__(self, 
                api_key: str, 
                model: str = "gpt-4o", 
                config: Optional[Dict[str, Any]] = None,
                organization: Optional[str] = None):
        """Initialize OpenAI engine.
        
        Args:
            api_key: OpenAI API key
            model: Model name/identifier (e.g., 'gpt-4o', 'gpt-3.5-turbo')
            config: Optional configuration dictionary
            organization: Optional organization ID
        """
        self.api_key = api_key
        self.model = model
        self.organization = organization
        super().__init__(config)
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get OpenAI-specific default configuration.
        
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
            "stream": False,
            "default_system_message": "You are a helpful, accurate, and concise assistant.",
        })
        return config
        
    def _initialize(self) -> None:
        """Initialize the OpenAI client."""
        self.client = AsyncOpenAI(
            api_key=self.api_key, 
            organization=self.organization
        )
        
        # Log initialization
        self.logger.info(
            "Initialized OpenAI engine with model %s", 
            self.model
        )
        
    def _prepare_message_params(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Prepare parameters for chat completion request.
        
        Args:
            prompt: The user prompt
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Parameters for the OpenAI API call
        """
        # Start with config values and override with kwargs
        params = {k: v for k, v in self.config.items() if k in [
            "temperature", 
            "max_tokens", 
            "top_p", 
            "frequency_penalty", 
            "presence_penalty",
            "stream"
        ]}
        
        params.update({k: v for k, v in kwargs.items() if k in [
            "temperature", 
            "max_tokens", 
            "top_p", 
            "frequency_penalty", 
            "presence_penalty",
            "stream",
            "stop",
            "tools",
            "tool_choice"
        ]})
        
        # Create message array
        messages = []
        
        # Add system message if provided or use default
        system_message = kwargs.get("system_message", 
                                  self.config.get("default_system_message"))
        if system_message:
            messages.append({"role": "system", "content": system_message})
            
        # Add conversation history if provided
        history = kwargs.get("history", [])
        if history:
            messages.extend(history)
            
        # Add the user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Create final parameters dictionary
        final_params = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            **params
        }
        
        return final_params
        
    async def _make_request(self, params: Dict[str, Any]) -> Any:
        """Make an API request with retry logic.
        
        Args:
            params: Request parameters
            
        Returns:
            Any: API response
            
        Raises:
            Exception: On repeated failure after retries
        """
        retry_count = self.config.get("retry_count", 3)
        retry_delay = self.config.get("retry_delay", 1.0)
        timeout = self.config.get("timeout", 60.0)
        
        for attempt in range(retry_count + 1):
            try:
                start_time = time.time()
                response = await self.client.chat.completions.create(
                    **params,
                    timeout=timeout
                )
                elapsed = time.time() - start_time
                
                return response, elapsed
                
            except RateLimitError as e:
                # For rate limit errors, use exponential backoff
                self.logger.warning(
                    "OpenAI rate limit hit (attempt %d/%d)", 
                    attempt + 1, 
                    retry_count + 1
                )
                if attempt < retry_count:
                    # Calculate exponential backoff with jitter
                    delay = retry_delay * (2 ** attempt) + (0.1 * random.random())
                    await asyncio.sleep(delay)
                else:
                    raise e
                    
            except (APIError, httpx.ReadTimeout) as e:
                # For server errors, also retry with backoff
                self.logger.warning(
                    "OpenAI API error: %s (attempt %d/%d)", 
                    str(e),
                    attempt + 1, 
                    retry_count + 1
                )
                if attempt < retry_count:
                    # Linear backoff for other errors
                    delay = retry_delay * (attempt + 1)
                    await asyncio.sleep(delay)
                else:
                    raise e
                    
            except Exception as e:
                # Don't retry other exceptions
                raise e
        
    def _handle_response(self, response: Any) -> str:
        """Extract text from OpenAI API response.
        
        Args:
            response: OpenAI API response object
            
        Returns:
            str: Extracted text content
        """
        if hasattr(response, "choices") and response.choices:
            message = response.choices[0].message
            if message.content:
                return message.content
            # Handle tool calls or function calls if content is None
            return json.dumps({
                "tool_calls": [
                    {"function": tc.function.to_dict(), "id": tc.id, "type": tc.type}
                    for tc in message.tool_calls
                ] if hasattr(message, "tool_calls") and message.tool_calls else []
            })
        return str(response)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a piece of text.
        
        This is a simple approximation. For accurate token counting,
        you should use the official tokenizer.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        # Simple estimation: ~4 chars per token (very approximate)
        return len(text) // 4
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response for the given prompt.
        
        Args:
            prompt: The prompt to send to OpenAI
            **kwargs: Additional parameters for the API call
            
        Returns:
            str: The generated response
            
        Raises:
            Exception: On API or validation errors
        """
        # Validate the prompt
        prompt = self._validate_prompt(prompt)
        
        try:
            # Prepare API parameters
            params = self._prepare_message_params(prompt, **kwargs)
            
            # Make the API request
            response, elapsed = await self._make_request(params)
            
            # Extract and return the response text
            result = self._handle_response(response)
            
            # Log the request
            self._log_request(
                prompt, 
                result, 
                {
                    "model": params["model"],
                    "latency": elapsed,
                    "tokens": self._estimate_tokens(prompt) + self._estimate_tokens(result),
                }
            )
            
            return result
            
        except Exception as e:
            self._handle_error(e, prompt)
            # If we get here, fail_on_error is False
            return f"Error: {str(e)}"
            
    async def generate_with_schema(self, 
                                 prompt: str, 
                                 output_schema: Type[T],
                                 **kwargs) -> T:
        """Generate a structured response based on the provided schema.
        
        Args:
            prompt: The prompt to send to OpenAI
            output_schema: Pydantic model class for response validation
            **kwargs: Additional parameters for the API call
            
        Returns:
            T: The structured response as a Pydantic model instance
            
        Raises:
            ValidationError: If the response cannot be parsed into the schema
        """
        # Inject schema information into the prompt
        schema_json = output_schema.schema_json(indent=2)
        enhanced_prompt = f"""
        Based on the following request, please provide a response formatted according to this JSON schema:
        
        {schema_json}
        
        Your response must be valid JSON that conforms to this schema.
        
        Request: {prompt}
        """
        
        # Set system message for better formatting
        system_message = kwargs.pop("system_message", 
                                  "You are a helpful assistant that always responds with valid JSON according to the requested schema.")
        
        # Lower temperature for more deterministic outputs
        temperature = kwargs.pop("temperature", 0.2)
        
        try:
            # Generate the response
            response = await self.generate(
                enhanced_prompt,
                system_message=system_message,
                temperature=temperature,
                **kwargs
            )
            
            # Extract JSON from response, handling code blocks
            if "```json" in response:
                # Extract JSON from code block
                json_text = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                # Extract from generic code block
                json_text = response.split("```")[1].strip()
            else:
                # Assume the whole response is JSON
                json_text = response
                
            # Parse and validate with the schema
            try:
                data = json.loads(json_text)
                result = output_schema.parse_obj(data)
                return result
            except (json.JSONDecodeError, ValidationError) as e:
                self.logger.error(
                    "Failed to parse response as JSON: %s", 
                    str(e),
                    response=response
                )
                
                # Try to fix common JSON issues and retry
                corrected_json = self._attempt_json_correction(response)
                if corrected_json:
                    try:
                        data = json.loads(corrected_json)
                        result = output_schema.parse_obj(data)
                        return result
                    except (json.JSONDecodeError, ValidationError):
                        pass
                
                # If still failing, try one more time with an explicit fix request
                retry_prompt = f"""
                The previous response couldn't be parsed as valid JSON for this schema:
                
                {schema_json}
                
                Please provide ONLY the JSON object with no explanation or code formatting.
                """
                
                response = await self.generate(
                    retry_prompt,
                    system_message="You must respond with only valid JSON that matches the schema, nothing else.",
                    temperature=0.1,  # Lower temperature for more deterministic output
                    **kwargs
                )
                
                # Try to parse the corrected response
                try:
                    data = json.loads(response)
                    result = output_schema.parse_obj(data)
                    return result
                except (json.JSONDecodeError, ValidationError) as e:
                    self.logger.error(
                        "Failed to parse corrected response: %s", 
                        str(e),
                        response=response
                    )
                    raise ValidationError(
                        f"Could not parse OpenAI response as valid JSON for the schema: {str(e)}",
                        output_schema
                    )
                    
        except Exception as e:
            self._handle_error(e, prompt)
            # If we reach here, fail_on_error is False
            raise ValidationError(
                f"Error generating schema-based response: {str(e)}",
                output_schema
            )
            
    def _attempt_json_correction(self, text: str) -> Optional[str]:
        """Attempt to correct common JSON formatting issues.
        
        Args:
            text: Text to correct
            
        Returns:
            Optional[str]: Corrected JSON text, or None if correction failed
        """
        # Try to extract JSON content if it's embedded in other text
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                text = text[start:end]
                
        # Replace single quotes with double quotes
        text = text.replace("'", '"')
        
        # Try to fix trailing commas
        text = text.replace(",\n}", "\n}")
        text = text.replace(",\n]", "\n]")
        
        # Try to fix missing quotes around keys
        import re
        text = re.sub(r'(\s*)(\w+)(\s*):', r'\1"\2"\3:', text)
        
        # Try to verify it's valid JSON
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            return None