"""Standardized logging utilities for consistent logging across the application."""

import logging
import time
import functools
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

def setup_logging(
    logger_name: str,
    log_level: Optional[str] = None,
    include_console: bool = True
) -> logging.Logger:
    """
    Setup standardized logging configuration.
    
    Args:
        logger_name: Name of the logger
        log_level: Optional log level (defaults to INFO)
        include_console: Whether to include console output
    
    Returns:
        Configured logger instance
    """
    # Use provided values or fall back to defaults
    log_level = log_level or "INFO"
    
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level))
    
    # Clear any existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a standardized logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return setup_logging(name)


class PerformanceLogger:
    """Context manager for logging performance metrics."""
    
    def __init__(self, logger: logging.Logger, operation: str, log_level: str = "INFO"):
        self.logger = logger
        self.operation = operation
        self.log_level = getattr(logging, log_level)
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(self.log_level, f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            self.logger.log(self.log_level, f"Completed {self.operation} in {duration:.3f}s")
        else:
            self.logger.error(f"Failed {self.operation} after {duration:.3f}s: {exc_val}")
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the operation if completed."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


def log_performance(operation: str, log_level: str = "INFO"):
    """
    Decorator for logging function performance.
    
    Args:
        operation: Description of the operation
        log_level: Log level for performance messages
    
    Usage:
        @log_performance("SQL query execution")
        def execute_query(sql):
            # function implementation
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            
            with PerformanceLogger(logger, f"{operation} ({func.__name__})", log_level):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_with_context(logger: logging.Logger, level: str, message: str, context: Dict[str, Any] = None):
    """
    Log a message with additional context information.
    
    Args:
        logger: Logger instance
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        context: Additional context information
    """
    log_level = getattr(logging, level.upper())
    
    if context:
        context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
        full_message = f"{message} | {context_str}"
    else:
        full_message = message
    
    logger.log(log_level, full_message)


def mask_sensitive_info(text: str, patterns: list = None) -> str:
    """
    Mask sensitive information in log messages.
    
    Args:
        text: Text to mask
        patterns: List of regex patterns to mask (uses defaults if not provided)
    
    Returns:
        Text with sensitive information masked
    """
    import re
    
    if patterns is None:
        patterns = [
            r'api[_-]?key["\s]*[:=]["\s]*([a-zA-Z0-9-_]{10,})',  # API keys
            r'password["\s]*[:=]["\s]*([^\s"]{6,})',              # Passwords  
            r'token["\s]*[:=]["\s]*([a-zA-Z0-9-_\.]{10,})',      # Tokens
            r'postgresql://([^:]+):([^@]+)@',                     # DB passwords
        ]
    
    masked_text = text
    for pattern in patterns:
        masked_text = re.sub(pattern, r'***MASKED***', masked_text, flags=re.IGNORECASE)
    
    return masked_text


class LoggingMixin:
    """Mixin class to add standardized logging to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def log_info(self, message: str, context: Dict[str, Any] = None):
        """Log info message with optional context."""
        log_with_context(self.logger, "INFO", message, context)
    
    def log_warning(self, message: str, context: Dict[str, Any] = None):
        """Log warning message with optional context."""
        log_with_context(self.logger, "WARNING", message, context)
    
    def log_error(self, message: str, context: Dict[str, Any] = None):
        """Log error message with optional context."""
        log_with_context(self.logger, "ERROR", message, context)
    
    def log_debug(self, message: str, context: Dict[str, Any] = None):
        """Log debug message with optional context."""
        log_with_context(self.logger, "DEBUG", message, context)
    
    def log_performance_start(self, operation: str) -> PerformanceLogger:
        """Start performance logging for an operation."""
        return PerformanceLogger(self.logger, operation)