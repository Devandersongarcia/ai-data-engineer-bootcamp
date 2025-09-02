#!/usr/bin/env python3
"""
🧪 Test Script for Fraud Detection App Components
Tests MindsDB connection and database connectivity
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_mindsdb_connection():
    """Test MindsDB client connection"""
    print("🧠 Testing MindsDB Connection")
    print("-" * 40)
    
    try:
        from mindsdb_interface.mindsdb_client import FraudDetectionMindsDBClient
        
        # Test client initialization
        client = FraudDetectionMindsDBClient()
        print("✅ Client initialized successfully")
        
        # Test connection
        if client.connect_to_agent("agent_fraud_analytics"):
            print("✅ Connected to fraud analytics agent")
            
            # Test a simple query
            response = client.query_agent("What is the current status?")
            print(f"✅ Agent query successful: {response[:100]}...")
            
            return True
        else:
            print("❌ Failed to connect to agent")
            return False
            
    except Exception as e:
        print(f"❌ MindsDB test failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\n🗄️ Testing Database Connection")
    print("-" * 40)
    
    try:
        from mindsdb_interface.fraud_data_service import FraudDataService
        
        # Test service initialization
        service = FraudDataService()
        print("✅ Service initialized successfully")
        
        # Test connection
        if service.connect():
            print("✅ Connected to fraud database")
            
            # Test a simple query
            summary = service.get_fraud_summary_stats()
            if summary:
                print(f"✅ Database query successful: {len(summary)} metrics retrieved")
                print(f"   Sample data: {list(summary.keys())[:5]}")
            else:
                print("⚠️ Database connected but no data found")
            
            service.disconnect()
            return True
        else:
            print("❌ Failed to connect to database")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_imports():
    """Test all required imports"""
    print("\n📦 Testing Required Imports")
    print("-" * 40)
    
    required_modules = [
        'streamlit',
        'pandas', 
        'plotly',
        'psycopg2',
        'requests'
    ]
    
    all_good = True
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - Not installed")
            all_good = False
    
    return all_good

def main():
    """Run all tests"""
    print("🧪 Fraud Detection App Component Tests")
    print("=" * 60)
    
    # Test imports first
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\n💡 Install missing dependencies:")
        print("   pip install -r requirements_streamlit.txt")
        return
    
    # Test connections
    mindsdb_ok = test_mindsdb_connection()
    db_ok = test_database_connection()
    
    print("\n📋 Test Results Summary")
    print("=" * 30)
    print(f"Required Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"MindsDB Connection: {'✅ PASS' if mindsdb_ok else '❌ FAIL'}")
    print(f"Database Connection: {'✅ PASS' if db_ok else '❌ FAIL'}")
    
    if all([imports_ok, mindsdb_ok, db_ok]):
        print("\n🎉 All tests passed! App is ready to run.")
        print("\nTo start the dashboard:")
        print("   python run_fraud_app.py")
    else:
        print("\n⚠️ Some tests failed. Check the issues above.")
        
        if not mindsdb_ok:
            print("\n💡 MindsDB troubleshooting:")
            print("   1. Start MindsDB: python -m mindsdb")
            print("   2. Create agent: Execute SQL setup for 'agent_fraud_analytics'")
        
        if not db_ok:
            print("\n💡 Database troubleshooting:")
            print("   1. Start PostgreSQL service")
            print("   2. Create database: uberats_fraud")
            print("   3. Run schema: database/agentic_fraud_schema.sql")

if __name__ == "__main__":
    main()