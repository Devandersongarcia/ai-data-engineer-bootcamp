"""Utility functions for UberEats Brasil production system."""

# Phase 1 & 2 utilities
from .logging_utils import get_logger, setup_logging, log_performance
from .security_utils import validate_sql_query, sanitize_input, mask_sensitive_data
from .error_handling import handle_database_error, handle_api_error, UberEatsError
from .health_check import get_health_checker, HealthStatus, HealthCheckResult

# Phase 3 performance utilities
from .performance_utils import (
    get_query_cache, get_performance_monitor, cached_query, performance_tracked,
    optimize_dataframe_memory, IntelligentCache, PerformanceMetrics
)
from .connection_pool import get_connection_manager, setup_default_pools
from .async_utils import (
    get_async_query_executor, get_background_task_manager, run_async_in_sync,
    make_async_compatible, AsyncBatchProcessor
)

__all__ = [
    # Phase 1 & 2
    "get_logger",
    "setup_logging", 
    "log_performance",
    "validate_sql_query",
    "sanitize_input",
    "mask_sensitive_data",
    "handle_database_error",
    "handle_api_error", 
    "UberEatsError",
    "get_health_checker",
    "HealthStatus",
    "HealthCheckResult",
    # Phase 3 performance
    "get_query_cache",
    "get_performance_monitor",
    "cached_query",
    "performance_tracked",
    "optimize_dataframe_memory",
    "IntelligentCache",
    "PerformanceMetrics",
    "get_connection_manager",
    "setup_default_pools",
    "get_async_query_executor",
    "get_background_task_manager",
    "run_async_in_sync",
    "make_async_compatible",
    "AsyncBatchProcessor"
]