#!/usr/bin/env python3
"""AI Engine Usage Example.

This example script demonstrates the usage of different AI engine implementations
and how to extend them with custom functionality.
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, List, Optional, Type

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError(
        "Pydantic dependencies not installed. "
        "Install them with: pip install pydantic"
    )

from ailf.core.ai_engine_base import AIEngineBase
from ailf.ai.engine_factory import AIEngineFactory


class CustomAIEngine(AIEngineBase):
    """Example of a custom AI engine implementation.
    
    This class extends AIEngineBase to create a simple mock AI engine
    for testing and demonstration purposes.
    """
    
    def __init__(self, responses=None, config=None):
        """Initialize with custom responses dictionary."""
        self.responses = responses or {
            "hello": "Hello! How can I assist you today?",
            "time": f"The current time is {time.strftime('%H:%M:%S')}",
            "default": "I'm a mock AI engine. I don't know how to respond to that."
        }
        super().__init__(config)
        
    def _get_default_config(self):
        """Override default config."""
        config = super()._get_default_config()
        config["response_delay"] = 0.5  # Simulate network delay
        return config
        
    def _preprocess_prompt(self, prompt, context=None):
        """Apply custom prompt preprocessing."""
        prompt = super()._validate_prompt(prompt)
        # Convert prompt to lowercase for case-insensitive matching
        return prompt.lower().strip()
        
    async def generate(self, prompt, **kwargs):
        """Generate a mock response based on the prompt."""
        # Apply preprocessing
        processed_prompt = self._preprocess_prompt(prompt)
        
        # Simulate network delay
        delay = self.config.get("response_delay", 0.5)
        await asyncio.sleep(delay)
        
        # Look for a matching response or use default
        for key, response in self.responses.items():
            if key in processed_prompt:
                result = response
                break
        else:
            result = self.responses.get("default", "No response available")
            
        # Log the request
        metrics = {
            "latency": delay,
            "model": "mock-ai",
            "tokens": len(prompt.split())
        }
        self._log_request(prompt, result, metrics)
        
        return result
        
    async def generate_with_schema(self, prompt, output_schema, **kwargs):
        """Generate a structured response matching the schema."""
        # For demonstration, we'll create a valid instance of the schema with mock data
        schema_dict = output_schema.schema()
        
        # Extract required fields and their types
        properties = schema_dict.get("properties", {})
        result = {}
        
        # Generate mock data for each field based on its type
        for field_name, field_info in properties.items():
            field_type = field_info.get("type")
            if field_type == "string":
                result[field_name] = f"Mock {field_name} for: {prompt}"
            elif field_type == "integer":
                result[field_name] = 42
            elif field_type == "number":
                result[field_name] = 3.14
            elif field_type == "boolean":
                result[field_name] = True
            elif field_type == "array":
                result[field_name] = ["item1", "item2"]
            elif field_type == "object":
                result[field_name] = {"key": "value"}
                
        # Log the request with metrics
        metrics = {
            "latency": self.config.get("response_delay", 0.5),
            "model": "mock-ai",
            "tokens": len(prompt.split())
        }
        self._log_request(prompt, str(result), metrics)
        
        # Create and return an instance of the schema
        return output_schema.parse_obj(result)


class WeatherRequest(BaseModel):
    """Schema for weather request data."""
    location: str = Field(description="City name or location")
    days: int = Field(description="Number of days to forecast", ge=1, le=7)


class WeatherForecast(BaseModel):
    """Schema for weather forecast response."""
    location: str = Field(description="Location for the forecast")
    current_temp: float = Field(description="Current temperature in Celsius")
    conditions: str = Field(description="Current weather conditions")
    forecast: List[Dict[str, Any]] = Field(description="Daily forecasts")


async def simple_generation_example(engine: AIEngineBase):
    """Run a simple text generation example."""
    print(f"\nRunning simple generation with {engine.__class__.__name__}")
    print("-" * 50)
    
    prompt = "Write a short poem about artificial intelligence."
    
    print(f"Prompt: {prompt}")
    response = await engine.generate(prompt)
    print(f"Response:\n{response}")
    
    # Get metrics
    metrics = engine.get_metrics()
    print("\nMetrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")


async def structured_generation_example(engine: AIEngineBase):
    """Run a structured data generation example."""
    print(f"\nRunning structured generation with {engine.__class__.__name__}")
    print("-" * 50)
    
    prompt = "Provide a 3-day weather forecast for Seattle, Washington."
    
    print(f"Prompt: {prompt}")
    try:
        # Generate structured data
        weather = await engine.generate_with_schema(
            prompt,
            WeatherForecast,
            temperature=0.2
        )
        
        # Print the result in a nice format
        print("\nStructured Response:")
        print(f"Location: {weather.location}")
        print(f"Current Temperature: {weather.current_temp}°C")
        print(f"Conditions: {weather.conditions}")
        print("\nForecast:")
        for i, day in enumerate(weather.forecast):
            print(f"  Day {i+1}: High: {day.get('high')}°C, "
                  f"Low: {day.get('low')}°C, "
                  f"Conditions: {day.get('conditions')}")
                  
    except Exception as e:
        print(f"Error generating structured response: {str(e)}")


async def custom_engine_example():
    """Demonstrate a custom engine implementation."""
    print("\nRunning custom engine example")
    print("-" * 50)
    
    # Create custom responses
    responses = {
        "weather": "It's a sunny day with a few clouds. Temperature is 22°C.",
        "help": "I can provide information about weather, time, or greet you!",
        "hello": "Hello there! I'm a custom AI engine.",
        "default": "I don't have a specific response for that query."
    }
    
    # Create custom engine
    engine = CustomAIEngine(responses=responses, config={"response_delay": 0.3})
    
    # Test with a few prompts
    prompts = [
        "Hello, how are you today?",
        "What's the weather like?",
        "Can you help me with something?",
        "Tell me about quantum physics."
    ]
    
    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        response = await engine.generate(prompt)
        print(f"Response: {response}")
        
    # Try structured generation
    class Profile(BaseModel):
        name: str
        age: int
        bio: str
        
    print("\nStructured generation:")
    result = await engine.generate_with_schema(
        "Create a profile for a fictional character",
        Profile
    )
    print(f"Generated profile: {result.name}, {result.age} years old")
    print(f"Bio: {result.bio}")


async def factory_example():
    """Demonstrate the AI engine factory."""
    print("\nRunning AI engine factory example")
    print("-" * 50)
    
    factory = AIEngineFactory()
    
    # Register our custom engine
    factory.register_engine("custom", CustomAIEngine)
    
    # List available engines
    engines = factory.list_available_engines()
    print("Available engines:")
    for name in engines:
        print(f"  - {name}")
        
    # Create an engine from config
    config = {
        "provider": "custom",
        "config": {
            "response_delay": 0.2
        }
    }
    
    engine = factory.create_engine_from_config(config)
    print(f"\nCreated engine: {engine.__class__.__name__}")
    
    # Test the engine
    response = await engine.generate("Hello there!")
    print(f"Response: {response}")


async def main():
    """Run the AI engine examples."""
    print("AI Engine Implementation Examples\n" + "="*30)
    
    # First, check if API keys are available for actual engines
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # Always run the custom engine example
    await custom_engine_example()
    
    # Run the factory example
    await factory_example()
    
    # If API keys are available, run examples with real engines
    factory = AIEngineFactory()
    engines = []
    
    if openai_key:
        try:
            from ailf.ai.openai_engine import OpenAIEngine
            engines.append(OpenAIEngine(api_key=openai_key, model="gpt-4o"))
        except ImportError:
            print("\nOpenAI package not installed. Skipping OpenAI examples.")
    else:
        print("\nOpenAI API key not found in environment. Skipping OpenAI examples.")
        
    if anthropic_key:
        try:
            from ailf.ai.anthropic_engine import AnthropicEngine
            engines.append(AnthropicEngine(api_key=anthropic_key))
        except ImportError:
            print("\nAnthropic package not installed. Skipping Anthropic examples.")
    else:
        print("\nAnthropic API key not found in environment. Skipping Anthropic examples.")
        
    # If no real engines are available, use the custom engine for examples
    if not engines:
        print("\nNo API keys found for real engines. Using custom engine for examples.")
        engines.append(CustomAIEngine())
        
    # Run examples with available engines
    for engine in engines:
        await simple_generation_example(engine)
        await structured_generation_example(engine)


if __name__ == "__main__":
    asyncio.run(main())