"""Pydantic schemas for AILF prompt engineering and management."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import time

class PromptTemplateV1(BaseModel):
    """
    Represents a versioned prompt template.
    """
    template_id: str = Field(..., description="Unique identifier for this prompt template.")
    version: int = Field(1, description="Version number of this prompt template.")
    description: Optional[str] = Field(None, description="A brief description of what this prompt is for.")
    
    system_prompt: Optional[str] = Field(None, description="The system-level instructions for the AI model.")
    user_prompt_template: str = Field(..., description="The template for the user-facing prompt, may contain placeholders like {variable}.")
    
    # Placeholders expected by the user_prompt_template
    placeholders: List[str] = Field(default_factory=list, description="List of placeholder names (e.g., ['query', 'context']) used in user_prompt_template.")
    
    # Metadata for tracking and optimization
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing or searching for this template.")
    created_at: float = Field(default_factory=time.time, description="Timestamp of template creation.")
    updated_at: Optional[float] = Field(None, description="Timestamp of last template update.")
    
    # Example usage or notes for developers
    usage_notes: Optional[str] = Field(None, description="Notes on how and when to use this prompt template.")
    
    # Expected output structure or schema (optional, for guidance or validation)
    expected_output_schema_name: Optional[str] = Field(None, description="Name of the Pydantic schema expected as output when using this prompt.")

    def fill(self, **kwargs: Any) -> str:
        """
        Fills the user_prompt_template with provided keyword arguments.
        
        :param kwargs: Keyword arguments corresponding to placeholders in the template.
        :type kwargs: Any
        :raises KeyError: If a required placeholder is not provided in kwargs.
        :return: The formatted user prompt string.
        :rtype: str
        """
        try:
            return self.user_prompt_template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing placeholder: {e}. Required: {self.placeholders}, Provided: {list(kwargs.keys())}") from e

class PromptLibraryConfig(BaseModel):
    """
    Configuration for managing a library of prompt templates.
    """
    library_path: Optional[str] = Field(None, description="Path to a directory where prompt templates (e.g., JSON files) are stored.")
    # Potentially add database connection details if templates are stored in a DB
    # db_connection_string: Optional[str] = None
    default_prompt_id: Optional[str] = Field(None, description="Default prompt to use if a specific one isn't requested.")

# Example of how a PromptTemplateV1 might be stored or loaded (e.g., as a JSON file)
# {
#   "template_id": "general_query_v1",
#   "version": 1,
#   "description": "A general purpose query prompt for answering user questions.",
#   "system_prompt": "You are a helpful AI assistant. Answer the user's question clearly and concisely.",
#   "user_prompt_template": "User question: {query}\nAdditional context (if any): {context}",
#   "placeholders": ["query", "context"],
#   "tags": ["general", "qa"],
#   "usage_notes": "Use for straightforward questions. Provide relevant context if available.",
#   "expected_output_schema_name": "SimpleAnswer"
# }
