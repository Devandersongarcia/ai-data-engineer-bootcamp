#!/usr/bin/env python3
"""
UberEats Agent Tools Integration Demo
Demonstrates how to integrate tools with Agno agents for delivery optimization
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.eta_prediction_agent import SmartETAPredictionAgent
from src.agents.driver_allocation_agent import DriverAllocationAgent
from src.agents.route_optimization_agent import RouteOptimizationAgent
from src.tools import (
    postgres_tool, redis_tool, sms_tool, email_tool, slack_tool,
    google_maps_tool, weather_tool, pandas_tool, calculator_tool
)


class ToolIntegratedAgent:
    """Demonstrates tool integration patterns with UberEats agents"""
    
    def __init__(self):
        self.eta_agent = SmartETAPredictionAgent()
        self.driver_agent = DriverAllocationAgent()
        self.route_agent = RouteOptimizationAgent()
    
    async def demo_eta_prediction_with_tools(self):
        """Demo ETA prediction using multiple tools"""
        print("\n🎯 DEMO: ETA Prediction with Tool Integration")
        print("=" * 60)
        
        # Sample order data
        order_data = {
            "order_id": "ORD2024001",
            "restaurant_location": {"lat": 37.7749, "lng": -122.4194},
            "customer_location": {"lat": 37.7849, "lng": -122.4094},
            "restaurant_id": "REST001"
        }
        
        print(f"Order: {order_data['order_id']}")
        print(f"Restaurant: {order_data['restaurant_location']}")
        print(f"Customer: {order_data['customer_location']}")
        
        # 1. Use Google Maps tool for route calculation
        print("\n1. 📍 Calculating route with Google Maps...")
        route_result = google_maps_tool.execute({
            "origin": f"{order_data['restaurant_location']['lat']},{order_data['restaurant_location']['lng']}",
            "destination": f"{order_data['customer_location']['lat']},{order_data['customer_location']['lng']}",
            "mode": "driving",
            "optimize": True
        })
        
        if route_result["success"]:
            print(f"   Distance: {route_result['distance']['text']}")
            print(f"   Duration: {route_result['duration']['text']}")
            print(f"   Traffic: {route_result['traffic_conditions']}")
        
        # 2. Check weather conditions
        print("\n2. 🌤️  Checking weather conditions...")
        weather_result = weather_tool.execute({
            "location": f"{order_data['customer_location']['lat']},{order_data['customer_location']['lng']}",
            "units": "metric"
        })
        
        if weather_result["success"]:
            weather = weather_result["current"]
            impact = weather_result["delivery_impact"]
            print(f"   Condition: {weather['condition']}")
            print(f"   Temperature: {weather['temperature']}°C")
            print(f"   Impact: {impact['severity']} (x{impact['multiplier']})")
        
        # 3. Use calculator for ETA adjustment
        print("\n3. 🧮 Calculating adjusted ETA...")
        base_time = route_result["duration"]["value"] / 60 if route_result["success"] else 25
        weather_multiplier = weather_result["delivery_impact"]["multiplier"] if weather_result["success"] else 1.0
        
        calc_result = calculator_tool.execute({
            "operation": "basic",
            "expression": f"{base_time} * {weather_multiplier}"
        })
        
        if calc_result["success"]:
            adjusted_eta = calc_result["result"]
            print(f"   Base ETA: {base_time:.1f} minutes")
            print(f"   Weather multiplier: {weather_multiplier}")
            print(f"   Adjusted ETA: {adjusted_eta:.1f} minutes")
        
        # 4. Store prediction in Redis
        print("\n4. 💾 Storing prediction in Redis...")
        prediction_data = {
            "order_id": order_data["order_id"],
            "eta_minutes": adjusted_eta if calc_result["success"] else base_time,
            "factors": {
                "distance_km": route_result.get("distance", {}).get("value", 0) / 1000,
                "weather_condition": weather_result.get("current", {}).get("condition", "unknown"),
                "weather_impact": weather_multiplier,
                "traffic": route_result.get("traffic_conditions", "unknown")
            },
            "timestamp": datetime.now().isoformat()
        }
        
        redis_result = redis_tool.execute({
            "operation": "set",
            "key": f"eta_prediction:{order_data['order_id']}",
            "value": prediction_data,
            "ttl": 3600  # 1 hour
        })
        
        if redis_result["success"]:
            print(f"   ✅ Prediction cached for 1 hour")
        
        # 5. Send SMS notification to customer
        print("\n5. 📱 Sending customer notification...")
        sms_result = sms_tool.execute({
            "to": "+1234567890",  # Demo number
            "message": f"Hi! Your order {order_data['order_id']} is confirmed. "
                      f"Estimated delivery: {adjusted_eta:.0f} minutes. "
                      f"We'll keep you updated!"
        })
        
        if sms_result["success"]:
            print(f"   ✅ SMS sent: {sms_result['message_id']}")
        
        return prediction_data
    
    async def demo_driver_allocation_with_tools(self):
        """Demo driver allocation using database and communication tools"""
        print("\n🚗 DEMO: Driver Allocation with Database Integration")
        print("=" * 60)
        
        # 1. Query available drivers using Postgres tool
        print("\n1. 🗄️  Querying available drivers...")
        postgres_result = postgres_tool.execute({
            "query": """
                SELECT driver_id, current_location, rating, vehicle_type, status
                FROM drivers 
                WHERE status = 'available' 
                AND rating >= 4.0
                ORDER BY rating DESC
                LIMIT 5
            """,
            "fetch_all": True
        })
        
        # Since we don't have real DB, simulate with sample data
        sample_drivers = [
            {"driver_id": "D001", "rating": 4.8, "vehicle_type": "car", "distance_km": 2.1},
            {"driver_id": "D002", "rating": 4.6, "vehicle_type": "scooter", "distance_km": 1.8},
            {"driver_id": "D003", "rating": 4.9, "vehicle_type": "car", "distance_km": 3.2}
        ]
        
        print(f"   Found {len(sample_drivers)} available drivers")
        for driver in sample_drivers:
            print(f"   - {driver['driver_id']}: {driver['rating']}⭐ ({driver['vehicle_type']}, {driver['distance_km']}km)")
        
        # 2. Calculate optimal driver using analytics
        print("\n2. 📊 Analyzing driver performance...")
        analytics_result = pandas_tool.execute({
            "operation": "analyze",
            "data": sample_drivers
        })
        
        # 3. Select best driver based on multiple factors
        print("\n3. 🎯 Selecting optimal driver...")
        best_driver = sample_drivers[0]  # Simplified selection
        
        calc_result = calculator_tool.execute({
            "operation": "optimization",
            "parameters": {
                "delivery_efficiency": True,
                "delivery_time": 25,
                "distance": best_driver["distance_km"],
                "fuel_cost": 3.5
            }
        })
        
        if calc_result["success"]:
            efficiency = calc_result["efficiency_score"]
            print(f"   Selected: {best_driver['driver_id']} (efficiency score: {efficiency})")
        
        # 4. Send driver notification
        print("\n4. 📞 Notifying selected driver...")
        sms_result = sms_tool.execute({
            "to": "+1234567891",  # Driver's number
            "message": f"New pickup available! Order ORD2024001 at Downtown Bistro, "
                      f"123 Market St. Pickup by 7:30 PM. Accept? Reply YES/NO"
        })
        
        if sms_result["success"]:
            print(f"   ✅ Driver notified: {sms_result['message_id']}")
        
        # 5. Alert operations team via Slack
        print("\n5. 📢 Updating operations team...")
        slack_result = slack_tool.execute({
            "channel": "#operations",
            "message": f"🚗 Order ORD2024001 assigned to {best_driver['driver_id']} "
                      f"(rating: {best_driver['rating']}⭐, ETA: 25 min)"
        })
        
        if slack_result["success"]:
            print(f"   ✅ Slack notification sent")
        
        return best_driver
    
    async def demo_route_optimization_with_analytics(self):
        """Demo route optimization using analytics tools"""
        print("\n🗺️  DEMO: Route Optimization with Analytics")
        print("=" * 60)
        
        # Sample multi-order scenario
        orders = [
            {"order_id": "ORD001", "location": [37.7749, -122.4194], "priority": "high"},
            {"order_id": "ORD002", "location": [37.7849, -122.4094], "priority": "normal"},
            {"order_id": "ORD003", "location": [37.7649, -122.4294], "priority": "normal"},
            {"order_id": "ORD004", "location": [37.7949, -122.3994], "priority": "urgent"}
        ]
        
        print(f"Optimizing route for {len(orders)} orders...")
        for order in orders:
            print(f"   - {order['order_id']}: {order['location']} ({order['priority']})")
        
        # 1. Calculate distances between all points
        print("\n1. 📏 Calculating distances...")
        coordinates = [order["location"] for order in orders]
        
        distance_result = calculator_tool.execute({
            "operation": "distance",
            "coordinates": coordinates
        })
        
        if distance_result["success"]:
            total_distance = distance_result["total_distance_km"]
            print(f"   Total route distance: {total_distance} km")
            for i, dist_info in enumerate(distance_result["distances"]):
                print(f"   - Segment {i+1}: {dist_info['distance_km']} km")
        
        # 2. Analyze delivery patterns
        print("\n2. 📈 Analyzing delivery patterns...")
        
        # Create sample historical data for analysis
        historical_data = [
            {"order_id": f"HIST{i}", "delivery_time": 20 + (i % 15), 
             "distance": 2 + (i % 5), "hour": 12 + (i % 10)}
            for i in range(50)
        ]
        
        analytics_result = pandas_tool.execute({
            "operation": "analyze",
            "data": historical_data
        })
        
        if analytics_result["success"]:
            insights = analytics_result["analysis"]["delivery_insights"]
            print(f"   Average delivery time: {insights['avg_delivery_time']:.1f} minutes")
            print(f"   On-time rate: {insights['on_time_rate']:.1f}%")
        
        # 3. Optimize route order
        print("\n3. 🎯 Optimizing delivery sequence...")
        
        # Simple priority-based optimization
        priority_weights = {"urgent": 3, "high": 2, "normal": 1}
        optimized_orders = sorted(orders, 
                                key=lambda x: priority_weights[x["priority"]], 
                                reverse=True)
        
        calc_result = calculator_tool.execute({
            "operation": "optimization",
            "parameters": {
                "route_optimization": True,
                "stops": [{"id": o["order_id"], "priority": o["priority"]} for o in orders]
            }
        })
        
        if calc_result["success"]:
            print(f"   Optimization complete: {calc_result['estimated_savings']}")
        
        print("\n   Optimized sequence:")
        for i, order in enumerate(optimized_orders):
            print(f"   {i+1}. {order['order_id']} ({order['priority']} priority)")
        
        # 4. Calculate efficiency improvement
        print("\n4. 📊 Calculating efficiency gains...")
        original_time = sum(20 + i*3 for i in range(len(orders)))  # Simulate original time
        optimized_time = sum(20 + i*2 for i in range(len(orders)))  # Simulate optimized time
        
        efficiency_calc = calculator_tool.execute({
            "operation": "statistics",
            "values": [original_time, optimized_time]
        })
        
        time_saved = original_time - optimized_time
        efficiency_gain = (time_saved / original_time) * 100
        
        print(f"   Original total time: {original_time} minutes")
        print(f"   Optimized total time: {optimized_time} minutes")
        print(f"   Time saved: {time_saved} minutes ({efficiency_gain:.1f}% improvement)")
        
        # 5. Send optimization report via email
        print("\n5. 📧 Sending optimization report...")
        
        email_result = email_tool.execute({
            "to": ["operations@ubereats.com"],
            "subject": "Route Optimization Report - Driver Route001",
            "message": f"""
            Route Optimization Complete
            
            Orders optimized: {len(orders)}
            Total distance: {total_distance} km
            Time saved: {time_saved} minutes ({efficiency_gain:.1f}% improvement)
            
            Optimized sequence: {', '.join([o['order_id'] for o in optimized_orders])}
            
            Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """,
            "html": False
        })
        
        if email_result["success"]:
            print(f"   ✅ Report sent: {email_result['message_id']}")
        
        return {
            "optimized_orders": optimized_orders,
            "total_distance": total_distance,
            "time_saved": time_saved,
            "efficiency_gain": efficiency_gain
        }
    
    async def demo_comprehensive_workflow(self):
        """Demo comprehensive workflow using all tools"""
        print("\n🔄 DEMO: Comprehensive Delivery Workflow")
        print("=" * 70)
        
        print("Executing complete delivery optimization workflow...")
        
        # Run all demos in sequence
        eta_prediction = await self.demo_eta_prediction_with_tools()
        driver_allocation = await self.demo_driver_allocation_with_tools()
        route_optimization = await self.demo_route_optimization_with_analytics()
        
        # Consolidate results
        print("\n📋 WORKFLOW SUMMARY")
        print("=" * 50)
        print(f"✅ ETA Prediction: {eta_prediction['eta_minutes']:.1f} minutes")
        print(f"✅ Driver Allocated: {driver_allocation['driver_id']} ({driver_allocation['rating']}⭐)")
        print(f"✅ Route Optimized: {route_optimization['efficiency_gain']:.1f}% improvement")
        print(f"✅ Customer Notified: SMS sent")
        print(f"✅ Driver Notified: SMS sent")
        print(f"✅ Team Updated: Slack notification")
        print(f"✅ Report Generated: Email sent")
        
        # Store final workflow result in Redis
        workflow_result = {
            "workflow_id": f"WF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "eta_prediction": eta_prediction,
            "driver_allocation": driver_allocation,
            "route_optimization": route_optimization,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
        redis_result = redis_tool.execute({
            "operation": "set",
            "key": f"workflow:{workflow_result['workflow_id']}",
            "value": workflow_result,
            "ttl": 86400  # 24 hours
        })
        
        if redis_result["success"]:
            print(f"✅ Workflow cached: {workflow_result['workflow_id']}")
        
        return workflow_result


async def main():
    """Main demo function"""
    print("🚀 UberEats Agent Tools Integration Demo")
    print("=" * 70)
    print("This demo shows how Agno agents can leverage various tools")
    print("for comprehensive delivery optimization.\n")
    
    demo = ToolIntegratedAgent()
    
    try:
        # Run individual demos
        print("Running tool integration demonstrations...\n")
        
        await demo.demo_eta_prediction_with_tools()
        await demo.demo_driver_allocation_with_tools()
        await demo.demo_route_optimization_with_analytics()
        
        # Run comprehensive workflow
        result = await demo.demo_comprehensive_workflow()
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"Workflow ID: {result['workflow_id']}")
        print("\nKey takeaways:")
        print("• Tools enable agents to access external data and services")
        print("• Multi-tool workflows create powerful automation capabilities")
        print("• Real-time notifications keep all stakeholders informed")
        print("• Analytics provide insights for continuous improvement")
        print("• Redis caching optimizes performance and enables persistence")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())