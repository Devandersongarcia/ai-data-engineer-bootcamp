"""Performance test suite for fraud detection system.

Tests system performance, scalability, latency, throughput,
and resource utilization under various load conditions.
"""

import asyncio
import concurrent.futures
import time
import threading
from collections import defaultdict
from typing import List, Dict, Any
import pytest
from unittest.mock import Mock, patch
import statistics

# Test imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.circuit_breaker import CircuitBreaker, circuit_breaker_manager
from src.utils.input_validator import validate_order_data
from src.utils.retry_handler import RetryHandler, RetryConfig, RetryPolicy
from src.monitoring.system_monitor import SystemMonitor


class PerformanceTestSuite:
    """Comprehensive performance test suite."""
    
    def setup_method(self):
        """Setup test environment."""
        self.sample_order = {
            "order_id": "perf_test_123",
            "user_id": "user_456",
            "total_amount": 25.99,
            "currency": "USD",
            "payment_method": "credit_card",
            "delivery_country": "US",
            "user_email": "test@example.com",
            "items": [
                {"id": "item1", "name": "Test Item", "price": 25.99}
            ]
        }
        
        self.performance_metrics = defaultdict(list)
    
    def measure_execution_time(self, func, *args, **kwargs):
        """Measure function execution time."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, (end_time - start_time) * 1000  # Return ms
    
    # Input Validation Performance Tests
    def test_input_validation_single_request_latency(self):
        """Test input validation latency for single requests."""
        latencies = []
        
        for _ in range(100):
            _, latency_ms = self.measure_execution_time(
                validate_order_data, self.sample_order
            )
            latencies.append(latency_ms)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        
        # Performance assertions
        assert avg_latency < 10.0, f"Average latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 20.0, f"P95 latency too high: {p95_latency:.2f}ms"
        assert p99_latency < 50.0, f"P99 latency too high: {p99_latency:.2f}ms"
        
        print(f"Input Validation Performance:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms") 
        print(f"  P99: {p99_latency:.2f}ms")
    
    def test_input_validation_throughput(self):
        """Test input validation throughput under load."""
        num_requests = 1000
        start_time = time.perf_counter()
        
        # Sequential processing
        for _ in range(num_requests):
            result = validate_order_data(self.sample_order)
            assert result.is_valid
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        throughput = num_requests / duration
        
        # Should handle at least 100 requests per second
        assert throughput > 100, f"Throughput too low: {throughput:.1f} req/s"
        
        print(f"Input Validation Throughput: {throughput:.1f} req/s")
    
    def test_input_validation_concurrent_performance(self):
        """Test input validation under concurrent load."""
        num_threads = 10
        requests_per_thread = 100
        
        def worker():
            latencies = []
            for _ in range(requests_per_thread):
                start = time.perf_counter()
                result = validate_order_data(self.sample_order)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
                assert result.is_valid
            return latencies
        
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            all_latencies = []
            
            for future in concurrent.futures.as_completed(futures):
                all_latencies.extend(future.result())
        
        end_time = time.perf_counter()
        
        total_requests = num_threads * requests_per_thread
        duration = end_time - start_time
        throughput = total_requests / duration
        
        avg_latency = statistics.mean(all_latencies)
        p95_latency = statistics.quantiles(all_latencies, n=20)[18]
        
        # Performance under concurrency
        assert throughput > 200, f"Concurrent throughput too low: {throughput:.1f} req/s"
        assert avg_latency < 20.0, f"Concurrent avg latency too high: {avg_latency:.2f}ms"
        assert p95_latency < 50.0, f"Concurrent P95 latency too high: {p95_latency:.2f}ms"
        
        print(f"Concurrent Input Validation:")
        print(f"  Throughput: {throughput:.1f} req/s")
        print(f"  Avg Latency: {avg_latency:.2f}ms")
        print(f"  P95 Latency: {p95_latency:.2f}ms")
    
    def test_input_validation_memory_usage(self):
        """Test input validation memory efficiency."""
        import tracemalloc
        
        tracemalloc.start()
        
        # Baseline memory
        baseline = tracemalloc.get_traced_memory()[0]
        
        # Process many requests
        for _ in range(1000):
            result = validate_order_data(self.sample_order)
            assert result.is_valid
        
        # Measure memory after processing
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_used = (current - baseline) / 1024 / 1024  # MB
        peak_memory = (peak - baseline) / 1024 / 1024  # MB
        
        # Should not use excessive memory
        assert memory_used < 10.0, f"Memory usage too high: {memory_used:.2f}MB"
        assert peak_memory < 20.0, f"Peak memory too high: {peak_memory:.2f}MB"
        
        print(f"Input Validation Memory Usage: {memory_used:.2f}MB (peak: {peak_memory:.2f}MB)")
    
    # Circuit Breaker Performance Tests
    def test_circuit_breaker_performance(self):
        """Test circuit breaker performance overhead."""
        circuit_breaker = CircuitBreaker(
            name="perf_test_cb",
            failure_threshold=5,
            recovery_timeout=1.0
        )
        
        def fast_success_function():
            return "success"
        
        # Measure overhead of circuit breaker
        latencies_with_cb = []
        latencies_without_cb = []
        
        # Without circuit breaker
        for _ in range(1000):
            _, latency = self.measure_execution_time(fast_success_function)
            latencies_without_cb.append(latency)
        
        # With circuit breaker
        for _ in range(1000):
            _, latency = self.measure_execution_time(
                circuit_breaker.call, fast_success_function
            )
            latencies_with_cb.append(latency)
        
        avg_without = statistics.mean(latencies_without_cb)
        avg_with = statistics.mean(latencies_with_cb)
        overhead = avg_with - avg_without
        overhead_percent = (overhead / avg_without) * 100
        
        # Circuit breaker should add minimal overhead
        assert overhead_percent < 50.0, f"Circuit breaker overhead too high: {overhead_percent:.1f}%"
        
        print(f"Circuit Breaker Overhead: {overhead:.3f}ms ({overhead_percent:.1f}%)")
    
    def test_circuit_breaker_failure_detection_speed(self):
        """Test circuit breaker failure detection performance."""
        circuit_breaker = CircuitBreaker(
            name="failure_detection_test",
            failure_threshold=3,
            recovery_timeout=0.1
        )
        
        def failing_function():
            raise Exception("Simulated failure")
        
        # Measure time to detect failures and open circuit
        start_time = time.perf_counter()
        
        for _ in range(3):  # Should trigger circuit opening
            try:
                circuit_breaker.call(failing_function)
            except Exception:
                pass
        
        failure_detection_time = time.perf_counter() - start_time
        
        # Should detect failures quickly
        assert failure_detection_time < 0.1, f"Failure detection too slow: {failure_detection_time:.3f}s"
        assert circuit_breaker.is_open()
        
        # Test fast failure when circuit is open
        start_time = time.perf_counter()
        try:
            circuit_breaker.call(failing_function)
        except Exception:
            pass
        fast_failure_time = time.perf_counter() - start_time
        
        assert fast_failure_time < 0.001, f"Fast failure too slow: {fast_failure_time:.6f}s"
        
        print(f"Circuit Breaker Failure Detection: {failure_detection_time:.3f}s")
        print(f"Circuit Breaker Fast Failure: {fast_failure_time:.6f}s")
    
    # Retry Handler Performance Tests
    def test_retry_handler_performance(self):
        """Test retry handler performance characteristics."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.001,  # Very small delay for testing
            max_delay=0.01,
            policy=RetryPolicy.EXPONENTIAL_BACKOFF
        )
        
        retry_handler = RetryHandler(config)
        
        def intermittent_function(attempt_count=[0]):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Simulated failure")
            return "success"
        
        start_time = time.perf_counter()
        result = retry_handler.retry(intermittent_function)
        end_time = time.perf_counter()
        
        assert result.success
        total_time = end_time - start_time
        
        # Should complete retry logic quickly
        assert total_time < 0.1, f"Retry took too long: {total_time:.3f}s"
        
        print(f"Retry Handler Performance: {total_time:.3f}s for 3 attempts")
    
    @pytest.mark.asyncio
    async def test_async_retry_performance(self):
        """Test async retry handler performance."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.001,
            max_delay=0.01,
            policy=RetryPolicy.EXPONENTIAL_BACKOFF
        )
        
        retry_handler = RetryHandler(config)
        
        async def async_intermittent_function(attempt_count=[0]):
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Simulated async failure")
            await asyncio.sleep(0.001)  # Simulate async work
            return "async_success"
        
        start_time = time.perf_counter()
        result = await retry_handler.retry_async(async_intermittent_function)
        end_time = time.perf_counter()
        
        assert result.success
        total_time = end_time - start_time
        
        # Should complete async retry quickly
        assert total_time < 0.1, f"Async retry took too long: {total_time:.3f}s"
        
        print(f"Async Retry Performance: {total_time:.3f}s for 3 attempts")
    
    # System Monitor Performance Tests
    def test_system_monitor_metrics_collection_performance(self):
        """Test system monitoring overhead."""
        monitor = SystemMonitor()
        
        # Measure metrics collection performance
        start_time = time.perf_counter()
        
        for _ in range(100):
            monitor.record_metric("test_metric", 42.0, monitor.MetricType.GAUGE)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        throughput = 100 / duration
        
        # Should handle high throughput of metric recording
        assert throughput > 1000, f"Metrics throughput too low: {throughput:.1f} metrics/s"
        
        print(f"Metrics Collection Throughput: {throughput:.1f} metrics/s")
    
    def test_system_monitor_memory_efficiency(self):
        """Test system monitor memory efficiency with many metrics."""
        import tracemalloc
        
        monitor = SystemMonitor()
        tracemalloc.start()
        
        baseline = tracemalloc.get_traced_memory()[0]
        
        # Record many metrics
        for i in range(10000):
            monitor.record_metric(f"metric_{i % 100}", float(i), monitor.MetricType.COUNTER)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_used = (current - baseline) / 1024 / 1024  # MB
        
        # Should use reasonable memory even with many metrics
        assert memory_used < 50.0, f"Monitor memory usage too high: {memory_used:.2f}MB"
        
        print(f"System Monitor Memory Usage: {memory_used:.2f}MB for 10k metrics")
    
    # Load Testing
    def test_system_under_sustained_load(self):
        """Test system performance under sustained load."""
        duration_seconds = 10
        target_rps = 50  # requests per second
        
        def load_worker():
            end_time = time.time() + duration_seconds
            request_count = 0
            latencies = []
            
            while time.time() < end_time:
                start = time.perf_counter()
                
                # Simulate processing
                result = validate_order_data(self.sample_order)
                assert result.is_valid
                
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
                request_count += 1
                
                # Rate limiting
                time.sleep(1.0 / target_rps)
            
            return request_count, latencies
        
        # Run load test with multiple workers
        num_workers = 4
        start_time = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(load_worker) for _ in range(num_workers)]
            
            total_requests = 0
            all_latencies = []
            
            for future in concurrent.futures.as_completed(futures):
                requests, latencies = future.result()
                total_requests += requests
                all_latencies.extend(latencies)
        
        actual_duration = time.perf_counter() - start_time
        actual_rps = total_requests / actual_duration
        
        avg_latency = statistics.mean(all_latencies)
        p95_latency = statistics.quantiles(all_latencies, n=20)[18]
        
        # Performance under sustained load
        assert actual_rps > target_rps * num_workers * 0.8, f"RPS too low: {actual_rps:.1f}"
        assert avg_latency < 50.0, f"Avg latency under load too high: {avg_latency:.2f}ms"
        assert p95_latency < 100.0, f"P95 latency under load too high: {p95_latency:.2f}ms"
        
        print(f"Sustained Load Test ({duration_seconds}s):")
        print(f"  Actual RPS: {actual_rps:.1f}")
        print(f"  Total Requests: {total_requests}")
        print(f"  Avg Latency: {avg_latency:.2f}ms")
        print(f"  P95 Latency: {p95_latency:.2f}ms")
    
    def test_burst_load_handling(self):
        """Test system performance under burst load."""
        burst_size = 1000
        
        start_time = time.perf_counter()
        
        # Simulate burst of concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(validate_order_data, self.sample_order)
                for _ in range(burst_size)
            ]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # All requests should succeed
        assert all(r.is_valid for r in results)
        
        # Should handle burst load efficiently
        throughput = burst_size / duration
        assert throughput > 100, f"Burst throughput too low: {throughput:.1f} req/s"
        assert duration < 30.0, f"Burst took too long: {duration:.2f}s"
        
        print(f"Burst Load Test:")
        print(f"  {burst_size} requests in {duration:.2f}s")
        print(f"  Throughput: {throughput:.1f} req/s")
    
    # Resource Utilization Tests
    def test_cpu_utilization_under_load(self):
        """Test CPU utilization during processing."""
        import psutil
        import threading
        
        cpu_usage = []
        monitoring = [True]
        
        def cpu_monitor():
            while monitoring[0]:
                cpu_usage.append(psutil.cpu_percent(interval=0.1))
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=cpu_monitor)
        monitor_thread.start()
        
        try:
            # Generate CPU load
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 seconds of load
                validate_order_data(self.sample_order)
        finally:
            monitoring[0] = False
            monitor_thread.join()
        
        if cpu_usage:
            avg_cpu = statistics.mean(cpu_usage)
            max_cpu = max(cpu_usage)
            
            # Should use reasonable CPU
            assert avg_cpu < 90.0, f"Average CPU too high: {avg_cpu:.1f}%"
            assert max_cpu < 100.0, f"Max CPU too high: {max_cpu:.1f}%"
            
            print(f"CPU Utilization: Avg {avg_cpu:.1f}%, Max {max_cpu:.1f}%")
    
    # Memory Leak Tests
    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation."""
        import tracemalloc
        import gc
        
        tracemalloc.start()
        
        # Baseline measurement
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0]
        
        # Process many requests in batches
        for batch in range(10):
            for _ in range(100):
                result = validate_order_data(self.sample_order)
                assert result.is_valid
            
            # Force garbage collection
            gc.collect()
            
            if batch % 3 == 0:  # Check periodically
                current_memory = tracemalloc.get_traced_memory()[0]
                memory_growth = (current_memory - baseline_memory) / 1024 / 1024  # MB
                
                # Should not have significant memory growth
                assert memory_growth < 10.0, f"Memory leak detected: {memory_growth:.2f}MB growth"
        
        tracemalloc.stop()
        print("Memory leak test passed - no significant growth detected")


class PerformanceBenchmarks:
    """Performance benchmarking utilities."""
    
    @staticmethod
    def run_benchmark(name: str, func, iterations: int = 1000):
        """Run a performance benchmark."""
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # ms
        
        avg = statistics.mean(latencies)
        median = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]
        p99 = statistics.quantiles(latencies, n=100)[98]
        
        print(f"\n{name} Benchmark ({iterations} iterations):")
        print(f"  Average: {avg:.3f}ms")
        print(f"  Median:  {median:.3f}ms")
        print(f"  P95:     {p95:.3f}ms")
        print(f"  P99:     {p99:.3f}ms")
        
        return {
            "avg": avg,
            "median": median,
            "p95": p95,
            "p99": p99
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])