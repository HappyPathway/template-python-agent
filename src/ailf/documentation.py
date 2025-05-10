"""Python Documentation Helper MCP Server.

This MCP server provides tools for inspecting Python objects and generating
structured documentation using AI assistance.

Key Features:
    - Import Python objects by name
    - Extract documentation using Python's introspection
    - Generate structured documentation using AI analysis
    - Support for modules, classes, functions, and more

Example:
    Start the server:
        >>> from ailf.documentation import start_server
        >>> 
        >>> # Start the server on default port
        >>> start_server()
        
    Or run directly:
        $ python -m ailf.documentation
"""
import asyncio
import importlib
import inspect
import os
import sys
import textwrap
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from ailf import BaseMCP, Context
from ailf.core.logging import setup_logging
from ailf.ai_engine import AIEngine

# Initialize logging
logger = setup_logging("doc_helper")

# Documentation result schema
class DocumentationResult(BaseModel):
    """Result of a documentation request.
    
    Attributes:
        object_name: Name of the object that was documented
        object_type: Type of the object (module, class, function, etc.)
        summary: Short summary of the object's purpose
        docstring: Original docstring of the object
        attributes: Dictionary of attributes and their values/types
        methods: List of method names if applicable
        signature: Function/method signature if applicable
        error: Error message if documentation failed
    """
    object_name: str
    object_type: str
    summary: str
    docstring: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    methods: List[str] = Field(default_factory=list)
    signature: Optional[str] = None
    error: Optional[str] = None

# Create MCP server
mcp = BaseMCP(
    name="Python Documentation Helper",
    instructions="""
    This tool helps you understand Python objects by providing structured documentation.
    You can get documentation for modules, classes, functions, and other Python objects
    by providing their fully qualified import path.
    """
)

class ImportError(Exception):
    """Error raised when an object cannot be imported."""
    pass


def safe_import(object_name: str) -> Tuple[Any, str]:
    """
    Safely import a Python object by its fully qualified name.
    
    Args:
        object_name: Fully qualified name of the object to import
        
    Returns:
        Tuple of (object, object_type)
        
    Raises:
        ImportError: If the object cannot be imported
    """
    parts = object_name.split(".")
    
    # Try importing the module first
    module_path = parts[0]
    try:
        module = importlib.import_module(module_path)
    except Exception as e:
        raise ImportError(f"Could not import module '{module_path}': {str(e)}")
    
    # For single-part names (just a module), return the module
    if len(parts) == 1:
        return module, "module"
    
    # For multi-part names, try to get the object from the module
    obj = module
    for i, part in enumerate(parts[1:], 1):
        # Try importing as a module first
        if i < len(parts) - 1:
            try:
                next_module_path = ".".join(parts[:i+1])
                next_module = importlib.import_module(next_module_path)
                obj = next_module
                continue
            except ImportError:
                pass  # Not a module, try as an attribute
        
        # Try getting as an attribute
        try:
            obj = getattr(obj, part)
        except AttributeError:
            full_path = ".".join(parts[:i+1])
            raise ImportError(f"Could not find '{part}' in '{'.'.join(parts[:i])}'")
    
    # Determine the object type
    if inspect.ismodule(obj):
        obj_type = "module"
    elif inspect.isclass(obj):
        obj_type = "class"
    elif inspect.isfunction(obj):
        obj_type = "function"
    elif inspect.ismethod(obj):
        obj_type = "method"
    elif inspect.isbuiltin(obj):
        obj_type = "builtin"
    else:
        obj_type = "attribute"
    
    return obj, obj_type


def capture_help_output(obj: Any) -> str:
    """
    Capture the output of Python's built-in help() function for an object.
    
    Args:
        obj: The Python object to get help for
        
    Returns:
        The captured help text
    """
    buffer = StringIO()
    with redirect_stdout(buffer):
        help(obj)
    return buffer.getvalue()


def get_object_documentation(obj: Any, obj_type: str, obj_name: str) -> Dict[str, Any]:
    """
    Extract documentation for a Python object using introspection.
    
    Args:
        obj: The Python object
        obj_type: Type of the object (module, class, function, etc.)
        obj_name: Name of the object
        
    Returns:
        Dictionary containing extracted documentation
    """
    doc_data = {
        "object_name": obj_name,
        "object_type": obj_type,
        "docstring": inspect.getdoc(obj) or "",
        "help_text": capture_help_output(obj),
    }
    
    # Add specific information based on object type
    if obj_type == "module":
        doc_data.update({
            "functions": [name for name, _ in inspect.getmembers(obj, inspect.isfunction)],
            "classes": [name for name, _ in inspect.getmembers(obj, inspect.isclass)],
            "attributes": {name: str(value) for name, value in inspect.getmembers(obj) 
                          if not name.startswith("__") and not inspect.isfunction(value) 
                          and not inspect.isclass(value) and not inspect.ismodule(value)},
        })
    elif obj_type == "class":
        doc_data.update({
            "bases": [base.__name__ for base in obj.__bases__],
            "methods": [name for name, _ in inspect.getmembers(obj, inspect.isfunction)],
            "attributes": {name: str(value) for name, value in inspect.getmembers(obj) 
                          if not name.startswith("__") and not inspect.isfunction(value) 
                          and not inspect.isclass(value) and not inspect.ismethod(value)},
        })
    elif obj_type in ("function", "method"):
        # Get signature
        try:
            signature = str(inspect.signature(obj))
        except (ValueError, TypeError):
            signature = "()"
        
        doc_data.update({
            "signature": signature,
            "source": inspect.getsource(obj) if not inspect.isbuiltin(obj) else None,
        })
    
    return doc_data


@mcp.tool()
async def get_documentation(ctx: Context, object_name: str) -> DocumentationResult:
    """
    Get documentation for a Python object by name.
    
    This tool will import the specified Python object by its fully qualified name,
    extract documentation using Python's introspection capabilities, and use AI to
    generate structured documentation.
    
    Args:
        ctx: Tool context
        object_name: Fully qualified name of the Python object (e.g., "os.path", "json.loads")
        
    Returns:
        Structured documentation for the object
        
    Example:
        To get documentation for the `json` module:
        ```python
        doc = await get_documentation("json")
        ```
        
        To get documentation for a specific function:
        ```python
        doc = await get_documentation("json.loads")
        ```
    """
    await ctx.info(f"Getting documentation for {object_name}")
    
    try:
        # Import the object
        obj, obj_type = safe_import(object_name)
        
        # Extract documentation
        raw_doc_data = get_object_documentation(obj, obj_type, object_name)
        
        # Create AI engine for processing the documentation
        ai_engine = AIEngine(
            feature_name="python_documentation",
            model_name="google-gla:gemini-1.5-pro"
        )
        
        # Generate structured documentation using AI
        prompt = textwrap.dedent(f"""
        Parse and structure the following Python documentation for '{object_name}' 
        (type: {obj_type}). Extract key information into a structured format.
        
        Documentation:
        ```
        {raw_doc_data.get('docstring', '')}
        
        Help text:
        {raw_doc_data.get('help_text', '')}
        ```
        
        Additional information:
        {raw_doc_data}
        """)
        
        # Generate structured documentation
        result = await ai_engine.generate(
            prompt=prompt,
            output_schema=DocumentationResult
        )
        
        # Return the structured documentation
        return result
    
    except ImportError as e:
        # Return error information in the result
        await ctx.error(f"Import error: {str(e)}")
        return DocumentationResult(
            object_name=object_name,
            object_type="unknown",
            summary="",
            error=f"Import error: {str(e)}"
        )
    except Exception as e:
        # Return error information in the result
        await ctx.error(f"Error getting documentation: {str(e)}")
        return DocumentationResult(
            object_name=object_name,
            object_type="unknown",
            summary="",
            error=f"Error: {str(e)}"
        )


async def start_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Start the documentation helper MCP server.
    
    Args:
        host: Host address to bind to
        port: Port number to listen on
    """
    await mcp.serve(host=host, port=port)


if __name__ == "__main__":
    # Run the server directly when the script is executed
    import argparse
    
    parser = argparse.ArgumentParser(description="Python Documentation Helper MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(start_server(host=args.host, port=args.port))
    except KeyboardInterrupt:
        print("\nServer stopped by user")
