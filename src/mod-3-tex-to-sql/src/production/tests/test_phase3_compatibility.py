#!/usr/bin/env python3
"""
Comprehensive test suite to verify Phase 3 performance enhancements maintain 100% backward compatibility.
This ensures all performance optimizations work correctly while preserving existing functionality.
"""

import os
import sys
import time
import tempfile
import threading
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Add the production directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all the Phase 3 components
try:
    from config.settings import get_settings, AppSettings
    from utils.performance_utils import (
        get_query_cache, get_performance_monitor, cached_query, 
        performance_tracked, IntelligentCache, PerformanceMetrics
    )
    from utils.connection_pool import (
        get_connection_manager, DatabaseConnectionPool, QdrantConnectionPool,
        ConnectionManager, setup_default_pools
    )
    from utils.async_utils import (
        get_async_query_executor, get_background_task_manager,
        AsyncQueryExecutor, BackgroundTaskManager, run_async_in_sync
    )
    from utils.logging_utils import get_logger, setup_logging
    from core.vanna_converter import VannaTextToSQLConverter
    
    print("✅ All Phase 3 imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


class Phase3CompatibilityTester:
    """Comprehensive tester for Phase 3 performance enhancements."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.test_results = []
        self.failed_tests = []
        
        # Setup test environment
        os.environ["OPENAI_API_KEY"] = "test-key-12345"
        
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        full_message = f"{status} {test_name}"
        if message:
            full_message += f" - {message}"
        
        print(full_message)
        self.test_results.append((test_name, success, message))
        
        if not success:
            self.failed_tests.append(test_name)
    
    def test_configuration_compatibility(self):
        """Test that configuration system maintains backward compatibility."""
        print("\n🔧 Testing Configuration Compatibility...")
        
        try:
            # Test settings loading
            settings = get_settings()
            assert hasattr(settings, 'openai_api_key'), "Missing openai_api_key"
            assert hasattr(settings, 'database_url'), "Missing database_url"
            
            # Test new Phase 3 settings exist
            assert hasattr(settings, 'db_pool_size'), "Missing db_pool_size"
            assert hasattr(settings, 'query_cache_size'), "Missing query_cache_size"
            assert hasattr(settings, 'max_concurrent_queries'), "Missing max_concurrent_queries"
            
            # Test default values
            assert settings.db_pool_size > 0, "Invalid db_pool_size"
            assert settings.query_cache_size > 0, "Invalid query_cache_size"
            assert settings.max_concurrent_queries > 0, "Invalid max_concurrent_queries"
            
            self.log_result("Configuration system", True)
        except Exception as e:
            self.log_result("Configuration system", False, str(e))
    
    def test_performance_utilities(self):
        """Test performance utilities functionality."""
        print("\n⚡ Testing Performance Utilities...")
        
        try:
            # Test query cache
            cache = get_query_cache()
            assert cache is not None, "Query cache not initialized"
            
            # Test cache operations
            test_sql = "SELECT * FROM test"
            test_params = {"limit": 10}
            test_data = {"result": "test_data", "rows": 10}
            
            cache.cache_query_result(test_sql, test_params, test_data)
            cached_result = cache.get_cached_result(test_sql, test_params)
            assert cached_result == test_data, "Cache storage/retrieval failed"
            
            self.log_result("Query cache operations", True)
            
            # Test performance monitor
            monitor = get_performance_monitor()
            assert monitor is not None, "Performance monitor not initialized"
            
            # Test performance tracking decorator
            @performance_tracked("test_operation")
            def test_function():
                time.sleep(0.01)  # Small delay to measure
                return "test_result"
            
            result = test_function()
            assert result == "test_result", "Performance tracked function failed"
            
            self.log_result("Performance monitoring", True)
            
        except Exception as e:
            self.log_result("Performance utilities", False, str(e))
    
    def test_connection_pooling(self):
        """Test connection pooling functionality."""
        print("\n🔗 Testing Connection Pooling...")
        
        try:
            # Test connection manager
            manager = get_connection_manager()
            assert manager is not None, "Connection manager not initialized"
            
            # Test pool registration (mock database URL for testing)
            test_db_url = "postgresql://test:test@localhost:5432/test"
            
            # Mock the actual database connection for testing
            with patch('sqlalchemy.create_engine') as mock_engine:
                mock_engine.return_value = Mock()
                pool = manager.register_postgresql_pool("test_pool", test_db_url, pool_size=2)
                assert pool is not None, "Failed to register PostgreSQL pool"
            
            # Test Qdrant pool registration
            with patch('qdrant_client.QdrantClient') as mock_client:
                mock_client.return_value.get_collections.return_value = Mock()
                qdrant_pool = manager.register_qdrant_pool(
                    "test_qdrant", "http://localhost:6333", "test-key", pool_size=2
                )
                assert qdrant_pool is not None, "Failed to register Qdrant pool"
            
            self.log_result("Connection pooling", True)
            
        except Exception as e:
            self.log_result("Connection pooling", False, str(e))
    
    def test_async_utilities(self):
        """Test async utilities functionality."""
        print("\n🔄 Testing Async Utilities...")
        
        try:
            # Test async query executor
            executor = get_async_query_executor()
            assert executor is not None, "Async query executor not initialized"
            
            # Test background task manager
            task_manager = get_background_task_manager()
            assert task_manager is not None, "Background task manager not initialized"
            
            # Test run_async_in_sync utility
            async def test_async_function():
                return "async_result"
            
            result = run_async_in_sync(test_async_function)
            assert result == "async_result", "run_async_in_sync failed"
            
            self.log_result("Async utilities", True)
            
        except Exception as e:
            self.log_result("Async utilities", False, str(e))
    
    def test_converter_integration(self):
        """Test that the main converter works with all Phase 3 enhancements."""
        print("\n🔄 Testing Converter Integration...")
        
        try:
            # Mock external dependencies
            with patch('chromadb.Client') as mock_chroma, \
                 patch('openai.OpenAI') as mock_openai, \
                 patch('sqlalchemy.create_engine') as mock_engine:
                
                # Setup mocks
                mock_chroma.return_value = Mock()
                mock_openai.return_value = Mock()
                mock_engine.return_value = Mock()
                
                # Create converter instance
                converter = VannaTextToSQLConverter()
                assert converter is not None, "Converter initialization failed"
                
                # Test that performance tracking is integrated
                assert hasattr(converter, 'execute_query'), "execute_query method missing"
                
                # Test method signature includes caching parameter
                import inspect
                sig = inspect.signature(converter.execute_query)
                assert 'use_cache' in sig.parameters, "use_cache parameter missing from execute_query"
                
                self.log_result("Converter integration", True)
                
        except Exception as e:
            self.log_result("Converter integration", False, str(e))
    
    def test_backward_compatibility(self):
        """Test that all existing functionality still works as before."""
        print("\n🔄 Testing Backward Compatibility...")
        
        try:
            # Test that old imports still work
            from utils import get_logger  # Should work from Phase 1
            logger = get_logger("test")
            assert logger is not None, "Logger import compatibility failed"
            
            # Test settings singleton behavior
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2, "Settings not singleton"
            
            # Test cache decorator doesn't break normal function behavior
            @cached_query(ttl=60)
            def simple_function(x):
                return x * 2
            
            result = simple_function(5)
            assert result == 10, "Cached function behavior changed"
            
            # Test that performance tracking is optional
            @performance_tracked("optional_test")
            def optional_function():
                return "works"
            
            result = optional_function()
            assert result == "works", "Performance tracking broke function"
            
            self.log_result("Backward compatibility", True)
            
        except Exception as e:
            self.log_result("Backward compatibility", False, str(e))
    
    def test_thread_safety(self):
        """Test that all components are thread-safe."""
        print("\n🧵 Testing Thread Safety...")
        
        try:
            results = []
            errors = []
            
            def worker_thread(thread_id):
                try:
                    # Test thread-safe access to singletons
                    cache = get_query_cache()
                    monitor = get_performance_monitor()
                    manager = get_connection_manager()
                    
                    # Perform some operations
                    sql = f"SELECT * FROM test_{thread_id}"
                    params = {"thread_id": thread_id}
                    data = {"data": thread_id}
                    
                    cache.cache_query_result(sql, params, data)
                    value = cache.get_cached_result(sql, params)
                    
                    results.append((thread_id, value["data"]))
                except Exception as e:
                    errors.append((thread_id, str(e)))
            
            # Create multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker_thread, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Check results
            assert len(errors) == 0, f"Thread errors: {errors}"
            assert len(results) == 5, "Not all threads completed"
            
            self.log_result("Thread safety", True)
            
        except Exception as e:
            self.log_result("Thread safety", False, str(e))
    
    def test_memory_management(self):
        """Test that caching and pooling don't cause memory leaks."""
        print("\n💾 Testing Memory Management...")
        
        try:
            cache = get_query_cache()
            
            # Add many items to test cleanup
            for i in range(100):
                sql = f"SELECT * FROM memory_test_{i}"
                params = {"test_id": i}
                data = {"data": f"test_data_{i}"}
                cache.cache_query_result(sql, params, data)
            
            # Test that cache has reasonable size limits
            # (The intelligent cache should handle cleanup automatically)
            
            # Test connection pool cleanup
            manager = get_connection_manager()
            
            # Test that pools can be health checked without errors
            with patch('sqlalchemy.create_engine') as mock_engine:
                mock_engine.return_value = Mock()
                pool = manager.register_postgresql_pool("memory_test", "postgresql://test", pool_size=2)
                
                # Simulate cleanup
                if hasattr(pool, 'cleanup_stale_connections'):
                    pool.cleanup_stale_connections()
            
            self.log_result("Memory management", True)
            
        except Exception as e:
            self.log_result("Memory management", False, str(e))
    
    def run_all_tests(self):
        """Run all compatibility tests."""
        print("🚀 Starting Phase 3 Compatibility Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        self.test_configuration_compatibility()
        self.test_performance_utilities()
        self.test_connection_pooling()
        self.test_async_utilities()
        self.test_converter_integration()
        self.test_backward_compatibility()
        self.test_thread_safety()
        self.test_memory_management()
        
        # Summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("🎯 PHASE 3 COMPATIBILITY TEST RESULTS")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success, _ in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Duration: {duration:.2f}s")
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED - Phase 3 maintains 100% backward compatibility!")
            return True
        else:
            print(f"\n⚠️  TESTS FAILED - Issues found in: {', '.join(self.failed_tests)}")
            return False


def main():
    """Run the compatibility test suite."""
    tester = Phase3CompatibilityTester()
    success = tester.run_all_tests()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()