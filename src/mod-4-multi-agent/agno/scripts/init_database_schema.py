#!/usr/bin/env python3
"""
Initialize UberEats database schema for production deployment
"""
import asyncio
import os
import sys
from typing import List, Dict, Any

import asyncpg
import motor.motor_asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def create_postgresql_schema():
    """Create missing PostgreSQL tables and indexes"""
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        print("🗄️ Initializing PostgreSQL schema...")
        
        # Create restaurants table (missing)
        restaurants_table = """
        CREATE TABLE IF NOT EXISTS restaurants (
            restaurant_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            cuisine_type VARCHAR(50),
            rating DECIMAL(2,1),
            total_orders INTEGER DEFAULT 0,
            avg_prep_time INTEGER,
            is_active BOOLEAN DEFAULT true,
            location JSONB,
            commission_rate DECIMAL(4,3),
            partner_since TIMESTAMP,
            menu_items_count INTEGER DEFAULT 0,
            avg_order_value DECIMAL(8,2)
        );
        """
        
        await conn.execute(restaurants_table)
        print("✅ Created restaurants table")
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_orders_order_time ON orders(order_time);",
            "CREATE INDEX IF NOT EXISTS idx_orders_restaurant_id ON orders(restaurant_id);", 
            "CREATE INDEX IF NOT EXISTS idx_orders_driver_id ON orders(driver_id);",
            "CREATE INDEX IF NOT EXISTS idx_drivers_status ON drivers(status);",
            "CREATE INDEX IF NOT EXISTS idx_drivers_rating ON drivers(rating);",
            "CREATE INDEX IF NOT EXISTS idx_restaurants_active ON restaurants(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants(rating);"
        ]
        
        for index in indexes:
            await conn.execute(index)
        
        print("✅ Created performance indexes")
        
        # Insert sample restaurants data if table is empty
        count = await conn.fetchval("SELECT COUNT(*) FROM restaurants")
        if count == 0:
            sample_restaurants = """
            INSERT INTO restaurants (restaurant_id, name, cuisine_type, rating, total_orders, avg_prep_time, is_active, commission_rate, partner_since, menu_items_count, avg_order_value) VALUES
            ('rest_001', 'Pizza Palace', 'Italian', 4.5, 1200, 15, true, 0.125, '2023-01-15', 25, 18.50),
            ('rest_002', 'Burger Junction', 'American', 4.2, 890, 12, true, 0.115, '2023-02-20', 18, 12.75),
            ('rest_003', 'Sushi Masters', 'Japanese', 4.8, 650, 20, true, 0.135, '2023-01-10', 42, 28.90),
            ('rest_004', 'Taco Fiesta', 'Mexican', 4.3, 1450, 8, true, 0.105, '2022-11-05', 15, 9.25),
            ('rest_005', 'Green Salad Co', 'Healthy', 4.6, 780, 7, true, 0.120, '2023-03-12', 22, 14.80)
            ON CONFLICT (restaurant_id) DO NOTHING;
            """
            await conn.execute(sample_restaurants)
            print("✅ Inserted sample restaurant data")
        
    finally:
        await conn.close()

async def create_mongodb_collections():
    """Create MongoDB collections with proper indexes"""
    mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
    mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db]
    
    try:
        print("🗄️ Initializing MongoDB collections...")
        
        # Get existing collections
        existing_collections = await db.list_collection_names()
        print(f"📋 Found existing collections: {existing_collections}")
        
        # Collections to create
        collections_config = {
            'order_events': [
                {'keys': [('timestamp', 1)]},
                {'keys': [('event_type', 1)]},
                {'keys': [('order_id', 1)]}
            ],
            'driver_events': [
                {'keys': [('timestamp', 1)]},
                {'keys': [('driver_id', 1)]},
                {'keys': [('event_type', 1)]}
            ],
            'customer_feedback': [
                {'keys': [('order_id', 1)]},
                {'keys': [('submitted_at', 1)]}
            ],
            'customer_behavior': [
                {'keys': [('timestamp', 1)]},
                {'keys': [('user_id', 1)]},
                {'keys': [('action', 1)]}
            ],
            'menus': [
                {'keys': [('restaurant_id', 1)]},
                {'keys': [('updated_at', 1)]}
            ]
        }
        
        for collection_name, indexes in collections_config.items():
            if collection_name not in existing_collections:
                # Create collection
                await db.create_collection(collection_name)
                print(f"✅ Created collection: {collection_name}")
            else:
                print(f"📂 Collection exists: {collection_name}")
            
            # Create indexes
            collection = db[collection_name]
            for index_spec in indexes:
                try:
                    await collection.create_index(**index_spec)
                except Exception as e:
                    # Index might already exist
                    pass
            
            print(f"✅ Created indexes for: {collection_name}")
        
        # Insert sample data for order_events if empty
        order_events = db['order_events']
        count = await order_events.count_documents({})
        if count == 0:
            sample_events = [
                {
                    "order_id": "ord_001",
                    "event_type": "order_placed",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "details": {"restaurant_id": "rest_001", "customer_id": "cust_001", "total": 18.50}
                },
                {
                    "order_id": "ord_001", 
                    "event_type": "restaurant_confirmed",
                    "timestamp": "2024-01-15T10:32:00Z",
                    "details": {"prep_time_estimate": 15}
                },
                {
                    "order_id": "ord_002",
                    "event_type": "order_placed", 
                    "timestamp": "2024-01-15T11:15:00Z",
                    "details": {"restaurant_id": "rest_002", "customer_id": "cust_002", "total": 12.75}
                }
            ]
            await order_events.insert_many(sample_events)
            print("✅ Inserted sample order events")
        
    finally:
        client.close()

async def verify_schema():
    """Verify that all schema elements are properly created"""
    print("\n🔍 Verifying schema initialization...")
    
    # Verify PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    pg_conn = await asyncpg.connect(database_url)
    
    try:
        # Check tables
        tables = await pg_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('orders', 'drivers', 'restaurants')
        """)
        table_names = [row['table_name'] for row in tables]
        print(f"📊 PostgreSQL tables: {table_names} ({len(table_names)}/3)")
        
        # Check indexes
        indexes = await pg_conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
        """)
        index_names = [row['indexname'] for row in indexes]
        print(f"📊 PostgreSQL indexes: {len(index_names)} performance indexes created")
        
    finally:
        await pg_conn.close()
    
    # Verify MongoDB
    mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
    mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
    
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
    db = mongo_client[mongodb_db]
    
    try:
        collections = await db.list_collection_names()
        expected_collections = ['order_events', 'driver_events', 'customer_feedback', 'customer_behavior', 'menus']
        found_expected = [col for col in expected_collections if col in collections]
        print(f"📄 MongoDB collections: {found_expected} ({len(found_expected)}/5 expected)")
        
        # Check sample data
        order_events_count = await db.order_events.count_documents({})
        print(f"📄 Sample order events: {order_events_count}")
        
    finally:
        mongo_client.close()
    
    return len(table_names) >= 3 and len(found_expected) >= 4

async def main():
    """Main initialization function"""
    print("🚀 Initializing UberEats Database Schema\n")
    print("=" * 50)
    
    try:
        # Initialize PostgreSQL schema
        await create_postgresql_schema()
        print()
        
        # Initialize MongoDB collections
        await create_mongodb_collections()
        print()
        
        # Verify everything is set up correctly
        success = await verify_schema()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 Database schema initialization completed successfully!")
            print("📈 System is ready for production deployment")
            return 0
        else:
            print("⚠️  Schema initialization incomplete. Check errors above.")
            return 1
            
    except Exception as e:
        print(f"❌ Schema initialization failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))