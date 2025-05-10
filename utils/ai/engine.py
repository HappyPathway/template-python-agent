"""AI Engine Module.

This module provides a comprehensive interface for AI and LLM interactions,
combining the capabilities of both AIEngine and BaseLLMAgent approaches.
It supports structured and unstructured outputs, with robust monitoring,
error handling, and type safety.

Key Components:
    AIEngine: Main class providing AI/LLM interaction interface
    GeminiSettings: Configuration model for Gemini-specific settings
    OpenAISettings: Configuration model for OpenAI-specific settings
    AnthropicSettings: Configuration model for Anthropic-specific settings
    AIEngineError: Base exception class for AI engine errors

Features:
    - Multiple model support (OpenAI, Gemini, Anthropic)
    - Structured output using Pydantic models
    - Comprehensive monitoring and logging
    - Error handling and retries
    - Type-safe interactions
    - Tool registration for agents

Example:
    Basic usage with structured output:
        >>> from utils.ai_engine import AIEngine
        >>> from my_schemas import JobAnalysis
        >>> 
        >>> engine = AIEngine(
        ...     feature_name='job_analysis',
        ...     output_type=JobAnalysis,
        ...     model_name='openai:gpt-4-turbo'
        ... )
        >>> 
        >>> # Generate structured output
        >>> result = await engine.generate(
        ...     prompt="Analyze this job description...",
        ...     output_schema=JobAnalysis
        ... )

    Using as an agent with tools:
        >>> @engine.add_tool
        ... async def search_jobs(query: str) -> List[dict]:
        ...     # Tool implementation
        ...     return [{"id": "123", "title": "Python Developer"}]
        >>> 
        >>> result = await engine.generate(
        ...     prompt="Find Python jobs in Seattle",
        ...     system="You are a job search assistant"
        ... )

Note:
    Always use environment variables for API keys.
    Follow provider-specific guidelines for rate limits and token usage.
"""

import asyncio
import os
from enum import Enum
from typing import Any, AsyncIterator, Generic, List, Literal, Optional, Type, TypeVar, Union
import inspect  # Added import

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior

from utils.core.logging import setup_logging  # Corrected import
from utils.core.monitoring import MetricsCollector, setup_monitoring  # Corrected import
from schemas.ai import (  # Corrected import: Referencing the top-level schemas module
    AnthropicSettings,
    GeminiSafetySettings,
    GeminiSettings,
    OpenAISettings,
    UsageLimits,
)
from ailf.tooling import ToolManager, ToolSelector  # Added import
from ailf.schemas.tooling import ToolDescription  # Added import
import uuid  # Added import for ToolDescription default ID

logger = setup_logging(__name__)

# Initialize logging and monitoring
logger = setup_logging('ai_engine')
monitoring = setup_monitoring('ai_engine')

# Optional Logfire class (will be None if not available)
try:
    from logfire import LogfireMonitoring
except ImportError:
    LogfireMonitoring = None

# Type variable for output types
T = TypeVar('T')

# Safety settings for Gemini


class GeminiHarmCategory(str, Enum):
    """Categories for Gemini model safety settings."""
    HARASSMENT = "HARM_CATEGORY_HARASSMENT"
    HATE_SPEECH = "HARM_CATEGORY_HATE_SPEECH"
    SEXUALLY_EXPLICIT = "HARM_CATEGORY_SEXUALLY_EXPLICIT"
    DANGEROUS = "HARM_CATEGORY_DANGEROUS_CONTENT"


class GeminiThreshold(str, Enum):
    """Threshold levels for Gemini safety settings."""
    BLOCK_NONE = "BLOCK_NONE"
    BLOCK_LOW = "BLOCK_LOW_AND_ABOVE"
    BLOCK_MEDIUM = "BLOCK_MEDIUM_AND_ABOVE"
    BLOCK_HIGH = "BLOCK_HIGH"


class AIEngine(Generic[T]):
    """Unified AI Engine for all AI/LLM interactions.

    This class provides a unified interface for AI model interactions,
    supporting multiple providers and both structured/unstructured outputs.

    :param T: Generic type parameter for output type specification
    :type T: TypeVar

    Features:
        - Multiple model providers (OpenAI, Gemini, etc.)
        - Structured and unstructured output
        - Tool registration for agent functionality
        - Comprehensive monitoring and error handling

    Example:
        >>> from utils.ai_engine import AIEngine
        >>> engine = AIEngine(
        ...     feature_name='summarizer',
        ...     model_name='openai:gpt-4-turbo'
        ... )
        >>> 
        >>> text = await engine.generate_text(
        ...     prompt="Summarize this article..."
        ... )
    """

    # Provider settings mapping
    settings_map = {
        "openai": OpenAISettings(temperature=0.7),
        "gemini": GeminiSettings(),
        "anthropic": AnthropicSettings(temperature=0.7)
    }

    # Default usage limits
    usage_limits = UsageLimits(
        max_requests_per_minute=60,
        max_input_tokens=8000,
        max_output_tokens=1024,
        max_parallel_requests=5
    )

    def __init__(
        self,
        feature_name: str,
        output_type: Optional[Type[BaseModel]] = None,
        model_name: str = 'openai:gpt-4-turbo',
        provider: str = 'openai',
        instructions: Optional[str] = None,
        retries: int = 2
    ):
        """Initialize the AI engine.

        :param feature_name: Name of the feature using this engine
        :type feature_name: str
        :param output_type: Optional Pydantic model for structured output
        :type output_type: Optional[Type[BaseModel]]
        :param model_name: Name of the model to use
        :type model_name: str
        :param provider: AI provider to use ('openai', 'gemini', or 'anthropic')
        :type provider: str
        :param instructions: Optional system instructions
        :type instructions: Optional[str]
        :param retries: Number of retries for failed generations
        :type retries: int
        :raises ValueError: If provider or API key configuration is invalid

        Example:
            >>> engine = AIEngine(
            ...     feature_name='text_classifier',
            ...     model_name='openai:gpt-4-turbo',
            ...     instructions='You are a text classifier'
            ... )
        """
        self.feature_name = feature_name
        self.output_type = output_type
        self.model_name = model_name
        self.provider = provider
        self.instructions = instructions
        self.retries = retries

        # Set up monitoring for this feature
        self.monitoring = setup_monitoring(f'ai_{feature_name}')

        # Set up logfire config
        self.logfire_config = {
            "project_id": "jobsearch-ai",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "api_key": os.getenv("LOGFIRE_API_KEY")
        }

        # Configure monitoring with Logfire if available
        if LogfireMonitoring:
            self.logfire = LogfireMonitoring(
                project_id=self.logfire_config["project_id"],
                environment=self.logfire_config["environment"],
                service_name=feature_name
            )
        else:
            self.logfire = None

        # Initialize the agent
        self.agent = self._setup_agent()

        # Initialize AILF Tooling components
        self.tool_manager = ToolManager()
        self.tool_selector = ToolSelector(tools_data=self.tool_manager.tools)

    @property
    def metrics(self) -> MetricsCollector:
        """Get the metrics collector."""
        return self.monitoring

    def add_tool(self, func=None, *, name=None, description=None, retries=None):
        """Register a function as a tool with the agent.

        This method can be used as a decorator or called directly.
        Tools registered here will be available to the pydantic-ai agent and
        will be executed via the AILF ToolManager.

        :param func: The function to register as a tool
        :type func: Callable, optional
        :param name: Custom name for the tool (defaults to function name)
        :type name: str, optional
        :param description: Description of what the tool does
        :type description: str, optional
        :param retries: Optional retry count for tool invocations by pydantic-ai
        :type retries: Optional[int]
        :return: The original function or a decorator
        :rtype: Callable

        Example as decorator:
            >>> @engine.add_tool
            ... async def search_database(query: str) -> List[dict]:
            ...     # Implementation
            ...     return results

        Example with parameters:
            >>> @engine.add_tool(
            ...     name="search_web",
            ...     description="Search the web for information"
            ... )
            ... async def search(query: str) -> List[dict]:
            ...     # Implementation
            ...     return [{"title": "Result", "url": "http://..."}]

        Example as function:
            >>> async def fetch_data(url: str) -> dict:
            ...     # Implementation
            ...     return data
            >>> 
            >>> engine.add_tool(fetch_data, name="get_data")
        """
        # Define the decorator
        def decorator(f_decorated):
            tool_name_for_llm = name or f_decorated.__name__
            tool_desc_for_llm = description or inspect.getdoc(f_decorated) or ""

            # Create ToolDescription for AILF ToolManager
            # TODO: Enhance to allow passing input/output schemas or infer them.
            ailf_tool_description = ToolDescription(
                name=tool_name_for_llm,  # Use the same name for consistency
                description=tool_desc_for_llm
                # id will be auto-generated
                # input_schema_ref, output_schema_ref, etc., are not populated here yet.
            )

            try:
                # Register the original callable with AILF ToolManager
                self.tool_manager.register_tool(
                    tool_description=ailf_tool_description,
                    tool_callable=f_decorated,
                    overwrite=True  # Allow overwriting if tool with same name is added
                )
                logger.debug(f"Tool '{tool_name_for_llm}' registered with AILF ToolManager.")
            except Exception as e:
                logger.error(f"Failed to register tool '{tool_name_for_llm}' with AILF ToolManager: {e}")
                # Optionally, re-raise or handle if registration with ToolManager is critical

            # Create a wrapper for pydantic-ai to call our ToolManager
            # This wrapper must be async as ToolManager.execute_tool is async.
            async def pydantic_ai_tool_wrapper(**kwargs):
                # The 'tool_name_for_llm' is captured from the outer scope.
                # This is the name ToolManager knows the tool by.
                try:
                    logger.debug(f"AIEngine: Pydantic-AI invoking tool '{tool_name_for_llm}' via ToolManager with args: {kwargs}")
                    return await self.tool_manager.execute_tool(tool_name_for_llm, kwargs)
                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name_for_llm}' via ToolManager: {e}")
                    # Re-raise the exception so pydantic-ai can handle it (e.g., retries)
                    raise

            # Register the wrapper with pydantic-ai's agent
            # Pydantic-AI uses the 'name' and 'description' for LLM prompting and
            # inspects the callable for its parameters.
            # Passing the wrapper directly. Pydantic-AI should call it with kwargs
            # corresponding to the original function's signature.
            self.agent.add_tool(
                pydantic_ai_tool_wrapper,
                name=tool_name_for_llm,
                description=tool_desc_for_llm,
                retries=(retries or self.retries)
            )
            logger.debug(f"Tool '{tool_name_for_llm}' (wrapper) registered with pydantic-ai agent.")

            return f_decorated  # Return the original function so it can be used directly if needed

        # Handle both decorator and direct call patterns
        if func is None:
            return decorator
        return decorator(func)

    def _get_api_key(self) -> str:
        """Get API key for the current provider."""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY"
        }
        env_var = key_map.get(self.provider)
        if not env_var:
            raise ValueError(f"Unsupported provider: {self.provider}")

        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(
                f"Missing API key for provider {self.provider}. Set {env_var} environment variable.")
        return api_key

    def _setup_agent(self) -> Agent:
        """Set up the Agent with proper configuration.

        This is a key extension point for subclasses, which can override this method
        to customize how the agent is configured and initialized.

        Returns:
            Agent: Configured agent object

        Raises:
            ValueError: If the provider is not supported or API key is missing
        """
        api_key = self._get_api_key()

        # Configure monitoring if Logfire is enabled
        instrument = self._setup_instrumentation()

        # Get provider-specific settings
        default_settings = self._get_provider_settings()

        # Configure settings for this instance
        settings = self._create_settings_instance(default_settings)

        # Create model settings
        model_settings = {
            "temperature": settings.temperature or 0.7,
            "max_tokens": settings.max_tokens
        }

        # Initialize and return the agent
        self.agent = Agent(
            model=self.model_name,
            api_key=api_key,
            monitoring_callback=instrument,
            model_settings=model_settings,
            usage_limits=self.usage_limits,
            system=self.instructions
        )

        return self.agent

    def _setup_instrumentation(self):
        """Set up instrumentation for the agent.

        Override this method in subclasses to customize instrumentation.

        Returns:
            Object or None: Instrumentation object if configured, None otherwise
        """
        instrument = None
        if self.logfire_config and LogfireMonitoring:
            instrument = LogfireMonitoring(
                project_id=self.logfire_config["project_id"],
                api_key=self.logfire_config["api_key"]
            )
        return instrument

    def _get_provider_settings(self):
        """Get the default settings for the current provider.

        Override this method in subclasses to customize provider settings.

        Returns:
            BaseModel: Provider-specific settings

        Raises:
            ValueError: If the provider is not supported
        """
        default_settings = self.settings_map.get(self.provider)
        if not default_settings:
            raise ValueError(f"Unsupported provider: {self.provider}")
        return default_settings

    def _create_settings_instance(self, default_settings):
        """Create a new instance of settings.

        Override this method in subclasses to customize settings creation.

        Args:
            default_settings: Default settings for the provider

        Returns:
            BaseModel: Settings instance
        """
        settings = type(default_settings)()
        settings.temperature = default_settings.temperature
        settings.max_tokens = default_settings.max_tokens
        return settings

    def _get_provider_specific_settings(self, settings: Optional[BaseModel]) -> dict:
        """Get provider-specific settings."""
        if not settings:
            return {}

        if self.provider == "gemini":
            return {
                "safety_settings": settings.safety_settings,
                "generation_config": settings.generation_config
            } if isinstance(settings, GeminiSettings) else {}

        elif self.provider == "openai":
            return {
                "frequency_penalty": settings.frequency_penalty,
                "presence_penalty": settings.presence_penalty,
                "stop": settings.stop
            } if isinstance(settings, OpenAISettings) else {}

        elif self.provider == "anthropic":
            return {
                "top_k": settings.top_k
            } if isinstance(settings, AnthropicSettings) else {}

        return {}

    async def generate(
        self,
        prompt: str,
        *,
        output_schema: Optional[Type[BaseModel]] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> Union[str, BaseModel, AsyncIterator[str]]:
        """Generate content from the LLM.

        :param prompt: The input prompt
        :type prompt: str
        :param output_schema: Optional Pydantic model for structured output
        :type output_schema: Optional[Type[BaseModel]]
        :param system: Optional system prompt
        :type system: Optional[str]
        :param temperature: Optional temperature override
        :type temperature: Optional[float]
        :param stream: Whether to stream the response
        :type stream: bool
        :return: Generated content
        :rtype: Union[str, BaseModel, AsyncIterator[str]]
        :raises AIEngineError: If generation fails
        :raises ContentFilterError: If content is filtered by safety settings
        :raises ModelError: If model behaves unexpectedly

        Example:
            Simple text generation:
                >>> text = await engine.generate(
                ...     prompt="Write a story about...",
                ...     temperature=0.7
                ... )

            Structured output:
                >>> from my_schemas import Article
                >>> article = await engine.generate(
                ...     prompt="Write an article about Python...",
                ...     output_schema=Article,
                ...     system="You are a technical writer"
                ... )

            Streaming response:
                >>> async for chunk in engine.generate(
                ...     prompt="Tell me a long story...",
                ...     stream=True
                ... ):
                ...     print(chunk, end="")
        """
        try:
            with self.monitoring.timer("generate_latency"):
                if stream:
                    return self.agent.stream(
                        prompt,
                        system=system,
                        temperature=temperature
                    )

                result = await self.agent.run(
                    prompt,
                    output_schema=output_schema,
                    system=system,
                    temperature=temperature
                )
                self.monitoring.increment_success("generate")

                # Handle different result attributes based on what's available
                if output_schema:
                    return result.output
                elif hasattr(result, 'text'):
                    return result.text
                elif hasattr(result, 'content'):
                    return result.content
                else:
                    # Last resort: try to get the result as a string
                    return str(result)

        except ModelRetry as e:
            # Handle rate limits with exponential backoff
            self.monitoring.track_error("generate", "rate_limit")
            # Use a default retry delay of 1 second or extract from message if possible
            retry_delay = 1.0  # Default delay in seconds
            # Try to extract a delay value from the error message if it's there
            try:
                import re
                delay_match = re.search(
                    r'retry after (\d+(?:\.\d+)?)', str(e).lower())
                if delay_match:
                    retry_delay = float(delay_match.group(1))
            except Exception:
                pass  # Use default delay if extraction fails

            await asyncio.sleep(retry_delay)
            return await self.generate(
                prompt,
                output_schema=output_schema,
                system=system,
                temperature=temperature,
                stream=stream
            )

        except UnexpectedModelBehavior as e:
            # Map to appropriate error type
            if "content filtered" in str(e).lower():
                self.monitoring.track_error("generate", "content_filtered")
                raise ContentFilterError(str(e)) from e
            self.monitoring.track_error("generate", "model_behavior")
            raise ModelError(f"Unexpected model behavior: {str(e)}") from e

        except Exception as e:
            if hasattr(e, "schema_error"):
                self.monitoring.track_error("generate", "schema_error")
            else:
                self.monitoring.track_error("generate", str(e))
            raise AIEngineError(f"Generation failed: {str(e)}") from e

    async def classify(
        self,
        content: str,
        *,
        categories: List[str],
        multi_label: bool = False,
        system: Optional[str] = None
    ) -> Union[str, List[str]]:
        """Classify content into predefined categories.

        This is an extension point that demonstrates how to build specialized methods
        on top of the base generation functionality.

        :param content: Content to classify
        :type content: str
        :param categories: List of possible classification categories
        :type categories: List[str]
        :param multi_label: Whether multiple labels can be assigned
        :type multi_label: bool
        :param system: Optional system prompt
        :type system: Optional[str]
        :return: Selected category or categories
        :rtype: Union[str, List[str]]
        :raises AIEngineError: If classification fails

        Example:
            >>> category = await engine.classify(
            ...     content="I love this product!",
            ...     categories=["positive", "negative", "neutral"]
            ... )
            >>> print(category)
            positive
        """
        try:
            # Build prompt for classification
            categories_str = ", ".join(categories)
            instruction = f"Classify the following text into {'one of' if not multi_label else 'one or more of'} these categories: {categories_str}."
            if multi_label:
                instruction += " Return the categories as a comma-separated list."

            # Set up system prompt
            sys_prompt = system or f"You are a text classifier. {instruction} Only respond with the category name(s)."

            # Generate classification
            result = await self.generate(
                prompt=content,
                system=sys_prompt,
                temperature=0.1  # Lower temperature for more deterministic classification
            )

            # Process result
            if multi_label:
                # Split by commas and strip whitespace
                return [cat.strip() for cat in result.split(',')]
            return result.strip()

        except Exception as e:
            self.monitoring.track_error("classify", str(e))
            raise AIEngineError(f"Classification failed: {str(e)}") from e

    async def analyze(
        self,
        content: str,
        *,
        analysis_type: Literal["sentiment", "topics",
                               "summary", "entities"] = "summary",
        schema: Optional[Type[BaseModel]] = None
    ) -> Union[str, BaseModel]:
        """Analyze content using the LLM.

        :param content: Content to analyze
        :type content: str
        :param analysis_type: Type of analysis to perform
        :type analysis_type: Literal["sentiment", "topics", "summary", "entities"]
        :param schema: Optional output schema for structured analysis
        :type schema: Optional[Type[BaseModel]]
        :return: Analysis result
        :rtype: Union[str, BaseModel]
        :raises AIEngineError: If analysis fails

        Example:
            Text analysis:
                >>> sentiment = await engine.analyze(
                ...     content="This product is amazing!",
                ...     analysis_type="sentiment"
                ... )

            Structured analysis:
                >>> from my_schemas import TextAnalysis
                >>> analysis = await engine.analyze(
                ...     content="Long article text...",
                ...     analysis_type="topics",
                ...     schema=TextAnalysis
                ... )
        """
        # Configure analysis prompt based on type
        prompts = {
            "sentiment": "Analyze the sentiment of the following text:",
            "topics": "Extract the main topics from the following text:",
            "summary": "Provide a concise summary of the following text:",
            "entities": "Extract key entities (people, organizations, locations) from the following text:"
        }

        system_prompt = f"""
        You are an expert content analyzer.
        {prompts[analysis_type]}
        Provide an objective analysis focusing on {analysis_type}.
        """

        return await self.generate(
            content,
            system=system_prompt,
            output_schema=schema,
            temperature=0.1  # Lower temperature for analytical tasks
        )

    async def extract_data(
        self,
        content: str,
        extraction_schema: Type[BaseModel],
    ) -> BaseModel:
        """Extract structured data from content.

        :param content: Content to extract data from
        :type content: str
        :param extraction_schema: Pydantic model defining the data structure
        :type extraction_schema: Type[BaseModel]
        :return: Extracted data
        :rtype: BaseModel
        :raises AIEngineError: If extraction fails
        :raises ValueError: If content cannot be parsed into the schema

        Example:
            >>> class JobPosting(BaseModel):
            ...     title: str
            ...     company: str
            ...     requirements: List[str]
            >>> 
            >>> job = await engine.extract_data(
            ...     content="Job posting text...",
            ...     extraction_schema=JobPosting
            ... )
            >>> print(job.title)
            'Senior Python Developer'
        """
        system_prompt = """
        You are a precise data extractor.
        Extract the requested information from the provided content.
        Follow the output schema exactly.
        """

        return await self.generate(
            content,
            system=system_prompt,
            output_schema=extraction_schema,
            temperature=0.1
        )

    async def generate_text(
        self,
        prompt: str,
        max_length: Optional[int] = None,
        **kwargs
    ) -> Optional[str]:
        """Generate unstructured text content.

        Args:
            prompt: Input prompt
            max_length: Optional maximum length
            **kwargs: Additional arguments for generate()

        Returns:
            Generated text or None on failure
        """
        try:
            # Use str as output type for unstructured text
            # Note: max_length is not directly supported in generate()
            # but can be handled in the prompt or system instructions
            system = kwargs.pop('system', None)
            if max_length:
                system_prefix = f"Keep your response under {max_length} characters. "
                system = system_prefix + (system or "")

            result = await self.generate(
                prompt=prompt,
                output_schema=None,  # We want raw text, not structured output
                system=system,
                **kwargs
            )
            return result
        except Exception as e:
            logger.error("Error generating text: %s", str(e))
            return None

    def add_system_prompt(self, func: callable) -> callable:
        """Register a system prompt function.

        Args:
            func: Function that returns system prompt

        Returns:
            Decorated function
        """
        return self.agent.system_prompt(func)

    def run_sync(
        self,
        prompt: str,
        **kwargs
    ) -> Any:
        """Run generation synchronously.

        Args:
            prompt: Input prompt
            **kwargs: Additional arguments

        Returns:
            Generated content
        """
        result = self.agent.run_sync(prompt, **kwargs)
        return result.output

# Custom exceptions


class AIEngineError(Exception):
    """Base exception for AI engine errors.

    This is the base exception class for all AI engine related errors.
    Specific error types inherit from this class.

    :param message: Error message
    :type message: str

    Example:
        >>> try:
        ...     result = await engine.generate("prompt")
        ... except AIEngineError as e:
        ...     print(f"AI operation failed: {e}")
    """
    pass


class ModelError(AIEngineError):
    """Exception for model-specific errors.

    Raised when the AI model behaves unexpectedly or returns an error.

    :param message: Error message
    :type message: str

    Example:
        >>> try:
        ...     result = await engine.generate("prompt")
        ... except ModelError as e:
        ...     print(f"Model error: {e}")
    """
    pass


class ContentFilterError(AIEngineError):
    """Exception for content that was filtered by safety settings.

    Raised when content is blocked by the model's safety filters.

    :param message: Error message
    :type message: str

    Example:
        >>> try:
        ...     result = await engine.generate("inappropriate content")
        ... except ContentFilterError as e:
        ...     print(f"Content filtered: {e}")
    """
    pass

# Utility functions


def create_default_safety_settings() -> List[GeminiSafetySettings]:
    """Create default safety settings for Gemini models."""
    return [
        GeminiSafetySettings(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
        GeminiSafetySettings(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
        GeminiSafetySettings(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
        GeminiSafetySettings(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
    ]


def default_gemini_settings() -> GeminiSettings:
    """Create default settings for Gemini models."""
    return GeminiSettings(
        safety_settings=create_default_safety_settings(),
        generation_config={
            "top_k": 40,
            "top_p": 0.95,
            "temperature": 0.7,
        }
    )


def default_openai_settings() -> OpenAISettings:
    """Create default settings for OpenAI models."""
    return OpenAISettings(
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        max_tokens=None  # Let the model decide based on context
    )


def default_anthropic_settings() -> AnthropicSettings:
    """Create default settings for Anthropic models."""
    return AnthropicSettings(
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        max_tokens=None
    )
