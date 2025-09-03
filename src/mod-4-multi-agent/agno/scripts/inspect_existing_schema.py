#!/usr/bin/env python3
"""
Inspect existing database schema structure
"""
import asyncio
import asyncpg
import motor.motor_asyncio
from dotenv import load_dotenv
import os

load_dotenv()

async def inspect_postgresql():
    """Inspect existing PostgreSQL schema"""
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        print("🔍 PostgreSQL Schema Inspection:")
        print("-" * 40)
        
        # Get all tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        for table in tables:
            table_name = table['table_name']
            print(f"\n📋 Table: {table_name}")
            
            # Get column information
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position
            """, table_name)
            
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  • {col['column_name']}: {col['data_type']} {nullable}{default}")
            
            # Get sample data count
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"  📊 Records: {count}")
        
        # Check existing indexes
        indexes = await conn.fetch("""
            SELECT indexname, tablename, indexdef 
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)
        
        if indexes:
            print(f"\n🔍 Existing Indexes:")
            for idx in indexes:
                print(f"  • {idx['indexname']} on {idx['tablename']}")
    
    finally:
        await conn.close()

async def inspect_mongodb():
    """Inspect existing MongoDB collections"""
    mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
    mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db]
    
    try:
        print(f"\n🔍 MongoDB Database: {mongodb_db}")
        print("-" * 40)
        
        collections = await db.list_collection_names()
        
        for collection_name in collections:
            collection = db[collection_name]
            
            # Get document count
            count = await collection.count_documents({})
            print(f"\n📋 Collection: {collection_name}")
            print(f"  📊 Documents: {count}")
            
            # Get sample document structure
            if count > 0:
                sample = await collection.find_one()
                if sample:
                    print(f"  🔍 Sample fields: {list(sample.keys())}")
            
            # Get indexes
            indexes = await collection.index_information()
            if len(indexes) > 1:  # More than just _id_
                print(f"  🔍 Indexes: {list(indexes.keys())}")
    
    finally:
        client.close()

async def main():
    """Main inspection function"""
    print("🔍 Database Schema Inspection")
    print("=" * 50)
    
    await inspect_postgresql()
    await inspect_mongodb()
    
    print("\n" + "=" * 50)
    print("✅ Schema inspection completed")

if __name__ == "__main__":
    asyncio.run(main())