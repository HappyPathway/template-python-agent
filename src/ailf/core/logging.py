"""Logging Utility Module.

This module provides convenience functions for setting up loggers
throughout the application using a consistent approach.
"""
import os
from typing import Dict, Any, Optional

from ailf.core.logger import StandardLogger


# Global configuration that applies to all loggers
_GLOBAL_CONFIG = {
    "level": "info",
    "format": "standard",
    "add_color": True,
    "include_context": True
}


def setup_logging(name: str, config: Optional[Dict[str, Any]] = None) -> StandardLogger:
    """Set up a logger with consistent configuration.
    
    This function creates a StandardLogger with the given name,
    combining global configuration with any provided config.
    
    Args:
        name: The name for the logger
        config: Optional configuration to override defaults
        
    Returns:
        StandardLogger: Configured logger instance
    
    Example:
        >>> logger = setup_logging("my_module")
        >>> logger.info("Module initialized")
        
        >>> # Override some config
        >>> debug_logger = setup_logging("debug_module", {"level": "debug"})
    """
    # Start with global config
    effective_config = _GLOBAL_CONFIG.copy()
    
    # Override with environment variables if present
    log_level_env = os.environ.get("AILF_LOG_LEVEL")
    if log_level_env:
        effective_config["level"] = log_level_env
        
    log_format_env = os.environ.get("AILF_LOG_FORMAT")
    if log_format_env and log_format_env.lower() in ["standard", "json"]:
        effective_config["format"] = log_format_env.lower()
        
    # Override with provided config
    if config:
        effective_config.update(config)
    
    # Create and return the logger
    return StandardLogger.get_logger(name, effective_config)


def configure_global_logging(config: Dict[str, Any]) -> None:
    """Configure global logging settings that apply to all new loggers.
    
    Args:
        config: Configuration dictionary to apply globally
    
    Example:
        >>> configure_global_logging({
        ...     "level": "debug",
        ...     "format": "json",
        ...     "include_hostname": True
        ... })
        >>> # All loggers created after this will use these settings
    """
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG.update(config)
    
    # Also apply to existing loggers
    StandardLogger.configure_all(config)


def set_global_log_level(level: str) -> None:
    """Set the log level for all existing loggers.
    
    Args:
        level: Log level to set ("debug", "info", "warning", "error", "critical")
    
    Example:
        >>> set_global_log_level("debug")  # Enable debug logging everywhere
        >>> set_global_log_level("warning")  # Reduce noise in production
    """
    _GLOBAL_CONFIG["level"] = level
    StandardLogger.set_global_level(level)
