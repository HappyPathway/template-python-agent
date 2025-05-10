"""Intent Refiner for AILF agents, using AIEngine for CoT and clarification."""

import asyncio
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from ailf.schemas.cognition import IntentRefinementRequest, IntentRefinementResponse

# Placeholder for AIEngine
try:
    from utils.ai.engine import AIEngine
except ImportError:
    class AIEngine: # type: ignore
        async def analyze(self, content: str, output_schema: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
            print(f"Warning: Using placeholder AIEngine. Analyze called for IntentRefiner with prompt: {system_prompt}")
            # Simulate AI refining intent or asking clarifying questions
            if "book a flight" in content.lower() and "paris" not in content.lower():
                return IntentRefinementResponse(is_clear=False, clarifying_questions=["What is your destination?", "When would you like to travel?"])
            elif "book a flight to paris" in content.lower():
                return IntentRefinementResponse(is_clear=True, refined_query="User wants to book a flight to Paris.", extracted_parameters={"action": "book_flight", "destination": "Paris"})
            return IntentRefinementResponse(is_clear=True, refined_query=content) # Default pass-through

class IntentRefiner:
    """
    Refines user intent using an AIEngine, potentially employing Chain-of-Thought (CoT)
    reasoning and generating clarifying questions if the intent is ambiguous.
    """

    def __init__(self, ai_engine: AIEngine):
        """
        Initializes the IntentRefiner.

        :param ai_engine: The AI engine for intent analysis and refinement.
        :type ai_engine: AIEngine
        """
        self.ai_engine = ai_engine

    async def refine_intent(self, request: IntentRefinementRequest) -> IntentRefinementResponse:
        """
        Processes an IntentRefinementRequest to clarify and structure the user's intent.

        :param request: The request containing the original query and any context.
        :type request: IntentRefinementRequest
        :return: An IntentRefinementResponse with the refined query, clarifying questions, or extracted parameters.
        :rtype: IntentRefinementResponse
        """
        # Construct a detailed prompt for the AIEngine.
        # This prompt guides the LLM to perform CoT, identify ambiguities, and generate clarifying questions if needed.
        prompt_parts = [
            f"Original user query: \"{request.original_query}\"",
        ]

        if request.conversation_history:
            history_str = "\n".join([f"  {turn['role']}: {turn['content']}" for turn in request.conversation_history])
            prompt_parts.append(f"Conversation History:\n{history_str}")
        
        if request.context_data:
            context_str = "\n".join([f"  {key}: {value}" for key, value in request.context_data.items()])
            prompt_parts.append(f"Additional Context:\n{context_str}")
        
        prompt_parts.extend([
            "Analyze the user's intent based on the query and any provided history or context.",
            "1. Determine if the intent is clear and actionable. If not, identify ambiguities.",
            "2. If ambiguous, formulate specific clarifying questions to ask the user.",
            "3. If clear, rephrase the intent into a precise, actionable statement (refined_query).",
            "4. Extract key parameters or entities from the query into extracted_parameters (e.g., locations, dates, item names).",
            "Output your analysis in the IntentRefinementResponse schema."
        ])
        
        full_prompt_content = "\n".join(prompt_parts)

        system_prompt = (
            "You are an advanced intent refinement assistant. Your goal is to understand the user's true intent, "
            "clarify ambiguities by asking questions, or structure the intent for downstream processing. "
            "Employ Chain-of-Thought reasoning to arrive at your conclusions."
        )

        # Call the AIEngine with the constructed prompt and expect an IntentRefinementResponse
        response_model = await self.ai_engine.analyze(
            content=full_prompt_content,
            output_schema=IntentRefinementResponse,
            system_prompt=system_prompt
        )

        if not isinstance(response_model, IntentRefinementResponse):
            print("Error: AIEngine did not return a valid IntentRefinementResponse. Returning a default unclear response.")
            # Fallback or error handling
            return IntentRefinementResponse(is_clear=False, clarifying_questions=["Sorry, I had trouble understanding that. Could you please rephrase?"])
        
        return response_model

# Example Usage (Illustrative)
async def example_intent_refiner_usage():
    # 1. Setup AIEngine (using placeholder)
    ai_engine_instance = AIEngine()

    # 2. Initialize IntentRefiner
    refiner = IntentRefiner(ai_engine=ai_engine_instance)

    # 3. Example 1: Ambiguous query
    print("\n--- Example 1: Ambiguous Query ---")
    ambiguous_request = IntentRefinementRequest(original_query="I want to book a flight.")
    refined_response_1 = await refiner.refine_intent(ambiguous_request)
    print(f"Refined Response 1: {refined_response_1.model_dump_json(indent=2)}")

    # 4. Example 2: Clearer query
    print("\n--- Example 2: Clearer Query ---")
    clearer_request = IntentRefinementRequest(original_query="I want to book a flight to Paris for next week.")
    refined_response_2 = await refiner.refine_intent(clearer_request)
    print(f"Refined Response 2: {refined_response_2.model_dump_json(indent=2)}")

    # 5. Example 3: Query with conversation history
    print("\n--- Example 3: Query with History ---")
    history_request = IntentRefinementRequest(
        original_query="Yes, that sounds good.",
        conversation_history=[
            {"role": "assistant", "content": "We have flights to Paris available next Monday or Tuesday. Which do you prefer?"},
            {"role": "user", "content": "Monday is better."}
        ],
        context_data={"session_id": "xyz123"}
    )
    refined_response_3 = await refiner.refine_intent(history_request)
    print(f"Refined Response 3: {refined_response_3.model_dump_json(indent=2)}")

if __name__ == "__main__":
    # asyncio.run(example_intent_refiner_usage()) # Commented out to prevent execution during tool use
    pass
