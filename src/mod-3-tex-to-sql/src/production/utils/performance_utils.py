"""Performance utilities for optimization, caching, and monitoring."""

import time
import hashlib
import pickle
import threading
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Callable, Union, Tuple
from functools import wraps, lru_cache
from dataclasses import dataclass, field
from collections import defaultdict
import json
import os

from .logging_utils import get_logger
from config.settings import get_settings


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    timestamp: datetime
    hit_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl_seconds)
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()


@dataclass 
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cache_hit: Optional[bool] = None
    query_complexity: Optional[int] = None
    result_size: Optional[int] = None
    error_occurred: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, error: Optional[Exception] = None):
        """Mark operation as finished."""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        if error:
            self.error_occurred = True
            self.metadata['error'] = str(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            'operation': self.operation_name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'cache_hit': self.cache_hit,
            'query_complexity': self.query_complexity,
            'result_size': self.result_size,
            'error_occurred': self.error_occurred,
            'metadata': self.metadata
        }


class IntelligentCache:
    """Thread-safe intelligent cache with TTL, size limits, and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600, max_memory_mb: int = 100):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0,
            'memory_usage': 0
        }
        self.logger = get_logger(__name__)
    
    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate size of object in bytes."""
        try:
            return len(pickle.dumps(obj))
        except:
            # Fallback for non-picklable objects
            return len(str(obj).encode('utf-8'))
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else None
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def _evict_expired(self):
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items() 
            if entry.is_expired()
        ]
        for key in expired_keys:
            self._remove_entry(key)
    
    def _evict_lru(self):
        """Evict least recently used entries to free memory."""
        if not self._cache:
            return
        
        # Sort by hit count (ascending) and then by timestamp (ascending)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: (x[1].hit_count, x[1].timestamp)
        )
        
        # Remove entries until we're under limits
        for key, _ in sorted_entries:
            if (len(self._cache) <= self.max_size * 0.8 and 
                self._stats['memory_usage'] <= self.max_memory_bytes * 0.8):
                break
            self._remove_entry(key)
            self._stats['evictions'] += 1
    
    def _remove_entry(self, key: str):
        """Remove entry and update stats."""
        if key in self._cache:
            entry = self._cache[key]
            self._stats['memory_usage'] -= entry.size_bytes
            del self._cache[key]
            self._stats['size'] = len(self._cache)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry.is_expired():
                    self._remove_entry(key)
                    self._stats['misses'] += 1
                    return None
                
                # Update hit count and stats
                entry.hit_count += 1
                self._stats['hits'] += 1
                return entry.value
            
            self._stats['misses'] += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put value in cache."""
        with self._lock:
            # Calculate size
            size_bytes = self._calculate_size(value)
            
            # Check if single item is too large
            if size_bytes > self.max_memory_bytes * 0.5:
                self.logger.warning(f"Cache item too large: {size_bytes} bytes")
                return False
            
            # Clean expired entries first
            self._evict_expired()
            
            # Evict LRU if needed
            while (len(self._cache) >= self.max_size or 
                   self._stats['memory_usage'] + size_bytes > self.max_memory_bytes):
                self._evict_lru()
                if len(self._cache) == 0:
                    break
            
            # Create entry
            entry = CacheEntry(
                value=value,
                timestamp=datetime.now(),
                size_bytes=size_bytes,
                ttl_seconds=ttl or self.default_ttl
            )
            
            # Remove old entry if exists
            if key in self._cache:
                self._remove_entry(key)
            
            # Add new entry
            self._cache[key] = entry
            self._stats['memory_usage'] += size_bytes
            self._stats['size'] = len(self._cache)
            
            return True
    
    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache."""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'size': 0,
                'memory_usage': 0
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                **self._stats,
                'hit_rate': hit_rate,
                'memory_usage_mb': self._stats['memory_usage'] / (1024 * 1024)
            }


class QueryCache(IntelligentCache):
    """Specialized cache for SQL queries and results."""
    
    def __init__(self):
        settings = get_settings()
        super().__init__(
            max_size=getattr(settings, 'query_cache_size', 500),
            default_ttl=getattr(settings, 'query_cache_ttl', 1800),  # 30 minutes
            max_memory_mb=getattr(settings, 'query_cache_memory_mb', 50)
        )
    
    def cache_query_result(self, sql: str, params: Dict[str, Any], result: Any, ttl: Optional[int] = None):
        """Cache SQL query result."""
        key = self._generate_query_key(sql, params)
        return self.put(key, result, ttl)
    
    def get_cached_result(self, sql: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached query result."""
        key = self._generate_query_key(sql, params)
        return self.get(key)
    
    def _generate_query_key(self, sql: str, params: Dict[str, Any]) -> str:
        """Generate cache key for SQL query."""
        # Normalize SQL (remove extra whitespace, convert to lowercase)
        normalized_sql = ' '.join(sql.strip().split()).lower()
        return self._generate_key(normalized_sql, **params)
    
    def invalidate_table_queries(self, table_name: str):
        """Invalidate all cached queries that reference a specific table."""
        with self._lock:
            keys_to_remove = []
            table_lower = table_name.lower()
            
            for key, entry in self._cache.items():
                # This is a simple heuristic - in production you might want more sophisticated tracking
                if hasattr(entry.value, 'query') and table_lower in str(entry.value.query).lower():
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._remove_entry(key)


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, list] = defaultdict(list)
        self._lock = threading.RLock()
        self.logger = get_logger(__name__)
    
    def start_operation(self, operation_name: str, **metadata) -> PerformanceMetrics:
        """Start tracking an operation."""
        return PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now(),
            metadata=metadata
        )
    
    def record_metric(self, metric: PerformanceMetrics):
        """Record a completed performance metric."""
        with self._lock:
            self.metrics[metric.operation_name].append(metric)
            
            # Keep only last 1000 metrics per operation
            if len(self.metrics[metric.operation_name]) > 1000:
                self.metrics[metric.operation_name] = self.metrics[metric.operation_name][-1000:]
        
        # Log slow operations
        if metric.duration_ms and metric.duration_ms > 5000:  # > 5 seconds
            self.logger.warning(f"Slow operation detected: {metric.operation_name} took {metric.duration_ms:.2f}ms")
    
    def get_operation_stats(self, operation_name: str, last_n: int = 100) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        with self._lock:
            operation_metrics = self.metrics.get(operation_name, [])[-last_n:]
            
            if not operation_metrics:
                return {"operation": operation_name, "count": 0}
            
            durations = [m.duration_ms for m in operation_metrics if m.duration_ms is not None]
            cache_hits = [m.cache_hit for m in operation_metrics if m.cache_hit is not None]
            errors = [m for m in operation_metrics if m.error_occurred]
            
            stats = {
                "operation": operation_name,
                "count": len(operation_metrics),
                "error_count": len(errors),
                "error_rate": len(errors) / len(operation_metrics) if operation_metrics else 0
            }
            
            if durations:
                stats.update({
                    "avg_duration_ms": sum(durations) / len(durations),
                    "min_duration_ms": min(durations),
                    "max_duration_ms": max(durations),
                    "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)]
                })
            
            if cache_hits:
                hit_count = sum(1 for hit in cache_hits if hit)
                stats["cache_hit_rate"] = hit_count / len(cache_hits)
            
            return stats
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all operations."""
        with self._lock:
            return {
                operation: self.get_operation_stats(operation)
                for operation in self.metrics.keys()
            }


# Global instances
_query_cache: Optional[QueryCache] = None
_performance_monitor: Optional[PerformanceMonitor] = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def cached_query(ttl: Optional[int] = None, ignore_params: Optional[list] = None):
    """Decorator for caching query results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_query_cache()
            
            # Filter out ignored parameters
            cache_kwargs = kwargs.copy()
            if ignore_params:
                for param in ignore_params:
                    cache_kwargs.pop(param, None)
            
            # Try to get from cache
            cached_result = cache.get_cached_result(
                sql=str(args) if args else "no_args",
                params=cache_kwargs
            )
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.cache_query_result(
                sql=str(args) if args else "no_args",
                params=cache_kwargs,
                result=result,
                ttl=ttl
            )
            
            return result
        return wrapper
    return decorator


def performance_tracked(operation_name: Optional[str] = None):
    """Decorator for tracking performance metrics."""
    def decorator(func):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            metric = monitor.start_operation(op_name)
            
            try:
                result = func(*args, **kwargs)
                
                # Record result size if possible
                if hasattr(result, '__len__'):
                    metric.result_size = len(result)
                
                metric.finish()
                monitor.record_metric(metric)
                return result
                
            except Exception as e:
                metric.finish(error=e)
                monitor.record_metric(metric)
                raise
                
        return wrapper
    return decorator


def warm_up_cache(cache_functions: list):
    """Warm up cache with predefined functions."""
    logger = get_logger(__name__)
    logger.info(f"Warming up cache with {len(cache_functions)} functions")
    
    for func_name, func, args, kwargs in cache_functions:
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            logger.info(f"Cache warm-up: {func_name} completed in {duration:.2f}ms")
        except Exception as e:
            logger.warning(f"Cache warm-up failed for {func_name}: {e}")


def optimize_dataframe_memory(df):
    """Optimize pandas DataFrame memory usage."""
    if df is None or df.empty:
        return df
    
    original_memory = df.memory_usage(deep=True).sum()
    
    # Optimize object columns
    for col in df.select_dtypes(include=['object']):
        if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique values
            df[col] = df[col].astype('category')
    
    # Optimize numeric columns
    for col in df.select_dtypes(include=['int64']):
        if df[col].max() < 2147483647 and df[col].min() > -2147483648:
            df[col] = df[col].astype('int32')
    
    for col in df.select_dtypes(include=['float64']):
        df[col] = df[col].astype('float32')
    
    optimized_memory = df.memory_usage(deep=True).sum()
    reduction_pct = (1 - optimized_memory / original_memory) * 100
    
    if reduction_pct > 10:  # Only log if significant reduction
        logger = get_logger(__name__)
        logger.info(f"DataFrame memory optimized: {reduction_pct:.1f}% reduction")
    
    return df


class BatchProcessor:
    """Process items in batches for better performance."""
    
    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.logger = get_logger(__name__)
    
    def process_batches(self, items: list, process_func: Callable, **kwargs):
        """Process items in batches."""
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            self.logger.debug(f"Processing batch {i//self.batch_size + 1} with {len(batch)} items")
            
            batch_result = process_func(batch, **kwargs)
            results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
        
        return results