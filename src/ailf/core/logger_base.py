"""Base Logger Interface.

This module defines the base logger interface that all logger implementations
should follow. It provides a foundation class with clear extension points for
customization.
"""
import logging
import sys
import time
from abc import ABC
from datetime import datetime
from typing import Any, Dict, Optional, Union, List

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LoggerBase(ABC):
    """Base class for logger implementations.

    This class provides a foundation for all logger implementations with
    clear extension points for customization in subclasses.

    Extension Points:
        - _get_default_config: Override to customize default configuration
        - _initialize: Override to customize initialization logic
        - _format_message: Override to customize message formatting
        - _should_log: Override to customize log filtering
        - _write_log: Override to customize where logs are written

    Example:
        ```python
        class CustomLogger(LoggerBase):
            def __init__(self, name=None, config=None):
                self.custom_destinations = []
                super().__init__(name, config)
                
            def _get_default_config(self):
                config = super()._get_default_config()
                config.update({"enable_metrics": True})
                return config
                
            def _write_log(self, level, msg, *args, **kwargs):
                # First let the parent class log normally
                super()._write_log(level, msg, *args, **kwargs)
                
                # Then do custom logging
                for dest in self.custom_destinations:
                    dest.send(level, msg, *args)
        ```
    """
    
    # Log level mapping
    LOG_LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    def __init__(self, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize logger with optional name and configuration.

        Args:
            name: Logger name (defaults to module name of caller)
            config: Optional configuration dictionary
        """
        self.name = name or self.__class__.__name__
        self.config = config or self._get_default_config()
        self._metrics = {
            "created_at": datetime.now(),
            "log_counts": {level: 0 for level in self.LOG_LEVELS},
            "last_log": None
        }
        self._initialize()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Override this method to provide custom default configuration settings.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        return {
            "level": "info",
            "format": DEFAULT_LOG_FORMAT,
            "date_format": DEFAULT_DATE_FORMAT,
            "output": "stdout",  # or "file" or "both"
            "file_path": None,
            "track_metrics": True,
            "include_context": True,
            "max_context_depth": 3,
        }
        
    def _initialize(self) -> None:
        """Perform initialization after config is set.
        
        Override this method to add custom initialization logic.
        This is called at the end of __init__.
        """
        # Get the configured log level
        level_name = self.config.get("level", "info").lower()
        self.level = self.LOG_LEVELS.get(level_name, logging.INFO)
        
        # Initialize the Python logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.level)
        
        # Remove existing handlers to avoid duplicates when re-initializing
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            
        # Create handlers based on configuration
        self._setup_handlers()
        
    def _setup_handlers(self) -> None:
        """Set up logging handlers based on configuration.
        
        Override this method to customize handler setup.
        """
        log_format = self.config.get("format", DEFAULT_LOG_FORMAT)
        date_format = self.config.get("date_format", DEFAULT_DATE_FORMAT)
        formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        
        output = self.config.get("output", "stdout").lower()
        
        # Set up console handler if requested
        if output in ["stdout", "both"]:
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(formatter)
            console.setLevel(self.level)
            self.logger.addHandler(console)
            
        # Set up file handler if requested
        if output in ["file", "both"]:
            file_path = self.config.get("file_path")
            if file_path:
                try:
                    file_handler = logging.FileHandler(file_path)
                    file_handler.setFormatter(formatter)
                    file_handler.setLevel(self.level)
                    self.logger.addHandler(file_handler)
                except Exception as e:
                    # Fall back to stdout if file handling fails
                    sys.stderr.write(f"Failed to set up log file: {str(e)}\n")
                    if output == "file" and not self.logger.handlers:
                        console = logging.StreamHandler(sys.stdout)
                        console.setFormatter(formatter)
                        console.setLevel(self.level)
                        self.logger.addHandler(console)
        
    def _format_message(self, msg: str, *args: Any, **kwargs: Any) -> str:
        """Format a log message with args and kwargs.
        
        Override this method to customize message formatting.
        
        Args:
            msg: Message template
            *args: Positional arguments for formatting
            **kwargs: Keyword arguments for context
            
        Returns:
            str: Formatted message
        """
        # First, format the message with positional args
        if args:
            try:
                msg = msg % args
            except (TypeError, ValueError):
                # Fall back to simple concatenation if formatting fails
                msg = f"{msg} {' '.join(str(arg) for arg in args)}"
                
        # Append context data if configured
        if self.config.get("include_context", True) and kwargs:
            context = self._format_context(kwargs)
            if context:
                msg = f"{msg} {context}"
                
        return msg
        
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context data for logging.
        
        Override this method to customize context formatting.
        
        Args:
            context: Context data dictionary
            
        Returns:
            str: Formatted context string
        """
        max_depth = self.config.get("max_context_depth", 3)
        
        # Helper function for truncation with max depth
        def _format_value(value, depth=0):
            if depth >= max_depth:
                return "..."
                
            if isinstance(value, dict):
                if not value:
                    return "{}"
                return "{" + ", ".join(f"{k}={_format_value(v, depth+1)}" for k, v in value.items()) + "}"
            elif isinstance(value, (list, tuple)):
                if not value:
                    return "[]"
                return "[" + ", ".join(_format_value(v, depth+1) for v in value) + "]"
            else:
                return str(value)
                
        items = [f"{k}={_format_value(v)}" for k, v in context.items()]
        return f"[{' | '.join(items)}]"
        
    def _should_log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> bool:
        """Determine if a message should be logged.
        
        Override this method to customize log filtering.
        
        Args:
            level: Log level
            msg: Log message
            *args: Message formatting args
            **kwargs: Additional context
            
        Returns:
            bool: True if the message should be logged
        """
        # Default implementation just checks the level
        return level >= self.level
        
    def _write_log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Write a log message to the configured outputs.
        
        Override this method to customize where logs are written.
        
        Args:
            level: Log level
            msg: Log message
            *args: Message formatting args
            **kwargs: Additional context
        """
        # Format the message
        formatted_msg = self._format_message(msg, *args, **kwargs)
        
        # Write to the Python logger
        self.logger.log(level, formatted_msg)
        
        # Update metrics
        if self.config.get("track_metrics", True):
            self._update_metrics(level)
        
    def _update_metrics(self, level: int) -> None:
        """Update internal logging metrics.
        
        Args:
            level: Log level
        """
        # Find the level name
        level_name = "unknown"
        for name, value in self.LOG_LEVELS.items():
            if value == level:
                level_name = name
                break
                
        # Update counts
        if level_name in self._metrics["log_counts"]:
            self._metrics["log_counts"][level_name] += 1
        else:
            self._metrics["log_counts"][level_name] = 1
            
        # Update timestamp
        self._metrics["last_log"] = datetime.now()
        
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message.
        
        Args:
            msg: Message format string
            *args: Format string arguments
            **kwargs: Additional context data
        """
        if self._should_log(logging.DEBUG, msg, *args, **kwargs):
            self._write_log(logging.DEBUG, msg, *args, **kwargs)
            
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message.
        
        Args:
            msg: Message format string
            *args: Format string arguments
            **kwargs: Additional context data
        """
        if self._should_log(logging.INFO, msg, *args, **kwargs):
            self._write_log(logging.INFO, msg, *args, **kwargs)
            
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message.
        
        Args:
            msg: Message format string
            *args: Format string arguments
            **kwargs: Additional context data
        """
        if self._should_log(logging.WARNING, msg, *args, **kwargs):
            self._write_log(logging.WARNING, msg, *args, **kwargs)
    
    # Alias for warning
    warn = warning
            
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message.
        
        Args:
            msg: Message format string
            *args: Format string arguments
            **kwargs: Additional context data
        """
        if self._should_log(logging.ERROR, msg, *args, **kwargs):
            self._write_log(logging.ERROR, msg, *args, **kwargs)
            
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message.
        
        Args:
            msg: Message format string
            *args: Format string arguments
            **kwargs: Additional context data
        """
        if self._should_log(logging.CRITICAL, msg, *args, **kwargs):
            self._write_log(logging.CRITICAL, msg, *args, **kwargs)
            
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception message with traceback.
        
        Args:
            msg: Message format string
            *args: Format string arguments
            **kwargs: Additional context data
        """
        # Include exc_info by default
        kwargs.setdefault('exc_info', True)
        self.error(msg, *args, **kwargs)
            
    def log(self, level: Union[int, str], msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a message with an explicit level.
        
        Args:
            level: Log level (name or numeric value)
            msg: Message format string
            *args: Format string arguments
            **kwargs: Additional context data
        """
        # Convert string level to numeric if needed
        if isinstance(level, str):
            level = self.LOG_LEVELS.get(level.lower(), logging.INFO)
            
        if self._should_log(level, msg, *args, **kwargs):
            self._write_log(level, msg, *args, **kwargs)
            
    def set_level(self, level: Union[int, str]) -> None:
        """Set the logging level.
        
        Args:
            level: New log level (name or numeric value)
        """
        if isinstance(level, str):
            level = self.LOG_LEVELS.get(level.lower(), logging.INFO)
            
        self.level = level
        self.logger.setLevel(level)
        
        # Update handlers
        for handler in self.logger.handlers:
            handler.setLevel(level)
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics.
        
        Returns:
            Dict[str, Any]: Logging metrics
        """
        if not self.config.get("track_metrics", True):
            return {}
            
        metrics = dict(self._metrics)
        
        # Add derived metrics
        now = datetime.now()
        uptime = (now - metrics["created_at"]).total_seconds()
        metrics["uptime"] = uptime
        
        # Calculate total logs
        total_logs = sum(metrics["log_counts"].values())
        metrics["total_logs"] = total_logs
        
        # Calculate logs per level percentage
        if total_logs > 0:
            percentages = {}
            for level, count in metrics["log_counts"].items():
                percentages[f"{level}_percent"] = (count / total_logs) * 100
            metrics["percentages"] = percentages
            
        return metrics