#!/usr/bin/env python3
"""
Populate sample data for testing production tools
"""
import asyncio
import asyncpg
import motor.motor_asyncio
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import random

load_dotenv()

async def populate_restaurant_data():
    """Add sample restaurants to the empty restaurants table"""
    database_url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(database_url)
    
    try:
        # Check if restaurants table is empty
        count = await conn.fetchval("SELECT COUNT(*) FROM restaurants")
        print(f"📊 Current restaurants count: {count}")
        
        if count == 0:
            print("🏪 Adding sample restaurant data...")
            
            sample_restaurants = """
            INSERT INTO restaurants (restaurant_id, name, cuisine_type, rating, total_orders, avg_prep_time, is_active, commission_rate, partner_since, menu_items_count, avg_order_value) VALUES
            ('rest_001', 'Pizza Palace Downtown', 'Italian', 4.5, 1200, 15, true, 0.125, '2023-01-15', 25, 18.50),
            ('rest_002', 'Burger Junction Central', 'American', 4.2, 890, 12, true, 0.115, '2023-02-20', 18, 12.75),
            ('rest_003', 'Sushi Masters Premium', 'Japanese', 4.8, 650, 20, true, 0.135, '2023-01-10', 42, 28.90),
            ('rest_004', 'Taco Fiesta Express', 'Mexican', 4.3, 1450, 8, true, 0.105, '2022-11-05', 15, 9.25),
            ('rest_005', 'Green Salad Co Health', 'Healthy', 4.6, 780, 7, true, 0.120, '2023-03-12', 22, 14.80),
            ('rest_006', 'Golden Dragon Chinese', 'Chinese', 4.4, 920, 18, true, 0.118, '2022-12-08', 35, 16.30),
            ('rest_007', 'Pasta Bella Italiana', 'Italian', 4.7, 1100, 14, true, 0.128, '2023-02-28', 28, 19.80),
            ('rest_008', 'BBQ Kings Smokehouse', 'American', 4.1, 680, 25, true, 0.122, '2023-04-15', 20, 22.40)
            """
            await conn.execute(sample_restaurants)
            print("✅ Added 8 sample restaurants")
        else:
            print("✅ Restaurants table already has data")
    
    finally:
        await conn.close()

async def create_mongodb_sample_collections():
    """Create UberEats-specific collections for production tools"""
    mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
    mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db]
    
    try:
        # Create order_events collection for tracking
        if 'order_events' not in await db.list_collection_names():
            await db.create_collection('order_events')
            
            # Add sample order events
            sample_events = [
                {
                    "order_id": 1,
                    "event_type": "order_placed",
                    "timestamp": datetime.now() - timedelta(hours=2),
                    "details": {
                        "restaurant_id": "rest_001",
                        "customer_name": "João Silva",
                        "total": 28.50,
                        "items": ["Pizza Margherita", "Coca Cola"]
                    }
                },
                {
                    "order_id": 1,
                    "event_type": "restaurant_confirmed", 
                    "timestamp": datetime.now() - timedelta(hours=1, minutes=58),
                    "details": {"prep_time_estimate": 15, "kitchen_notes": "Extra cheese requested"}
                },
                {
                    "order_id": 1,
                    "event_type": "driver_assigned",
                    "timestamp": datetime.now() - timedelta(hours=1, minutes=45),
                    "details": {"driver_id": 1, "driver_name": "Carlos Santos", "eta": 30}
                },
                {
                    "order_id": 2,
                    "event_type": "order_placed",
                    "timestamp": datetime.now() - timedelta(minutes=45),
                    "details": {
                        "restaurant_id": "rest_002", 
                        "customer_name": "Maria Oliveira",
                        "total": 15.75,
                        "items": ["Classic Burger", "French Fries"]
                    }
                },
                {
                    "order_id": 3,
                    "event_type": "delivery_completed",
                    "timestamp": datetime.now() - timedelta(minutes=30),
                    "details": {
                        "driver_id": 2,
                        "delivery_time": 18,
                        "customer_rating": 5,
                        "tip": 3.00
                    }
                }
            ]
            
            await db.order_events.insert_many(sample_events)
            await db.order_events.create_index([("timestamp", 1)])
            await db.order_events.create_index([("event_type", 1)])
            await db.order_events.create_index([("order_id", 1)])
            print("✅ Created order_events collection with sample data")
        
        # Create driver_events collection
        if 'driver_events' not in await db.list_collection_names():
            await db.create_collection('driver_events')
            
            sample_driver_events = [
                {
                    "driver_id": 1,
                    "event_type": "shift_start",
                    "timestamp": datetime.now() - timedelta(hours=4),
                    "location": {"lat": -23.5505, "lng": -46.6333},
                    "details": {"shift_goal": 8, "vehicle_type": "motorcycle"}
                },
                {
                    "driver_id": 1,
                    "event_type": "delivery_completed",
                    "timestamp": datetime.now() - timedelta(hours=2),
                    "location": {"lat": -23.5525, "lng": -46.6345},
                    "details": {"order_id": 1, "delivery_time": 18, "earnings": 12.50}
                },
                {
                    "driver_id": 2,
                    "event_type": "delivery_completed",
                    "timestamp": datetime.now() - timedelta(minutes=35),
                    "location": {"lat": -23.5515, "lng": -46.6355},
                    "details": {"order_id": 3, "delivery_time": 22, "earnings": 8.75}
                }
            ]
            
            await db.driver_events.insert_many(sample_driver_events)
            await db.driver_events.create_index([("timestamp", 1)])
            await db.driver_events.create_index([("driver_id", 1)])
            await db.driver_events.create_index([("event_type", 1)])
            print("✅ Created driver_events collection with sample data")
        
        # Create customer_feedback collection
        if 'customer_feedback' not in await db.list_collection_names():
            await db.create_collection('customer_feedback')
            
            sample_feedback = [
                {
                    "order_id": 1,
                    "customer_id": "user_001",
                    "rating": 5,
                    "review": "Excellent pizza, arrived hot and on time!",
                    "categories": {
                        "food_quality": 5,
                        "delivery_time": 5,
                        "driver_service": 4
                    },
                    "submitted_at": datetime.now() - timedelta(hours=1)
                },
                {
                    "order_id": 3,
                    "customer_id": "user_003", 
                    "rating": 4,
                    "review": "Good food but delivery took longer than expected",
                    "categories": {
                        "food_quality": 5,
                        "delivery_time": 3,
                        "driver_service": 4
                    },
                    "submitted_at": datetime.now() - timedelta(minutes=25)
                }
            ]
            
            await db.customer_feedback.insert_many(sample_feedback)
            await db.customer_feedback.create_index([("order_id", 1)])
            await db.customer_feedback.create_index([("submitted_at", 1)])
            print("✅ Created customer_feedback collection with sample data")
        
    finally:
        client.close()

async def main():
    """Main data population function"""
    print("🗄️ Populating Sample Data for Production Testing")
    print("=" * 50)
    
    try:
        await populate_restaurant_data()
        print()
        await create_mongodb_sample_collections()
        
        print("\n" + "=" * 50)
        print("✅ Sample data population completed successfully!")
        print("🔧 Production tools are ready for testing")
        
        return 0
        
    except Exception as e:
        print(f"❌ Data population failed: {str(e)}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))