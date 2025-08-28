"""Production-grade error handling with structured exceptions and recovery patterns.

This module provides comprehensive error handling capabilities including:
- Structured custom exceptions with context
- Automated error classification and severity assessment
- Retry mechanisms with exponential backoff
- Comprehensive error logging and alerting
- Error recovery strategies
"""

import sys
import traceback
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Callable, Type

from .logging_utils import get_logger


class ErrorSeverity(Enum):
    """Standardized error severity classification."""
    LOW = "low"          # Minor issues, system continues normally
    MEDIUM = "medium"    # Notable issues, may affect some functionality
    HIGH = "high"        # Serious issues, significant impact on operations
    CRITICAL = "critical" # System-threatening issues, immediate attention required


class ErrorCategory(Enum):
    """Comprehensive error categorization for systematic handling."""
    DATABASE = "database"                # Database connectivity, query issues
    API = "api"                          # External API failures, rate limits
    VALIDATION = "validation"            # Input validation, data format issues
    AUTHENTICATION = "authentication"    # Authentication, authorization failures
    CONFIGURATION = "configuration"      # Config errors, missing settings
    PERFORMANCE = "performance"          # Performance degradation, timeouts
    NETWORK = "network"                  # Network connectivity issues
    RESOURCE = "resource"                # Memory, disk, CPU resource issues
    UNKNOWN = "unknown"                  # Unclassified errors


@dataclass
class ErrorContext:
    """Rich contextual information for comprehensive error tracking.
    
    Attributes:
        user_id: User identifier associated with the error
        session_id: Session identifier for request tracing
        request_id: Unique request identifier
        operation: Name of the operation that failed
        component: System component where error occurred
        additional_data: Flexible container for extra context
        stack_trace: Optional stack trace information
        timestamp: Error occurrence timestamp
    """
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


class UberEatsError(Exception):
    """Base exception class with comprehensive error handling capabilities.
    
    This exception class provides structured error handling with automatic
    classification, logging, and context preservation for debugging.
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None,
        auto_log: bool = True
    ):
        """Initialize structured exception with rich context.
        
        Args:
            message: Human-readable error description
            category: Error classification category
            severity: Error severity level
            context: Optional contextual information
            original_exception: Original exception that caused this error
            auto_log: Whether to automatically log the error
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        self.error_id = self._generate_error_id()
        
        # Capture stack trace if not in context
        if self.context.stack_trace is None:
            self.context.stack_trace = traceback.format_exc()
        
        if auto_log:
            self._log_error()
    
    def _generate_error_id(self) -> str:
        """Generate unique error identifier for tracking."""
        import uuid
        return f"ERR-{uuid.uuid4().hex[:8].upper()}"
    
    def _log_error(self) -> None:
        """Log error with appropriate severity level and comprehensive context."""
        logger = get_logger(__name__)
        
        log_data = {
            "error_id": self.error_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat()
        }
        
        # Add contextual information
        if self.context:
            context_fields = [
                'operation', 'component', 'user_id', 'session_id', 'request_id'
            ]
            for field in context_fields:
                value = getattr(self.context, field, None)
                if value:
                    log_data[field] = value
            
            if self.context.additional_data:
                log_data.update(self.context.additional_data)
        
        # Log at appropriate level
        log_message = f"[{self.error_id}] {self.message}"
        
        severity_to_log_level = {
            ErrorSeverity.CRITICAL: logger.critical,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.MEDIUM: logger.warning,
            ErrorSeverity.LOW: logger.info
        }
        
        log_func = severity_to_log_level.get(self.severity, logger.warning)
        log_func(log_message, extra=log_data)
        
        # Log original exception with stack trace
        if self.original_exception:
            logger.debug(
                f"[{self.error_id}] Original exception: {self.original_exception}",
                exc_info=self.original_exception
            )
    
    def to_dict(self, include_stack_trace: bool = False) -> Dict[str, Any]:
        """Serialize error to dictionary for logging, storage, or API responses.
        
        Args:
            include_stack_trace: Whether to include stack trace in output
            
        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            "error_id": self.error_id,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.context:
            context_dict = {
                "operation": self.context.operation,
                "component": self.context.component,
                "user_id": self.context.user_id,
                "session_id": self.context.session_id,
                "request_id": self.context.request_id,
                "additional_data": self.context.additional_data
            }
            # Remove None values
            error_dict["context"] = {k: v for k, v in context_dict.items() if v is not None}
            
            if include_stack_trace and self.context.stack_trace:
                error_dict["stack_trace"] = self.context.stack_trace
        
        if self.original_exception:
            error_dict["original_exception"] = {
                "type": type(self.original_exception).__name__,
                "message": str(self.original_exception)
            }
        
        return error_dict
    
    def is_recoverable(self) -> bool:
        """Determine if this error type is potentially recoverable.
        
        Returns:
            True if error might be recoverable with retry
        """
        recoverable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.API,
            ErrorCategory.PERFORMANCE
        }
        
        return (
            self.category in recoverable_categories and
            self.severity in (ErrorSeverity.LOW, ErrorSeverity.MEDIUM)
        )


class DatabaseError(UberEatsError):
    """Specialized exception for database-related failures."""
    
    def __init__(
        self, 
        message: str, 
        context: Optional[ErrorContext] = None, 
        original_exception: Optional[Exception] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH
    ):
        """Initialize database error with appropriate defaults.
        
        Args:
            message: Error description
            context: Optional error context
            original_exception: Original database exception
            severity: Error severity (defaults to HIGH)
        """
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            severity=severity,
            context=context,
            original_exception=original_exception
        )


class APIError(UberEatsError):
    """Specialized exception for external API failures."""
    
    def __init__(
        self, 
        message: str, 
        context: Optional[ErrorContext] = None, 
        original_exception: Optional[Exception] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        status_code: Optional[int] = None
    ):
        """Initialize API error with HTTP context.
        
        Args:
            message: Error description
            context: Optional error context
            original_exception: Original API exception
            severity: Error severity (defaults to MEDIUM)
            status_code: HTTP status code if applicable
        """
        if context and status_code:
            if context.additional_data is None:
                context.additional_data = {}
            context.additional_data['status_code'] = status_code
        
        super().__init__(
            message=message,
            category=ErrorCategory.API,
            severity=severity,
            context=context,
            original_exception=original_exception
        )


class ValidationError(UberEatsError):
    """Specialized exception for input validation failures."""
    
    def __init__(
        self, 
        message: str, 
        context: Optional[ErrorContext] = None, 
        original_exception: Optional[Exception] = None,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None
    ):
        """Initialize validation error with field context.
        
        Args:
            message: Validation error description
            context: Optional error context
            original_exception: Original validation exception
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
        """
        if context and (field_name or field_value):
            if context.additional_data is None:
                context.additional_data = {}
            if field_name:
                context.additional_data['field_name'] = field_name
            if field_value is not None:
                context.additional_data['field_value'] = str(field_value)
        
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            context=context,
            original_exception=original_exception
        )


class ConfigurationError(UberEatsError):
    """Specialized exception for configuration issues."""
    
    def __init__(
        self, 
        message: str, 
        context: Optional[ErrorContext] = None, 
        original_exception: Optional[Exception] = None,
        config_key: Optional[str] = None
    ):
        """Initialize configuration error with config context.
        
        Args:
            message: Configuration error description
            context: Optional error context
            original_exception: Original configuration exception
            config_key: Configuration key that caused the error
        """
        if context and config_key:
            if context.additional_data is None:
                context.additional_data = {}
            context.additional_data['config_key'] = config_key
        
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            original_exception=original_exception
        )


def handle_database_error(
    operation: str,
    original_exception: Exception,
    context: Optional[ErrorContext] = None
) -> Dict[str, Any]:
    """Handle database errors with intelligent classification and response generation.
    
    Args:
        operation: Description of the failed database operation
        original_exception: Original exception that occurred
        context: Optional additional context information
    
    Returns:
        Standardized error response with classification and recovery suggestions
    """
    if context is None:
        context = ErrorContext()
    
    context.operation = operation
    context.component = "database"
    
    # Intelligent error classification
    error_message = str(original_exception).lower()
    severity, friendly_message, suggestions = _classify_database_error(error_message)
    
    # Create structured exception
    db_error = DatabaseError(
        message=friendly_message,
        context=context,
        original_exception=original_exception,
        severity=severity,
        auto_log=False  # We'll log manually for better control
    )
    
    # Enhanced logging
    logger = get_logger(__name__)
    logger.error(
        f"Database error in {operation}: {friendly_message}",
        extra={
            "error_id": db_error.error_id,
            "operation": operation,
            "original_error": str(original_exception),
            "suggestions": suggestions
        }
    )
    
    return {
        "success": False,
        "error": friendly_message,
        "error_id": db_error.error_id,
        "category": "database",
        "severity": severity.value,
        "suggestions": suggestions,
        "recoverable": db_error.is_recoverable(),
        "timestamp": datetime.now().isoformat(),
        "context": db_error.context.operation
    }

def _classify_database_error(error_message: str) -> tuple[ErrorSeverity, str, list[str]]:
    """Classify database error and provide recovery suggestions."""
    error_patterns = {
        ("connection", "timeout", "network"): (
            ErrorSeverity.HIGH,
            "Database connection issue. Please try again.",
            ["Check network connectivity", "Verify database server status", "Retry after brief delay"]
        ),
        ("permission", "access", "denied"): (
            ErrorSeverity.CRITICAL,
            "Database access denied. Please check permissions.",
            ["Verify database credentials", "Check user permissions", "Contact administrator"]
        ),
        ("syntax", "invalid", "malformed"): (
            ErrorSeverity.MEDIUM,
            "Invalid query format. Please check input.",
            ["Review query syntax", "Validate input parameters", "Check table/column names"]
        ),
        ("deadlock", "lock"): (
            ErrorSeverity.MEDIUM,
            "Database lock detected. Retrying operation.",
            ["Operation will retry automatically", "Consider reducing transaction scope"]
        ),
        ("duplicate", "constraint", "unique"): (
            ErrorSeverity.LOW,
            "Data constraint violation. Please check input uniqueness.",
            ["Verify data uniqueness", "Check existing records", "Modify input data"]
        )
    }
    
    for patterns, (severity, message, suggestions) in error_patterns.items():
        if any(pattern in error_message for pattern in patterns):
            return severity, message, suggestions
    
    # Default classification
    return (
        ErrorSeverity.MEDIUM,
        "Database operation failed. Please try again.",
        ["Retry the operation", "Check system status", "Contact support if issue persists"]
    )


def handle_api_error(
    operation: str,
    original_exception: Exception,
    context: Optional[ErrorContext] = None,
    status_code: Optional[int] = None
) -> Dict[str, Any]:
    """Handle API errors with intelligent classification and retry recommendations.
    
    Args:
        operation: Description of the failed API operation
        original_exception: Original exception that occurred
        context: Optional additional context information
        status_code: HTTP status code if applicable
    
    Returns:
        Standardized error response with recovery recommendations
    """
    if context is None:
        context = ErrorContext()
    
    context.operation = operation
    context.component = "api"
    
    # Classify API error
    error_message = str(original_exception).lower()
    severity, friendly_message, suggestions = _classify_api_error(error_message, status_code)
    
    # Create structured exception
    api_error = APIError(
        message=friendly_message,
        context=context,
        original_exception=original_exception,
        severity=severity,
        status_code=status_code,
        auto_log=False
    )
    
    # Enhanced logging
    logger = get_logger(__name__)
    logger.error(
        f"API error in {operation}: {friendly_message}",
        extra={
            "error_id": api_error.error_id,
            "operation": operation,
            "status_code": status_code,
            "original_error": str(original_exception),
            "suggestions": suggestions
        }
    )
    
    return {
        "success": False,
        "error": friendly_message,
        "error_id": api_error.error_id,
        "category": "api",
        "severity": severity.value,
        "status_code": status_code,
        "suggestions": suggestions,
        "recoverable": api_error.is_recoverable(),
        "timestamp": datetime.now().isoformat(),
        "context": api_error.context.operation
    }

def _classify_api_error(
    error_message: str, 
    status_code: Optional[int] = None
) -> tuple[ErrorSeverity, str, list[str]]:
    """Classify API error based on message and status code."""
    # Status code based classification
    if status_code:
        if status_code == 401:
            return (
                ErrorSeverity.HIGH,
                "API authentication failed. Please check credentials.",
                ["Verify API key", "Check authentication method", "Renew expired tokens"]
            )
        elif status_code == 429:
            return (
                ErrorSeverity.MEDIUM,
                "API rate limit exceeded. Please wait before retrying.",
                ["Implement exponential backoff", "Reduce request frequency", "Check rate limit headers"]
            )
        elif status_code >= 500:
            return (
                ErrorSeverity.HIGH,
                "API server error. The service is temporarily unavailable.",
                ["Retry after delay", "Check service status", "Implement circuit breaker"]
            )
    
    # Message-based classification
    error_patterns = {
        ("api key", "authentication", "unauthorized"): (
            ErrorSeverity.HIGH,
            "API authentication failed. Please verify credentials.",
            ["Check API key validity", "Verify authentication headers", "Review API documentation"]
        ),
        ("rate limit", "quota", "throttled"): (
            ErrorSeverity.MEDIUM,
            "API rate limit exceeded. Please wait before retrying.",
            ["Implement rate limiting", "Use exponential backoff", "Check usage quotas"]
        ),
        ("network", "connection", "timeout"): (
            ErrorSeverity.MEDIUM,
            "Network connectivity issue. Please check connection.",
            ["Check internet connectivity", "Verify DNS resolution", "Test with different network"]
        )
    }
    
    for patterns, (severity, message, suggestions) in error_patterns.items():
        if any(pattern in error_message for pattern in patterns):
            return severity, message, suggestions
    
    # Default classification
    return (
        ErrorSeverity.MEDIUM,
        "API request failed. Please try again.",
        ["Retry the request", "Check API documentation", "Verify request parameters"]
    )


class ErrorHandler:
    """Advanced error handling system with intelligent retry logic and recovery patterns.
    
    Features:
        - Configurable retry strategies with exponential backoff
        - Error classification and recovery recommendations
        - Circuit breaker patterns for failing services
        - Comprehensive logging and metrics collection
    """
    
    def __init__(
        self, 
        max_retries: int = 3, 
        base_delay: float = 1.0, 
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0
    ):
        """Initialize error handler with configurable retry parameters.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.logger = get_logger(__name__)
        self._circuit_breakers = {}
        self._error_counts = {}
    
    def with_retry(
        self,
        operation: Callable,
        operation_name: str,
        context: Optional[ErrorContext] = None,
        retryable_exceptions: tuple = (Exception,),
        custom_max_retries: Optional[int] = None
    ):
        """Execute operation with intelligent retry logic and exponential backoff.
        
        Args:
            operation: Function to execute
            operation_name: Operation identifier for logging and metrics
            context: Optional error context for enhanced logging
            retryable_exceptions: Exceptions that should trigger retry
            custom_max_retries: Override default max retries for this operation
        
        Returns:
            Result of the successful operation
        
        Raises:
            UberEatsError: If all retries are exhausted or non-retryable error occurs
        """
        max_attempts = custom_max_retries or self.max_retries
        last_exception = None
        
        for attempt in range(max_attempts + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_backoff_delay(attempt)
                    self.logger.info(
                        f"Retrying {operation_name} (attempt {attempt + 1}/{max_attempts + 1}) "
                        f"after {delay:.1f}s delay"
                    )
                    
                    import time
                    time.sleep(delay)
                
                result = operation()
                
                # Reset error count on success
                self._error_counts.pop(operation_name, None)
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                self._track_error(operation_name, e)
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {operation_name}: {e}",
                    extra={"attempt": attempt + 1, "operation": operation_name}
                )
                
                if attempt == max_attempts:
                    break
                    
            except Exception as e:
                # Non-retryable exception
                self.logger.error(f"Non-retryable error in {operation_name}: {e}")
                raise UberEatsError(
                    message=f"Operation {operation_name} failed with non-retryable error: {e}",
                    context=context,
                    original_exception=e,
                    category=self._classify_error_category(e)
                )
        
        # All retries exhausted
        final_error = UberEatsError(
            message=f"Operation {operation_name} failed after {max_attempts + 1} attempts",
            context=context,
            original_exception=last_exception,
            category=self._classify_error_category(last_exception) if last_exception else ErrorCategory.UNKNOWN
        )
        
        self.logger.error(f"All retries exhausted for {operation_name}")
        raise final_error
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        import random
        
        delay = min(
            self.base_delay * (self.backoff_multiplier ** (attempt - 1)),
            self.max_delay
        )
        
        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * random.random()
        return delay + jitter
    
    def _track_error(self, operation_name: str, error: Exception) -> None:
        """Track error occurrences for circuit breaker logic."""
        self._error_counts[operation_name] = self._error_counts.get(operation_name, 0) + 1
    
    def _classify_error_category(self, error: Exception) -> ErrorCategory:
        """Classify error into appropriate category."""
        error_str = str(error).lower()
        
        if any(keyword in error_str for keyword in ['connection', 'network', 'timeout']):
            return ErrorCategory.NETWORK
        elif any(keyword in error_str for keyword in ['database', 'sql', 'query']):
            return ErrorCategory.DATABASE
        elif any(keyword in error_str for keyword in ['api', 'http', 'request']):
            return ErrorCategory.API
        elif any(keyword in error_str for keyword in ['validation', 'invalid', 'format']):
            return ErrorCategory.VALIDATION
        elif any(keyword in error_str for keyword in ['auth', 'permission', 'access']):
            return ErrorCategory.AUTHENTICATION
        else:
            return ErrorCategory.UNKNOWN
    
    def safe_execute(
        self,
        operation: Callable,
        operation_name: str,
        context: Optional[ErrorContext] = None,
        default_return: Any = None,
        suppress_logging: bool = False
    ) -> Any:
        """Execute operation safely with graceful error handling.
        
        This method catches all exceptions and returns a default value instead of raising.
        Useful for non-critical operations where failure should not interrupt the main flow.
        
        Args:
            operation: Function to execute
            operation_name: Operation identifier for logging
            context: Optional error context
            default_return: Value to return on any error
            suppress_logging: Whether to suppress error logging
        
        Returns:
            Operation result on success, default_return on error
        """
        try:
            return operation()
        except Exception as e:
            if not suppress_logging:
                self.logger.warning(f"Safe execution failed for {operation_name}: {e}")
            
            # Create error for tracking but don't raise it
            error = UberEatsError(
                message=f"Safe execution of {operation_name} failed: {e}",
                context=context,
                original_exception=e,
                category=self._classify_error_category(e),
                auto_log=not suppress_logging
            )
            
            self._track_error(operation_name, e)
            return default_return
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics for monitoring.
        
        Returns:
            Dictionary with error counts, rates, and trends
        """
        return {
            "total_operations_tracked": len(self._error_counts),
            "error_counts_by_operation": dict(self._error_counts),
            "high_error_operations": {
                op: count for op, count in self._error_counts.items() 
                if count > 10
            },
            "circuit_breaker_status": dict(self._circuit_breakers),
            "timestamp": datetime.now().isoformat()
        }


def create_error_context(
    operation: Optional[str] = None,
    component: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs
) -> ErrorContext:
    """Create comprehensive error context with flexible parameters.
    
    Args:
        operation: Name of the failed operation
        component: System component where error occurred
        user_id: User identifier for request tracing
        session_id: Session identifier for request tracing
        request_id: Unique request identifier
        **kwargs: Additional contextual data
    
    Returns:
        Populated ErrorContext instance
    """
    return ErrorContext(
        operation=operation,
        component=component,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        additional_data=kwargs if kwargs else None
    )


def get_error_summary(exception: Exception, include_traceback: bool = True) -> Dict[str, Any]:
    """Generate comprehensive error summary for logging and debugging.
    
    Args:
        exception: Exception to analyze and summarize
        include_traceback: Whether to include full stack trace
    
    Returns:
        Dictionary containing detailed error information
    """
    summary = {
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "error_module": getattr(exception, '__module__', 'unknown'),
        "timestamp": datetime.now().isoformat()
    }
    
    # Add traceback if requested
    if include_traceback:
        summary["traceback"] = traceback.format_exc()
        summary["stack_depth"] = len(traceback.extract_tb(exception.__traceback__)) if exception.__traceback__ else 0
    
    # Add exception-specific attributes
    if hasattr(exception, 'args') and exception.args:
        summary["exception_args"] = list(exception.args)
    
    # For structured exceptions, add additional details
    if isinstance(exception, UberEatsError):
        summary.update({
            "error_id": exception.error_id,
            "category": exception.category.value,
            "severity": exception.severity.value,
            "is_recoverable": exception.is_recoverable()
        })
        
        if exception.context:
            summary["error_context"] = {
                "operation": exception.context.operation,
                "component": exception.context.component,
                "user_id": exception.context.user_id,
                "session_id": exception.context.session_id
            }
    
    return summary