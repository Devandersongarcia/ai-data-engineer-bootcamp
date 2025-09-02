#!/usr/bin/env python3
"""
Kafka + Qdrant Real Integration Test
Tests actual Kafka consumption and Qdrant queries with your real infrastructure
"""

import logging
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from kafka import KafkaConsumer
from src.agents.crewai_qdrant_knowledge import CrewAIQdrantKnowledge
from src.streaming.optimized_fraud_processor import OptimizedFraudProcessor
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class KafkaQdrantIntegrationTest:
    """Test real Kafka and Qdrant integration"""
    
    def __init__(self):
        self.qdrant_knowledge = None
        self.fraud_processor = None
        self.kafka_consumer = None
    
    def test_qdrant_real_connection(self) -> bool:
        """Test actual Qdrant cloud connection with your credentials"""
        try:
            logger.info("🔍 Testing real Qdrant connection...")
            
            # Initialize with your real credentials
            self.qdrant_knowledge = CrewAIQdrantKnowledge()
            
            # Test connection health
            health = self.qdrant_knowledge.test_connection()
            if not health.get('success'):
                logger.error(f"❌ Qdrant connection failed: {health}")
                return False
            
            logger.info(f"✅ Qdrant connected successfully!")
            logger.info(f"   URL: {health.get('url', 'N/A')}")
            logger.info(f"   Collections: {health.get('collections', [])}")
            
            # Test your specific fraud collection
            if 'rag_fraud_analysis' in health.get('collections', []):
                logger.info("✅ Found 'rag_fraud_analysis' collection")
                
                # Test specific fraud pattern queries matching your data structure
                test_queries = [
                    "velocity_fraud",
                    "amount_anomaly", 
                    "new_account_risk",
                    "card_testing",
                    "account_takeover"
                ]
                
                for fraud_type in test_queries:
                    result = self.qdrant_knowledge.search_fraud_knowledge(
                        query_text=f"fraud detection {fraud_type} pattern analysis",
                        fraud_types=[fraud_type],
                        limit=3
                    )
                    
                    if result.get('success') and result.get('knowledge_points'):
                        patterns = result['knowledge_points']
                        high_score_patterns = [p for p in patterns if p.get('fraud_score', 0) >= 0.8]
                        
                        logger.info(f"   📊 {fraud_type}: {len(patterns)} patterns, "
                                   f"{len(high_score_patterns)} high-risk (≥0.8)")
                        
                        # Log highest scoring pattern
                        if patterns:
                            top_pattern = max(patterns, key=lambda x: x.get('fraud_score', 0))
                            logger.info(f"      Top score: {top_pattern.get('fraud_score', 'N/A')} - "
                                       f"{top_pattern.get('fraud_type', 'N/A')}")
                    else:
                        logger.warning(f"   ⚠️ No patterns found for {fraud_type}")
                
            else:
                logger.error("❌ 'rag_fraud_analysis' collection not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Qdrant real connection test failed: {e}")
            return False
    
    def test_kafka_real_connection(self) -> bool:
        """Test actual Kafka connection and message consumption"""
        try:
            logger.info("🔍 Testing real Kafka connection...")
            
            # Configure Kafka consumer with your actual settings
            kafka_config = {
                'bootstrap_servers': settings.kafka.bootstrap_servers,
                'security_protocol': settings.kafka.security_protocol,
                'sasl_mechanism': settings.kafka.sasl_mechanism,
                'sasl_plain_username': settings.kafka.sasl_username,
                'sasl_plain_password': settings.kafka.sasl_password,
                'auto_offset_reset': 'latest',
                'enable_auto_commit': False,
                'group_id': 'fraud_test_consumer',
                'value_deserializer': lambda x: json.loads(x.decode('utf-8')) if x else None
            }
            
            logger.info(f"📡 Connecting to Kafka: {kafka_config['bootstrap_servers']}")
            
            self.kafka_consumer = KafkaConsumer('kafka-orders', **kafka_config)
            
            logger.info("✅ Kafka consumer created successfully")
            logger.info("⏳ Waiting for messages (timeout: 30 seconds)...")
            
            # Poll for messages with timeout
            messages_received = 0
            start_time = time.time()
            timeout = 30  # seconds
            
            while time.time() - start_time < timeout and messages_received < 5:
                message_batch = self.kafka_consumer.poll(timeout_ms=5000)
                
                if message_batch:
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            messages_received += 1
                            logger.info(f"📨 Message {messages_received} received:")
                            logger.info(f"   Topic: {message.topic}")
                            logger.info(f"   Partition: {message.partition}")
                            logger.info(f"   Offset: {message.offset}")
                            
                            # Parse message
                            order_data = message.value
                            if order_data:
                                logger.info(f"   Order ID: {order_data.get('order_id', 'N/A')}")
                                logger.info(f"   User: {order_data.get('user_key', 'N/A')}")
                                logger.info(f"   Amount: ${order_data.get('total_amount', 'N/A')}")
                                logger.info(f"   Payment: {order_data.get('payment_key', 'N/A')}")
                                
                                # Test fraud processing on real message
                                self._test_fraud_processing_on_message(order_data)
                            else:
                                logger.warning("   ⚠️ Empty message received")
                            
                            logger.info("")
                            
                            if messages_received >= 5:
                                break
                else:
                    logger.info("⏳ No messages in current poll, waiting...")
                    time.sleep(2)
            
            if messages_received == 0:
                logger.warning("⚠️ No messages received from Kafka in 30 seconds")
                logger.info("💡 Make sure your data generator is running:")
                logger.info("   python -m data_generator.kafka_fraud_orders")
                return False
            else:
                logger.info(f"✅ Kafka integration successful! Processed {messages_received} messages")
                return True
                
        except Exception as e:
            logger.error(f"❌ Kafka real connection test failed: {e}")
            logger.info("💡 Check your Kafka credentials and connection settings")
            return False
        finally:
            if self.kafka_consumer:
                self.kafka_consumer.close()
    
    def _test_fraud_processing_on_message(self, kafka_message: Dict[str, Any]):
        """Test fraud processing on actual Kafka message"""
        try:
            # Transform Kafka message to fraud processor format
            order_data = {
                "order_id": kafka_message.get("order_id", "kafka_test"),
                "user_id": kafka_message.get("user_key", "unknown"),
                "total_amount": float(kafka_message.get("total_amount", 0.0)),
                "payment_method": kafka_message.get("payment_key", "unknown"),
                "account_age_days": 30,  # Would be enriched with real data
                "total_orders": 5,       # Would be enriched with real data
                "avg_order_value": 35.0  # Would be enriched with real data
            }
            
            if not self.fraud_processor:
                self.fraud_processor = OptimizedFraudProcessor()
            
            # Process through fraud detection
            fraud_result = self.fraud_processor._analyze_order_optimized(order_data)
            
            logger.info("   🔍 Fraud Analysis Results:")
            logger.info(f"      Fraud Score: {fraud_result['fraud_score']:.3f}")
            logger.info(f"      Recommended Action: {fraud_result['recommended_action']}")
            logger.info(f"      Similar Patterns: {fraud_result['similar_patterns_found']}")
            logger.info(f"      Processing Time: {fraud_result['processing_time_ms']}ms")
            
            if fraud_result.get('matched_fraud_types'):
                logger.info(f"      Matched Fraud Types: {fraud_result['matched_fraud_types']}")
            
        except Exception as e:
            logger.error(f"   ❌ Fraud processing failed: {e}")
    
    def test_qdrant_fraud_pattern_accuracy(self) -> bool:
        """Test Qdrant pattern matching accuracy with known fraud scenarios"""
        try:
            logger.info("🔍 Testing Qdrant fraud pattern accuracy...")
            
            if not self.qdrant_knowledge:
                self.qdrant_knowledge = CrewAIQdrantKnowledge()
            
            # Test scenarios based on your Qdrant data structure
            test_scenarios = [
                {
                    "name": "High Velocity Pattern",
                    "query": "new account multiple orders short time high frequency velocity",
                    "fraud_types": ["velocity_fraud"],
                    "expected_min_score": 0.8,
                    "description": "Should match your velocity_fraud patterns with high scores"
                },
                {
                    "name": "Amount Anomaly Pattern", 
                    "query": "large transaction amount unusual customer spending pattern",
                    "fraud_types": ["amount_anomaly"],
                    "expected_min_score": 0.7,
                    "description": "Should match amount anomaly patterns"
                },
                {
                    "name": "New Account Risk Pattern",
                    "query": "brand new account first transaction suspicious timing",
                    "fraud_types": ["new_account_risk"],
                    "expected_min_score": 0.6,
                    "description": "Should match new account risk patterns"
                },
                {
                    "name": "Card Testing Pattern",
                    "query": "multiple small transactions testing card validation",
                    "fraud_types": ["card_testing"],
                    "expected_min_score": 0.7,
                    "description": "Should match card testing patterns"
                }
            ]
            
            accuracy_results = []
            
            for scenario in test_scenarios:
                logger.info(f"🧪 Testing: {scenario['name']}")
                
                result = self.qdrant_knowledge.search_fraud_knowledge(
                    query_text=scenario["query"],
                    fraud_types=scenario["fraud_types"],
                    limit=5
                )
                
                if result.get('success') and result.get('knowledge_points'):
                    patterns = result['knowledge_points']
                    max_score = max(p.get('fraud_score', 0) for p in patterns)
                    avg_score = sum(p.get('fraud_score', 0) for p in patterns) / len(patterns)
                    
                    logger.info(f"   📊 Found {len(patterns)} patterns")
                    logger.info(f"   🎯 Max fraud score: {max_score:.3f}")
                    logger.info(f"   📈 Avg fraud score: {avg_score:.3f}")
                    logger.info(f"   🎪 Expected min: {scenario['expected_min_score']:.3f}")
                    
                    # Check accuracy
                    meets_expectation = max_score >= scenario['expected_min_score']
                    accuracy_results.append(meets_expectation)
                    
                    if meets_expectation:
                        logger.info("   ✅ Pattern accuracy test PASSED")
                    else:
                        logger.warning("   ⚠️ Pattern accuracy test FAILED")
                    
                    # Show top pattern details
                    top_pattern = max(patterns, key=lambda x: x.get('fraud_score', 0))
                    logger.info(f"   🏆 Top pattern: {top_pattern.get('fraud_type', 'N/A')} "
                               f"(score: {top_pattern.get('fraud_score', 'N/A')})")
                    
                else:
                    logger.error(f"   ❌ No patterns found for {scenario['name']}")
                    accuracy_results.append(False)
                
                logger.info("")
            
            # Calculate overall accuracy
            passed_tests = sum(accuracy_results)
            total_tests = len(accuracy_results)
            accuracy_percentage = (passed_tests / total_tests) * 100
            
            logger.info("📊 Pattern Accuracy Summary:")
            logger.info(f"   Tests passed: {passed_tests}/{total_tests}")
            logger.info(f"   Accuracy: {accuracy_percentage:.1f}%")
            
            if accuracy_percentage >= 75:
                logger.info("✅ Qdrant pattern accuracy test PASSED")
                return True
            else:
                logger.error("❌ Qdrant pattern accuracy test FAILED")
                return False
                
        except Exception as e:
            logger.error(f"❌ Qdrant pattern accuracy test failed: {e}")
            return False
    
    def test_real_time_performance(self) -> bool:
        """Test real-time performance with Qdrant queries"""
        try:
            logger.info("🔍 Testing real-time performance with Qdrant...")
            
            if not self.fraud_processor:
                self.fraud_processor = OptimizedFraudProcessor()
            
            # Simulate high-frequency order processing
            test_orders = []
            for i in range(20):
                order = {
                    "order_id": f"perf_test_{i:03d}",
                    "user_id": f"user_{i % 10}",  # Simulate returning customers
                    "total_amount": 50.0 + (i * 15),
                    "account_age_days": max(1, i // 4),
                    "total_orders": 1 + (i // 3),
                    "avg_order_value": 40.0
                }
                test_orders.append(order)
            
            logger.info(f"⚡ Processing {len(test_orders)} orders for performance test...")
            
            start_time = time.time()
            results = []
            
            for order in test_orders:
                result = self.fraud_processor._analyze_order_optimized(order)
                results.append(result)
            
            total_time = time.time() - start_time
            
            # Analyze performance metrics
            processing_times = [r['processing_time_ms'] for r in results]
            qdrant_queries = sum(1 for r in results if r['similar_patterns_found'] > 0)
            fraud_detected = sum(1 for r in results if r['fraud_score'] >= 0.5)
            
            logger.info("⚡ Performance Test Results:")
            logger.info(f"   Orders processed: {len(results)}")
            logger.info(f"   Total time: {total_time:.2f}s")
            logger.info(f"   Avg time per order: {(total_time * 1000) / len(results):.1f}ms")
            logger.info(f"   Min processing time: {min(processing_times)}ms")
            logger.info(f"   Max processing time: {max(processing_times)}ms")
            logger.info(f"   Orders with Qdrant matches: {qdrant_queries}")
            logger.info(f"   Fraud cases detected: {fraud_detected}")
            logger.info(f"   Throughput: {len(results) / total_time:.1f} orders/second")
            
            # Performance validation
            avg_time_ms = (total_time * 1000) / len(results)
            if avg_time_ms < 1000:  # Less than 1 second per order
                logger.info("✅ Real-time performance test PASSED")
                return True
            else:
                logger.warning(f"⚠️ Performance may be too slow for real-time: {avg_time_ms:.1f}ms/order")
                return False
                
        except Exception as e:
            logger.error(f"❌ Real-time performance test failed: {e}")
            return False

def main():
    """Run Kafka + Qdrant integration tests"""
    logger.info("🚀 Kafka + Qdrant Real Integration Tests")
    logger.info("=" * 60)
    
    tester = KafkaQdrantIntegrationTest()
    
    tests = [
        ("Real Qdrant Connection", tester.test_qdrant_real_connection),
        ("Qdrant Fraud Pattern Accuracy", tester.test_qdrant_fraud_pattern_accuracy),
        ("Real-Time Performance", tester.test_real_time_performance),
        ("Real Kafka Connection", tester.test_kafka_real_connection),
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
    
    # Results
    logger.info("\n" + "=" * 60)
    logger.info("📊 KAFKA + QDRANT INTEGRATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"✅ Tests Passed: {passed}/{len(tests)}")
    
    if failed:
        logger.error(f"❌ Tests Failed: {len(failed)}")
        for test_name in failed:
            logger.error(f"   - {test_name}")
        
        logger.info("\n💡 Troubleshooting Tips:")
        if "Real Qdrant Connection" in failed:
            logger.info("   - Check QDRANT_URL and QDRANT_API_KEY in .env")
            logger.info("   - Verify Qdrant cloud instance is running")
        if "Real Kafka Connection" in failed:
            logger.info("   - Start your Kafka data generator:")
            logger.info("     python -m data_generator.kafka_fraud_orders")
            logger.info("   - Check Kafka credentials in settings")
    else:
        logger.info("🎉 ALL INTEGRATION TESTS PASSED!")
        logger.info("Your real Kafka → Qdrant fraud detection is working perfectly!")
    
    return len(failed) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)