"""
Database connection testing utility
Run this script to test all database connections
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.database_connections import db_connections

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_connections():
    """Test all database connections and show detailed information"""
    
    print("🔍 Testing UberEats Database Connections...")
    print("=" * 50)
    
    try:
        # Initialize connections
        await db_connections.initialize_connections()
        
        # Test connections
        results = await db_connections.test_all_connections()
        
        # Display results
        print("\n📊 Connection Test Results:")
        print("-" * 30)
        
        for db_name, result in results.items():
            status = result["status"]
            if status == "connected":
                print(f"✅ {db_name.upper()}: Connected")
            elif status == "failed":
                print(f"❌ {db_name.upper()}: Failed - {result.get('error', 'Unknown error')}")
            else:
                print(f"⚠️  {db_name.upper()}: Not configured")
        
        # If PostgreSQL is connected, show tables
        if results["postgresql"]["status"] == "connected":
            print(f"\n📋 PostgreSQL Tables:")
            tables = await db_connections.get_postgresql_tables()
            if tables:
                for table in tables:
                    print(f"   • {table}")
            else:
                print("   No tables found")
        
        # If MongoDB is connected, show collections
        if results["mongodb"]["status"] == "connected":
            print(f"\n📋 MongoDB Collections:")
            collections = await db_connections.get_mongodb_collections()
            if collections:
                for collection in collections:
                    print(f"   • {collection}")
            else:
                print("   No collections found")
        
        # Test Qdrant collection setup
        if results["qdrant"]["status"] == "connected":
            print(f"\n🔧 Setting up Qdrant collection...")
            success = await db_connections.setup_qdrant_collection()
            if success:
                print("✅ Qdrant collection setup successful")
            else:
                print("❌ Qdrant collection setup failed")
        
        print(f"\n🎉 Connection test completed!")
        
        # Check if all required connections are working
        required_connections = ["postgresql", "mongodb", "qdrant"]
        all_connected = all(
            results[conn]["status"] == "connected" 
            for conn in required_connections
        )
        
        if all_connected:
            print("🚀 All systems ready for RAG implementation!")
            return True
        else:
            missing = [
                conn for conn in required_connections 
                if results[conn]["status"] != "connected"
            ]
            print(f"⚠️  Missing connections: {', '.join(missing)}")
            return False
            
    except Exception as e:
        print(f"❌ Critical error during connection test: {e}")
        return False
    
    finally:
        db_connections.close_connections()


async def sample_data_exploration():
    """Explore sample data from databases"""
    print("\n🔍 Exploring Sample Data...")
    print("=" * 30)
    
    try:
        await db_connections.initialize_connections()
        
        # Sample PostgreSQL query (if connected)
        if db_connections.pg_engine:
            try:
                # Try to get sample data from any existing tables
                tables = await db_connections.get_postgresql_tables()
                if tables:
                    sample_table = tables[0]
                    print(f"\n📊 Sample data from PostgreSQL table '{sample_table}':")
                    df = await db_connections.execute_sql_query(
                        f"SELECT * FROM {sample_table} LIMIT 5"
                    )
                    if not df.empty:
                        print(df.to_string(index=False))
                    else:
                        print("   Table is empty")
                else:
                    print("   No tables available for sampling")
            except Exception as e:
                print(f"   Error sampling PostgreSQL: {e}")
        
        # Sample MongoDB query (if connected)
        if db_connections.mongo_client:
            try:
                collections = await db_connections.get_mongodb_collections()
                if collections:
                    sample_collection = collections[0]
                    print(f"\n📊 Sample data from MongoDB collection '{sample_collection}':")
                    docs = await db_connections.query_mongodb_collection(
                        sample_collection, limit=3
                    )
                    for i, doc in enumerate(docs, 1):
                        print(f"   Document {i}: {doc}")
                else:
                    print("   No collections available for sampling")
            except Exception as e:
                print(f"   Error sampling MongoDB: {e}")
    
    except Exception as e:
        print(f"❌ Error during data exploration: {e}")
    
    finally:
        db_connections.close_connections()


async def main():
    """Main function to run connection tests"""
    print("🚀 UberEats Multi-Agent RAG System - Connection Test")
    print("=" * 60)
    
    # Test basic connections
    connections_ok = await test_connections()
    
    if connections_ok:
        # Explore sample data
        await sample_data_exploration()
        
        print("\n✨ Ready to implement RAG system!")
        print("Next steps:")
        print("1. Run the data ingestion script")
        print("2. Test agent RAG capabilities")
        print("3. Set up real-time sync")
    else:
        print("\n⚠️  Please fix connection issues before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())