#!/usr/bin/env python3
"""
Simple test of production database tools with real data
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
import asyncpg
import motor.motor_asyncio
import pandas as pd
from datetime import datetime, timedelta

load_dotenv()

class SimpleProductionTools:
    """Simplified production tools for testing"""
    
    def __init__(self):
        self.postgres_url = os.getenv('DATABASE_URL')
        self.mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
        self.mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
    
    async def postgres_query(self, query: str, params=None):
        """Execute PostgreSQL query"""
        conn = await asyncpg.connect(self.postgres_url)
        try:
            if params:
                result = await conn.fetch(query, *params)
            else:
                result = await conn.fetch(query)
            
            # Convert to list of dicts
            return [dict(row) for row in result]
        finally:
            await conn.close()
    
    async def mongodb_aggregation(self, collection: str, pipeline: list):
        """Execute MongoDB aggregation"""
        client = motor.motor_asyncio.AsyncIOMotorClient(self.mongodb_url)
        try:
            db = client[self.mongodb_db]
            collection_obj = db[collection]
            
            cursor = collection_obj.aggregate(pipeline)
            result = []
            async for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                result.append(doc)
            
            return result
        finally:
            client.close()
    
    async def analyze_delivery_performance(self, restaurant_id: str = None):
        """Analyze delivery performance combining PostgreSQL and MongoDB data"""
        print(f"🔍 Analyzing delivery performance for restaurant: {restaurant_id or 'ALL'}")
        
        # 1. Get order data from PostgreSQL
        if restaurant_id:
            order_query = """
            SELECT 
                o.id as order_id,
                o.order_number,
                o.restaurant_name,
                o.status,
                o.total_amount,
                o.distance_km,
                o.estimated_delivery_time,
                o.actual_delivery_time,
                o.created_at,
                r.name as restaurant_full_name,
                r.avg_prep_time,
                r.rating as restaurant_rating
            FROM orders o
            LEFT JOIN restaurants r ON o.restaurant_name = r.name
            WHERE o.status IN ('delivered', 'cancelled')
            AND o.created_at >= NOW() - INTERVAL '7 days'
            ORDER BY o.created_at DESC
            LIMIT 50
            """
            params = None
        else:
            order_query = """
            SELECT 
                o.id as order_id,
                o.order_number,
                o.restaurant_name,
                o.status,
                o.total_amount,
                o.distance_km,
                o.estimated_delivery_time,
                o.actual_delivery_time,
                o.created_at
            FROM orders o
            WHERE o.status IN ('delivered', 'cancelled')
            AND o.created_at >= NOW() - INTERVAL '7 days'
            ORDER BY o.created_at DESC
            LIMIT 20
            """
            params = None
        
        orders = await self.postgres_query(order_query, params)
        print(f"📊 Found {len(orders)} recent orders")
        
        if not orders:
            return {"status": "no_data", "message": "No recent orders found"}
        
        # 2. Get order events from MongoDB
        order_ids = [order['order_id'] for order in orders]
        
        events_pipeline = [
            {"$match": {"order_id": {"$in": order_ids}}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$order_id",
                "events": {"$push": {
                    "event_type": "$event_type",
                    "timestamp": "$timestamp",
                    "details": "$details"
                }}
            }}
        ]
        
        events = await self.mongodb_aggregation("order_events", events_pipeline)
        print(f"📊 Found events for {len(events)} orders")
        
        # 3. Analyze the data
        analysis = {
            "total_orders": len(orders),
            "delivered_orders": len([o for o in orders if o['status'] == 'delivered']),
            "cancelled_orders": len([o for o in orders if o['status'] == 'cancelled']),
            "avg_order_value": sum(o['total_amount'] or 0 for o in orders) / len(orders),
            "avg_distance": sum(o['distance_km'] or 0 for o in orders) / len(orders) if any(o['distance_km'] for o in orders) else 0,
            "orders_with_events": len(events)
        }
        
        # 4. Calculate delivery times for completed orders
        delivered_orders = [o for o in orders if o['status'] == 'delivered' and o['actual_delivery_time']]
        if delivered_orders:
            delivery_times = []
            for order in delivered_orders:
                if order['actual_delivery_time'] and order['created_at']:
                    delivery_time = (order['actual_delivery_time'] - order['created_at']).total_seconds() / 60
                    delivery_times.append(delivery_time)
            
            if delivery_times:
                analysis.update({
                    "avg_delivery_time_minutes": sum(delivery_times) / len(delivery_times),
                    "min_delivery_time": min(delivery_times),
                    "max_delivery_time": max(delivery_times)
                })
        
        return {
            "status": "success",
            "analysis": analysis,
            "sample_orders": orders[:5],  # First 5 orders for inspection
            "events_summary": len(events)
        }

    async def get_driver_intelligence(self, driver_id: int = None):
        """Get driver performance and intelligence data"""
        print(f"🚗 Analyzing driver performance for driver: {driver_id or 'ALL'}")
        
        # 1. Get driver data from PostgreSQL
        if driver_id:
            driver_query = """
            SELECT 
                d.id,
                d.driver_code,
                d.name,
                d.status,
                d.total_deliveries,
                d.current_lat,
                d.current_lng,
                d.last_movement,
                COUNT(o.id) as recent_orders
            FROM drivers d
            LEFT JOIN orders o ON d.id = o.driver_id AND o.created_at >= NOW() - INTERVAL '24 hours'
            WHERE d.id = $1
            GROUP BY d.id, d.driver_code, d.name, d.status, d.total_deliveries, d.current_lat, d.current_lng, d.last_movement
            """
            params = [driver_id]
        else:
            driver_query = """
            SELECT 
                d.id,
                d.driver_code,
                d.name,
                d.status,
                d.total_deliveries,
                d.current_lat,
                d.current_lng,
                d.last_movement,
                COUNT(o.id) as recent_orders
            FROM drivers d
            LEFT JOIN orders o ON d.id = o.driver_id AND o.created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY d.id, d.driver_code, d.name, d.status, d.total_deliveries, d.current_lat, d.current_lng, d.last_movement
            ORDER BY d.total_deliveries DESC
            LIMIT 10
            """
            params = None
        
        drivers = await self.postgres_query(driver_query, params)
        print(f"📊 Found {len(drivers)} drivers")
        
        if not drivers:
            return {"status": "no_data", "message": "No drivers found"}
        
        # 2. Get driver events from MongoDB
        driver_ids = [driver['id'] for driver in drivers]
        
        events_pipeline = [
            {"$match": {"driver_id": {"$in": driver_ids}}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$driver_id",
                "total_events": {"$sum": 1},
                "event_types": {"$addToSet": "$event_type"},
                "last_event": {"$first": {
                    "event_type": "$event_type",
                    "timestamp": "$timestamp",
                    "location": "$location"
                }}
            }}
        ]
        
        events = await self.mongodb_aggregation("driver_events", events_pipeline)
        print(f"📊 Found events for {len(events)} drivers")
        
        # 3. Combine data and analyze
        analysis = {
            "total_drivers": len(drivers),
            "active_drivers": len([d for d in drivers if d['status'] == 'active']),
            "drivers_with_events": len(events),
            "top_performers": sorted(drivers, key=lambda x: x['total_deliveries'], reverse=True)[:3]
        }
        
        return {
            "status": "success",
            "analysis": analysis,
            "drivers": drivers,
            "events_summary": {str(e['_id']): e['total_events'] for e in events}
        }

async def main():
    """Main test function"""
    print("🚀 Testing Production Database Tools")
    print("=" * 50)
    
    tools = SimpleProductionTools()
    
    try:
        # Test 1: Delivery performance analysis
        print("\n📈 Test 1: Delivery Performance Analysis")
        delivery_result = await tools.analyze_delivery_performance()
        
        if delivery_result['status'] == 'success':
            analysis = delivery_result['analysis']
            print(f"✅ Analysis completed:")
            print(f"   • Total orders: {analysis['total_orders']}")
            print(f"   • Delivered: {analysis['delivered_orders']}")
            print(f"   • Cancelled: {analysis['cancelled_orders']}")
            print(f"   • Avg order value: ${analysis['avg_order_value']:.2f}")
            print(f"   • Avg distance: {analysis['avg_distance']:.2f}km")
            
            if 'avg_delivery_time_minutes' in analysis:
                print(f"   • Avg delivery time: {analysis['avg_delivery_time_minutes']:.1f} minutes")
        else:
            print(f"⚠️  {delivery_result['message']}")
        
        # Test 2: Driver intelligence
        print("\n🚗 Test 2: Driver Intelligence Analysis")
        driver_result = await tools.get_driver_intelligence()
        
        if driver_result['status'] == 'success':
            analysis = driver_result['analysis']
            print(f"✅ Analysis completed:")
            print(f"   • Total drivers: {analysis['total_drivers']}")
            print(f"   • Active drivers: {analysis['active_drivers']}")
            print(f"   • Top performer: {analysis['top_performers'][0]['name']} ({analysis['top_performers'][0]['total_deliveries']} deliveries)")
        else:
            print(f"⚠️  {driver_result['message']}")
        
        # Test 3: MongoDB collections inspection
        print("\n📄 Test 3: MongoDB Collections Analysis")
        collections_data = {}
        
        # Order events
        order_events_pipeline = [
            {"$group": {
                "_id": "$event_type",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        order_events = await tools.mongodb_aggregation("order_events", order_events_pipeline)
        collections_data['order_events'] = order_events
        
        # Driver events  
        driver_events_pipeline = [
            {"$group": {
                "_id": "$event_type", 
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        driver_events = await tools.mongodb_aggregation("driver_events", driver_events_pipeline)
        collections_data['driver_events'] = driver_events
        
        # Customer feedback
        feedback_pipeline = [
            {"$group": {
                "_id": "$rating",
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": -1}}
        ]
        feedback = await tools.mongodb_aggregation("customer_feedback", feedback_pipeline)
        collections_data['customer_feedback'] = feedback
        
        print("✅ MongoDB analysis completed:")
        for collection_name, data in collections_data.items():
            print(f"   • {collection_name}: {len(data)} event types/ratings")
            for item in data[:3]:  # Show top 3
                print(f"     - {item['_id']}: {item['count']}")
        
        print("\n" + "=" * 50)
        print("🎉 All production tools tested successfully!")
        print("📈 Database integration is working correctly")
        print("🔧 Ready for agent integration")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))