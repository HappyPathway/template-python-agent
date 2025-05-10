"""
Custom AI Engine Example
========================

This example demonstrates how to create a custom AI engine by extending the base
AIEngine class from the AILF package. This allows you to:

1. Add custom logging and monitoring
2. Implement specialized processing for specific domains
3. Add validation and post-processing to AI responses
4. Customize provider selection and settings

The example shows how to create:
- A custom AI engine with enhanced logging
- A domain-specific engine for analyzing text sentiment
- A multi-model engine that switches between providers based on query content
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Type, TypeVar, Union
from pydantic import BaseModel, Field

from ailf.ai_engine import AIEngine
from ailf.schemas.ai import AIResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedAIEngine(AIEngine):
    """Enhanced AI engine with additional logging and metrics."""
    
    def __init__(
        self, 
        feature_name: str,
        model_name: str = "openai:gpt-4-turbo",
        log_requests: bool = True,
        log_responses: bool = False,  # Default to False for privacy
        track_metrics: bool = True
    ):
        """Initialize the enhanced AI engine.
        
        Args:
            feature_name: The name of the feature using this engine
            model_name: The name of the model to use (provider:model format)
            log_requests: Whether to log requests
            log_responses: Whether to log responses (may contain sensitive info)
            track_metrics: Whether to track usage metrics
        """
        super().__init__(feature_name=feature_name, model_name=model_name)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.track_metrics = track_metrics
        self.requests_count = 0
        self.total_tokens = 0
        self.avg_response_time = 0
        self.AIEngineError = AIEngine.AIEngineError
        
        logger.info(f"Enhanced AI Engine initialized with model {model_name}")
    
    async def generate(
        self, 
        prompt: str, 
        max_tokens: Optional[int] = None, 
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """Generate a response from the AI model with enhanced logging.
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1)
            kwargs: Additional parameters to pass to the model
        
        Returns:
            The AI response
        
        Raises:
            AIEngineError: If there's an error generating the response
        """
        self.requests_count += 1
        
        if self.log_requests:
            # Truncate long prompts in logs
            log_prompt = prompt if len(prompt) < 100 else f"{prompt[:100]}..."
            logger.info(f"Request #{self.requests_count}: {log_prompt}")
        
        start_time = time.time()
        
        try:
            response = await super().generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Track metrics
            if self.track_metrics:
                elapsed = time.time() - start_time
                
                # Update running average of response time
                self.avg_response_time = (
                    (self.avg_response_time * (self.requests_count - 1) + elapsed) / 
                    self.requests_count
                )
                
                self.total_tokens += response.usage.total_tokens
                
                logger.info(
                    f"Request #{self.requests_count} completed in {elapsed:.2f}s, "
                    f"used {response.usage.total_tokens} tokens"
                )
            
            if self.log_responses:
                logger.info(f"Response #{self.requests_count}: {response.content[:100]}...")
            
            return response
            
        except self.AIEngineError as e:
            logger.error(f"Error in AI request #{self.requests_count}: {str(e)}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine usage metrics.
        
        Returns:
            Dictionary with usage metrics
        """
        return {
            "requests_count": self.requests_count,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_request": self.total_tokens / self.requests_count if self.requests_count > 0 else 0,
            "avg_response_time": self.avg_response_time,
        }


class SentimentAnalysisEngine(EnhancedAIEngine):
    """Specialized AI engine for sentiment analysis."""
    
    def __init__(
        self, 
        feature_name: str = "sentiment_analysis",
        model_name: str = "openai:gpt-4-turbo"
    ):
        """Initialize the sentiment analysis engine.
        
        Args:
            feature_name: The name of the feature using this engine
            model_name: The name of the model to use
        """
        super().__init__(feature_name=feature_name, model_name=model_name)
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze the sentiment of the provided text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        # Create a structured prompt for sentiment analysis
        prompt = f"""
        Analyze the sentiment of the following text. Return a JSON with these fields:
        - overall_sentiment: "positive", "negative", or "neutral"
        - confidence: a score from 0 to 1 
        - emotions: an array of primary emotions detected
        - tone: the overall tone of the text
        
        Text to analyze:
        "{text}"
        
        JSON response:
        """
        
        # Use a lower temperature for more consistent results
        response = await self.generate(prompt, temperature=0.2)
        
        try:
            # Extract JSON from response
            result = response.content.strip()
            if result.startswith("```json"):
                result = result.replace("```json", "").replace("```", "")
            elif result.startswith("```"):
                result = result.replace("```", "")
                
            return json.loads(result)
            
        except json.JSONDecodeError:
            # Fallback parsing if the model doesn't return proper JSON
            lines = response.content.strip().split("\n")
            result = {}
            
            for line in lines:
                if "overall_sentiment" in line.lower():
                    sentiment = line.split(":")[1].strip().strip('",')
                    result["overall_sentiment"] = sentiment
                elif "confidence" in line.lower():
                    confidence = line.split(":")[1].strip().strip(',')
                    try:
                        result["confidence"] = float(confidence)
                    except ValueError:
                        result["confidence"] = 0.5
                        
            # Default values if parsing fails
            if "overall_sentiment" not in result:
                result["overall_sentiment"] = "neutral"
            if "confidence" not in result:
                result["confidence"] = 0.5
                
            return result


class MultiModelEngine:
    """AI engine that dynamically selects between different models based on task."""
    
    def __init__(self):
        """Initialize the multi-model engine."""
        # Initialize different specialized engines
        self.general_engine = EnhancedAIEngine(
            feature_name="general",
            model_name="openai:gpt-4-turbo"
        )
        
        self.fast_engine = EnhancedAIEngine(
            feature_name="fast_responses",
            model_name="openai:gpt-3.5-turbo"
        )
        
        self.creative_engine = EnhancedAIEngine(
            feature_name="creative",
            model_name="anthropic:claude-3-opus-20240229",
            log_requests=True,
            track_metrics=True
        )
        
        self.sentiment_engine = SentimentAnalysisEngine()
    
    def select_engine(self, query: str, task_type: str = "general") -> AIEngine:
        """Select the appropriate engine based on the query and task.
        
        Args:
            query: The user's query
            task_type: The type of task (general, creative, fast, sentiment)
            
        Returns:
            The selected AI engine
        """
        # Override with explicit task type if provided
        if task_type == "creative":
            return self.creative_engine
        elif task_type == "fast":
            return self.fast_engine
        elif task_type == "sentiment":
            return self.sentiment_engine
        
        # Otherwise, analyze the query to select the engine
        query_lower = query.lower()
        
        # Keywords that suggest creativity is needed
        creative_keywords = [
            "story", "poem", "creative", "imagine", "fiction", 
            "generate", "invent", "innovative"
        ]
        
        # Keywords that suggest sentiment analysis
        sentiment_keywords = [
            "sentiment", "emotion", "feel", "opinion", "reaction",
            "positive", "negative", "analyze text"
        ]
        
        # Check for keywords in the query
        if any(keyword in query_lower for keyword in creative_keywords):
            return self.creative_engine
        elif any(keyword in query_lower for keyword in sentiment_keywords):
            return self.sentiment_engine
        elif len(query.split()) < 15:  # Short queries can use the fast engine
            return self.fast_engine
        else:
            return self.general_engine
    
    async def generate(
        self, 
        query: str, 
        task_type: str = "general", 
        **kwargs
    ) -> AIResponse:
        """Generate a response using the appropriate engine.
        
        Args:
            query: The user's query
            task_type: The type of task
            kwargs: Additional parameters for the generation
            
        Returns:
            The AI response
        """
        engine = self.select_engine(query, task_type)
        logger.info(f"Selected engine: {engine.__class__.__name__} for task: {task_type}")
        
        return await engine.generate(query, **kwargs)
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Convenience method for sentiment analysis.
        
        Args:
            text: The text to analyze
            
        Returns:
            Sentiment analysis results
        """
        return await self.sentiment_engine.analyze_sentiment(text)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics from all engines.
        
        Returns:
            Dictionary of metrics for each engine
        """
        return {
            "general": self.general_engine.get_metrics(),
            "fast": self.fast_engine.get_metrics(),
            "creative": self.creative_engine.get_metrics(),
            "sentiment": self.sentiment_engine.get_metrics(),
        }


async def main():
    """Run an example of the custom AI engines."""
    # Simple enhanced engine example
    print("\n=== Enhanced AI Engine Example ===")
    enhanced_engine = EnhancedAIEngine(
        feature_name="example",
        model_name="openai:gpt-3.5-turbo"  # Using a faster model for the example
    )
    
    response = await enhanced_engine.generate(
        prompt="Explain what makes a well-designed software API in one paragraph.",
        max_tokens=150
    )
    
    print(f"Response: {response.content}")
    print("\nEngine metrics:", json.dumps(enhanced_engine.get_metrics(), indent=2))
    
    # Sentiment analysis example
    print("\n=== Sentiment Analysis Engine Example ===")
    sentiment_engine = SentimentAnalysisEngine()
    
    texts = [
        "I absolutely love this product! It's the best purchase I've made all year.",
        "The service was terrible and the staff was rude. I won't be returning.",
        "The weather today is partly cloudy with a chance of rain later."
    ]
    
    for text in texts:
        print(f"\nAnalyzing: \"{text}\"")
        result = await sentiment_engine.analyze_sentiment(text)
        print(json.dumps(result, indent=2))
    
    # Multi-model example
    print("\n=== Multi-Model Engine Example ===")
    multi_engine = MultiModelEngine()
    
    queries = [
        ("Tell me about the solar system", "general"),
        ("Write a short poem about autumn leaves", "creative"),
        ("What is 15 * 24?", "fast"),
        ("I'm feeling really disappointed with the election results", "sentiment")
    ]
    
    for query, task_type in queries:
        print(f"\nQuery: \"{query}\" (Task: {task_type})")
        selected_engine = multi_engine.select_engine(query, task_type)
        print(f"Selected engine: {selected_engine.__class__.__name__}")
        
        # Generate a response (commenting out to avoid actual API calls)
        # response = await multi_engine.generate(query, task_type=task_type)
        # print(f"Response: {response.content[:100]}...")
    
    print("\nAll engine metrics:", json.dumps(multi_engine.get_all_metrics(), indent=2))


if __name__ == "__main__":
    import asyncio
    
    # Run the example
    print("Custom AI Engine Example")
    print("=======================")
    print("This example demonstrates creating custom AI engines by extending the base AIEngine.")
    print("Note: Running this example would make actual API calls. The code is provided for reference.")
    print("To run it, uncomment the API calls in the main() function and provide valid API keys.")
    
    # Uncomment to run the examples (requires API keys)
    # asyncio.run(main())