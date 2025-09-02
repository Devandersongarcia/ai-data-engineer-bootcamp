#!/usr/bin/env python3
"""
Test RAG System Integration
Verify that the RAG orchestration system is working
"""

import requests
import json
import time
from datetime import datetime

def test_airflow_api():
    """Test Airflow API connectivity"""
    print("🧪 Testing Airflow API connectivity...")
    
    try:
        # Test API health
        response = requests.get("http://localhost:8080/health", timeout=10)
        if response.status_code == 200:
            print("✅ Airflow API is responding")
            return True
        else:
            print(f"❌ Airflow API returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Airflow API at localhost:8080")
        return False
    except Exception as e:
        print(f"❌ Airflow API test failed: {e}")
        return False

def test_rag_components():
    """Test RAG system components"""
    print("🔍 Testing RAG components...")
    
    try:
        # Test Qdrant connection
        from rag.include.rag_system.qdrant_fraud_rag import QdrantFraudRAG
        
        rag = QdrantFraudRAG()
        print("✅ Qdrant RAG system initialized")
        
        # Test knowledge query
        test_query = "What are common credit card fraud patterns?"
        results = rag.query_fraud_patterns(test_query, limit=3)
        
        if results:
            print(f"✅ Knowledge base query successful: Found {len(results)} patterns")
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. {result.get('pattern_name', 'Unknown')}")
        else:
            print("⚠️  Knowledge base query returned no results")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG components test failed: {e}")
        return False

def test_fraud_rag():
    """Test fraud RAG system"""
    print("🧠 Testing fraud RAG system...")
    
    try:
        from rag.include.rag_system.fraud_rag import FraudRAG
        
        rag = FraudRAG()
        print("✅ Fraud RAG system initialized")
        
        # Test fraud analysis
        test_order = {
            "order_id": "test_123",
            "user_id": "user_456", 
            "total_amount": 150.0,
            "payment_method": "credit_card",
            "account_age_days": 2
        }
        
        analysis = rag.analyze_order_with_knowledge(test_order)
        
        if analysis:
            print("✅ Fraud analysis with RAG successful")
            print(f"   Risk Assessment: {analysis.get('risk_level', 'unknown')}")
            print(f"   Confidence: {analysis.get('confidence', 0):.2f}")
        else:
            print("⚠️  Fraud analysis returned no results")
        
        return True
        
    except Exception as e:
        print(f"❌ Fraud RAG test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 UberEats Fraud Detection - RAG System Test")
    print("=" * 60)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Airflow API", test_airflow_api),
        ("RAG Components", test_rag_components),
        ("Fraud RAG", test_fraud_rag)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test ERROR: {e}")
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All RAG system tests passed!")
        print("✅ Phase 3: RAG System Orchestration is ready!")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)