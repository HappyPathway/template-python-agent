"""AI Engine Factory Module.

This module provides a factory class for creating and configuring
different AI engine implementations based on configuration.
"""
import os
from typing import Dict, Any, Optional, Type, Union

from ailf.core.ai_engine_base import AIEngineBase
from ailf.core.logging import setup_logging


class AIEngineFactory:
    """Factory for creating AI engine instances.
    
    This factory provides a convenient way to create and configure
    different AI engine implementations based on configuration.
    
    Example:
        ```python
        # Create a factory
        factory = AIEngineFactory()
        
        # Register engine implementations
        factory.register("openai", OpenAIEngine)
        factory.register("anthropic", AnthropicEngine)
        
        # Create an engine instance
        engine = factory.create(
            provider="openai",
            api_key="your_api_key",
            model="gpt-4o",
            config={"temperature": 0.2}
        )
        
        # Or create from environment variables
        engine = factory.create_from_env("OPENAI_API_KEY")
        ```
    """
    
    def __init__(self):
        """Initialize the factory."""
        self.logger = setup_logging("ai.factory")
        self._engines: Dict[str, Type[AIEngineBase]] = {}
        
    def register(self, 
                provider: str, 
                engine_class: Type[AIEngineBase]) -> None:
        """Register an engine implementation.
        
        Args:
            provider: Provider identifier string
            engine_class: Engine implementation class
        """
        self._engines[provider.lower()] = engine_class
        self.logger.debug("Registered AI engine: %s", provider)
        
    def register_all_available(self) -> None:
        """Register all available engine implementations.
        
        This method attempts to import and register all known engine
        implementations without failing if some are not available.
        """
        # Try to register OpenAI engine
        try:
            from ailf.ai.openai_engine import OpenAIEngine
            self.register("openai", OpenAIEngine)
        except ImportError:
            self.logger.debug("OpenAI engine not available")
            
        # Try to register Anthropic engine
        try:
            from ailf.ai.anthropic_engine import AnthropicEngine
            self.register("anthropic", AnthropicEngine)
        except ImportError:
            self.logger.debug("Anthropic engine not available")
            
        # Add more engines here as they become available
        
    def create(self, 
              provider: str, 
              api_key: str,
              model: Optional[str] = None,
              config: Optional[Dict[str, Any]] = None,
              **kwargs) -> AIEngineBase:
        """Create an engine instance.
        
        Args:
            provider: Provider identifier string
            api_key: API key for the provider
            model: Optional model identifier
            config: Optional configuration dictionary
            **kwargs: Additional provider-specific arguments
            
        Returns:
            AIEngineBase: Configured engine instance
            
        Raises:
            ValueError: If the provider is not registered
        """
        provider = provider.lower()
        
        if provider not in self._engines:
            # Try auto-registering if not found
            self.register_all_available()
            
            if provider not in self._engines:
                raise ValueError(
                    f"Provider '{provider}' not registered. "
                    f"Available providers: {list(self._engines.keys())}"
                )
                
        engine_class = self._engines[provider]
        
        # Create engine instance
        try:
            if provider == "openai":
                return engine_class(
                    api_key=api_key,
                    model=model or "gpt-4o",
                    config=config,
                    **kwargs
                )
            elif provider == "anthropic":
                return engine_class(
                    api_key=api_key,
                    model=model or "claude-3-haiku-20240307",
                    config=config,
                    **kwargs
                )
            else:
                # Generic instantiation for other providers
                return engine_class(
                    api_key=api_key,
                    model=model,
                    config=config,
                    **kwargs
                )
        except Exception as e:
            self.logger.error(
                "Failed to create %s engine: %s", 
                provider, str(e)
            )
            raise
            
    def create_from_env(self, 
                       api_key_env: Optional[str] = None,
                       provider: Optional[str] = None,
                       model: Optional[str] = None,
                       config: Optional[Dict[str, Any]] = None,
                       **kwargs) -> AIEngineBase:
        """Create an engine instance using environment variables.
        
        Args:
            api_key_env: Name of environment variable containing the API key
            provider: Provider identifier string (or loaded from environment)
            model: Optional model identifier (or loaded from environment)
            config: Optional configuration dictionary
            **kwargs: Additional provider-specific arguments
            
        Returns:
            AIEngineBase: Configured engine instance
            
        Raises:
            ValueError: If required environment variables are not set
        """
        # Determine provider from environment if not provided
        if provider is None:
            provider_env = os.environ.get("AILF_AI_PROVIDER")
            if not provider_env:
                # Default to OpenAI if OPENAI_API_KEY is set
                if os.environ.get("OPENAI_API_KEY"):
                    provider = "openai"
                # Default to Anthropic if ANTHROPIC_API_KEY is set
                elif os.environ.get("ANTHROPIC_API_KEY"):
                    provider = "anthropic"
                else:
                    raise ValueError(
                        "No AI provider specified and could not determine from environment. "
                        "Set AILF_AI_PROVIDER environment variable or specify 'provider' parameter."
                    )
            else:
                provider = provider_env
                
        # Determine API key environment variable name if not provided
        if api_key_env is None:
            if provider.lower() == "openai":
                api_key_env = "OPENAI_API_KEY"
            elif provider.lower() == "anthropic":
                api_key_env = "ANTHROPIC_API_KEY"
            else:
                # Try with a standard pattern
                api_key_env = f"{provider.upper()}_API_KEY"
                
        # Get API key from environment
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(
                f"API key environment variable '{api_key_env}' not set. "
                f"Please set this environment variable or provide an API key directly."
            )
            
        # Get model from environment if not provided
        if model is None:
            model_env_var = f"AILF_AI_MODEL_{provider.upper()}"
            model = os.environ.get(model_env_var)
            # No error if model is None, will use default
            
        # Create the engine
        return self.create(
            provider=provider,
            api_key=api_key,
            model=model,
            config=config,
            **kwargs
        )


# Global factory instance for convenience
factory = AIEngineFactory()

# Register default engines
factory.register_all_available()


def create_engine(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> AIEngineBase:
    """Convenience function to create an AI engine.
    
    If api_key is not provided, it will be loaded from environment
    variables based on the provider.
    
    Args:
        provider: Provider identifier (default: "openai")
        api_key: API key (or loaded from environment if None)
        model: Optional model identifier
        config: Optional configuration dictionary
        **kwargs: Additional provider-specific arguments
        
    Returns:
        AIEngineBase: Configured engine instance
    """
    global factory
    
    if api_key is None:
        return factory.create_from_env(
            provider=provider,
            model=model,
            config=config,
            **kwargs
        )
    else:
        return factory.create(
            provider=provider,
            api_key=api_key,
            model=model,
            config=config,
            **kwargs
        )