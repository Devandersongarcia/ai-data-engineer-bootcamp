"""
Correlation ID Tracking System for UberEats Fraud Detection
Enables end-to-end tracking of orders through the entire fraud detection pipeline
"""

import uuid
import logging
import time
from contextvars import ContextVar
from functools import wraps
from typing import Dict, Any, Optional, Callable
from datetime import datetime

# Context variable for correlation ID (thread-safe)
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default=None)

# Context variable for order context (additional order info)
order_context_var: ContextVar[Dict[str, Any]] = ContextVar('order_context', default=None)

class CorrelationContext:
    """Context manager for correlation ID and order context tracking"""
    
    def __init__(self, correlation_id: Optional[str] = None, order_context: Optional[Dict[str, Any]] = None):
        """
        Initialize correlation context
        
        Args:
            correlation_id: Existing correlation ID or None to generate new one
            order_context: Order context information (order_id, user_id, amount, etc.)
        """
        self.correlation_id = correlation_id or self.generate_correlation_id()
        self.order_context = order_context or {}
        self.correlation_token = None
        self.order_token = None
        
        # Create logger for this context
        self.logger = logging.getLogger('correlation')
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a new correlation ID with timestamp and random component"""
        timestamp = int(time.time())
        random_part = uuid.uuid4().hex[:8]
        return f"ord_{timestamp}_{random_part}"
    
    @staticmethod
    def generate_correlation_id_from_order(order_id: str) -> str:
        """Generate correlation ID based on order ID"""
        timestamp = int(time.time())
        # Use first 8 chars of order_id hash for consistency
        order_hash = str(hash(order_id))[-8:]
        return f"ord_{order_id}_{timestamp}_{order_hash}"
    
    def __enter__(self):
        """Enter context and set correlation variables"""
        self.correlation_token = correlation_id_var.set(self.correlation_id)
        self.order_token = order_context_var.set(self.order_context)
        
        # Log context start
        self._log_context_start()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and reset correlation variables"""
        # Log context end
        self._log_context_end(exc_type, exc_val)
        
        # Reset context variables
        if self.correlation_token:
            correlation_id_var.reset(self.correlation_token)
        if self.order_token:
            order_context_var.reset(self.order_token)
    
    def _log_context_start(self):
        """Log correlation context start"""
        record = logging.LogRecord(
            name='correlation',
            level=logging.DEBUG,
            pathname='',
            lineno=0,
            msg="Correlation context started",
            args=(),
            exc_info=None
        )
        
        record.correlation_id = self.correlation_id
        record.order_context = self.order_context
        record.business_event = {
            'type': 'CORRELATION_START',
            'correlation_id': self.correlation_id,
            'order_context': self.order_context,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        self.logger.handle(record)
    
    def _log_context_end(self, exc_type, exc_val):
        """Log correlation context end"""
        success = exc_type is None
        
        record = logging.LogRecord(
            name='correlation',
            level=logging.DEBUG if success else logging.ERROR,
            pathname='',
            lineno=0,
            msg=f"Correlation context ended - {'SUCCESS' if success else 'ERROR'}",
            args=(),
            exc_info=(exc_type, exc_val, None) if exc_type else None
        )
        
        record.correlation_id = self.correlation_id
        record.order_context = self.order_context
        record.business_event = {
            'type': 'CORRELATION_END',
            'correlation_id': self.correlation_id,
            'success': success,
            'error_type': exc_type.__name__ if exc_type else None,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        self.logger.handle(record)
    
    def update_order_context(self, **kwargs):
        """Update order context within this correlation"""
        self.order_context.update(kwargs)
        # Update the context variable
        if self.order_token:
            order_context_var.set(self.order_context)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context"""
    return correlation_id_var.get()

def get_order_context() -> Optional[Dict[str, Any]]:
    """Get current order context from context"""
    return order_context_var.get()

def with_correlation(func: Callable) -> Callable:
    """
    Decorator to automatically add correlation ID and order context to log records
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        correlation_id = get_correlation_id()
        order_context = get_order_context()
        
        if correlation_id or order_context:
            # Store original factory
            old_factory = logging.getLogRecordFactory()
            
            def enhanced_record_factory(*factory_args, **factory_kwargs):
                """Enhanced log record factory with correlation context"""
                record = old_factory(*factory_args, **factory_kwargs)
                
                if correlation_id:
                    record.correlation_id = correlation_id
                
                if order_context:
                    record.order_context = order_context
                
                return record
            
            # Set enhanced factory
            logging.setLogRecordFactory(enhanced_record_factory)
            
            try:
                return func(*args, **kwargs)
            finally:
                # Restore original factory
                logging.setLogRecordFactory(old_factory)
        else:
            return func(*args, **kwargs)
    
    return wrapper

def log_with_correlation(
    logger: logging.Logger,
    level: int,
    message: str,
    **kwargs
):
    """
    Log message with automatic correlation ID and order context injection
    
    Args:
        logger: Logger instance
        level: Log level
        message: Log message
        **kwargs: Additional fields for the log record
    """
    correlation_id = get_correlation_id()
    order_context = get_order_context()
    
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname='',
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    
    if correlation_id:
        record.correlation_id = correlation_id
    
    if order_context:
        record.order_context = order_context
    
    # Add any additional fields
    for key, value in kwargs.items():
        setattr(record, key, value)
    
    logger.handle(record)

class CorrelationLogger:
    """Logger that automatically includes correlation context"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def debug(self, message: str, **kwargs):
        """Log debug message with correlation context"""
        log_with_correlation(self.logger, logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with correlation context"""
        log_with_correlation(self.logger, logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with correlation context"""
        log_with_correlation(self.logger, logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with correlation context"""
        log_with_correlation(self.logger, logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with correlation context"""
        log_with_correlation(self.logger, logging.CRITICAL, message, **kwargs)

def get_correlation_logger(name: str) -> CorrelationLogger:
    """Get a correlation-aware logger"""
    return CorrelationLogger(name)

# Utility functions for common correlation patterns

def start_order_correlation(order_data: Dict[str, Any]) -> CorrelationContext:
    """
    Start correlation context for order processing
    
    Args:
        order_data: Order data including order_id, user_id, amount, etc.
    
    Returns:
        CorrelationContext that should be used as context manager
    """
    order_id = order_data.get('order_id', 'unknown')
    correlation_id = CorrelationContext.generate_correlation_id_from_order(order_id)
    
    order_context = {
        'order_id': order_data.get('order_id'),
        'user_id': order_data.get('user_id'),
        'amount': order_data.get('total_amount'),
        'payment_method': order_data.get('payment_method'),
        'restaurant_id': order_data.get('restaurant_id')
    }
    
    return CorrelationContext(correlation_id=correlation_id, order_context=order_context)

def start_batch_correlation(batch_id: int, batch_size: int) -> CorrelationContext:
    """
    Start correlation context for batch processing
    
    Args:
        batch_id: Batch identifier
        batch_size: Number of orders in batch
    
    Returns:
        CorrelationContext for batch processing
    """
    correlation_id = f"batch_{batch_id}_{int(time.time())}"
    
    batch_context = {
        'batch_id': batch_id,
        'batch_size': batch_size,
        'processing_type': 'batch'
    }
    
    return CorrelationContext(correlation_id=correlation_id, order_context=batch_context)

def propagate_correlation_to_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add correlation information to a dictionary (useful for passing to external systems)
    
    Args:
        data: Dictionary to enhance with correlation info
    
    Returns:
        Enhanced dictionary with correlation fields
    """
    correlation_id = get_correlation_id()
    order_context = get_order_context()
    
    enhanced_data = data.copy()
    
    if correlation_id:
        enhanced_data['_correlation_id'] = correlation_id
    
    if order_context:
        enhanced_data['_order_context'] = order_context
    
    enhanced_data['_correlation_timestamp'] = datetime.utcnow().isoformat() + 'Z'
    
    return enhanced_data

# Performance monitoring utilities

class CorrelationPerformanceTracker:
    """Track performance metrics within correlation context"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = get_correlation_logger('performance')
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Performance tracking started: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        success = exc_type is None
        
        self.logger.info(
            f"Performance tracking completed: {self.operation_name}",
            metrics={
                'operation': self.operation_name,
                'duration_ms': round(duration_ms, 2),
                'success': success,
                'error_type': exc_type.__name__ if exc_type else None
            }
        )

def track_performance(operation_name: str):
    """Context manager to track performance of an operation"""
    return CorrelationPerformanceTracker(operation_name)