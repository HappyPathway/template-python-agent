"""Standardized Logging Configuration

This module provides a unified logging setup that ensures all components use consistent 
log formatting and behavior, making it easier to monitor and debug the application.

Key Features:
- Consistency: Uniform log formatting across all modules
- Ease of Use: Simple function to set up logging for any module
- Scalability: Supports adding custom handlers if needed

Example Usage:
    ```python
    from core.logging import setup_logging
    
    logger = setup_logging('my_module')
    logger.info('This is an info message')
    logger.error('This is an error message')
    ```

Use this module to ensure reliable and consistent logging throughout your application.
"""
import logging
import sys
from typing import Optional


def setup_logging(logger_name: str, log_level: Optional[int] = None) -> logging.Logger:
    """Set Up Standardized Logging Configuration

    This function creates and configures a logger with consistent formatting and behavior.
    It ensures that all logs are formatted uniformly, making it easier to monitor and debug
    the application.

    Args:
        logger_name (str): The name for the logger, typically the module name.
        log_level (Optional[int]): Optional logging level (e.g. logging.INFO)

    Returns:
        logging.Logger: A configured logger instance ready for use.

    Example:
        ```python
        from core.logging import setup_logging

        logger = setup_logging('my_module')
        logger.info('Application started')
        ```

    Why Use This Function:
        - Ensures consistent log formatting
        - Simplifies logger setup for developers
        - Avoids reconfiguring loggers with existing handlers
        - Provides uniform logging behavior across the application
    """
    # Get logger instance
    logger = logging.getLogger(logger_name)

    # Only add handler if the logger doesn't already have one
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        if log_level:
            handler.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add formatter to handler
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)

        # Set default level if not already set
        if not log_level and not logger.level:
            logger.setLevel(logging.INFO)

    return logger

# Make sure the root logger has a handler to avoid "no handler found" warnings
logging.getLogger().addHandler(logging.NullHandler())
