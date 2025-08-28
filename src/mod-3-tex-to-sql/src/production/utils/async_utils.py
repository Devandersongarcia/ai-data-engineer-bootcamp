"""Async utilities for better performance and throughput."""

import asyncio
import time
import concurrent.futures
from typing import Any, Callable, List, Optional, Dict, Coroutine, Union
from functools import wraps
import threading

from .logging_utils import get_logger
from .performance_utils import get_performance_monitor, PerformanceMetrics


class AsyncQueryExecutor:
    """Async executor for database queries with connection pooling."""
    
    def __init__(self, max_concurrent_queries: int = 10):
        self.max_concurrent_queries = max_concurrent_queries
        self.semaphore = asyncio.Semaphore(max_concurrent_queries)
        self.logger = get_logger(__name__)
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent_queries,
            thread_name_prefix="async_query"
        )
    
    async def execute_query_async(self, query_func: Callable, *args, **kwargs):
        """Execute a query function asynchronously."""
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            
            try:
                # Run the synchronous query function in a thread pool
                result = await loop.run_in_executor(
                    self._executor,
                    query_func,
                    *args,
                    **kwargs
                )
                return result
            except Exception as e:
                self.logger.error(f"Async query execution failed: {e}")
                raise
    
    async def execute_batch_queries(self, query_tasks: List[tuple]) -> List[Any]:
        """Execute multiple queries concurrently."""
        self.logger.info(f"Executing {len(query_tasks)} queries in parallel")
        start_time = time.time()
        
        # Create async tasks
        tasks = []
        for query_func, args, kwargs in query_tasks:
            task = self.execute_query_async(query_func, *args, **kwargs)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        error_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch query {i} failed: {result}")
                processed_results.append(None)
                error_count += 1
            else:
                processed_results.append(result)
        
        execution_time = (time.time() - start_time) * 1000
        self.logger.info(
            f"Batch execution completed in {execution_time:.2f}ms "
            f"({len(query_tasks) - error_count}/{len(query_tasks)} successful)"
        )
        
        return processed_results
    
    def __del__(self):
        """Clean up thread pool executor."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


class ConcurrentProcessor:
    """Process multiple operations concurrently with rate limiting."""
    
    def __init__(self, max_concurrent: int = 5, rate_limit_per_second: Optional[float] = None):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit_per_second
        self.logger = get_logger(__name__)
        
        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0
        self._rate_lock = threading.Lock()
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        if not self.rate_limit:
            return
        
        with self._rate_lock:
            current_time = time.time()
            
            # Reset counter if more than 1 second has passed
            if current_time - self._last_request_time >= 1.0:
                self._request_count = 0
                self._last_request_time = current_time
            
            # Check if we've exceeded rate limit
            if self._request_count >= self.rate_limit:
                sleep_time = 1.0 - (current_time - self._last_request_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    self._request_count = 0
                    self._last_request_time = time.time()
            
            self._request_count += 1
    
    async def process_concurrent(self, items: List[Any], process_func: Callable, **kwargs) -> List[Any]:
        """Process items concurrently with rate limiting."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_item(item):
            async with semaphore:
                # Rate limiting
                if self.rate_limit:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._check_rate_limit)
                
                # Process item
                try:
                    if asyncio.iscoroutinefunction(process_func):
                        return await process_func(item, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, process_func, item, **kwargs)
                except Exception as e:
                    self.logger.error(f"Concurrent processing failed for item: {e}")
                    return None
        
        # Create tasks for all items
        tasks = [process_item(item) for item in items]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results


def async_cache_wrapper(cache_key_func: Optional[Callable] = None, ttl: int = 300):
    """Decorator for caching async function results."""
    cache = {}
    cache_times = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = str(args) + str(sorted(kwargs.items()))
            
            # Check cache
            current_time = time.time()
            if (cache_key in cache and 
                cache_key in cache_times and 
                current_time - cache_times[cache_key] < ttl):
                return cache[cache_key]
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache[cache_key] = result
            cache_times[cache_key] = current_time
            
            # Clean old cache entries (simple cleanup)
            if len(cache) > 1000:
                old_keys = [
                    key for key, timestamp in cache_times.items()
                    if current_time - timestamp > ttl
                ]
                for key in old_keys:
                    cache.pop(key, None)
                    cache_times.pop(key, None)
            
            return result
        
        return wrapper
    return decorator


class BackgroundTaskManager:
    """Manage background tasks for non-blocking operations."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._tasks: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, Any] = {}
    
    def start_background_task(self, name: str, coro: Coroutine, callback: Optional[Callable] = None):
        """Start a background task."""
        async def task_wrapper():
            try:
                result = await coro
                self._results[name] = result
                
                if callback:
                    callback(result)
                
                self.logger.info(f"Background task '{name}' completed successfully")
                return result
                
            except Exception as e:
                self.logger.error(f"Background task '{name}' failed: {e}")
                self._results[name] = e
                
                if callback:
                    callback(e)
                
                raise
            finally:
                # Clean up task reference
                self._tasks.pop(name, None)
        
        # Cancel existing task with same name
        if name in self._tasks and not self._tasks[name].done():
            self._tasks[name].cancel()
        
        # Start new task
        task = asyncio.create_task(task_wrapper())
        self._tasks[name] = task
        
        self.logger.info(f"Started background task: {name}")
        return task
    
    def get_task_result(self, name: str) -> Optional[Any]:
        """Get result of completed background task."""
        return self._results.get(name)
    
    def is_task_running(self, name: str) -> bool:
        """Check if task is currently running."""
        return name in self._tasks and not self._tasks[name].done()
    
    def cancel_task(self, name: str) -> bool:
        """Cancel a running background task."""
        if name in self._tasks and not self._tasks[name].done():
            self._tasks[name].cancel()
            self.logger.info(f"Cancelled background task: {name}")
            return True
        return False
    
    def get_all_task_status(self) -> Dict[str, str]:
        """Get status of all tasks."""
        status = {}
        
        for name, task in self._tasks.items():
            if task.done():
                if task.cancelled():
                    status[name] = "cancelled"
                elif task.exception():
                    status[name] = "failed"
                else:
                    status[name] = "completed"
            else:
                status[name] = "running"
        
        return status
    
    async def wait_for_task(self, name: str, timeout: Optional[float] = None) -> Any:
        """Wait for a background task to complete."""
        if name not in self._tasks:
            raise ValueError(f"Task '{name}' not found")
        
        try:
            result = await asyncio.wait_for(self._tasks[name], timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self.logger.warning(f"Task '{name}' timed out after {timeout} seconds")
            raise


def run_async_in_sync(async_func: Callable, *args, **kwargs):
    """Run async function in synchronous context."""
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        
        # If loop is running, use run_in_executor
        if loop.is_running():
            # Create a new event loop in a thread
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(async_func(*args, **kwargs))
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        else:
            # Use existing loop
            return loop.run_until_complete(async_func(*args, **kwargs))
            
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(async_func(*args, **kwargs))


class AsyncBatchProcessor:
    """Process items in batches asynchronously."""
    
    def __init__(self, batch_size: int = 100, max_concurrent_batches: int = 3):
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.logger = get_logger(__name__)
    
    def create_batches(self, items: List[Any]) -> List[List[Any]]:
        """Split items into batches."""
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batches.append(batch)
        return batches
    
    async def process_batches(self, items: List[Any], process_func: Callable, **kwargs) -> List[Any]:
        """Process items in batches asynchronously."""
        batches = self.create_batches(items)
        self.logger.info(f"Processing {len(items)} items in {len(batches)} batches")
        
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)
        
        async def process_batch(batch, batch_num):
            async with semaphore:
                self.logger.debug(f"Processing batch {batch_num + 1}/{len(batches)}")
                
                try:
                    if asyncio.iscoroutinefunction(process_func):
                        return await process_func(batch, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, process_func, batch, **kwargs)
                except Exception as e:
                    self.logger.error(f"Batch {batch_num + 1} processing failed: {e}")
                    return []
        
        # Process all batches concurrently
        tasks = [process_batch(batch, i) for i, batch in enumerate(batches)]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        all_results = []
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                continue
            elif isinstance(batch_result, list):
                all_results.extend(batch_result)
            else:
                all_results.append(batch_result)
        
        self.logger.info(f"Batch processing completed: {len(all_results)} results")
        return all_results


# Global instances
_async_query_executor: Optional[AsyncQueryExecutor] = None
_background_task_manager: Optional[BackgroundTaskManager] = None


def get_async_query_executor() -> AsyncQueryExecutor:
    """Get global async query executor."""
    global _async_query_executor
    if _async_query_executor is None:
        _async_query_executor = AsyncQueryExecutor()
    return _async_query_executor


def get_background_task_manager() -> BackgroundTaskManager:
    """Get global background task manager."""
    global _background_task_manager
    if _background_task_manager is None:
        _background_task_manager = BackgroundTaskManager()
    return _background_task_manager


def make_async_compatible(sync_func: Callable):
    """Make a synchronous function work in async context."""
    @wraps(sync_func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)
    
    return async_wrapper