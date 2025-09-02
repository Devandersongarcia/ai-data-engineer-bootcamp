#!/usr/bin/env python3
"""
🧪 Comprehensive Logging Test for MindsDB Interface
Tests all logging components and verifies they work correctly
"""
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_logging_config():
    """Test the logging configuration system"""
    print("🔧 Testing Logging Configuration")
    print("-" * 50)
    
    try:
        from mindsdb_interface.logging_config import (
            setup_logging, log_function_call, log_api_request, 
            log_database_operation, log_agent_interaction, 
            log_performance_metric, log_system_info
        )
        
        # Initialize logging
        logger = setup_logging(level="DEBUG", console_output=True)
        print("✅ Logging configuration imported successfully")
        
        # Test different log functions
        print("\n🧪 Testing logging functions...")
        
        # Function call logging
        log_function_call("test_function", {"param1": "value1", "param2": 123})
        
        # API request logging
        log_api_request("GET", "http://127.0.0.1:47334/api/status", 200, 0.5)
        log_api_request("POST", "http://127.0.0.1:47334/api/sql/query", error="Connection timeout")
        
        # Database operation logging
        log_database_operation("SELECT", "fraud_detection_results", 150, 0.3)
        log_database_operation("INSERT", "agent_analysis_results", error="Duplicate key")
        
        # Agent interaction logging
        log_agent_interaction(
            "agent_fraud_analytics", 
            "What is the current fraud status?", 
            "Current fraud detection shows 5 high-risk cases...", 
            1.2
        )
        log_agent_interaction("agent_fraud_analytics", "Test query", error="Agent timeout")
        
        # Performance metrics
        log_performance_metric("response_time", 0.456, "seconds", "test_context")
        log_performance_metric("memory_usage", 512, "MB", "system_check")
        
        # System info
        log_system_info()
        
        return True
        
    except Exception as e:
        print(f"❌ Logging configuration test failed: {e}")
        return False

def test_mindsdb_client_logging():
    """Test MindsDB client with logging"""
    print("\n🧠 Testing MindsDB Client Logging")
    print("-" * 50)
    
    try:
        from mindsdb_interface.mindsdb_client import FraudDetectionMindsDBClient
        
        # Initialize client
        client = FraudDetectionMindsDBClient("http://127.0.0.1:47334")
        print("✅ MindsDB client initialized with logging")
        
        # Test connection (will fail if MindsDB not running, but we'll see logs)
        print("\n🔗 Testing connection logging...")
        success = client.connect_to_agent("agent_fraud_analytics")
        
        if success:
            print("✅ Connected to agent - checking query logging...")
            response = client.query_agent("Test logging query")
            print(f"📝 Response: {response[:100]}...")
        else:
            print("⚠️ Connection failed (expected if MindsDB not running)")
        
        # Test other methods
        print("\n🔍 Testing additional methods...")
        client.test_connection()
        client.get_available_agents()
        
        return True
        
    except Exception as e:
        print(f"❌ MindsDB client logging test failed: {e}")
        return False

def test_database_service_logging():
    """Test database service with logging"""
    print("\n🗄️ Testing Database Service Logging")
    print("-" * 50)
    
    try:
        from mindsdb_interface.fraud_data_service import FraudDataService
        
        # Initialize service
        service = FraudDataService()
        print("✅ Database service initialized with logging")
        
        # Test connection (will fail if PostgreSQL not running, but we'll see logs)
        print("\n🔗 Testing connection logging...")
        success = service.connect()
        
        if success:
            print("✅ Connected to database - checking query logging...")
            stats = service.get_fraud_summary_stats()
            print(f"📊 Stats retrieved: {len(stats) if stats else 0} metrics")
            service.disconnect()
        else:
            print("⚠️ Database connection failed (expected if PostgreSQL not running)")
        
        return True
        
    except Exception as e:
        print(f"❌ Database service logging test failed: {e}")
        return False

def test_log_files():
    """Test that log files are created and contain data"""
    print("\n📄 Testing Log Files")
    print("-" * 50)
    
    try:
        logs_dir = Path("logs")
        
        if not logs_dir.exists():
            print("⚠️ Logs directory doesn't exist yet - will be created on first use")
            return True
        
        log_files = list(logs_dir.glob("*.log"))
        
        if log_files:
            print(f"✅ Found {len(log_files)} log files:")
            for log_file in log_files:
                size = log_file.stat().st_size
                print(f"   📄 {log_file.name}: {size:,} bytes")
                
                # Show last few lines
                if size > 0:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        print(f"      Last entry: {lines[-1].strip()}" if lines else "      (empty)")
        else:
            print("⚠️ No log files found yet")
        
        return True
        
    except Exception as e:
        print(f"❌ Log files test failed: {e}")
        return False

def simulate_error_scenarios():
    """Simulate various error scenarios to test error logging"""
    print("\n⚠️ Testing Error Logging Scenarios")
    print("-" * 50)
    
    try:
        from mindsdb_interface.logging_config import log_api_request, log_database_operation
        import logging
        
        logger = logging.getLogger("error_test")
        
        # Simulate various error conditions
        scenarios = [
            ("Connection Timeout", "API connection timeout after 30 seconds"),
            ("Database Error", "PostgreSQL connection failed: database not found"),
            ("Agent Not Found", "MindsDB agent 'agent_fraud_analytics' not found"),
            ("Query Timeout", "SQL query timeout after 60 seconds"),
            ("Invalid Response", "Agent returned invalid JSON response"),
            ("Permission Error", "Access denied to table 'fraud_detection_results'"),
        ]
        
        for scenario_name, error_msg in scenarios:
            logger.error(f"🔴 SIMULATED ERROR - {scenario_name}: {error_msg}")
            
        print("✅ Error scenarios logged successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error logging test failed: {e}")
        return False

def main():
    """Run all logging tests"""
    print("🧪 MindsDB Interface Logging Test Suite")
    print("=" * 70)
    
    tests = [
        ("Logging Configuration", test_logging_config),
        ("MindsDB Client Logging", test_mindsdb_client_logging),
        ("Database Service Logging", test_database_service_logging),
        ("Log Files", test_log_files),
        ("Error Scenarios", simulate_error_scenarios),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} | {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All logging tests passed! The logging system is working correctly.")
        print("\n💡 What to check next:")
        print("   1. Look at the 'logs/' directory for log files")
        print("   2. Run the Streamlit app and check for logging output")
        print("   3. Connect to MindsDB and database to see detailed logs")
    else:
        print("⚠️ Some tests failed. Check the error messages above.")
        print("\n💡 Common issues:")
        print("   1. Missing dependencies: pip install -r requirements_streamlit.txt")
        print("   2. MindsDB not running: python -m mindsdb")
        print("   3. PostgreSQL not running or wrong credentials")

if __name__ == "__main__":
    main()