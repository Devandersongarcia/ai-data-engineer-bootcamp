#!/usr/bin/env python3
"""
Full Integration Test Suite
Tests Kafka → Spark → Qdrant → Agents pipeline with real connections
"""

import logging
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.streaming.optimized_fraud_processor import OptimizedFraudProcessor
from src.agents.crewai_qdrant_knowledge import CrewAIQdrantKnowledge
from src.streaming.data_enrichment_service import DataEnrichmentService
from pyspark.sql import SparkSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class FullIntegrationTester:
    """Comprehensive integration testing for the fraud detection pipeline"""
    
    def __init__(self):
        self.spark = None
        self.qdrant_knowledge = None
        self.fraud_processor = None
        self.enrichment_service = None
        
    def setup_components(self):
        """Initialize all pipeline components"""
        try:
            logger.info("🔧 Setting up pipeline components...")
            
            # Initialize Spark
            self.spark = SparkSession.builder \
                .appName("Integration-Test") \
                .config("spark.sql.adaptive.enabled", "true") \
                .getOrCreate()
            
            self.spark.sparkContext.setLogLevel("WARN")
            
            # Initialize Qdrant connection
            self.qdrant_knowledge = CrewAIQdrantKnowledge()
            
            # Initialize fraud processor
            self.fraud_processor = OptimizedFraudProcessor()
            
            # Initialize enrichment service
            self.enrichment_service = DataEnrichmentService(self.spark)
            
            logger.info("✅ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Component setup failed: {e}")
            return False
    
    def test_qdrant_connection(self) -> bool:
        """Test direct Qdrant connection and query capabilities"""
        try:
            logger.info("🔍 Testing Qdrant connection...")
            
            # Test basic connection
            health_result = self.qdrant_knowledge.test_connection()
            if not health_result.get('success'):
                logger.error(f"❌ Qdrant connection failed: {health_result.get('error')}")
                return False
            
            logger.info(f"✅ Qdrant connected: {health_result['collections']} collections")
            
            # Test fraud knowledge search
            test_queries = [
                {
                    "query": "velocity fraud new account high frequency orders",
                    "fraud_types": ["velocity_fraud"],
                    "expected_patterns": ["velocity_fraud"]
                },
                {
                    "query": "amount anomaly large transaction suspicious",
                    "fraud_types": ["amount_anomaly"],
                    "expected_patterns": ["amount_anomaly"]
                },
                {
                    "query": "new account risk suspicious activity",
                    "fraud_types": ["new_account_risk"],
                    "expected_patterns": ["new_account_risk"]
                }
            ]
            
            for i, test_query in enumerate(test_queries, 1):
                logger.info(f"🔍 Test query {i}: {test_query['fraud_types']}")
                
                result = self.qdrant_knowledge.search_fraud_knowledge(
                    query_text=test_query["query"],
                    fraud_types=test_query["fraud_types"],
                    limit=5
                )
                
                if result.get('success') and result.get('knowledge_points'):
                    patterns = result['knowledge_points']
                    logger.info(f"✅ Found {len(patterns)} patterns for {test_query['fraud_types']}")
                    
                    # Check for high fraud scores
                    high_risk_patterns = [p for p in patterns if p.get('fraud_score', 0) >= 0.8]
                    logger.info(f"   High-risk patterns: {len(high_risk_patterns)}")
                    
                    # Log sample pattern
                    if patterns:
                        sample = patterns[0]
                        logger.info(f"   Sample: fraud_score={sample.get('fraud_score', 'N/A')}, "
                                   f"type={sample.get('fraud_type', 'N/A')}")
                else:
                    logger.warning(f"⚠️ No patterns found for {test_query['fraud_types']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Qdrant test failed: {e}")
            return False
    
    def test_fraud_processor_with_real_patterns(self) -> bool:
        """Test fraud processor with realistic fraud scenarios"""
        try:
            logger.info("🔍 Testing fraud processor with real patterns...")
            
            # Test cases matching your Qdrant data structure
            test_cases = [
                {
                    "name": "Velocity Fraud - High Risk",
                    "order_data": {
                        "order_id": "test_velocity_001",
                        "user_id": "new_user_001",
                        "total_amount": 150.0,
                        "account_age_days": 1,
                        "total_orders": 5,
                        "avg_order_value": 30.0,
                        "orders_today": 5,
                        "orders_last_hour": 3
                    },
                    "expected_risk": "HIGH",
                    "expected_patterns": ["velocity_fraud"]
                },
                {
                    "name": "Amount Anomaly - Suspicious",
                    "order_data": {
                        "order_id": "test_amount_002", 
                        "user_id": "regular_user_002",
                        "total_amount": 500.0,
                        "account_age_days": 45,
                        "total_orders": 20,
                        "avg_order_value": 35.0,
                        "orders_today": 1,
                        "orders_last_hour": 1
                    },
                    "expected_risk": "MEDIUM",
                    "expected_patterns": ["amount_anomaly"]
                },
                {
                    "name": "New Account Risk",
                    "order_data": {
                        "order_id": "test_new_003",
                        "user_id": "new_account_003", 
                        "total_amount": 75.0,
                        "account_age_days": 0,
                        "total_orders": 1,
                        "avg_order_value": 75.0,
                        "orders_today": 1,
                        "orders_last_hour": 1
                    },
                    "expected_risk": "MEDIUM",
                    "expected_patterns": ["new_account_risk"]
                },
                {
                    "name": "Legitimate Order",
                    "order_data": {
                        "order_id": "test_legit_004",
                        "user_id": "established_user_004",
                        "total_amount": 42.0,
                        "account_age_days": 180,
                        "total_orders": 50,
                        "avg_order_value": 40.0,
                        "orders_today": 1,
                        "orders_last_hour": 1
                    },
                    "expected_risk": "LOW",
                    "expected_patterns": []
                }
            ]
            
            results = []
            
            for test_case in test_cases:
                logger.info(f"🧪 Testing: {test_case['name']}")
                
                # Run fraud analysis
                fraud_result = self.fraud_processor._analyze_order_optimized(test_case["order_data"])
                
                results.append({
                    "test_name": test_case["name"],
                    "result": fraud_result,
                    "expected_risk": test_case["expected_risk"],
                    "order_data": test_case["order_data"]
                })
                
                # Log detailed results
                logger.info(f"   Order ID: {fraud_result['order_id']}")
                logger.info(f"   Fraud Score: {fraud_result['fraud_score']:.3f}")
                logger.info(f"   Action: {fraud_result['recommended_action']}")
                logger.info(f"   Patterns: {fraud_result.get('matched_fraud_types', [])}")
                logger.info(f"   Similar Patterns: {fraud_result['similar_patterns_found']}")
                logger.info(f"   Processing Time: {fraud_result['processing_time_ms']}ms")
                
                # Validate results
                if fraud_result['fraud_score'] >= 0.7 and test_case['expected_risk'] == "HIGH":
                    logger.info("   ✅ High risk correctly detected")
                elif fraud_result['fraud_score'] >= 0.4 and test_case['expected_risk'] == "MEDIUM":
                    logger.info("   ✅ Medium risk correctly detected")
                elif fraud_result['fraud_score'] < 0.4 and test_case['expected_risk'] == "LOW":
                    logger.info("   ✅ Low risk correctly detected")
                else:
                    logger.warning(f"   ⚠️ Risk level mismatch: got {fraud_result['fraud_score']:.3f}, expected {test_case['expected_risk']}")
                
                logger.info("")
            
            # Summary
            logger.info("📊 Fraud Detection Test Summary:")
            logger.info(f"   Tests run: {len(results)}")
            
            high_risk_detected = sum(1 for r in results if r['result']['fraud_score'] >= 0.7)
            medium_risk_detected = sum(1 for r in results if 0.4 <= r['result']['fraud_score'] < 0.7)
            low_risk_detected = sum(1 for r in results if r['result']['fraud_score'] < 0.4)
            
            logger.info(f"   High risk detected: {high_risk_detected}")
            logger.info(f"   Medium risk detected: {medium_risk_detected}")  
            logger.info(f"   Low risk detected: {low_risk_detected}")
            
            avg_processing_time = sum(r['result']['processing_time_ms'] for r in results) / len(results)
            logger.info(f"   Average processing time: {avg_processing_time:.1f}ms")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Fraud processor test failed: {e}")
            return False
    
    def test_data_enrichment_quality(self) -> bool:
        """Test data enrichment service quality"""
        try:
            logger.info("🔍 Testing data enrichment quality...")
            
            # Create test data
            test_data = [
                {"order_id": "enrich_001", "user_id": "new_test_user", "total_amount": 99.99},
                {"order_id": "enrich_002", "user_id": "regular_user_123", "total_amount": 45.50},
                {"order_id": "enrich_003", "user_id": "test_user_456", "total_amount": 200.00}
            ]
            
            test_df = self.spark.createDataFrame(test_data)
            
            # Enrich the data
            enriched_df = self.enrichment_service.enrich_order_stream(test_df)
            
            # Collect results for analysis
            enriched_data = enriched_df.collect()
            
            logger.info(f"📊 Enrichment Results ({len(enriched_data)} records):")
            
            for row in enriched_data:
                row_dict = row.asDict()
                logger.info(f"   Order: {row_dict['order_id']}")
                logger.info(f"     Account Age: {row_dict.get('account_age_days', 'N/A')} days")
                logger.info(f"     Total Orders: {row_dict.get('total_orders', 'N/A')}")
                logger.info(f"     Orders Today: {row_dict.get('orders_today', 'N/A')}")
                logger.info(f"     Orders Last Hour: {row_dict.get('orders_last_hour', 'N/A')}")
                logger.info(f"     Avg Order Value: ${row_dict.get('avg_order_value', 'N/A')}")
                logger.info(f"     Payment Failures: {row_dict.get('payment_failures_today', 'N/A')}")
                logger.info("")
            
            # Get enrichment statistics
            stats = self.enrichment_service.get_enrichment_stats(enriched_df)
            logger.info(f"📈 Enrichment Statistics:")
            logger.info(f"   Data Quality Score: {stats.get('data_quality_score', 'N/A'):.2f}")
            logger.info(f"   Enrichment Status: {stats.get('enrichment_status', 'N/A')}")
            logger.info(f"   Missing Data: {stats.get('missing_account_age', 0)} records")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Data enrichment test failed: {e}")
            return False
    
    def test_end_to_end_pipeline(self) -> bool:
        """Test complete pipeline with simulated Kafka data"""
        try:
            logger.info("🔍 Testing end-to-end pipeline simulation...")
            
            # Simulate Kafka messages
            kafka_messages = [
                {
                    "order_id": "e2e_001",
                    "user_key": "new_fraud_user",
                    "restaurant_key": "restaurant_123", 
                    "total_amount": 175.0,
                    "payment_key": "credit_card",
                    "item_count": 3
                },
                {
                    "order_id": "e2e_002",
                    "user_key": "regular_customer",
                    "restaurant_key": "restaurant_456",
                    "total_amount": 38.50,
                    "payment_key": "pix",
                    "item_count": 2
                },
                {
                    "order_id": "e2e_003",
                    "user_key": "new_account_test",
                    "restaurant_key": "restaurant_789",
                    "total_amount": 250.0,
                    "payment_key": "credit_card", 
                    "item_count": 5
                }
            ]
            
            # Convert to Spark DataFrame (simulating Kafka parsing)
            kafka_df = self.spark.createDataFrame(kafka_messages)
            
            # Rename columns to match parser expectations
            parsed_df = kafka_df.select(
                col("order_id"),
                col("user_key").alias("user_id"),
                col("restaurant_key").alias("restaurant_id"),
                col("total_amount"),
                col("payment_key").alias("payment_method"),
                col("item_count")
            )
            
            # Apply data enrichment
            enriched_df = self.enrichment_service.enrich_order_stream(parsed_df)
            
            # Process through fraud detection
            enriched_orders = enriched_df.collect()
            
            logger.info("🔄 Processing orders through fraud detection...")
            
            fraud_results = []
            for row in enriched_orders:
                order_dict = row.asDict()
                fraud_result = self.fraud_processor._analyze_order_optimized(order_dict)
                fraud_results.append(fraud_result)
            
            # Analyze results
            logger.info("📊 End-to-End Pipeline Results:")
            
            for result in fraud_results:
                risk_level = "HIGH" if result['fraud_score'] >= 0.7 else "MEDIUM" if result['fraud_score'] >= 0.4 else "LOW"
                
                logger.info(f"   📋 Order: {result['order_id']}")
                logger.info(f"      Risk Level: {risk_level} (score: {result['fraud_score']:.3f})")
                logger.info(f"      Action: {result['recommended_action']}")
                logger.info(f"      Patterns Found: {result['similar_patterns_found']}")
                logger.info(f"      Processing Time: {result['processing_time_ms']}ms")
                logger.info("")
            
            # Pipeline metrics
            total_time = sum(r['processing_time_ms'] for r in fraud_results)
            avg_time = total_time / len(fraud_results)
            fraud_detected = sum(1 for r in fraud_results if r['fraud_score'] >= 0.5)
            
            logger.info(f"🎯 Pipeline Performance Metrics:")
            logger.info(f"   Total Orders Processed: {len(fraud_results)}")
            logger.info(f"   Fraud Cases Detected: {fraud_detected}")
            logger.info(f"   Average Processing Time: {avg_time:.1f}ms")
            logger.info(f"   Total Pipeline Time: {total_time}ms")
            logger.info(f"   Fraud Detection Rate: {(fraud_detected/len(fraud_results)*100):.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ End-to-end pipeline test failed: {e}")
            return False
    
    def test_performance_under_load(self) -> bool:
        """Test performance with larger batch of orders"""
        try:
            logger.info("🔍 Testing performance under load...")
            
            # Generate batch of test orders
            batch_size = 50
            test_orders = []
            
            for i in range(batch_size):
                # Mix of fraud patterns
                if i % 10 == 0:  # Velocity fraud
                    order = {
                        "order_id": f"load_test_{i:03d}",
                        "user_id": f"new_user_{i:03d}",
                        "total_amount": 120.0 + (i * 10),
                        "account_age_days": 1,
                        "total_orders": 5 + i % 3,
                        "avg_order_value": 25.0,
                        "orders_today": 5,
                        "orders_last_hour": 2
                    }
                elif i % 15 == 0:  # Amount anomaly
                    order = {
                        "order_id": f"load_test_{i:03d}",
                        "user_id": f"regular_user_{i:03d}",
                        "total_amount": 400.0 + (i * 20),
                        "account_age_days": 60,
                        "total_orders": 25,
                        "avg_order_value": 40.0,
                        "orders_today": 1,
                        "orders_last_hour": 1
                    }
                else:  # Normal orders
                    order = {
                        "order_id": f"load_test_{i:03d}",
                        "user_id": f"customer_{i:03d}",
                        "total_amount": 25.0 + (i % 50),
                        "account_age_days": 30 + (i % 100),
                        "total_orders": 10 + (i % 20),
                        "avg_order_value": 35.0,
                        "orders_today": 1,
                        "orders_last_hour": 1
                    }
                
                test_orders.append(order)
            
            # Process batch
            logger.info(f"⚡ Processing batch of {batch_size} orders...")
            start_time = time.time()
            
            results = []
            for order in test_orders:
                result = self.fraud_processor._analyze_order_optimized(order)
                results.append(result)
            
            total_time = time.time() - start_time
            
            # Analyze performance
            processing_times = [r['processing_time_ms'] for r in results]
            fraud_detected = sum(1 for r in results if r['fraud_score'] >= 0.5)
            high_risk = sum(1 for r in results if r['fraud_score'] >= 0.7)
            
            logger.info(f"⚡ Load Test Results:")
            logger.info(f"   Orders Processed: {len(results)}")
            logger.info(f"   Total Time: {total_time:.2f}s")
            logger.info(f"   Avg Time per Order: {(total_time*1000)/len(results):.1f}ms")
            logger.info(f"   Min Processing Time: {min(processing_times)}ms")
            logger.info(f"   Max Processing Time: {max(processing_times)}ms")
            logger.info(f"   Fraud Cases: {fraud_detected} ({(fraud_detected/len(results)*100):.1f}%)")
            logger.info(f"   High Risk Cases: {high_risk} ({(high_risk/len(results)*100):.1f}%)")
            logger.info(f"   Throughput: {len(results)/total_time:.1f} orders/second")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if self.spark:
            self.spark.stop()
        logger.info("🧹 Cleanup completed")

def main():
    """Run full integration test suite"""
    logger.info("🚀 Starting Full Integration Test Suite")
    logger.info("=" * 60)
    
    tester = FullIntegrationTester()
    
    # Test suite
    tests = [
        ("Component Setup", tester.setup_components),
        ("Qdrant Connection", tester.test_qdrant_connection),
        ("Fraud Processor with Real Patterns", tester.test_fraud_processor_with_real_patterns),
        ("Data Enrichment Quality", tester.test_data_enrichment_quality),
        ("End-to-End Pipeline", tester.test_end_to_end_pipeline),
        ("Performance Under Load", tester.test_performance_under_load)
    ]
    
    passed = 0
    failed = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            if test_func():
                logger.info(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name}: FAILED")
                failed.append(test_name)
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            failed.append(test_name)
    
    # Final results
    logger.info("\n" + "=" * 60)
    logger.info("📊 INTEGRATION TEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"✅ Tests Passed: {passed}/{len(tests)}")
    
    if failed:
        logger.error(f"❌ Tests Failed: {len(failed)}")
        for test_name in failed:
            logger.error(f"   - {test_name}")
    else:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("Your Kafka → Spark → Qdrant → Fraud Detection pipeline is working correctly!")
    
    # Cleanup
    tester.cleanup()
    
    return len(failed) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)