#!/usr/bin/env python3
"""
Test Database Insertion
Verify that data is properly inserted into PostgreSQL tables
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connection"""
    logger.info("🔍 Testing database connection...")
    
    try:
        from src.database.unified_postgres_writer import unified_postgres_writer
        
        # Test connection
        if unified_postgres_writer.test_connection():
            logger.info("✅ Database connection successful")
            logger.info(f"📋 Detected schema type: {unified_postgres_writer.schema_type}")
            return True
        else:
            logger.error("❌ Database connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False

def test_fraud_detection_insertion():
    """Test fraud detection result insertion"""
    logger.info("🧪 Testing fraud detection result insertion...")
    
    try:
        from src.database.unified_postgres_writer import unified_postgres_writer
        from pyspark.sql import SparkSession
        from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, BooleanType, TimestampType, ArrayType
        
        # Create minimal Spark session for testing
        spark = SparkSession.builder \
            .appName("DatabaseTestApp") \
            .config("spark.master", "local[1]") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("ERROR")  # Reduce Spark logging
        
        # Create test data schema
        test_schema = StructType([
            StructField("order_id", StringType(), False),
            StructField("user_id", StringType(), True),
            StructField("total_amount", DoubleType(), True),
            StructField("payment_method", StringType(), True),
            StructField("account_age_days", IntegerType(), True),
            StructField("total_orders", IntegerType(), True),
            StructField("avg_order_value", DoubleType(), True),
            StructField("fraud_score", DoubleType(), False),
            StructField("fraud_prediction", StringType(), False),
            StructField("confidence", DoubleType(), True),
            StructField("fraud_reasons", ArrayType(StringType()), True),
            StructField("velocity_risk", DoubleType(), True),
            StructField("amount_risk", DoubleType(), True),
            StructField("account_risk", DoubleType(), True),
            StructField("payment_risk", DoubleType(), True),
            StructField("triage_decision", StringType(), False),
            StructField("priority_level", StringType(), True),
            StructField("requires_agent_analysis", BooleanType(), True),
            StructField("processing_timestamp", TimestampType(), True),
            StructField("detection_timestamp", TimestampType(), True),
            StructField("routing_timestamp", TimestampType(), True)
        ])
        
        # Create test data
        test_data = [
            (
                f"test_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
                "test_user_001",
                125.50,
                "credit_card",
                45,
                12,
                87.30,
                0.75,
                "HIGH_RISK",
                0.85,
                ["velocity_fraud", "amount_anomaly"],
                0.8,
                0.7,
                0.3,
                0.6,
                "AGENT_ANALYSIS",
                "HIGH",
                True,
                datetime.now(),
                datetime.now(),
                datetime.now()
            ),
            (
                f"test_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_002",
                "test_user_002",
                35.20,
                "debit_card",
                180,
                25,
                42.15,
                0.25,
                "LOW_RISK",
                0.90,
                [],
                0.1,
                0.2,
                0.1,
                0.3,
                "AUTO_ALLOW",
                "LOW",
                False,
                datetime.now(),
                datetime.now(),
                datetime.now()
            )
        ]
        
        # Create DataFrame
        df = spark.createDataFrame(test_data, test_schema)
        
        logger.info(f"📊 Created test DataFrame with {df.count()} records")
        df.show(truncate=False)
        
        # Test batch insertion
        unified_postgres_writer.write_fraud_detection_batch(df, 999)
        
        logger.info("✅ Fraud detection insertion test completed")
        
        spark.stop()
        return True
        
    except Exception as e:
        logger.error(f"❌ Fraud detection insertion test failed: {e}")
        return False

def test_agent_analysis_insertion():
    """Test agent analysis insertion"""
    logger.info("🤖 Testing agent analysis insertion...")
    
    try:
        from src.database.unified_postgres_writer import unified_postgres_writer
        
        # Use an order_id that should exist from the previous test
        test_order_id = f"test_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001"
        
        # First, let's check if we have any fraud detection records to link to
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(unified_postgres_writer.connection_string)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get any existing order_id from fraud_detection_results
        cursor.execute("SELECT order_id FROM fraud_detection_results ORDER BY created_at DESC LIMIT 1")
        existing_order = cursor.fetchone()
        
        if existing_order:
            test_order_id = existing_order['order_id']
            logger.info(f"🔗 Using existing order_id: {test_order_id}")
        else:
            logger.warning("⚠️ No existing fraud detection records found")
            cursor.close()
            conn.close()
            return False
        
        cursor.close()
        conn.close()
        
        test_agent_result = {
            "fraud_score": 0.82,
            "recommended_action": "BLOCK", 
            "confidence": 0.91,
            "patterns_detected": ["velocity_fraud", "card_testing"],
            "reasoning": "Multiple rapid transactions detected with new payment method",
            "processing_time_ms": 1250,
            "framework": "crewai_test",
            "success": True
        }
        
        # Test single insertion
        success = unified_postgres_writer.write_agent_analysis_result(test_order_id, test_agent_result)
        
        if success:
            logger.info("✅ Agent analysis insertion test completed")
        else:
            logger.warning("⚠️ Agent analysis insertion returned False")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Agent analysis insertion test failed: {e}")
        return False

def test_database_stats():
    """Test database statistics retrieval"""
    logger.info("📈 Testing database statistics...")
    
    try:
        from src.database.unified_postgres_writer import unified_postgres_writer
        
        stats = unified_postgres_writer.get_fraud_detection_stats()
        
        logger.info("📊 Database Statistics:")
        logger.info(f"   Schema Type: {stats.get('schema_type')}")
        logger.info(f"   Timestamp: {stats.get('timestamp')}")
        
        if stats.get('daily_summary'):
            logger.info(f"   Daily Summary: {stats['daily_summary']}")
        
        if stats.get('agent_performance'):
            logger.info(f"   Agent Performance: {stats['agent_performance']}")
        
        if stats.get('high_risk_alerts'):
            logger.info(f"   High Risk Alerts: {stats['high_risk_alerts']}")
        
        logger.info("✅ Database statistics test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database statistics test failed: {e}")
        return False

def main():
    """Run all database tests"""
    logger.info("🚀 Starting Database Insertion Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Fraud Detection Insertion", test_fraud_detection_insertion), 
        ("Agent Analysis Insertion", test_agent_analysis_insertion),
        ("Database Statistics", test_database_stats)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🏁 TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"   {test_name}: {status}")
    
    logger.info(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Database insertion is working correctly.")
    else:
        logger.warning("⚠️ Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)