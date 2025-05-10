"""ReAct (Reason-Act) Processor for AILF agents."""

import asyncio
import json
from typing import Any, Callable, Coroutine, Dict, Optional, Type, Tuple, List

from pydantic import BaseModel, Field

from ailf.schemas.cognition import ReActState, ReActStep, ReActStepType

# Placeholder for AIEngine and ToolRegistry/ToolExecutor
# In a real scenario, these would be properly imported and configured.
try:
    from utils.ai.engine import AIEngine
except ImportError:
    class AIEngine: # type: ignore
        async def analyze(self, content: str, output_schema: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
            print(f"Warning: Using placeholder AIEngine. Analyze called with prompt: {system_prompt}")
            # Simulate AI deciding on a thought or action based on the prompt
            if "what is the weather" in content.lower():
                return ReActStep(step_type=ReActStepType.ACTION, content="Get current weather for Paris", tool_name="get_weather", tool_input={"location": "Paris"})
            elif "what is ailf" in content.lower():
                 return ReActStep(step_type=ReActStepType.THOUGHT, content="AILF is an Agentic AI Library Framework. I should state this as the answer.")
            return ReActStep(step_type=ReActStepType.THOUGHT, content="I need to think about this more.")

# Define a type for an async tool function
AsyncTool = Callable[..., Coroutine[Any, Any, Any]]

class ReActProcessor:
    """
    Manages a ReAct (Reason-Act) loop to process prompts and utilize tools.
    """

    def __init__(self, ai_engine: AIEngine, max_steps: int = 10):
        """
        Initializes the ReActProcessor.

        :param ai_engine: The AI engine for generating thoughts and actions.
        :type ai_engine: AIEngine
        :param max_steps: Default maximum number of steps for a ReAct loop.
        :type max_steps: int
        """
        self.ai_engine = ai_engine
        self.tools: Dict[str, AsyncTool] = {}
        self.default_max_steps = max_steps

    def register_tool(self, name: str, tool_func: AsyncTool, description: Optional[str] = None) -> None:
        """
        Registers an asynchronous tool that the ReAct processor can use.

        :param name: The name of the tool.
        :type name: str
        :param tool_func: The asynchronous function implementing the tool.
        :type tool_func: AsyncTool
        :param description: A description of the tool (for LLM context).
        :type description: Optional[str]
        """
        self.tools[name] = tool_func
        # In a more advanced system, the description would be used to inform the LLM about available tools.
        print(f"Tool '{name}' registered. Description: {description if description else 'N/A'}")

    async def _execute_tool(self, tool_name: str, tool_input: Optional[Dict[str, Any]]) -> str:
        """
        Executes a registered tool with the given input.

        :param tool_name: The name of the tool to execute.
        :type tool_name: str
        :param tool_input: The input for the tool.
        :type tool_input: Optional[Dict[str, Any]]
        :return: The result of the tool execution as a string.
        :rtype: str
        """
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found."
        try:
            tool_func = self.tools[tool_name]
            # Simple argument handling: pass tool_input as kwargs if it's a dict
            if tool_input is None:
                result = await tool_func()
            elif isinstance(tool_input, dict):
                result = await tool_func(**tool_input)
            else:
                # Fallback or error if tool_input is not a dict and not None
                return f"Error: Invalid input type for tool '{tool_name}'. Expected dict or None."
            return str(result)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    def _format_history_for_prompt(self, history: List[ReActStep]) -> str:
        """Formats the ReAct history into a string for the LLM prompt."""
        formatted_history = ""
        for step in history:
            if step.step_type == ReActStepType.THOUGHT:
                formatted_history += f"Thought: {step.content}\n"
            elif step.step_type == ReActStepType.ACTION:
                formatted_history += f"Action: Tool: {step.tool_name}, Input: {json.dumps(step.tool_input)}\n"
            elif step.step_type == ReActStepType.OBSERVATION:
                formatted_history += f"Observation: {step.content}\n"
        return formatted_history.strip()

    async def process(self, initial_prompt: str, max_steps: Optional[int] = None) -> ReActState:
        """
        Processes a given prompt using the ReAct loop.

        :param initial_prompt: The initial prompt or question to address.
        :type initial_prompt: str
        :param max_steps: Maximum number of steps for this specific processing run.
                          Defaults to the processor's default_max_steps.
        :type max_steps: Optional[int]
        :return: The final state of the ReAct process.
        :rtype: ReActState
        """
        current_max_steps = max_steps if max_steps is not None else self.default_max_steps
        state = ReActState(initial_prompt=initial_prompt, max_steps=current_max_steps)

        while state.current_step_number < state.max_steps and not state.is_halted:
            state.current_step_number += 1
            print(f"--- ReAct Step {state.current_step_number} ---")

            # Construct prompt for AIEngine
            history_str = self._format_history_for_prompt(state.history)
            tool_descriptions = "\n".join([f"- {name}: {getattr(func, '__doc__', 'No description').strip()}" for name, func in self.tools.items()])
            # A more sophisticated prompt would be used in a real system
            ai_prompt_content = (
                f"You are a helpful assistant. Based on the history, decide on the next thought or action.\n"
                f"Initial Prompt: {state.initial_prompt}\n"
                f"History:\n{history_str if history_str else 'No history yet.'}\n"
                f"Available tools:\n{tool_descriptions if tool_descriptions else 'No tools available.'}\n"
                f"What is the next step (thought or action)? If you have the final answer, express it as a thought and then set final_answer."
            )
            
            # Get next step from AIEngine (thought or action)
            # The AIEngine is expected to return a ReActStep model or similar structure.
            next_step_model = await self.ai_engine.analyze(
                content=ai_prompt_content, # This content might need to be more structured
                output_schema=ReActStep, # Expecting the LLM to fill this schema
                system_prompt="You are a ReAct agent. Generate the next thought or action based on the provided context and history."
            )

            if not isinstance(next_step_model, ReActStep):
                print("Error: AIEngine did not return a valid ReActStep. Halting.")
                state.history.append(ReActStep(step_type=ReActStepType.OBSERVATION, content="Error: AI did not produce a valid next step."))
                state.is_halted = True
                break
            
            current_step: ReActStep = next_step_model
            state.history.append(current_step)
            print(f"{current_step.step_type.value.capitalize()}: {current_step.content}")

            if current_step.step_type == ReActStepType.THOUGHT:
                # If the thought contains a final answer (heuristic)
                if "final answer is" in current_step.content.lower() or state.current_step_number >= state.max_steps -1 : # Simple check
                    # A more robust way would be for the LLM to explicitly signal completion
                    # or for the ReActStep schema to have a `is_final_answer` field.
                    state.final_answer = current_step.content # Or extract from content
                    state.is_halted = True
                    print(f"Final Answer (from thought): {state.final_answer}")
            
            elif current_step.step_type == ReActStepType.ACTION:
                if not current_step.tool_name:
                    observation_content = "Error: Action specified but no tool_name provided."
                    print(observation_content)
                    state.history.append(ReActStep(step_type=ReActStepType.OBSERVATION, content=observation_content))
                    state.is_halted = True # Halt on critical error
                    break
                
                print(f"Action: Tool: {current_step.tool_name}, Input: {current_step.tool_input}")
                observation_content = await self._execute_tool(current_step.tool_name, current_step.tool_input)
                print(f"Observation: {observation_content}")
                state.history.append(ReActStep(step_type=ReActStepType.OBSERVATION, content=observation_content))
                
                # Heuristic: if observation contains critical error, halt.
                if "error:" in observation_content.lower() and ("tool \'" in observation_content.lower() and "\' not found" in observation_content.lower()):
                    state.is_halted = True

            if state.current_step_number >= state.max_steps and not state.is_halted:
                print("Max steps reached. Halting.")
                state.is_halted = True
                if not state.final_answer:
                    state.final_answer = "Process halted due to max steps without a definitive answer."

        return state

# Example Usage (Illustrative)
async def example_react_usage():
    # 1. Setup AIEngine (using placeholder)
    ai_engine_instance = AIEngine()

    # 2. Initialize ReActProcessor
    react_processor = ReActProcessor(ai_engine=ai_engine_instance, max_steps=5)

    # 3. (Optional) Register tools
    async def get_weather(location: str) -> str:
        """Gets the current weather for a given location."""
        # In a real tool, this would call an API
        if location.lower() == "paris":
            return "The weather in Paris is sunny and 25°C."
        return f"Sorry, I don't know the weather for {location}."
    
    react_processor.register_tool("get_weather", get_weather, description="Gets the current weather for a given location.")

    # 4. Process a prompt
    print("\n--- Example 1: Weather Query ---")
    initial_prompt_weather = "What is the weather like in Paris?"
    final_state_weather = await react_processor.process(initial_prompt_weather)
    print(f"\nFinal State for Weather Query: Is Halted: {final_state_weather.is_halted}, Final Answer: {final_state_weather.final_answer}")
    # print(f"Full History: {final_state_weather.model_dump_json(indent=2)}")

    print("\n--- Example 2: General Knowledge Query ---")
    initial_prompt_knowledge = "What is AILF?"
    final_state_knowledge = await react_processor.process(initial_prompt_knowledge)
    print(f"\nFinal State for Knowledge Query: Is Halted: {final_state_knowledge.is_halted}, Final Answer: {final_state_knowledge.final_answer}")
    # print(f"Full History: {final_state_knowledge.model_dump_json(indent=2)}")

if __name__ == "__main__":
    # asyncio.run(example_react_usage()) # Commented out to prevent execution during tool use
    pass
