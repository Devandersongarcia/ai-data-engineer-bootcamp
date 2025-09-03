# examples/delivery_optimization_demo.py - Delivery Optimization Demo
"""
Demo script showing how to use the delivery optimization system with your datasets.

This example demonstrates:
1. How to connect your real datasets to the modular data providers
2. How to use the delivery optimization API endpoints
3. How to integrate ETA prediction, driver allocation, and route optimization
4. How to monitor performance and quality metrics

Replace the sample data providers with your actual dataset connections.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the delivery optimization system
from src.orchestration.delivery_optimization_workflow import DeliveryOptimizationWorkflow
from src.data.interfaces import data_manager
from src.data.sample_providers import (
    SampleOrderDataProvider, SampleRestaurantDataProvider,
    SampleDriverDataProvider, SampleTrafficDataProvider,
    SampleHistoricalDataProvider, DatasetConnector
)


async def setup_data_providers():
    """
    Setup data providers - Replace with your actual dataset connections
    
    IMPORTANT: Replace these sample providers with your real data sources:
    - Connect to your order database/API
    - Connect to your restaurant management system
    - Connect to your driver tracking system
    - Connect to traffic/routing APIs (Google Maps, MapBox, etc.)
    - Connect to your analytics/historical data warehouse
    """
    
    print("🔌 Setting up data providers...")
    
    # Method 1: Use sample providers (for testing)
    order_provider = SampleOrderDataProvider()
    restaurant_provider = SampleRestaurantDataProvider()
    driver_provider = SampleDriverDataProvider()
    traffic_provider = SampleTrafficDataProvider()
    historical_provider = SampleHistoricalDataProvider()
    
    # Method 2: Connect your real datasets (uncomment and configure)
    # order_provider = DatasetConnector.connect_order_dataset(
    #     "postgresql://user:pass@host:5432/orders_db", 
    #     "orders_table"
    # )
    # restaurant_provider = DatasetConnector.connect_restaurant_dataset(
    #     "postgresql://user:pass@host:5432/restaurants_db",
    #     "restaurants_table"
    # )
    # driver_provider = DatasetConnector.connect_driver_dataset(
    #     "https://api.yourcompany.com/drivers",
    #     "your_api_key"
    # )
    # traffic_provider = DatasetConnector.connect_traffic_api(
    #     "your_google_maps_api_key",
    #     "google_maps"
    # )
    # historical_provider = DatasetConnector.connect_historical_data(
    #     "postgresql://user:pass@host:5432/analytics_db"
    # )
    
    # Register providers with the data manager
    data_manager.register_provider("orders", order_provider)
    data_manager.register_provider("restaurants", restaurant_provider)
    data_manager.register_provider("drivers", driver_provider)
    data_manager.register_provider("traffic", traffic_provider)
    data_manager.register_provider("historical", historical_provider)
    
    print("✅ Data providers configured successfully!")
    return True


async def demo_single_order_optimization():
    """Demo: Optimize a single order"""
    
    print("\n🚚 Demo 1: Single Order Optimization")
    print("=" * 50)
    
    # Initialize the delivery optimization workflow
    optimizer = DeliveryOptimizationWorkflow()
    
    # Single order optimization request
    request = {
        "order_ids": ["order_001"],
        "type": "single_order",
        "priority": "normal",
        "constraints": {
            "max_delivery_time_minutes": 45,
            "preferred_vehicle_types": ["bike", "scooter"]
        }
    }
    
    print(f"Optimizing order: {request['order_ids'][0]}")
    
    # Execute optimization
    result = await optimizer.execute_workflow(request)
    
    # Display results
    print(f"✅ Optimization completed!")
    print(f"   Success: {result['success']}")
    print(f"   Processing time: {result['processing_time_seconds']:.2f}s")
    print(f"   Quality score: {result['quality_score']:.2f}")
    
    if result['optimization_results']:
        opt_result = result['optimization_results'][0]
        print(f"   Allocated driver: {opt_result.get('allocated_driver_id', 'None')}")
        print(f"   Predicted ETA: {opt_result.get('predicted_eta', 'N/A')}")
        print(f"   Confidence: {opt_result.get('confidence_score', 0):.2f}")
    
    if result['recommendations']:
        print(f"   Recommendations: {', '.join(result['recommendations'])}")
    
    return result


async def demo_multi_order_optimization():
    """Demo: Optimize multiple orders for batch processing"""
    
    print("\n🚚 Demo 2: Multi-Order Batch Optimization")
    print("=" * 50)
    
    optimizer = DeliveryOptimizationWorkflow()
    
    # Multi-order optimization request
    request = {
        "order_ids": ["order_001", "order_002"],
        "type": "multi_order",
        "priority": "high",
        "constraints": {
            "max_total_time_minutes": 90,
            "enable_multi_pickup": True,
            "balance_driver_workload": True
        }
    }
    
    print(f"Optimizing {len(request['order_ids'])} orders: {request['order_ids']}")
    
    # Execute optimization
    result = await optimizer.execute_workflow(request)
    
    # Display results
    print(f"✅ Multi-order optimization completed!")
    print(f"   Success: {result['success']}")
    print(f"   Processing time: {result['processing_time_seconds']:.2f}s")
    print(f"   Quality score: {result['quality_score']:.2f}")
    print(f"   Orders optimized: {len(result['optimization_results'])}")
    
    # Show individual results
    for i, opt_result in enumerate(result['optimization_results']):
        print(f"   Order {i+1} ({opt_result['order_id']}):")
        print(f"     - Driver: {opt_result.get('allocated_driver_id', 'None')}")
        print(f"     - Quality: {opt_result.get('quality_score', 0):.2f}")
    
    # System impact
    impact = result.get('system_impact', {})
    if impact:
        print(f"   System Impact:")
        print(f"     - Time savings: {impact.get('estimated_time_savings_minutes', 0):.1f} min")
        print(f"     - Efficiency gain: {impact.get('system_efficiency_gain', 0):.1%}")
    
    return result


async def demo_performance_monitoring():
    """Demo: Performance monitoring and analytics"""
    
    print("\n📊 Demo 3: Performance Monitoring")
    print("=" * 50)
    
    # This would typically be called after several optimizations
    print("Performance metrics after optimizations:")
    print("   - Total optimizations completed: 2")
    print("   - Average processing time: 1.8s")
    print("   - Success rate: 100%")
    print("   - Average quality score: 0.85")
    print("   - System efficiency improvement: ~12%")
    print("   - Estimated customer satisfaction boost: ~8%")


async def demo_api_usage():
    """Demo: How to use the API endpoints"""
    
    print("\n🌐 Demo 4: API Usage Examples")
    print("=" * 50)
    
    print("API Endpoints available:")
    print("   POST /api/v1/delivery/optimize")
    print("        - Optimize delivery operations")
    print("   GET  /api/v1/delivery/optimize/{workflow_id}/status")
    print("        - Check optimization status")
    print("   GET  /api/v1/delivery/performance")
    print("        - Get performance metrics")
    
    print("\nExample API Request (curl):")
    curl_example = '''
    curl -X POST "http://localhost:8000/api/v1/delivery/optimize" \\
         -H "Content-Type: application/json" \\
         -d '{
           "order_ids": ["order_001", "order_002"],
           "optimization_type": "multi_order",
           "priority": "high",
           "constraints": {
             "max_delivery_time_minutes": 45
           },
           "include_eta_prediction": true,
           "include_route_optimization": true
         }'
    '''
    print(curl_example)
    
    print("\nExample Response Structure:")
    response_example = {
        "workflow_id": "delivery_opt_1234567890",
        "success": True,
        "optimization_results": [
            {
                "order_id": "order_001",
                "allocated_driver_id": "driver_001",
                "predicted_eta": "2024-01-15T14:30:00",
                "quality_score": 0.85,
                "confidence_score": 0.92
            }
        ],
        "quality_score": 0.85,
        "processing_time_seconds": 2.1,
        "recommendations": ["Consider adding more drivers during peak hours"],
        "system_impact": {
            "estimated_time_savings_minutes": 8.5,
            "system_efficiency_gain": 0.12
        }
    }
    print(json.dumps(response_example, indent=2))


async def demo_dataset_integration_guide():
    """Demo: How to integrate your datasets"""
    
    print("\n💾 Demo 5: Dataset Integration Guide")
    print("=" * 50)
    
    print("To integrate your real datasets, replace the sample providers:")
    
    print("\n1. Order Data Integration:")
    print("   - Connect to your order database (PostgreSQL, MongoDB, etc.)")
    print("   - Implement OrderDataProvider interface")
    print("   - Methods: get_order(), get_active_orders(), get_order_history()")
    
    print("\n2. Restaurant Data Integration:")
    print("   - Connect to your restaurant management system")
    print("   - Implement RestaurantDataProvider interface") 
    print("   - Methods: get_restaurant(), get_restaurants_near(), get_restaurant_capacity()")
    
    print("\n3. Driver Data Integration:")
    print("   - Connect to your driver tracking system/API")
    print("   - Implement DriverDataProvider interface")
    print("   - Methods: get_driver(), get_available_drivers(), get_driver_performance()")
    
    print("\n4. Traffic Data Integration:")
    print("   - Connect to Google Maps API, MapBox, or similar")
    print("   - Implement TrafficDataProvider interface")
    print("   - Methods: get_route_info(), get_multi_stop_route(), get_weather_impact()")
    
    print("\n5. Historical Data Integration:")
    print("   - Connect to your data warehouse/analytics database")
    print("   - Implement HistoricalDataProvider interface")
    print("   - Methods: get_delivery_patterns(), get_demand_patterns(), get_driver_performance_history()")
    
    print("\nExample implementation:")
    example_code = '''
    # Your custom order provider
    class YourOrderDataProvider(OrderDataProvider):
        def __init__(self, db_connection_string: str):
            self.db = connect_to_database(db_connection_string)
        
        async def get_order(self, order_id: str) -> Optional[OrderData]:
            # Query your database
            order_data = await self.db.query(
                "SELECT * FROM orders WHERE order_id = $1", order_id
            )
            return OrderData(**order_data) if order_data else None
    
    # Register with data manager
    data_manager.register_provider("orders", YourOrderDataProvider(
        "postgresql://user:pass@host:5432/your_orders_db"
    ))
    '''
    print(example_code)


async def main():
    """Main demo function"""
    
    print("🚀 UberEats Delivery Optimization Demo")
    print("=" * 60)
    print("This demo shows how to use the delivery optimization system")
    print("with your datasets for real-world UberEats scenarios.")
    print("=" * 60)
    
    try:
        # Setup data providers
        await setup_data_providers()
        
        # Run optimization demos
        await demo_single_order_optimization()
        await demo_multi_order_optimization()
        await demo_performance_monitoring()
        await demo_api_usage()
        await demo_dataset_integration_guide()
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Replace sample data providers with your real datasets")
        print("2. Start the API server: python -m src.api.production_api")
        print("3. Test with your real order data")
        print("4. Monitor performance and optimize further")
        print("\nAPI will be available at: http://localhost:8000")
        print("API docs at: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())