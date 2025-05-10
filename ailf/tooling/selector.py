"""Tool selection logic for ailf.tooling."""
from typing import List, Optional, Dict, Any
from ailf.schemas.tooling import ToolDescription
import re  # For simple keyword matching as a start

class ToolSelector:
    """
    Selects the most appropriate tool based on a query and available tool descriptions.
    """

    def __init__(self, selection_strategy: str = "keyword_match"):
        """
        Initializes the ToolSelector.

        :param selection_strategy: The strategy to use for selecting tools.
                                   Currently supports: "keyword_match".
        :type selection_strategy: str
        """
        self.selection_strategy = selection_strategy

    def select_tool(
        self,
        query: str,
        available_tools: List[ToolDescription],
        threshold: float = 0.1  # General threshold, interpretation depends on strategy
    ) -> Optional[ToolDescription]:
        """
        Selects a tool from the available list based on the query.

        :param query: The user query or task description.
        :type query: str
        :param available_tools: A list of ToolDescription objects.
        :type available_tools: List[ToolDescription]
        :param threshold: A minimum score or confidence for a tool to be selected.
        :type threshold: float
        :return: The selected ToolDescription, or None if no suitable tool is found.
        :rtype: Optional[ToolDescription]
        """
        if not available_tools:
            return None

        if self.selection_strategy == "keyword_match":
            return self._select_by_keyword_match(query, available_tools)
        # Add other strategies here, e.g., RAG-based selection
        # elif self.selection_strategy == "rag":
        #     return self._select_by_rag(query, available_tools, threshold)
        else:
            # Potentially log a warning for unknown strategy
            return None  # Or raise an error

    def _select_by_keyword_match(
        self,
        query: str,
        available_tools: List[ToolDescription]
    ) -> Optional[ToolDescription]:
        """
        Selects a tool by matching keywords from the query against tool names,
        descriptions, and keywords. This is a very basic strategy.
        """
        best_match_tool: Optional[ToolDescription] = None
        highest_score = 0

        query_tokens = set(re.findall(r'\w+', query.lower()))

        if not query_tokens:
            return None

        for tool in available_tools:
            current_score = 0

            # Match against tool name
            tool_name_tokens = set(re.findall(r'\w+', tool.name.lower()))
            current_score += len(query_tokens.intersection(tool_name_tokens)) * 3  # Higher weight for name

            # Match against tool description
            tool_desc_tokens = set(re.findall(r'\w+', tool.description.lower()))
            current_score += len(query_tokens.intersection(tool_desc_tokens))

            # Match against tool keywords
            tool_keywords_tokens = set()
            for kw in tool.keywords:
                tool_keywords_tokens.update(re.findall(r'\w+', kw.lower()))
            current_score += len(query_tokens.intersection(tool_keywords_tokens)) * 2  # Medium weight for keywords

            # Match against usage examples
            for example in tool.usage_examples:
                example_tokens = set(re.findall(r'\w+', example.lower()))
                current_score += len(query_tokens.intersection(example_tokens)) * 0.5  # Lower weight

            if current_score > highest_score:
                highest_score = current_score
                best_match_tool = tool

        # Simple threshold: require at least one strong match (e.g. in name or multiple keywords)
        # This threshold is arbitrary and needs refinement.
        if highest_score > 1:  # Arbitrary threshold, e.g. at least more than one keyword hit
            return best_match_tool
        return None

    # Placeholder for RAG-based selection
    # def _select_by_rag(self, query: str, available_tools: List[ToolDescription], threshold: float) -> Optional[ToolDescription]:
    #     # This would involve:
    #     # 1. Embedding the query.
    #     # 2. Comparing with pre-computed embeddings in ToolDescription (name_embedding, description_embedding, combined_embedding).
    #     # 3. Selecting the tool with the highest similarity score if above threshold.
    #     # Requires an embedding model and vector comparison logic.
    #     raise NotImplementedError("RAG selection strategy is not yet implemented.")
