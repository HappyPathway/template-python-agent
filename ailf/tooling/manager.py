# /workspaces/template-python-dev/ailf/tooling/manager.py
import importlib
import inspect
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

from ailf.schemas.tooling import ToolDescription
# Optional: from ailf.ai_engine import AIEngine # If AI engine integration is needed later

# Logger placeholder
# import logging
# logger = logging.getLogger(__name__)

class ToolExecutionError(Exception):
    """Custom exception for errors during tool execution."""
    pass

def _load_model_from_ref(model_ref: str) -> Optional[Type[BaseModel]]:
    """
    Dynamically loads a Pydantic model class from a string reference.

    :param model_ref: The string reference, e.g., "my_package.my_module.MyModel".
    :type model_ref: str
    :return: The loaded Pydantic model class, or None if loading fails.
    :rtype: Optional[Type[BaseModel]]
    """
    if not model_ref:
        return None
    try:
        module_path, class_name = model_ref.rsplit('.', 1)
        module = importlib.import_module(module_path)
        model_class = getattr(module, class_name)
        if not issubclass(model_class, BaseModel):
            # logger.warning(f"Warning: {model_ref} is not a Pydantic BaseModel subclass.")
            print(f"Warning: {model_ref} is not a Pydantic BaseModel subclass.") # Replaced logger with print for now
            return None
        return model_class
    except (ImportError, AttributeError, ValueError) as e:
        # logger.error(f"Error loading model from ref '{model_ref}': {e}")
        print(f"Error loading model from ref '{model_ref}': {e}") # Replaced logger with print for now
        return None

class ToolManager:
    """
    Manages the registration and execution of tools.
    It stores tool functions and their descriptions, handles input/output validation
    using Pydantic schemas, and auto-detects async tool functions.
    """
    def __init__(self, ai_engine: Optional[Any] = None): # ai_engine is kept for potential future use
        """
        Initialize the ToolManager.
        :param ai_engine: Optional AI engine, could be used for pre/post processing or error handling.
        """
        self.ai_engine = ai_engine
        self._tool_functions: Dict[str, Callable] = {}
        self._tool_descriptions: Dict[str, ToolDescription] = {}

    def register_tool(self, tool_function: Callable, description: ToolDescription) -> None:
        """
        Register a tool function along with its description.
        The `is_async` field in the provided `ToolDescription` instance will be
        updated based on introspection of the `tool_function`.

        :param tool_function: The actual callable function for the tool.
        :type tool_function: Callable
        :param description: The ToolDescription object for the tool.
        :type description: ToolDescription
        :raises ValueError: If a tool with the same name is already registered.
        """
        if description.name in self._tool_functions:
            raise ValueError(f"Tool with name '{description.name}' already registered.")

        # Auto-detect and set is_async based on the tool_function, updating the description instance.
        detected_is_async = inspect.iscoroutinefunction(tool_function)
        if description.is_async != detected_is_async:
            # logger.info(f"Tool '{description.name}': is_async flag updated by ToolManager. Was: {description.is_async}, Detected: {detected_is_async}.")
            print(f"Info: Tool '{description.name}' is_async flag updated by ToolManager. Was: {description.is_async}, Detected: {detected_is_async}.") # Replaced logger
            description.is_async = detected_is_async
        
        self._tool_functions[description.name] = tool_function
        self._tool_descriptions[description.name] = description # Store the (potentially updated) description

    def get_tool_description(self, tool_name: str) -> Optional[ToolDescription]:
        """Get the description of a registered tool."""
        return self._tool_descriptions.get(tool_name)

    def list_tools(self) -> List[ToolDescription]:
        """List descriptions of all registered tools."""
        return list(self._tool_descriptions.values())

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Execute a registered tool by its name.

        :param tool_name: The name of the tool to execute.
        :type tool_name: str
        :param tool_input: A dictionary of parameters for the tool.
        :type tool_input: Dict[str, Any]
        :return: The result of the tool execution, potentially a Pydantic model instance if output schema is defined.
        :rtype: Any
        :raises ToolExecutionError: If the tool is not found, input/output validation fails, or execution fails.
        """
        if tool_name not in self._tool_functions:
            # logger.error(f"Tool '{tool_name}' not found.")
            raise ToolExecutionError(f"Tool '{tool_name}' not found.")

        tool_func = self._tool_functions[tool_name]
        tool_desc = self._tool_descriptions[tool_name]

        validated_input_data = tool_input
        InputModel = _load_model_from_ref(tool_desc.input_schema_ref) if tool_desc.input_schema_ref else None
        
        if InputModel:
            try:
                # If tool_input is already an instance of the model, use it directly (less common for dict input)
                if isinstance(tool_input, InputModel):
                    validated_model_instance = tool_input
                else:
                    validated_model_instance = InputModel(**tool_input)
                validated_input_data = validated_model_instance.model_dump()
            except ValidationError as ve:
                # logger.error(f"Input validation failed for tool {tool_name} using {tool_desc.input_schema_ref}: {ve}")
                raise ToolExecutionError(f"Input validation failed for tool {tool_name}: {ve}") from ve
            except Exception as e: # Catch other instantiation errors
                # logger.error(f"Error preparing input for tool '{tool_name}': {e}")
                raise ToolExecutionError(f"Error preparing input for tool '{tool_name}': {e}")
        # else:
            # logger.debug(f"No input schema ref for tool {tool_name} or schema not loaded. Proceeding without Pydantic input validation.")
            # print(f"Debug: No input schema ref for tool {tool_name} or schema not loaded. Proceeding without Pydantic input validation.")


        try:
            if tool_desc.is_async:
                result = await tool_func(**validated_input_data)
            else:
                result = tool_func(**validated_input_data)
            
            OutputModel = _load_model_from_ref(tool_desc.output_schema_ref) if tool_desc.output_schema_ref else None
            if OutputModel:
                try:
                    if isinstance(result, OutputModel):
                        return result # Already the correct Pydantic model instance
                    elif isinstance(result, BaseModel): # It's a Pydantic model, but maybe not the exact OutputModel
                        # Attempt to convert/validate by dumping and reloading
                        # logger.debug(f"Tool {tool_name} returned a Pydantic model of type {type(result).__name__}, expected {OutputModel.__name__}. Attempting conversion.")
                        print(f"Debug: Tool {tool_name} returned a Pydantic model of type {type(result).__name__}, expected {OutputModel.__name__}. Attempting conversion.")
                        return OutputModel(**result.model_dump())
                    elif isinstance(result, dict):
                        return OutputModel(**result)
                    else:
                        # This case is tricky. If OutputModel expects a single field (e.g., result: str)
                        # and the tool returns just that value. Pydantic v2 might handle this with model_validate.
                        # For now, assume if it's not a dict or BaseModel, it might be a direct value for a single-field model.
                        # This requires OutputModel to be defined to accept such input.
                        # Example: class MyOutput(BaseModel): value: str; MyOutput.model_validate(tool_result_str)
                        # If the tool returns a raw value, and OutputModel expects {'some_field': raw_value}, this will fail.
                        # We will try direct validation, which might work for simple cases or if OutputModel is designed for it.
                        return OutputModel.model_validate(result)

                except ValidationError as ve:
                    # logger.error(f"Output validation failed for tool {tool_name} using {tool_desc.output_schema_ref}: {ve}")
                    raise ToolExecutionError(f"Output validation failed for tool {tool_name}: {ve}") from ve
                except Exception as e: # Catch other instantiation errors during output validation
                    # logger.error(f"Error validating output for tool '{tool_name}' with schema {tool_desc.output_schema_ref}: {e}")
                    raise ToolExecutionError(f"Error validating output for tool '{tool_name}': {e}")
            # else:
                # logger.debug(f"No output schema ref for tool {tool_name} or schema not loaded. Returning raw result.")
                # print(f"Debug: No output schema ref for tool {tool_name} or schema not loaded. Returning raw result.")
            
            return result
        except Exception as e:
            if isinstance(e, ToolExecutionError): # Re-raise if it's already our specific error
                raise
            # logger.exception(f"Error executing tool {tool_name}: {e}")
            raise ToolExecutionError(f"Error during execution of tool {tool_name}: {e}") from e
