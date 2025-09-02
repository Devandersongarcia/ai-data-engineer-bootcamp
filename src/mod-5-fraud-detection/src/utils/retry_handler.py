"""Retry mechanisms with exponential backoff for fraud detection system.

Provides resilient error handling for external service calls with configurable
retry strategies, circuit breaker integration, and comprehensive failure tracking.
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import threading

from .circuit_breaker import CircuitBreakerError, circuit_breaker_manager

logger = logging.getLogger(__name__)


class RetryPolicy(Enum):
    """Retry policy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff" 
    FIXED_DELAY = "fixed_delay"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_max: float = 0.1
    policy: RetryPolicy = RetryPolicy.EXPONENTIAL_BACKOFF
    
    # Exception handling
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()
    
    # Circuit breaker integration
    integrate_circuit_breaker: bool = True
    circuit_breaker_name: Optional[str] = None


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay: float
    exception: Optional[Exception] = None
    timestamp: float = field(default_factory=time.time)
    success: bool = False


@dataclass
class RetryResult:
    """Result of retry operation."""
    success: bool
    result: Any = None
    final_exception: Optional[Exception] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_duration: float = 0.0
    circuit_breaker_triggered: bool = False


class RetryHandler:
    """Advanced retry handler with multiple backoff strategies."""
    
    def __init__(self, config: RetryConfig):
        """Initialize retry handler.
        
        Args:
            config: Retry configuration
        """
        self.config = config
        self._validate_config()
        
    def _validate_config(self):
        """Validate retry configuration."""
        if self.config.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        
        if self.config.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")
            
        if self.config.max_delay < self.config.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
            
        if self.config.backoff_multiplier <= 0:
            raise ValueError("backoff_multiplier must be positive")
    
    def retry(self, func: Callable, *args, **kwargs) -> RetryResult:
        """Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments  
            **kwargs: Function keyword arguments
            
        Returns:
            RetryResult with outcome and attempt information
        """
        start_time = time.time()
        attempts = []
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            attempt_start = time.time()
            
            try:
                # Check circuit breaker if configured
                if (self.config.integrate_circuit_breaker and 
                    self.config.circuit_breaker_name):
                    
                    cb = circuit_breaker_manager.get_circuit_breaker(
                        self.config.circuit_breaker_name
                    )
                    if cb.is_open():
                        return RetryResult(
                            success=False,
                            final_exception=CircuitBreakerError(
                                f"Circuit breaker open: {self.config.circuit_breaker_name}"
                            ),
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                            circuit_breaker_triggered=True
                        )
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Success
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    timestamp=attempt_start,
                    success=True
                ))
                
                logger.info(f"Function succeeded on attempt {attempt_num}")
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )
                
            except Exception as e:
                # Check if exception should be retried
                if not self._should_retry(e, attempt_num):
                    attempts.append(RetryAttempt(
                        attempt_number=attempt_num,
                        delay=0.0,
                        exception=e,
                        timestamp=attempt_start
                    ))
                    
                    logger.error(f"Non-retryable exception on attempt {attempt_num}: {e}")
                    
                    return RetryResult(
                        success=False,
                        final_exception=e,
                        attempts=attempts,
                        total_duration=time.time() - start_time
                    )
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt_num)
                
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay=delay,
                    exception=e,
                    timestamp=attempt_start
                ))
                
                logger.warning(f"Attempt {attempt_num} failed: {e}. "
                             f"Retrying in {delay:.2f}s...")
                
                # Wait before next attempt (except for last attempt)
                if attempt_num < self.config.max_attempts:
                    time.sleep(delay)
        
        # All attempts failed
        final_exception = attempts[-1].exception if attempts else Exception("No attempts made")
        
        logger.error(f"All {self.config.max_attempts} attempts failed. "
                    f"Final exception: {final_exception}")
        
        return RetryResult(
            success=False,
            final_exception=final_exception,
            attempts=attempts,
            total_duration=time.time() - start_time
        )
    
    async def retry_async(self, func: Callable, *args, **kwargs) -> RetryResult:
        """Execute async function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            RetryResult with outcome and attempt information
        """
        start_time = time.time()
        attempts = []
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            attempt_start = time.time()
            
            try:
                # Check circuit breaker if configured
                if (self.config.integrate_circuit_breaker and 
                    self.config.circuit_breaker_name):
                    
                    cb = circuit_breaker_manager.get_circuit_breaker(
                        self.config.circuit_breaker_name
                    )
                    if cb.is_open():
                        return RetryResult(
                            success=False,
                            final_exception=CircuitBreakerError(
                                f"Circuit breaker open: {self.config.circuit_breaker_name}"
                            ),
                            attempts=attempts,
                            total_duration=time.time() - start_time,
                            circuit_breaker_triggered=True
                        )
                
                # Execute async function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    timestamp=attempt_start,
                    success=True
                ))
                
                logger.info(f"Async function succeeded on attempt {attempt_num}")
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_duration=time.time() - start_time
                )
                
            except Exception as e:
                # Check if exception should be retried
                if not self._should_retry(e, attempt_num):
                    attempts.append(RetryAttempt(
                        attempt_number=attempt_num,
                        delay=0.0,
                        exception=e,
                        timestamp=attempt_start
                    ))
                    
                    logger.error(f"Non-retryable async exception on attempt {attempt_num}: {e}")
                    
                    return RetryResult(
                        success=False,
                        final_exception=e,
                        attempts=attempts,
                        total_duration=time.time() - start_time
                    )
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt_num)
                
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay=delay,
                    exception=e,
                    timestamp=attempt_start
                ))
                
                logger.warning(f"Async attempt {attempt_num} failed: {e}. "
                             f"Retrying in {delay:.2f}s...")
                
                # Wait before next attempt (except for last attempt)
                if attempt_num < self.config.max_attempts:
                    await asyncio.sleep(delay)
        
        # All attempts failed
        final_exception = attempts[-1].exception if attempts else Exception("No attempts made")
        
        logger.error(f"All {self.config.max_attempts} async attempts failed. "
                    f"Final exception: {final_exception}")
        
        return RetryResult(
            success=False,
            final_exception=final_exception,
            attempts=attempts,
            total_duration=time.time() - start_time
        )
    
    def _should_retry(self, exception: Exception, attempt_num: int) -> bool:
        """Determine if exception should trigger a retry.
        
        Args:
            exception: Exception that occurred
            attempt_num: Current attempt number
            
        Returns:
            True if should retry
        """
        # Check if we've reached max attempts
        if attempt_num >= self.config.max_attempts:
            return False
        
        # Check non-retryable exceptions first
        if self.config.non_retryable_exceptions:
            if isinstance(exception, self.config.non_retryable_exceptions):
                return False
        
        # Check retryable exceptions
        if self.config.retryable_exceptions:
            return isinstance(exception, self.config.retryable_exceptions)
        
        # Default: retry all exceptions
        return True
    
    def _calculate_delay(self, attempt_num: int) -> float:
        """Calculate delay for next retry attempt.
        
        Args:
            attempt_num: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        if self.config.policy == RetryPolicy.FIXED_DELAY:
            delay = self.config.initial_delay
            
        elif self.config.policy == RetryPolicy.LINEAR_BACKOFF:
            delay = self.config.initial_delay * attempt_num
            
        elif self.config.policy == RetryPolicy.EXPONENTIAL_BACKOFF:
            delay = self.config.initial_delay * (self.config.backoff_multiplier ** (attempt_num - 1))
            
        elif self.config.policy == RetryPolicy.FIBONACCI_BACKOFF:
            delay = self.config.initial_delay * self._fibonacci(attempt_num)
            
        else:
            delay = self.config.initial_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if configured
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_max
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter
        
        return max(0.0, delay)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return 1
        elif n == 2:
            return 1
        
        a, b = 1, 1
        for _ in range(3, n + 1):
            a, b = b, a + b
        return b


class RetryManager:
    """Manages multiple retry handlers with different configurations."""
    
    def __init__(self):
        """Initialize retry manager."""
        self._handlers: Dict[str, RetryHandler] = {}
        self._lock = threading.RLock()
    
    def get_handler(self, name: str, config: Optional[RetryConfig] = None) -> RetryHandler:
        """Get or create a retry handler.
        
        Args:
            name: Handler name
            config: Retry configuration (uses default if None)
            
        Returns:
            RetryHandler instance
        """
        with self._lock:
            if name not in self._handlers:
                if config is None:
                    config = RetryConfig()
                
                self._handlers[name] = RetryHandler(config)
            
            return self._handlers[name]
    
    def create_handler(self, name: str, config: RetryConfig) -> RetryHandler:
        """Create a new retry handler with specific configuration.
        
        Args:
            name: Handler name
            config: Retry configuration
            
        Returns:
            RetryHandler instance
        """
        with self._lock:
            handler = RetryHandler(config)
            self._handlers[name] = handler
            return handler
    
    def get_handler_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all handlers."""
        with self._lock:
            return {
                name: {
                    "config": {
                        "max_attempts": handler.config.max_attempts,
                        "initial_delay": handler.config.initial_delay,
                        "policy": handler.config.policy.value
                    }
                }
                for name, handler in self._handlers.items()
            }


# Global retry manager instance
retry_manager = RetryManager()


def retry_on_failure(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    policy: RetryPolicy = RetryPolicy.EXPONENTIAL_BACKOFF,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (),
    circuit_breaker_name: Optional[str] = None
) -> Callable:
    """Decorator to add retry behavior to a function.
    
    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_multiplier: Backoff multiplier
        policy: Retry policy
        retryable_exceptions: Exceptions that trigger retry
        non_retryable_exceptions: Exceptions that don't trigger retry
        circuit_breaker_name: Circuit breaker name for integration
        
    Returns:
        Decorated function with retry behavior
    """
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_multiplier=backoff_multiplier,
            policy=policy,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
            circuit_breaker_name=circuit_breaker_name
        )
        
        handler = RetryHandler(config)
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await handler.retry_async(func, *args, **kwargs)
                if not result.success:
                    raise result.final_exception
                return result.result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = handler.retry(func, *args, **kwargs)
                if not result.success:
                    raise result.final_exception
                return result.result
            return sync_wrapper
    
    return decorator


# Predefined retry configurations for common scenarios
FRAUD_DETECTION_RETRY = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=10.0,
    backoff_multiplier=2.0,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=(ConnectionError, TimeoutError, Exception),
    non_retryable_exceptions=(ValueError, TypeError, CircuitBreakerError)
)

DATABASE_RETRY = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_multiplier=1.5,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=(ConnectionError, TimeoutError),
    non_retryable_exceptions=(ValueError, TypeError)
)

API_CALL_RETRY = RetryConfig(
    max_attempts=4,
    initial_delay=2.0,
    max_delay=60.0,
    backoff_multiplier=2.0,
    policy=RetryPolicy.EXPONENTIAL_BACKOFF,
    jitter=True,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    non_retryable_exceptions=(ValueError, TypeError, PermissionError)
)