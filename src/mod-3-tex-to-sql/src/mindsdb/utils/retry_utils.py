"""
Retry mechanisms for improved API reliability
Provides decorators and utilities for retrying failed operations
"""

import time
import logging
import functools
from typing import Callable, Any, Union, List, Type
import requests
from config.constants import APIConstants

logger = logging.getLogger(__name__)


def is_retryable_exception(exception: Exception) -> bool:
    """Check if an exception should trigger a retry"""
    exception_name = exception.__class__.__name__
    
    # Check for retryable exception types
    if exception_name in APIConstants.RETRYABLE_EXCEPTIONS:
        return True
    
    # Check for specific HTTP status codes
    if isinstance(exception, requests.exceptions.HTTPError):
        if hasattr(exception, 'response') and exception.response is not None:
            return exception.response.status_code in APIConstants.RETRYABLE_HTTP_CODES
    
    # Check for connection-related errors
    if isinstance(exception, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout
    )):
        return True
    
    return False


def calculate_delay(attempt: int, base_delay: float = None, max_delay: float = None) -> float:
    """Calculate exponential backoff delay"""
    base_delay = base_delay or APIConstants.RETRY_INITIAL_DELAY
    max_delay = max_delay or APIConstants.RETRY_MAX_DELAY
    
    # Exponential backoff: base_delay * (backoff_factor ^ attempt)
    delay = base_delay * (APIConstants.RETRY_BACKOFF_FACTOR ** attempt)
    
    # Cap at maximum delay
    return min(delay, max_delay)


def retry_on_failure(
    max_retries: int = None,
    delay: float = None,
    max_delay: float = None,
    exceptions: Union[Type[Exception], List[Type[Exception]]] = None,
    on_retry: Callable[[int, Exception], None] = None
):
    """
    Decorator that retries a function on failure with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)  
        exceptions: Exception types to retry on (defaults to retryable exceptions)
        on_retry: Callback function called on each retry attempt
    
    Example:
        @retry_on_failure(max_retries=3)
        def api_call():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            max_attempts = (max_retries or APIConstants.DEFAULT_MAX_RETRIES) + 1
            base_delay = delay or APIConstants.RETRY_INITIAL_DELAY
            
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry this exception
                    should_retry = (
                        exceptions is None and is_retryable_exception(e)
                    ) or (
                        exceptions is not None and isinstance(e, exceptions)
                    )
                    
                    # If this is the last attempt or shouldn't retry, re-raise
                    if attempt == max_attempts - 1 or not should_retry:
                        logger.error(
                            f"Function {func.__name__} failed after {attempt + 1} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay for next attempt
                    retry_delay = calculate_delay(attempt, base_delay, max_delay)
                    
                    # Log retry attempt
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {retry_delay:.2f}s: {e}"
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback failed: {callback_error}")
                    
                    # Wait before next attempt
                    time.sleep(retry_delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class RetryContext:
    """Context manager for retry operations with custom logic"""
    
    def __init__(
        self,
        max_retries: int = None,
        delay: float = None,
        max_delay: float = None,
        on_retry: Callable[[int, Exception], None] = None
    ):
        self.max_retries = max_retries or APIConstants.DEFAULT_MAX_RETRIES
        self.delay = delay or APIConstants.RETRY_INITIAL_DELAY
        self.max_delay = max_delay or APIConstants.RETRY_MAX_DELAY
        self.on_retry = on_retry
        self.attempt = 0
        self.last_exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self.should_retry(exc_val):
            return True  # Suppress the exception to continue retrying
        return False  # Let exception propagate
    
    def should_retry(self, exception: Exception) -> bool:
        """Check if we should retry given the current state"""
        return (
            self.attempt < self.max_retries and
            is_retryable_exception(exception)
        )
    
    def retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute an operation with retry logic"""
        while self.attempt <= self.max_retries:
            try:
                return operation(*args, **kwargs)
                
            except Exception as e:
                self.last_exception = e
                
                if not self.should_retry(e):
                    logger.error(f"Operation failed permanently after {self.attempt + 1} attempts: {e}")
                    raise
                
                # Calculate delay
                retry_delay = calculate_delay(self.attempt, self.delay, self.max_delay)
                
                # Log retry
                logger.warning(
                    f"Operation failed (attempt {self.attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {retry_delay:.2f}s: {e}"
                )
                
                # Call retry callback
                if self.on_retry:
                    try:
                        self.on_retry(self.attempt + 1, e)
                    except Exception as callback_error:
                        logger.warning(f"Retry callback failed: {callback_error}")
                
                # Wait and increment attempt
                time.sleep(retry_delay)
                self.attempt += 1
        
        # Max retries exceeded
        logger.error(f"Operation failed after {self.max_retries + 1} attempts")
        raise self.last_exception


def create_resilient_session(base_url: str = None) -> requests.Session:
    """Create a requests session with retry configuration and connection pooling"""
    try:
        # Try to use connection pooling if available
        from utils.connection_pool import create_resilient_pooled_session
        return create_resilient_pooled_session(base_url)
    except ImportError:
        # Fallback to basic session if connection pool not available
        session = requests.Session()
        
        # Configure default timeouts
        session.timeout = APIConstants.DEFAULT_TIMEOUT
        
        # Add default headers
        session.headers.update({
            'User-Agent': 'MindsDB-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        return session


# Convenience retry decorators for common scenarios
def retry_api_call(max_retries: int = 3):
    """Simplified decorator for API calls"""
    return retry_on_failure(
        max_retries=max_retries,
        exceptions=(
            requests.exceptions.RequestException,
            ConnectionError,
            TimeoutError
        )
    )


def retry_db_operation(max_retries: int = 2):
    """Simplified decorator for database operations"""  
    return retry_on_failure(
        max_retries=max_retries,
        delay=0.5,  # Shorter delay for DB operations
        exceptions=(ConnectionError, TimeoutError)
    )