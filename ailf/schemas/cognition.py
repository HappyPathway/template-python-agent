"""Pydantic schemas for AILF cognitive processing and reasoning."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import enum

class ReActStepType(str, enum.Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"

class ReActStep(BaseModel):
    """Represents a single step in a ReAct (Reason-Act) loop."""
    step_type: ReActStepType = Field(..., description="The type of ReAct step (thought, action, or observation).")
    content: str = Field(..., description="The textual content of the thought, action, or observation.")
    tool_name: Optional[str] = Field(None, description="If action, the name of the tool to be used.")
    tool_input: Optional[Dict[str, Any]] = Field(None, description="If action, the input for the tool.")
    timestamp: float = Field(default_factory=lambda: __import__('time').time(), description="Timestamp of the step.")

class ReActState(BaseModel):
    """Represents the current state of a ReAct process, including the history of steps."""
    initial_prompt: str = Field(..., description="The initial prompt or question that started the ReAct process.")
    max_steps: int = Field(10, description="Maximum number of steps allowed in the ReAct loop.")
    current_step_number: int = Field(0, description="The current step number.")
    history: List[ReActStep] = Field(default_factory=list, description="The history of ReAct steps taken so far.")
    final_answer: Optional[str] = Field(None, description="The final answer or result of the ReAct process, if reached.")
    is_halted: bool = Field(False, description="Flag indicating if the process has been halted (e.g., due to error, max steps, or successful completion).")

class PlanStep(BaseModel):
    """Represents a single step in a larger plan."""
    step_id: str = Field(..., description="Unique identifier for this plan step.")
    description: str = Field(..., description="A natural language description of what this step entails.")
    tool_name: Optional[str] = Field(None, description="The suggested tool to accomplish this step, if applicable.")
    tool_inputs: Optional[Dict[str, Any]] = Field(None, description="Suggested inputs for the tool.")
    dependencies: List[str] = Field(default_factory=list, description="List of step_ids that must be completed before this step can start.")
    status: str = Field("pending", description="Current status of the step (e.g., pending, in_progress, completed, failed).")
    result: Optional[Any] = Field(None, description="The outcome or result of executing this step.")

class Plan(BaseModel):
    """Represents a multi-step plan to achieve a goal."""
    plan_id: str = Field(..., description="Unique identifier for the entire plan.")
    goal: str = Field(..., description="The overall goal this plan aims to achieve.")
    steps: List[PlanStep] = Field(default_factory=list, description="The sequence of steps that make up the plan.")
    current_status: str = Field("pending", description="Overall status of the plan (e.g., pending, in_progress, completed, failed).")
    created_at: float = Field(default_factory=lambda: __import__('time').time(), description="Timestamp of plan creation.")
    updated_at: Optional[float] = Field(None, description="Timestamp of last plan update.")

class IntentRefinementRequest(BaseModel):
    """Schema for requesting intent refinement."""
    original_query: str
    conversation_history: Optional[List[Dict[str, str]]] = None # e.g., [{"role": "user", "content": "..."}]
    context_data: Optional[Dict[str, Any]] = None

class IntentRefinementResponse(BaseModel):
    """Schema for the response of an intent refinement process."""
    refined_query: Optional[str] = None
    clarifying_questions: Optional[List[str]] = None
    is_clear: bool = False
    extracted_parameters: Optional[Dict[str, Any]] = None

class PromptTemplateV1(BaseModel):
    """Version 1 of a prompt template schema."""
    template_id: str = Field(..., description="Unique identifier for the prompt template.")
    version: str = Field("1.0", description="Version of the prompt template format.")
    description: Optional[str] = Field(None, description="A brief description of the template's purpose.")
    template_string: str = Field(..., description="The actual template string with placeholders (e.g., using {{variable_name}} syntax).")
    input_variables: List[str] = Field(default_factory=list, description="List of variable names expected by the template.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arbitrary metadata associated with the template.")
