"""
Centralized Logging Configuration for UberEats Fraud Detection
Provides structured JSON logging with correlation tracking and business events
"""

import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """JSON structured logging formatter with rich context"""
    
    def format(self, record):
        """Format log record as structured JSON"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = record.correlation_id
        
        # Add order context if present
        if hasattr(record, 'order_context'):
            log_entry['order'] = record.order_context
        
        # Add performance metrics if present
        if hasattr(record, 'metrics'):
            log_entry['metrics'] = record.metrics
        
        # Add business context
        if hasattr(record, 'business_event'):
            log_entry['business_event'] = record.business_event
        
        # Add error details if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for console output"""
    
    def __init__(self):
        super().__init__()
        # Color codes for different log levels
        self.colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'      # Reset
        }
    
    def format(self, record):
        """Format with colors and correlation ID"""
        color = self.colors.get(record.levelname, self.colors['RESET'])
        reset = self.colors['RESET']
        
        # Build message
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        level = f"{color}{record.levelname:<8}{reset}"
        logger_name = f"{record.name:<20}"
        
        message = record.getMessage()
        
        # Add correlation ID if present
        correlation_id = ""
        if hasattr(record, 'correlation_id'):
            correlation_id = f"[{record.correlation_id}] "
        
        # Add order context if present
        order_info = ""
        if hasattr(record, 'order_context'):
            order = record.order_context
            order_id = order.get('order_id', 'unknown')
            amount = order.get('amount', 0)
            order_info = f"[{order_id}:${amount:.2f}] "
        
        return f"{timestamp} {level} {logger_name} {correlation_id}{order_info}{message}"

def setup_logging(log_level: str = 'INFO', enable_file_logging: bool = True) -> tuple:
    """
    Setup comprehensive structured logging for fraud detection system
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to enable file logging
    
    Returns:
        tuple: (root_logger, audit_logger, fraud_logger)
    """
    
    # Create logs directory
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with human-readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleFormatter())
    console_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    if enable_file_logging:
        # Main application log (structured JSON)
        app_handler = logging.FileHandler(logs_dir / 'fraud_detection.json')
        app_handler.setFormatter(StructuredFormatter())
        app_handler.setLevel(logging.DEBUG)  # Capture all levels in file
        root_logger.addHandler(app_handler)
        
        # Error log (structured JSON, errors only)
        error_handler = logging.FileHandler(logs_dir / 'errors.json')
        error_handler.setFormatter(StructuredFormatter())
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
    
    # Specialized loggers
    
    # Audit logger (compliance and regulatory)
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # Don't propagate to root
    
    if enable_file_logging:
        audit_handler = logging.FileHandler(logs_dir / 'audit.json')
        audit_handler.setFormatter(StructuredFormatter())
        audit_logger.addHandler(audit_handler)
    
    # Fraud events logger (business events)
    fraud_logger = logging.getLogger('fraud_events')
    fraud_logger.setLevel(logging.INFO)
    fraud_logger.propagate = False
    
    if enable_file_logging:
        fraud_handler = logging.FileHandler(logs_dir / 'fraud_events.json')
        fraud_handler.setFormatter(StructuredFormatter())
        fraud_logger.addHandler(fraud_handler)
    
    # Performance logger
    perf_logger = logging.getLogger('performance')
    perf_logger.setLevel(logging.INFO)
    perf_logger.propagate = False
    
    if enable_file_logging:
        perf_handler = logging.FileHandler(logs_dir / 'performance.json')
        perf_handler.setFormatter(StructuredFormatter())
        perf_logger.addHandler(perf_handler)
    
    # Transaction logger
    transaction_logger = logging.getLogger('transaction')
    transaction_logger.setLevel(logging.INFO)
    transaction_logger.propagate = True  # Also log to main application log
    
    # Silence noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # Log startup message
    startup_record = logging.LogRecord(
        name='fraud_detection.startup',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg="UberEats Fraud Detection System - Logging Initialized",
        args=(),
        exc_info=None
    )
    
    startup_record.business_event = {
        'type': 'SYSTEM_STARTUP',
        'log_level': log_level,
        'file_logging_enabled': enable_file_logging,
        'logs_directory': str(logs_dir.absolute()),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    root_logger.handle(startup_record)
    
    return root_logger, audit_logger, fraud_logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)

def create_log_record_with_context(
    logger_name: str,
    level: int,
    message: str,
    correlation_id: Optional[str] = None,
    order_context: Optional[Dict[str, Any]] = None,
    business_event: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> logging.LogRecord:
    """
    Create a log record with rich context information
    
    Args:
        logger_name: Name of the logger
        level: Log level (logging.INFO, etc.)
        message: Log message
        correlation_id: Correlation ID for request tracking
        order_context: Order-specific context
        business_event: Business event details
        metrics: Performance metrics
        extra_fields: Additional fields
    
    Returns:
        LogRecord with all context attached
    """
    record = logging.LogRecord(
        name=logger_name,
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
    
    if business_event:
        record.business_event = business_event
    
    if metrics:
        record.metrics = metrics
    
    if extra_fields:
        record.extra_fields = extra_fields
    
    return record

# Module-level setup for convenience
_loggers_initialized = False

def ensure_logging_initialized():
    """Ensure logging is initialized (called automatically by other modules)"""
    global _loggers_initialized
    if not _loggers_initialized:
        setup_logging()
        _loggers_initialized = True

# Initialize on module import
if not _loggers_initialized:
    setup_logging()
    _loggers_initialized = True