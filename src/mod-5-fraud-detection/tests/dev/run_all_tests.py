#!/usr/bin/env python3
"""
Test Runner - Execute all fraud detection tests
Runs comprehensive test suite to validate your Kafka → Spark → Qdrant → Agents pipeline
"""

import logging
import sys
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def run_test_script(script_path: str, test_name: str) -> bool:
    """Run a test script and return success status"""
    try:
        logger.info(f"🚀 Starting {test_name}...")
        logger.info(f"   Script: {script_path}")
        
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"✅ {test_name}: PASSED")
            return True
        else:
            logger.error(f"❌ {test_name}: FAILED")
            logger.error(f"   Error output: {result.stderr[:500]}...")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {test_name}: TIMEOUT (5 minutes)")
        return False
    except Exception as e:
        logger.error(f"❌ {test_name}: ERROR - {e}")
        return False

def main():
    """Run all test scripts in sequence"""
    logger.info("🧪 FRAUD DETECTION TEST SUITE")
    logger.info("=" * 60)
    logger.info("Running comprehensive tests for your fraud detection pipeline")
    logger.info("This will test: Kafka → Spark → Qdrant → CrewAI Agents")
    logger.info("=" * 60)
    
    # Define test scripts in order of execution
    test_scripts = [
        {
            "script": "test_batch_processor.py",
            "name": "Batch Processor Test",
            "description": "Tests basic batch processing functionality"
        },
        {
            "script": "validate_fraud_detection.py", 
            "name": "Fraud Detection Validation",
            "description": "Validates fraud detection accuracy with known patterns"
        },
        {
            "script": "test_kafka_qdrant_integration.py",
            "name": "Kafka + Qdrant Integration",
            "description": "Tests real Kafka and Qdrant connections"
        },
        {
            "script": "test_full_integration.py",
            "name": "Full Integration Test",
            "description": "End-to-end pipeline testing with performance metrics"
        }
    ]
    
    results = []
    
    for test_config in test_scripts:
        script_path = test_config["script"]
        test_name = test_config["name"]
        description = test_config["description"]
        
        logger.info(f"\n📋 {test_name}")
        logger.info(f"   {description}")
        logger.info("-" * 50)
        
        # Check if script exists
        if not Path(script_path).exists():
            logger.error(f"❌ Test script not found: {script_path}")
            results.append(False)
            continue
        
        # Run the test
        success = run_test_script(script_path, test_name)
        results.append(success)
        
        if success:
            logger.info(f"✅ {test_name} completed successfully")
        else:
            logger.error(f"❌ {test_name} failed")
            logger.info("💡 Check the detailed output above for troubleshooting")
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUITE RESULTS")
    logger.info("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    logger.info(f"Tests passed: {passed}/{total}")
    
    for i, (test_config, success) in enumerate(zip(test_scripts, results)):
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"   {test_config['name']}: {status}")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("Your fraud detection pipeline is working correctly!")
        logger.info("\n🚀 Ready for production deployment:")
        logger.info("   1. Start your Kafka data generator:")
        logger.info("      python -m data_generator.kafka_fraud_orders")
        logger.info("   2. Start the fraud detection pipeline:")
        logger.info("      python -m src.streaming.final_simple_app")
    else:
        failed_count = total - passed
        logger.error(f"\n❌ {failed_count} TESTS FAILED")
        logger.info("\n💡 Troubleshooting guide:")
        
        if not results[0]:  # Batch processor test
            logger.info("   - Check your CrewAI agents setup")
            logger.info("   - Verify prompt management system")
        
        if not results[1]:  # Fraud detection validation
            logger.info("   - Check fraud score calculations")
            logger.info("   - Verify Qdrant pattern matching")
        
        if not results[2]:  # Kafka + Qdrant integration
            logger.info("   - Check Kafka connection settings")
            logger.info("   - Verify Qdrant cloud credentials in .env")
            logger.info("   - Start data generator: python -m data_generator.kafka_fraud_orders")
        
        if not results[3]:  # Full integration
            logger.info("   - Check Spark session configuration")
            logger.info("   - Verify all components are working individually")
        
        logger.info("\n🔧 Common fixes:")
        logger.info("   - Update .env with correct Qdrant credentials")
        logger.info("   - Ensure Kafka data generator is running")
        logger.info("   - Check network connectivity to Qdrant cloud")
        logger.info("   - Verify Java version for Spark (Java 8 or 11)")
    
    logger.info("\n📖 For detailed logs, run individual tests:")
    for test_config in test_scripts:
        logger.info(f"   python {test_config['script']}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)