\
import asyncio
import logging
import os
from pydantic import BaseModel, Field
from typing import List

# Ensure utils and ailf are in the path for direct execution from examples dir.
# This is a common pattern for example scripts.
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.ai.engine import AIEngine
# We don't directly use ToolManager/Selector here, but AIEngine does.

# Setup basic logging to see debug messages from AIEngine, ToolManager, etc.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define a Pydantic model for the tool's output
class WeatherResponse(BaseModel):
    location: str = Field(..., description="The location for which weather is reported.")
    temperature: str = Field(..., description="The temperature.")
    unit: str = Field(..., description="The unit of temperature (e.g., celsius, fahrenheit).")
    condition: str = Field(..., description="The weather condition (e.g., Cloudy, Sunny).")

# Instantiate AIEngine
# AIEngine's initialization (specifically _setup_agent) will try to get an API key.
# If the relevant API key (e.g., OPENAI_API_KEY for provider 'openai') is not set,
# it will raise a ValueError.
engine = AIEngine(
    feature_name="weather_reporter_example",
    # pydantic-ai will use this model. If API key is dummy, actual call will fail.
    model_name="openai:gpt-3.5-turbo",
    instructions="You are a helpful assistant that can provide weather information."
)

@engine.add_tool
async def get_current_weather(location: str, unit: str = "celsius") -> WeatherResponse:
    """
    Gets the current weather for a specified location.
    Provide the city name for the location.
    The unit can be 'celsius' or 'fahrenheit'.
    """
    logger.info(f"TOOL EXECUTING: get_current_weather(location='{location}', unit='{unit}')")
    # Simulate calling a weather API
    if "San Francisco" in location:
        data = {"location": location, "temperature": "15", "unit": unit, "condition": "Cloudy"}
    elif "New York" in location:
        data = {"location": location, "temperature": "22", "unit": unit, "condition": "Sunny"}
    else:
        data = {"location": location, "temperature": "unknown", "unit": unit, "condition": "unknown"}
    
    # Log the data being returned by the tool
    logger.debug(f"Tool get_current_weather returning: {data}")
    return WeatherResponse(**data)

async def main():
    logger.info("Starting AILF Tooling integration test.")
    logger.info("This test checks if tool execution is routed through AILF's ToolManager.")
    logger.info("Look for log messages from 'AIEngine', 'ailf.tooling.manager', and the tool itself.")

    # Test 1: Prompt that should trigger the tool
    prompt1 = "What's the weather like in San Francisco?"
    logger.info(f"Test 1: Sending prompt: '{prompt1}'")
    try:
        # engine.generate() calls pydantic-ai's agent.run().
        # The agent should identify the tool and execute it.
        # The wrapper in AIEngine.add_tool routes this execution to ToolManager.
        response1 = await engine.generate(prompt=prompt1)
        logger.info(f"Test 1: Received response from AIEngine: {response1}")
    except Exception as e:
        logger.error(f"Test 1: An error occurred: {e}", exc_info=True)
    logger.info("-" * 50)

    # Test 2: Another prompt for the same tool with different arguments
    prompt2 = "Tell me the weather in New York in fahrenheit."
    logger.info(f"Test 2: Sending prompt: '{prompt2}'")
    try:
        response2 = await engine.generate(prompt=prompt2)
        logger.info(f"Test 2: Received response from AIEngine: {response2}")
    except Exception as e:
        logger.error(f"Test 2: An error occurred: {e}", exc_info=True)
    logger.info("-" * 50)

    # Test 3: A prompt that should ideally NOT trigger the tool
    # (Behavior depends on the LLM and pydantic-ai's tool selection logic)
    prompt3 = "What is the capital of France?"
    logger.info(f"Test 3: Sending prompt: '{prompt3}'")
    try:
        response3 = await engine.generate(prompt=prompt3)
        logger.info(f"Test 3: Received response from AIEngine: {response3}")
    except Exception as e:
        logger.error(f"Test 3: An error occurred: {e}", exc_info=True)
    logger.info("-" * 50)

    logger.info("AILF Tooling integration test finished.")
    logger.info("To confirm successful integration, check logs for messages indicating:")
    logger.info("1. Tool registration with AILF ToolManager (from AIEngine.add_tool).")
    logger.info("2. Pydantic-AI invoking the tool via ToolManager (from the wrapper in AIEngine.add_tool).")
    logger.info("3. ToolManager executing the tool (from ailf.tooling.manager.ToolManager).")
    logger.info("4. The tool itself logging its execution (e.g., 'TOOL EXECUTING: get_current_weather').")

if __name__ == "__main__":
    # Set a dummy API key if not present, to allow AIEngine to initialize.
    # Pydantic-AI's Agent requires an API key. Actual LLM calls will likely fail
    # with a dummy key, but this allows testing the tool invocation path.
    default_provider_key = "OPENAI_API_KEY" # Assuming default provider is OpenAI
    if default_provider_key not in os.environ:
        logger.warning(
            f"{default_provider_key} not set in environment. "
            f"Setting a dummy key ('dummy_for_test') for AIEngine initialization. "
            f"Actual LLM calls will likely fail."
        )
        os.environ[default_provider_key] = "dummy_for_test"
    
    asyncio.run(main())
