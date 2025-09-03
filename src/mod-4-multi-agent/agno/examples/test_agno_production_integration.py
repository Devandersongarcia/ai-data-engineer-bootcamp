#!/usr/bin/env python3
"""
Test Agno agents with production database tools
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
import asyncpg
import motor.motor_asyncio
from agno.tools import tool
from pydantic import Field
from typing import Dict, Any, List, Optional

load_dotenv()

# Production database tools as Agno tools
@tool
def analyze_restaurant_performance(
    restaurant_name: str = Field(None, description="Restaurant name to analyze (optional)"),
    days_back: int = Field(default=7, description="Number of days to look back for analysis")
) -> Dict[str, Any]:
    """
    Analyze restaurant performance using PostgreSQL and MongoDB data.
    Combines order data, delivery metrics, and customer feedback.
    """
    
    async def _analyze():
        postgres_url = os.getenv('DATABASE_URL')
        mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
        mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
        
        # PostgreSQL analysis
        conn = await asyncpg.connect(postgres_url)
        try:
            if restaurant_name:
                query = """
                SELECT 
                    r.name as restaurant_name,
                    r.rating,
                    r.avg_prep_time,
                    r.total_orders as lifetime_orders,
                    COUNT(o.id) as recent_orders,
                    AVG(o.total_amount) as avg_order_value,
                    AVG(o.distance_km) as avg_delivery_distance,
                    COUNT(CASE WHEN o.status = 'delivered' THEN 1 END) as delivered_count,
                    COUNT(CASE WHEN o.status = 'cancelled' THEN 1 END) as cancelled_count
                FROM restaurants r
                LEFT JOIN orders o ON r.name = o.restaurant_name 
                    AND o.created_at >= NOW() - INTERVAL '%s days'
                WHERE r.name ILIKE %s
                GROUP BY r.name, r.rating, r.avg_prep_time, r.total_orders
                """ % (days_back, "'%" + restaurant_name + "%'")
            else:
                query = f"""
                SELECT 
                    r.name as restaurant_name,
                    r.rating,
                    r.avg_prep_time,
                    r.total_orders as lifetime_orders,
                    COUNT(o.id) as recent_orders,
                    AVG(o.total_amount) as avg_order_value,
                    AVG(o.distance_km) as avg_delivery_distance,
                    COUNT(CASE WHEN o.status = 'delivered' THEN 1 END) as delivered_count,
                    COUNT(CASE WHEN o.status = 'cancelled' THEN 1 END) as cancelled_count
                FROM restaurants r
                LEFT JOIN orders o ON r.name = o.restaurant_name 
                    AND o.created_at >= NOW() - INTERVAL '{days_back} days'
                GROUP BY r.name, r.rating, r.avg_prep_time, r.total_orders
                ORDER BY recent_orders DESC
                LIMIT 5
                """
            
            restaurants = await conn.fetch(query)
            restaurant_data = [dict(row) for row in restaurants]
            
        finally:
            await conn.close()
        
        # MongoDB customer feedback analysis
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        try:
            db = client[mongodb_db]
            
            # Get recent feedback
            feedback_pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_rating": {"$avg": "$rating"},
                    "total_reviews": {"$sum": 1},
                    "rating_distribution": {
                        "$push": "$rating"
                    }
                }}
            ]
            
            feedback_cursor = db.customer_feedback.aggregate(feedback_pipeline)
            feedback_results = []
            async for doc in feedback_cursor:
                feedback_results.append(doc)
            
        finally:
            client.close()
        
        # Combine results
        analysis = {
            "restaurants": restaurant_data,
            "feedback_summary": feedback_results[0] if feedback_results else None,
            "analysis_period_days": days_back,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return {
            "success": True,
            "data": analysis,
            "insights": _generate_insights(analysis)
        }
    
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze())
    finally:
        loop.close()

def _generate_insights(analysis: Dict[str, Any]) -> List[str]:
    """Generate business insights from the analysis"""
    insights = []
    
    if analysis["restaurants"]:
        restaurants = analysis["restaurants"]
        
        # Performance insights
        avg_rating = sum(r["rating"] or 0 for r in restaurants) / len(restaurants)
        if avg_rating >= 4.5:
            insights.append(f"✅ Excellent average rating: {avg_rating:.1f}/5.0")
        elif avg_rating >= 4.0:
            insights.append(f"⚠️ Good but improvable rating: {avg_rating:.1f}/5.0")
        else:
            insights.append(f"🚨 Low average rating needs attention: {avg_rating:.1f}/5.0")
        
        # Order volume insights
        total_recent_orders = sum(r["recent_orders"] for r in restaurants)
        if total_recent_orders > 50:
            insights.append(f"📈 High order volume: {total_recent_orders} recent orders")
        else:
            insights.append(f"📉 Low order volume: {total_recent_orders} recent orders")
        
        # Cancellation rate insights
        total_delivered = sum(r["delivered_count"] for r in restaurants)
        total_cancelled = sum(r["cancelled_count"] for r in restaurants)
        if total_delivered + total_cancelled > 0:
            cancellation_rate = total_cancelled / (total_delivered + total_cancelled) * 100
            if cancellation_rate < 5:
                insights.append(f"✅ Low cancellation rate: {cancellation_rate:.1f}%")
            else:
                insights.append(f"⚠️ High cancellation rate: {cancellation_rate:.1f}%")
    
    return insights

@tool
def driver_optimization_analysis(
    driver_id: int = Field(None, description="Specific driver ID to analyze (optional)"),
    include_location_data: bool = Field(default=True, description="Include current location analysis")
) -> Dict[str, Any]:
    """
    Analyze driver performance and optimization opportunities.
    Combines driver data, delivery history, and location intelligence.
    """
    
    async def _analyze():
        postgres_url = os.getenv('DATABASE_URL')
        mongodb_url = os.getenv('MONGODB_CONNECTION_STRING')
        mongodb_db = os.getenv('MONGODB_DATABASE', 'ubereats_catalog')
        
        # PostgreSQL driver analysis
        conn = await asyncpg.connect(postgres_url)
        try:
            if driver_id:
                query = """
                SELECT 
                    d.id,
                    d.name,
                    d.status,
                    d.total_deliveries,
                    d.current_lat,
                    d.current_lng,
                    d.last_movement,
                    COUNT(o.id) as orders_today,
                    AVG(o.total_amount) as avg_order_value,
                    COUNT(CASE WHEN o.status = 'delivered' THEN 1 END) as delivered_today,
                    COUNT(CASE WHEN o.status = 'cancelled' THEN 1 END) as cancelled_today
                FROM drivers d
                LEFT JOIN orders o ON d.id = o.driver_id 
                    AND DATE(o.created_at) = CURRENT_DATE
                WHERE d.id = $1
                GROUP BY d.id, d.name, d.status, d.total_deliveries, d.current_lat, d.current_lng, d.last_movement
                """
                drivers = await conn.fetch(query, driver_id)
            else:
                query = """
                SELECT 
                    d.id,
                    d.name,
                    d.status,
                    d.total_deliveries,
                    d.current_lat,
                    d.current_lng,
                    d.last_movement,
                    COUNT(o.id) as orders_today,
                    AVG(o.total_amount) as avg_order_value,
                    COUNT(CASE WHEN o.status = 'delivered' THEN 1 END) as delivered_today,
                    COUNT(CASE WHEN o.status = 'cancelled' THEN 1 END) as cancelled_today
                FROM drivers d
                LEFT JOIN orders o ON d.id = o.driver_id 
                    AND DATE(o.created_at) = CURRENT_DATE
                GROUP BY d.id, d.name, d.status, d.total_deliveries, d.current_lat, d.current_lng, d.last_movement
                ORDER BY d.total_deliveries DESC
                LIMIT 10
                """
                drivers = await conn.fetch(query)
            
            driver_data = [dict(row) for row in drivers]
            
        finally:
            await conn.close()
        
        # MongoDB driver events analysis
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        try:
            db = client[mongodb_db]
            
            driver_ids = [d["id"] for d in driver_data]
            
            # Get recent driver events
            events_pipeline = [
                {"$match": {"driver_id": {"$in": driver_ids}}},
                {"$group": {
                    "_id": "$driver_id",
                    "total_events": {"$sum": 1},
                    "event_types": {"$addToSet": "$event_type"},
                    "last_event": {"$last": "$event_type"},
                    "avg_delivery_time": {"$avg": "$details.delivery_time"}
                }}
            ]
            
            events_cursor = db.driver_events.aggregate(events_pipeline)
            events_data = {}
            async for doc in events_cursor:
                events_data[doc["_id"]] = {
                    "total_events": doc["total_events"],
                    "event_types": doc["event_types"],
                    "last_event": doc["last_event"],
                    "avg_delivery_time": doc.get("avg_delivery_time", None)
                }
            
        finally:
            client.close()
        
        # Combine and analyze
        for driver in driver_data:
            driver_events = events_data.get(driver["id"], {})
            driver["events_summary"] = driver_events
            driver["performance_score"] = _calculate_driver_score(driver, driver_events)
        
        return {
            "success": True,
            "data": {
                "drivers": driver_data,
                "summary": {
                    "total_drivers": len(driver_data),
                    "active_drivers": len([d for d in driver_data if d["status"] == "active"]),
                    "avg_deliveries": sum(d["total_deliveries"] for d in driver_data) / len(driver_data) if driver_data else 0
                }
            },
            "optimization_recommendations": _generate_driver_recommendations(driver_data)
        }
    
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze())
    finally:
        loop.close()

def _calculate_driver_score(driver: Dict[str, Any], events: Dict[str, Any]) -> float:
    """Calculate driver performance score (0-100)"""
    score = 50  # Base score
    
    # Delivery experience bonus
    if driver["total_deliveries"] > 500:
        score += 15
    elif driver["total_deliveries"] > 100:
        score += 10
    elif driver["total_deliveries"] > 20:
        score += 5
    
    # Recent activity bonus
    if driver["orders_today"] > 5:
        score += 10
    elif driver["orders_today"] > 2:
        score += 5
    
    # Event activity bonus
    if events.get("total_events", 0) > 10:
        score += 10
    
    # Delivery time bonus (if available)
    avg_delivery_time = events.get("avg_delivery_time")
    if avg_delivery_time:
        if avg_delivery_time < 20:
            score += 10
        elif avg_delivery_time < 30:
            score += 5
    
    return min(score, 100)

def _generate_driver_recommendations(drivers: List[Dict[str, Any]]) -> List[str]:
    """Generate optimization recommendations for drivers"""
    recommendations = []
    
    if not drivers:
        return ["No driver data available for recommendations"]
    
    # High performers
    top_performer = max(drivers, key=lambda d: d["performance_score"])
    recommendations.append(f"🏆 Top performer: {top_performer['name']} (Score: {top_performer['performance_score']:.1f})")
    
    # Inactive drivers
    inactive_drivers = [d for d in drivers if d["status"] != "active"]
    if inactive_drivers:
        recommendations.append(f"📱 {len(inactive_drivers)} drivers are currently inactive - consider incentives")
    
    # Low activity drivers
    low_activity = [d for d in drivers if d["orders_today"] == 0]
    if low_activity:
        recommendations.append(f"⚠️ {len(low_activity)} drivers have no orders today - check availability")
    
    return recommendations

# Test the tools
async def test_agno_production_tools():
    """Test Agno tools with production data"""
    print("🧪 Testing Agno Production Tools Integration")
    print("=" * 60)
    
    try:
        # Test 1: Restaurant analysis
        print("\n🍕 Test 1: Restaurant Performance Analysis")
        restaurant_result = analyze_restaurant_performance()
        
        if restaurant_result["success"]:
            print("✅ Restaurant analysis completed:")
            restaurants = restaurant_result["data"]["restaurants"]
            print(f"   • Analyzed {len(restaurants)} restaurants")
            
            for insight in restaurant_result["insights"][:3]:
                print(f"   • {insight}")
        
        # Test 2: Driver optimization
        print("\n🚗 Test 2: Driver Optimization Analysis")
        driver_result = driver_optimization_analysis()
        
        if driver_result["success"]:
            print("✅ Driver analysis completed:")
            summary = driver_result["data"]["summary"]
            print(f"   • Total drivers: {summary['total_drivers']}")
            print(f"   • Active drivers: {summary['active_drivers']}")
            print(f"   • Average deliveries: {summary['avg_deliveries']:.1f}")
            
            for rec in driver_result["optimization_recommendations"][:2]:
                print(f"   • {rec}")
        
        print("\n" + "=" * 60)
        print("🎉 All Agno production tools working correctly!")
        print("🚀 Ready for full agent integration")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main test runner"""
    asyncio.run(test_agno_production_tools())

if __name__ == "__main__":
    main()