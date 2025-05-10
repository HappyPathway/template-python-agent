"""Standard Logger Implementation.

This module provides a concrete implementation of the LoggerBase interface
with additional features like JSON formatting, automatic context capture,
and better exception handling.
"""
import json
import logging
import os
import platform
import socket
import threading
import traceback
from datetime import datetime
from functools import wraps
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any, Callable, Dict, List, Optional, Set, Union, Type

from ailf.core.logger_base import LoggerBase


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.
    
    Formats log records as JSON objects for better parsing and analysis.
    """
    
    def __init__(self, include_timestamp=True, additional_fields=None):
        """Initialize JSON formatter.
        
        Args:
            include_timestamp: Whether to include a timestamp field
            additional_fields: Additional fields to include in every log
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.additional_fields = additional_fields or {}
        
    def format(self, record):
        """Format a log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            str: JSON-formatted log message
        """
        log_dict = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Add timestamp if requested
        if self.include_timestamp:
            log_dict["timestamp"] = datetime.fromtimestamp(record.created).isoformat()
            
        # Add additional context from record
        if hasattr(record, "context") and record.context:
            log_dict["context"] = record.context
            
        # Add exception info if present
        if record.exc_info:
            log_dict["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        # Add any additional fields
        log_dict.update(self.additional_fields)
        
        return json.dumps(log_dict)


class StandardLogger(LoggerBase):
    """Standard logger implementation with advanced features.
    
    This class extends LoggerBase with features like JSON formatting,
    auto-rotating log files, context decoration, and more.
    
    Example:
        >>> logger = StandardLogger("my_app")
        >>> logger.info("Starting app", version="1.0.0")
        >>> 
        >>> # JSON formatting
        >>> json_logger = StandardLogger("json_logger", config={"format": "json"})
        >>> json_logger.info("API request", endpoint="/users", status=200)
        >>> 
        >>> # Log file rotation
        >>> file_logger = StandardLogger("file_logger", config={
        ...     "output": "file",
        ...     "file_path": "app.log",
        ...     "rotation": "size",
        ...     "max_bytes": 10485760,  # 10 MB
        ...     "backup_count": 5
        ... })
    """
    
    # Keep track of all created loggers for global configuration
    _instances = {}
    
    def __init__(self, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize standard logger.
        
        Args:
            name: Logger name
            config: Optional configuration dictionary
        """
        super().__init__(name, config)
        
        # Register this instance
        StandardLogger._instances[self.name] = self
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        config = super()._get_default_config()
        config.update({
            "format": "standard",  # 'standard' or 'json'
            "include_hostname": False,
            "include_thread": False,
            "capture_call_context": True,
            "rotation": None,  # None, 'size', or 'time'
            "max_bytes": 10485760,  # 10 MB for size rotation
            "backup_count": 5,
            "when": "midnight",  # for time rotation (D, H, M, etc.)
            "add_color": True,  # Add ANSI colors to console output
        })
        return config
        
    def _initialize(self) -> None:
        """Initialize the logger with custom configuration."""
        # Get the configured log level
        level_name = self.config.get("level", "info").lower()
        self.level = self.LOG_LEVELS.get(level_name, logging.INFO)
        
        # Initialize the Python logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.level)
        
        # Remove existing handlers to avoid duplicates when re-initializing
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            
        # Set up handlers based on the configuration
        self._setup_handlers()
        
    def _setup_handlers(self) -> None:
        """Set up logging handlers with more advanced options."""
        output = self.config.get("output", "stdout").lower()
        format_type = self.config.get("format", "standard").lower()
        
        # Create formatter based on format type
        if format_type == "json":
            additional_fields = {}
            
            # Add hostname if requested
            if self.config.get("include_hostname", False):
                additional_fields["hostname"] = socket.gethostname()
                
            # Add platform info
            additional_fields["platform"] = platform.platform()
                
            formatter = JSONFormatter(
                include_timestamp=True,
                additional_fields=additional_fields
            )
        else:  # standard format
            log_format = self.config.get("format", None)
            
            if log_format is None:
                # Build format string based on configuration
                parts = ["%(asctime)s - %(name)s - %(levelname)s"]
                
                if self.config.get("include_thread", False):
                    parts.append("(thread:%(threadName)s)")
                    
                if self.config.get("include_hostname", False):
                    # Add hostname using a filter since it's not part of LogRecord
                    hostname = socket.gethostname()
                    parts.append(f"[{hostname}]")
                    
                parts.append("%(message)s")
                log_format = " ".join(parts)
                
            date_format = self.config.get("date_format")
            formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
            
        # Set up console handler if requested
        if output in ["stdout", "both"]:
            console = logging.StreamHandler()
            console.setFormatter(formatter)
            console.setLevel(self.level)
            
            # Add colors if requested and not using JSON format
            if self.config.get("add_color", True) and format_type != "json":
                self._add_colors_to_handler(console)
                
            self.logger.addHandler(console)
            
        # Set up file handler if requested
        if output in ["file", "both"]:
            file_path = self.config.get("file_path")
            if not file_path:
                # Default to <name>.log in current directory
                file_path = f"{self.name}.log"
                
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
                # Set up the appropriate file handler based on rotation settings
                rotation = self.config.get("rotation")
                
                if rotation == "size":
                    handler = RotatingFileHandler(
                        file_path,
                        maxBytes=self.config.get("max_bytes", 10485760),
                        backupCount=self.config.get("backup_count", 5)
                    )
                elif rotation == "time":
                    handler = TimedRotatingFileHandler(
                        file_path,
                        when=self.config.get("when", "midnight"),
                        backupCount=self.config.get("backup_count", 5)
                    )
                else:
                    handler = logging.FileHandler(file_path)
                    
                handler.setFormatter(formatter)
                handler.setLevel(self.level)
                self.logger.addHandler(handler)
            except Exception as e:
                # Fall back to console logging if file handling fails
                console = logging.StreamHandler()
                console.setFormatter(formatter)
                console.setLevel(self.level)
                self.logger.addHandler(console)
                
                # Log the error to stderr
                import sys
                sys.stderr.write(f"Failed to set up log file '{file_path}': {str(e)}\n")
                
    def _add_colors_to_handler(self, handler: logging.Handler) -> None:
        """Add ANSI color codes to log output.
        
        Args:
            handler: Handler to add colors to
        """
        # Define ANSI color codes for different log levels
        colors = {
            "DEBUG": "\033[36m",     # Cyan
            "INFO": "\033[32m",      # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "CRITICAL": "\033[41m",  # White on Red background
        }
        reset = "\033[0m"  # Reset code
        
        # Get the original formatter
        formatter = handler.formatter
        
        # Create a new formatter that adds color codes
        class ColorFormatter(logging.Formatter):
            def format(self, record):
                levelname = record.levelname
                if levelname in colors:
                    record.levelname = f"{colors[levelname]}{levelname}{reset}"
                    record.msg = f"{colors[levelname]}{record.msg}{reset}"
                return formatter.format(record)
                
        handler.setFormatter(ColorFormatter(formatter._fmt, formatter.datefmt))
                
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context data for logging with improved presentation.
        
        Args:
            context: Context data dictionary
            
        Returns:
            str: Formatted context string
        """
        if self.config.get("format") == "json":
            # Don't format context for JSON logging - it's handled by the formatter
            return ""
            
        return super()._format_context(context)
        
    def _write_log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Write a log message with enhanced context handling.
        
        Adds support for automatic context capture and better exception formatting.
        
        Args:
            level: Log level
            msg: Log message
            *args: Message formatting args
            **kwargs: Additional context
        """
        # Format the message
        formatted_msg = self._format_message(msg, *args, **kwargs)
        
        # Create a record
        record = logging.LogRecord(
            name=self.name,
            level=level,
            pathname="",
            lineno=0,
            msg=formatted_msg,
            args=(),
            exc_info=kwargs.get("exc_info"),
        )
        
        # Add context to the record for JSON formatter
        if self.config.get("format") == "json" and kwargs:
            # Remove special kwargs
            context = kwargs.copy()
            context.pop("exc_info", None)
            record.context = context
            
        # Add thread info if requested
        if self.config.get("include_thread", False):
            record.threadName = threading.current_thread().name
            
        # Log the record
        self.logger.handle(record)
        
        # Update metrics
        if self.config.get("track_metrics", True):
            self._update_metrics(level)
            
    def with_context(self, **context):
        """Create a context manager/decorator that adds context to all log calls.
        
        This provides a way to add consistent context to multiple log calls.
        
        Args:
            **context: Context values to include
            
        Returns:
            Union[ContextManager, Callable]: Context manager or decorator
        
        Example:
            >>> # As a context manager
            >>> with logger.with_context(request_id="123"):
            ...     logger.info("Processing request")  # Includes request_id
            ...     logger.info("Request complete")    # Also includes request_id
            >>> 
            >>> # As a decorator
            >>> @logger.with_context(component="auth")
            >>> def authenticate_user(user_id):
            ...     logger.info("Authenticating user", user_id=user_id)
        """
        class LogContextManager:
            def __init__(self, logger, context):
                self.logger = logger
                self.context = context
                self.original_methods = {}
                
            def __enter__(self):
                # Save original methods
                for method_name in ['debug', 'info', 'warning', 'error', 'critical']:
                    original_method = getattr(self.logger, method_name)
                    self.original_methods[method_name] = original_method
                    
                    # Replace with context-aware version
                    @wraps(original_method)
                    def with_context_method(msg, *args, **kwargs):
                        # Merge contexts, with kwargs having priority
                        ctx = self.context.copy()
                        ctx.update(kwargs)
                        return original_method(msg, *args, **ctx)
                        
                    setattr(self.logger, method_name, with_context_method)
                    
                return self.logger
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore original methods
                for method_name, method in self.original_methods.items():
                    setattr(self.logger, method_name, method)
                    
            def __call__(self, func):
                @wraps(func)
                def wrapper(*args, **kwargs):
                    with self:
                        return func(*args, **kwargs)
                return wrapper
                
        return LogContextManager(self, context)
        
    @classmethod
    def get_logger(cls, name: str = None, config: Dict[str, Any] = None) -> 'StandardLogger':
        """Factory method to get or create a logger.
        
        Returns an existing logger if one with the given name exists,
        otherwise creates a new one.
        
        Args:
            name: Logger name
            config: Optional configuration dictionary
            
        Returns:
            StandardLogger: Logger instance
        """
        if name in cls._instances:
            # Return existing instance if config is None, otherwise reconfigure
            instance = cls._instances[name]
            if config is not None:
                instance.config.update(config)
                instance._initialize()
            return instance
        else:
            # Create new instance
            return cls(name, config)
        
    @classmethod
    def set_global_level(cls, level: Union[int, str]) -> None:
        """Set the log level for all loggers created by this class.
        
        Args:
            level: New log level (name or numeric value)
        """
        for logger in cls._instances.values():
            logger.set_level(level)
            
    @classmethod
    def configure_all(cls, config: Dict[str, Any]) -> None:
        """Apply configuration to all loggers created by this class.
        
        Args:
            config: Configuration dictionary
        """
        for logger in cls._instances.values():
            logger.config.update(config)
            logger._initialize()