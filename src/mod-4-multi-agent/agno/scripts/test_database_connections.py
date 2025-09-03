#!/usr/bin/env python3
"""
Test database connectivity for UberEats production deployment
"""
import asyncio
import os
import sys
from typing import Dict, Any
from urllib.parse import unquote_plus

import asyncpg
import motor.motor_asyncio
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_postgresql_connection() -> Dict[str, Any]:
    """Test PostgreSQL connection using asyncpg"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return {
                'status': 'error',
                'message': 'DATABASE_URL not found in environment variables'
            }
        
        print(f"🔍 Connecting to PostgreSQL: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
        
        # Connect to PostgreSQL
        conn = await asyncpg.connect(database_url)
        
        # Test basic query
        result = await conn.fetchrow("SELECT version()")
        version = result['version']
        
        # Test if UberEats tables exist
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('orders', 'drivers', 'restaurants')
        """
        existing_tables = await conn.fetch(tables_query)
        table_names = [row['table_name'] for row in existing_tables]
        
        await conn.close()
        
        return {
            'status': 'success',
            'version': version,
            'existing_tables': table_names,
            'message': f'✅ PostgreSQL connection successful. Found {len(table_names)}/3 UberEats tables.'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'❌ PostgreSQL connection failed: {str(e)}'
        }

async def test_mongodb_connection() -> Dict[str, Any]:
    """Test MongoDB connection using motor"""
    try:
        mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
        mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
        
        if not mongodb_url:
            return {
                'status': 'error',
                'message': 'MONGODB_CONNECTION_STRING not found in environment variables'
            }
        
        print(f"🔍 Connecting to MongoDB database: {mongodb_db}")
        
        # Connect to MongoDB
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = client[mongodb_db]
        
        # Test connection with ping
        await client.admin.command('ping')
        
        # List existing collections
        collections = await db.list_collection_names()
        
        # Check for expected UberEats collections
        expected_collections = ['order_events', 'driver_events', 'customer_feedback', 'customer_behavior', 'menus']
        existing_expected = [col for col in expected_collections if col in collections]
        
        client.close()
        
        return {
            'status': 'success',
            'database': mongodb_db,
            'total_collections': len(collections),
            'collections': collections,
            'expected_collections_found': existing_expected,
            'message': f'✅ MongoDB connection successful. Found {len(existing_expected)}/{len(expected_collections)} expected collections.'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'❌ MongoDB connection failed: {str(e)}'
        }

def test_redis_connection() -> Dict[str, Any]:
    """Test Redis connection"""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://default:hicVnQPeMFzJjfETtNrYKKwMLdseLUnB@turntable.proxy.rlwy.net:57602')
        
        print(f"🔍 Connecting to Redis...")
        
        # Connect to Redis
        r = redis.from_url(redis_url)
        
        # Test connection
        response = r.ping()
        
        # Get Redis info
        info = r.info()
        redis_version = info.get('redis_version', 'unknown')
        
        return {
            'status': 'success',
            'version': redis_version,
            'ping_response': response,
            'message': f'✅ Redis connection successful. Version: {redis_version}'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'❌ Redis connection failed: {str(e)}'
        }

async def main():
    """Main test function"""
    print("🚀 Testing UberEats Database Connections\n")
    print("=" * 50)
    
    # Test PostgreSQL
    print("\n📊 PostgreSQL Connection Test:")
    postgres_result = await test_postgresql_connection()
    print(postgres_result['message'])
    if postgres_result['status'] == 'success':
        print(f"   Version: {postgres_result['version'][:50]}...")
        print(f"   Tables found: {postgres_result['existing_tables']}")
    
    # Test MongoDB
    print("\n📄 MongoDB Connection Test:")
    mongodb_result = await test_mongodb_connection()
    print(mongodb_result['message'])
    if mongodb_result['status'] == 'success':
        print(f"   Database: {mongodb_result['database']}")
        print(f"   Total collections: {mongodb_result['total_collections']}")
        print(f"   Expected collections found: {mongodb_result['expected_collections_found']}")
    
    # Test Redis
    print("\n🔄 Redis Connection Test:")
    redis_result = test_redis_connection()
    print(redis_result['message'])
    if redis_result['status'] == 'success':
        print(f"   Version: {redis_result['version']}")
    
    # Summary
    print("\n" + "=" * 50)
    successful_connections = sum(1 for result in [postgres_result, mongodb_result, redis_result] if result['status'] == 'success')
    print(f"📈 Summary: {successful_connections}/3 database connections successful")
    
    if successful_connections == 3:
        print("🎉 All database connections are ready for production deployment!")
    else:
        print("⚠️  Some connections failed. Check configuration and network connectivity.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))