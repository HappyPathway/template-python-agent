"""Reflection Engine for processing short-term memory and extracting insights."""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from ailf.memory.long_term import LongTermMemory
from ailf.memory.short_term import ShortTermMemory
from ailf.schemas.memory import KnowledgeFact, MemoryItem, UserProfile

# Assuming AIEngine will be available from this path as per project structure guidelines
# If AIEngine is not yet implemented, this serves as a placeholder for its integration.
try:
    from utils.ai.engine import AIEngine
except ImportError:
    # Placeholder AIEngine if the actual one is not available
    # This allows ReflectionEngine to be defined, but it won't fully function.
    class AIEngine:
        async def analyze(self, content: str, output_schema: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
            print("Warning: Using placeholder AIEngine. Analyze will not produce real results.")
            # Return a default instance of the output_schema
            return output_schema()


class ExtractedInsights(BaseModel):
    """Schema for insights extracted by the AIEngine from memory items."""
    user_id: Optional[str] = Field(None, description="Identified user ID from the interaction.")
    extracted_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences extracted from the content.")
    extracted_facts: Optional[List[str]] = Field(None, description="Key factual statements extracted.")
    fact_source_description: str = Field("Derived from agent interaction analysis", description="Source description for extracted facts.")

class ReflectionEngine:
    """
    Analyzes short-term memory, extracts insights using AIEngine,
    and stores them in long-term memory.
    """

    def __init__(
        self, 
        ai_engine: AIEngine, 
        short_term_memory: ShortTermMemory, 
        long_term_memory: LongTermMemory
    ):
        """
        Initializes the ReflectionEngine.

        :param ai_engine: The AI engine for content analysis.
        :type ai_engine: AIEngine
        :param short_term_memory: The short-term memory store to reflect upon.
        :type short_term_memory: ShortTermMemory
        :param long_term_memory: The long-term memory store for persisting insights.
        :type long_term_memory: LongTermMemory
        """
        self.ai_engine = ai_engine
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory

    async def perform_reflection_on_item(self, memory_item: MemoryItem) -> None:
        """
        Performs reflection on a single MemoryItem.
        Extracts insights and stores them in long-term memory.

        :param memory_item: The MemoryItem to process.
        :type memory_item: MemoryItem
        """
        try:
            content_to_analyze = str(memory_item.data) # Ensure data is string for analysis
            # Try to get user_id from metadata if available
            user_id_hint = memory_item.metadata.get('user_id') 
            
            system_prompt = (
                f"Analyze the following interaction content. "
                f"Identify the user ID if possible (hint: {user_id_hint if user_id_hint else 'not available'}). "
                f"Extract any stated or implied user preferences. "
                f"List key factual statements made during the interaction."
            )

            # Use AIEngine to extract insights
            # This assumes AIEngine has an 'analyze' method or similar
            insights = await self.ai_engine.analyze(
                content=content_to_analyze,
                output_schema=ExtractedInsights,
                system_prompt=system_prompt
            )

            if not isinstance(insights, ExtractedInsights):
                # Log error or handle unexpected type
                print(f"Error: AIEngine did not return ExtractedInsights for item {memory_item.item_id}")
                return

            # Process and store extracted preferences
            if insights.user_id and insights.extracted_preferences:
                await self._update_user_profile(insights.user_id, insights.extracted_preferences)

            # Process and store extracted facts
            if insights.extracted_facts:
                user_context_for_fact = insights.user_id or memory_item.metadata.get('session_id')
                source_info = f"{insights.fact_source_description} (item_id: {memory_item.item_id}, user_context: {user_context_for_fact})"
                await self._store_knowledge_facts(insights.extracted_facts, source_info)

        except Exception as e:
            # Log the exception
            print(f"Error during reflection on item {memory_item.item_id}: {e}")

    async def _update_user_profile(self, user_id: str, preferences: Dict[str, Any]) -> None:
        """Updates or creates a user profile with new preferences."""
        existing_profile = await self.long_term_memory.retrieve_item(UserProfile, user_id)
        if existing_profile:
            existing_profile.preferences.update(preferences)
            # Potentially update other fields like history_summary or last_updated
            await self.long_term_memory.store_item(existing_profile)
        else:
            new_profile = UserProfile(user_id=user_id, preferences=preferences)
            await self.long_term_memory.store_item(new_profile)
        print(f"Updated/Created UserProfile for {user_id} with preferences: {preferences}")

    async def _store_knowledge_facts(self, facts: List[str], source: str) -> None:
        """Stores a list of facts as KnowledgeFact items."""
        for fact_content in facts:
            fact_id = uuid.uuid4().hex # Generate a unique ID for each fact
            knowledge_fact = KnowledgeFact(
                fact_id=fact_id,
                content=fact_content,
                source=source,
                tags=["reflection_engine", "extracted_fact"]
                # Add confidence_score if AIEngine provides it
            )
            await self.long_term_memory.store_item(knowledge_fact)
            print(f"Stored KnowledgeFact: {fact_id} - {fact_content[:50]}...")

    async def reflect_on_recent_memory(self, limit: int = 10) -> None:
        """
        Retrieves recent items from short-term memory and performs reflection on them.
        
        Note: This simple version fetches all items and processes them.
        A more advanced version might fetch items based on criteria (e.g., not yet reflected upon)
        or process them in batches.

        :param limit: Max number of STM items to list (actual processing depends on STM content).
                      This is a conceptual limit for `list_items`, actual items processed might be less.
        """
        # STM list_items currently returns all keys. We might need a way to get actual items or recent items.
        # For now, let's assume we can get MemoryItem objects that need processing.
        # This is a conceptual loop. Actual fetching logic might differ based on STM capabilities.
        
        item_ids = await self.short_term_memory.list_items() # This lists all item IDs
        
        print(f"Found {len(item_ids)} items in STM. Reflecting on up to {limit} of them (or all if fewer).")

        processed_count = 0
        for item_id in item_ids:
            if processed_count >= limit and limit > 0: # limit=0 or negative means no limit
                break
            memory_item = await self.short_term_memory.get_item(item_id)
            if memory_item:
                print(f"Reflecting on STM item: {item_id}")
                await self.perform_reflection_on_item(memory_item)
                processed_count += 1
            else:
                print(f"Could not retrieve STM item: {item_id} (might have expired or been removed)")

# Example of how ReflectionEngine might be used (for illustration)
async def main_reflection_example():
    # This is a simplified setup. In a real app, these would be configured and managed.
    # 1. Setup AIEngine (replace with actual AIEngine instantiation)
    #    For this example, we rely on the placeholder if utils.ai.engine.AIEngine is not found.
    try:
        from utils.ai.engine import AIEngine as ActualAIEngine
        ai_engine_instance = ActualAIEngine() # Add necessary AIEngine params
    except ImportError:
        ai_engine_instance = AIEngine() # Uses the placeholder
        print("Using placeholder AIEngine for example.")

    # 2. Setup ShortTermMemory
    stm = ShortTermMemory(default_ttl=600) # Short TTL for example items
    await stm.add_item("interaction1", {"user_id": "user_alpha", "text": "I prefer dark mode and want to know about Python."}, metadata={"user_id": "user_alpha"})
    await stm.add_item("interaction2", {"user_id": "user_beta", "text": "AILF stands for Agentic AI Library Framework."}, metadata={"user_id": "user_beta"})
    await stm.add_item("interaction3", {"text": "The sky is blue."}) # No user_id in data or metadata

    # 3. Setup LongTermMemory
    ltm_base_path = "./agent_ltm_reflection_data"
    ltm = LongTermMemory(base_storage_path=ltm_base_path)

    # 4. Initialize ReflectionEngine
    reflection_engine = ReflectionEngine(ai_engine_instance, stm, ltm)

    # 5. Perform reflection
    print("\nStarting reflection process...")
    await reflection_engine.reflect_on_recent_memory(limit=5)
    print("\nReflection process completed.")

    # 6. (Optional) Verify LTM content
    print("\nVerifying LTM content after reflection:")
    user_alpha_profile = await ltm.retrieve_item(UserProfile, "user_alpha")
    if user_alpha_profile:
        print(f"User Alpha Profile: {user_alpha_profile.model_dump_json(indent=2)}")
    
    knowledge_facts_ids = await ltm.list_item_ids(KnowledgeFact)
    print(f"Knowledge Fact IDs in LTM: {knowledge_facts_ids}")
    for fact_id in knowledge_facts_ids:
        fact = await ltm.retrieve_item(KnowledgeFact, fact_id)
        if fact:
            print(f"- Fact {fact_id}: {fact.content}")

if __name__ == "__main__":
    # To run this example, you might need to ensure AIEngine is available
    # or be content with the placeholder's behavior.
    # asyncio.run(main_reflection_example()) # Commented out to prevent execution during tool use
    pass
