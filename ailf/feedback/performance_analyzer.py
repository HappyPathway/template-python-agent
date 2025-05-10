"""Performance Analyzer for AILF agent interactions."""

import logging
import pandas as pd
from typing import Dict, Any, List, Optional, Iterable # Added Optional and Iterable
from collections import Counter

from ailf.schemas.feedback import LoggedInteraction

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    Analyzes logged interactions to derive performance metrics and insights,
    particularly focusing on prompt effectiveness and agent behavior.
    """

    def __init__(self, interactions_data: Optional[Iterable[LoggedInteraction]] = None):
        """
        Initialize the PerformanceAnalyzer.

        :param interactions_data: An iterable of LoggedInteraction objects to analyze.
                                  This can be provided upfront or to individual methods.
        :type interactions_data: Optional[Iterable[LoggedInteraction]]
        """
        self.interactions_data = list(interactions_data) if interactions_data else []
        logger.info("PerformanceAnalyzer initialized.")

    def load_interactions(self, interactions_data: Iterable[LoggedInteraction]) -> None:
        """
        Load or update the interaction data to be analyzed.

        :param interactions_data: An iterable of LoggedInteraction objects.
        :type interactions_data: Iterable[LoggedInteraction]
        """
        self.interactions_data.extend(interactions_data)
        logger.info(f"Loaded {len(list(interactions_data))} new interactions. Total: {len(self.interactions_data)}.")

    def analyze_prompt_success(self, 
                               interactions: Optional[Iterable[LoggedInteraction]] = None
                               ) -> Dict[str, Any]:
        """
        Derives metrics on prompt success by correlating interaction outcomes with prompt versions.

        This is a placeholder for more sophisticated analysis. Currently, it might count
        success based on positive user feedback or absence of errors for prompts.

        :param interactions: An iterable of LoggedInteraction objects. If None, uses internal data.
        :type interactions: Optional[Iterable[LoggedInteraction]]
        :return: A dictionary containing prompt success metrics.
        :rtype: Dict[str, Any]
        """
        data_source = interactions if interactions is not None else self.interactions_data
        if not data_source:
            logger.warning("No interaction data available to analyze prompt success.")
            return {}

        prompt_stats: Dict[str, Dict[str, Any]] = {}

        for interaction in data_source:
            if interaction.prompt_template_id:
                prompt_key = f"{interaction.prompt_template_id}_v{interaction.prompt_template_version or 'unknown'}"
                if prompt_key not in prompt_stats:
                    prompt_stats[prompt_key] = {
                        "total_uses": 0,
                        "successful_outcomes": 0, # Define success e.g. positive feedback or no error
                        "error_count": 0,
                        "feedback_scores": [],
                    }
                
                prompt_stats[prompt_key]["total_uses"] += 1
                if interaction.error_message:
                    prompt_stats[prompt_key]["error_count"] += 1
                
                if interaction.user_feedback_score is not None:
                    prompt_stats[prompt_key]["feedback_scores"].append(interaction.user_feedback_score)
                    # Example: Consider positive feedback (e.g., > 0 or > 3 on a 1-5 scale) as success
                    if interaction.user_feedback_score > 0: # Adjust threshold as needed
                        prompt_stats[prompt_key]["successful_outcomes"] += 1
                elif not interaction.error_message:
                    # If no explicit feedback and no error, consider it a potential success (can be refined)
                    prompt_stats[prompt_key]["successful_outcomes"] += 1 

        # Calculate average feedback scores
        for key, stats in prompt_stats.items():
            if stats["feedback_scores"]:
                stats["average_feedback_score"] = sum(stats["feedback_scores"]) / len(stats["feedback_scores"])
            else:
                stats["average_feedback_score"] = None
            del stats["feedback_scores"] # Clean up intermediate data

        logger.info(f"Prompt success analysis completed for {len(prompt_stats)} unique prompts.")
        return prompt_stats

    def find_prompt_correlations(self, 
                                 interactions: Optional[Iterable[LoggedInteraction]] = None
                                 ) -> Dict[str, Any]:
        """
        Identifies correlations between prompt phrasing, parameters, and overall agent performance.

        This is a placeholder for more complex correlation analysis (e.g., statistical methods).
        Currently, it might group outcomes by prompt characteristics.

        :param interactions: An iterable of LoggedInteraction objects. If None, uses internal data.
        :type interactions: Optional[Iterable[LoggedInteraction]]
        :return: A dictionary containing identified correlations or patterns.
        :rtype: Dict[str, Any]
        """
        data_source = interactions if interactions is not None else self.interactions_data
        if not data_source:
            logger.warning("No interaction data available to find prompt correlations.")
            return {}

        # Placeholder: Example - group by a specific metadata tag if present in rendered_prompt or tags
        # This would require more sophisticated parsing of rendered_prompt or specific tagging strategies.
        correlations: Dict[str, Dict[str, int]] = {
            "by_keyword_in_prompt": Counter(),
            "by_tag_performance": {},
        }

        for interaction in data_source:
            # Example: Check for a keyword in the rendered prompt
            if interaction.rendered_prompt and "important_keyword" in interaction.rendered_prompt.lower():
                correlations["by_keyword_in_prompt"]["important_keyword_present"] += 1
            
            # Example: Correlate tags with error rates
            for tag in interaction.tags:
                if tag not in correlations["by_tag_performance"]:
                    correlations["by_tag_performance"][tag] = {"total": 0, "errors": 0, "avg_feedback": []}
                correlations["by_tag_performance"][tag]["total"] += 1
                if interaction.error_message:
                    correlations["by_tag_performance"][tag]["errors"] += 1
                if interaction.user_feedback_score is not None:
                    correlations["by_tag_performance"][tag]["avg_feedback"].append(interaction.user_feedback_score)

        for tag, stats in correlations["by_tag_performance"].items():
            if stats["avg_feedback"]:
                stats["average_feedback_score"] = sum(stats["avg_feedback"]) / len(stats["avg_feedback"])
            else:
                stats["average_feedback_score"] = None
            del stats["avg_feedback"]

        logger.info("Prompt correlation analysis placeholder executed.")
        return correlations

    def get_general_metrics(self, 
                            interactions: Optional[Iterable[LoggedInteraction]] = None
                            ) -> Dict[str, Any]:
        """
        Calculates general metrics from the interaction logs.

        :param interactions: An iterable of LoggedInteraction objects. If None, uses internal data.
        :type interactions: Optional[Iterable[LoggedInteraction]]
        :return: A dictionary of general metrics.
        :rtype: Dict[str, Any]
        """
        data_source = interactions if interactions is not None else self.interactions_data
        if not data_source:
            logger.warning("No interaction data available for general metrics.")
            return {}

        total_interactions = 0
        total_errors = 0
        feedback_scores = []
        model_usage = Counter()
        action_types = Counter()

        for interaction in data_source:
            total_interactions += 1
            if interaction.error_message:
                total_errors += 1
            if interaction.user_feedback_score is not None:
                feedback_scores.append(interaction.user_feedback_score)
            if interaction.llm_model_used:
                model_usage[interaction.llm_model_used] += 1
            if interaction.agent_actions:
                for action in interaction.agent_actions:
                    if isinstance(action, dict) and "action_type" in action:
                        action_types[action["action_type"]] += 1
                    elif isinstance(action, str): # Fallback if actions are just strings
                        action_types[action] +=1 
        
        metrics = {
            "total_interactions": total_interactions,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_interactions) if total_interactions > 0 else 0,
            "average_feedback_score": (sum(feedback_scores) / len(feedback_scores)) if feedback_scores else None,
            "model_usage_counts": dict(model_usage),
            "action_type_counts": dict(action_types),
        }
        logger.info("General metrics calculation completed.")
        return metrics
