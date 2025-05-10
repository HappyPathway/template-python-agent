"""Pydantic schemas for ailf.tooling."""
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field

class ToolInputSchema(BaseModel):
    """Base model for a tool's input schema. Tools should define their own specific Pydantic models inheriting from this or BaseModel."""
    # Example: query: str
    # Example: items: List[Any]
    pass

class ToolOutputSchema(BaseModel):
    """Base model for a tool's output schema. Tools should define their own specific Pydantic models inheriting from this or BaseModel."""
    # Example: result: str
    # Example: success: bool
    pass

class ToolDescription(BaseModel):
    """Enhanced description for a tool, including detailed metadata."""
    name: str = Field(description="Unique name of the tool.")
    description: str = Field(description="Detailed description of what the tool does and its purpose.")
    categories: List[str] = Field(default_factory=list, description="Categories the tool belongs to (e.g., 'data_analysis', 'text_generation').")
    keywords: List[str] = Field(default_factory=list, description="Keywords for searching and discovering the tool.")
    usage_examples: List[str] = Field(default_factory=list, description="Plain language examples of how to use the tool or what queries it can answer.")
    
    input_schema_ref: Optional[str] = Field(
        default=None, 
        description="Fully qualified string reference to the Pydantic model for the tool's input (e.g., 'my_module.schemas.MyToolInput')."
    )
    output_schema_ref: Optional[str] = Field(
        default=None, 
        description="Fully qualified string reference to the Pydantic model for the tool's output (e.g., 'my_module.schemas.MyToolOutput')."
    )
    
    input_schema_definition: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="JSON schema dictionary defining the tool's input. Can be used if `input_schema_ref` is not available or for external systems."
    )
    output_schema_definition: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="JSON schema dictionary defining the tool's output. Can be used if `output_schema_ref` is not available or for external systems."
    )

    # Optional embeddings for semantic search
    name_embedding: Optional[List[float]] = Field(default=None, description="Embedding of the tool name for semantic search.")
    description_embedding: Optional[List[float]] = Field(default=None, description="Embedding of the tool description for semantic search.")
    combined_embedding: Optional[List[float]] = Field(default=None, description="Combined embedding (e.g., name + description + keywords) for semantic search.")

    # Versioning and other metadata
    version: str = Field(default="1.0.0", description="Version of the tool.")
    author: Optional[str] = Field(default=None, description="Author or maintainer of the tool.")
    is_async: bool = Field(default=False, description="Indicates if the tool's primary execution method is asynchronous. This can be auto-detected by ToolManager upon registration.")
