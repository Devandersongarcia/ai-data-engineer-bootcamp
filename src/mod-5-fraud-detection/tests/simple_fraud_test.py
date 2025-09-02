#!/usr/bin/env python3
"""
Minimal fraud detection test for PostgreSQL output
Run this from the project root directory
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Set up environment
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))
os.environ['PYTHONPATH'] = str(project_root)

def test_database_connection():
    """Test PostgreSQL connection"""
    print("🔍 Testing PostgreSQL connection...")
    
    try:
        from src.database.postgres_handler import postgres_handler
        
        # Initialize connection
        success = postgres_handler.initialize_connection_pool()
        if not success:
            print("❌ Failed to initialize PostgreSQL connection pool")
            print("   Make sure PostgreSQL is running and credentials are correct in .env")
            return False
        
        # Test connection
        success = postgres_handler.test_connection()
        if not success:
            print("❌ PostgreSQL connection test failed")
            return False
            
        print("✅ PostgreSQL connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def create_sample_fraud_result():
    """Create a sample fraud result for testing"""
    try:
        from src.models.fraud_result import FraudResult, FraudDecision, FraudPatternType, FraudSeverity
        
        # Create sample fraud result
        fraud_result = FraudResult(
            order_id="test_001",
            user_id="test_user_123",
            fraud_score=0.85,
            recommended_action=FraudDecision.BLOCK,
            action_confidence=0.92,
            reasoning="High fraud score detected with suspicious velocity patterns",
            processing_time_ms=245,
            total_processing_time_ms=245,
            timestamp=datetime.now(),
            openai_tokens_used=50,
            estimated_cost_usd=0.005
        )
        
        # Add a pattern
        fraud_result.add_pattern(
            FraudPatternType.VELOCITY_FRAUD,
            0.85,
            ["multiple_orders_same_minute", "new_user_high_value"],
            FraudSeverity.HIGH
        )
        
        # Add agent analysis
        fraud_result.add_agent_analysis(
            agent_name="test_fraud_agent",
            analysis_type="pattern_analysis",
            result={"pattern_detected": True, "confidence": 0.85},
            confidence=0.85,
            processing_time_ms=245
        )
        
        return fraud_result
        
    except Exception as e:
        print(f"❌ Error creating sample fraud result: {e}")
        return None

def test_database_write():
    """Test writing to PostgreSQL database"""
    print("🔍 Testing database write operations...")
    
    try:
        from src.database.postgres_handler import postgres_handler
        
        # Create sample data
        fraud_result = create_sample_fraud_result()
        if not fraud_result:
            return False
        
        # Write to database
        success = postgres_handler.insert_fraud_result(fraud_result)
        if not success:
            print("❌ Failed to write fraud result to database")
            return False
            
        print("✅ Successfully wrote fraud result to PostgreSQL!")
        print(f"   Order ID: {fraud_result.order_id}")
        print(f"   Fraud Score: {fraud_result.fraud_score}")
        print(f"   Action: {fraud_result.recommended_action}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database write error: {e}")
        return False

def test_database_query():
    """Test querying from PostgreSQL database"""
    print("🔍 Testing database query operations...")
    
    try:
        from src.database.postgres_handler import postgres_handler
        
        # Get daily stats
        stats = postgres_handler.get_daily_stats()
        if stats:
            print("✅ Successfully queried daily statistics!")
            print(f"   Total Orders: {stats.get('total_orders', 0)}")
            print(f"   Average Fraud Score: {stats.get('avg_fraud_score', 0):.3f}")
        else:
            print("ℹ️  No daily statistics found (database might be empty)")
        
        # Get high-risk orders
        high_risk = postgres_handler.get_high_risk_orders(5)
        if high_risk:
            print(f"✅ Found {len(high_risk)} high-risk orders")
            for order in high_risk[:2]:  # Show first 2
                print(f"   - {order.get('order_id')}: {order.get('fraud_score'):.3f}")
        else:
            print("ℹ️  No high-risk orders found")
            
        return True
        
    except Exception as e:
        print(f"❌ Database query error: {e}")
        return False

def main():
    """Run fraud detection test"""
    print("🚀 UberEats Fraud Detection - PostgreSQL Test")
    print("=" * 50)
    
    # Basic logging setup
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    success_count = 0
    
    # Test 1: Database connection
    if test_database_connection():
        success_count += 1
    
    # Test 2: Database write
    if test_database_write():
        success_count += 1
        
    # Test 3: Database query  
    if test_database_query():
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {success_count}/3 tests passed")
    
    if success_count == 3:
        print("✅ All tests passed! PostgreSQL integration is working.")
        print("\n🚀 Next steps:")
        print("   1. Add your OpenAI API key to .env file")
        print("   2. Run: python scripts/query_fraud_results.py --daily")
        print("   3. Try the full streaming test: python run_fraud_detection_test.py")
        return 0
    else:
        print("❌ Some tests failed. Check your configuration:")
        print("   - PostgreSQL connection string in .env")
        print("   - Database server is running")
        print("   - Run: python scripts/setup_database.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())