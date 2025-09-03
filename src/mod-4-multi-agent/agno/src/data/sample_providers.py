# src/data/sample_providers.py - Sample Data Providers (Replace with Your Datasets)
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
from geopy.distance import geodesic

from .interfaces import (
    OrderDataProvider, RestaurantDataProvider, DriverDataProvider, 
    TrafficDataProvider, HistoricalDataProvider,
    OrderData, RestaurantData, DriverData, TrafficData
)

class SampleOrderDataProvider(OrderDataProvider):
    """Sample order data provider - Replace with your order dataset"""
    
    def __init__(self):
        # Sample data - replace with your database/API connections
        self.orders = {}
        self.active_orders = []
        self._generate_sample_data()
    
    def _generate_sample_data(self):
        """Generate sample order data - replace with your data loading logic"""
        sample_orders = [
            {
                "order_id": "order_001",
                "customer_id": "customer_123",
                "restaurant_id": "restaurant_456",
                "items": [
                    {"name": "Margherita Pizza", "quantity": 1, "prep_time": 15},
                    {"name": "Coke", "quantity": 2, "prep_time": 1}
                ],
                "order_time": datetime.now() - timedelta(minutes=5),
                "total_amount": 24.99,
                "delivery_address": {
                    "lat": 37.7749,
                    "lng": -122.4194,
                    "address": "123 Market St, San Francisco, CA"
                },
                "payment_method": "credit_card",
                "status": "confirmed"
            },
            {
                "order_id": "order_002", 
                "customer_id": "customer_456",
                "restaurant_id": "restaurant_789",
                "items": [
                    {"name": "Chicken Burrito", "quantity": 1, "prep_time": 8},
                    {"name": "Guacamole", "quantity": 1, "prep_time": 2}
                ],
                "order_time": datetime.now() - timedelta(minutes=12),
                "total_amount": 18.50,
                "delivery_address": {
                    "lat": 37.7849,
                    "lng": -122.4094,
                    "address": "456 Mission St, San Francisco, CA"
                },
                "payment_method": "credit_card", 
                "status": "preparing"
            }
        ]
        
        for order_data in sample_orders:
            order = OrderData(**order_data)
            self.orders[order.order_id] = order
            if order.status in ["confirmed", "preparing", "ready"]:
                self.active_orders.append(order)
    
    async def is_available(self) -> bool:
        return True  # Sample provider is always available
    
    async def get_data(self, **kwargs) -> Any:
        return self.orders
    
    async def get_order(self, order_id: str) -> Optional[OrderData]:
        """Get order by ID - Connect to your order database here"""
        return self.orders.get(order_id)
    
    async def get_active_orders(self, restaurant_id: Optional[str] = None) -> List[OrderData]:
        """Get active orders - Connect to your order database here"""
        if restaurant_id:
            return [order for order in self.active_orders if order.restaurant_id == restaurant_id]
        return self.active_orders.copy()
    
    async def get_order_history(
        self, 
        customer_id: Optional[str] = None,
        restaurant_id: Optional[str] = None,
        hours_back: int = 24
    ) -> List[OrderData]:
        """Get historical orders - Connect to your historical data here"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        # Filter sample data
        historical_orders = []
        for order in self.orders.values():
            if order.order_time < cutoff_time:
                continue
            
            if customer_id and order.customer_id != customer_id:
                continue
            
            if restaurant_id and order.restaurant_id != restaurant_id:
                continue
            
            historical_orders.append(order)
        
        return historical_orders

class SampleRestaurantDataProvider(RestaurantDataProvider):
    """Sample restaurant data provider - Replace with your restaurant dataset"""
    
    def __init__(self):
        self.restaurants = {}
        self._generate_sample_data()
    
    def _generate_sample_data(self):
        """Generate sample restaurant data - replace with your data loading"""
        sample_restaurants = [
            {
                "restaurant_id": "restaurant_456",
                "name": "Tony's Pizza Palace",
                "address": {
                    "lat": 37.7849,
                    "lng": -122.4294,
                    "address": "789 Pizza Ave, San Francisco, CA"
                },
                "cuisine_type": "Italian",
                "average_prep_time": 18.5,
                "current_capacity": 0.7,  # 70% busy
                "rating": 4.5,
                "is_open": True,
                "menu_items": [
                    {"item_id": "pizza_001", "name": "Margherita Pizza", "prep_time": 15, "available": True},
                    {"item_id": "drink_001", "name": "Coke", "prep_time": 1, "available": True}
                ]
            },
            {
                "restaurant_id": "restaurant_789", 
                "name": "Burrito Express",
                "address": {
                    "lat": 37.7749,
                    "lng": -122.4394,
                    "address": "321 Burrito Blvd, San Francisco, CA"
                },
                "cuisine_type": "Mexican",
                "average_prep_time": 12.0,
                "current_capacity": 0.4,  # 40% busy
                "rating": 4.2,
                "is_open": True,
                "menu_items": [
                    {"item_id": "burrito_001", "name": "Chicken Burrito", "prep_time": 8, "available": True},
                    {"item_id": "side_001", "name": "Guacamole", "prep_time": 2, "available": True}
                ]
            }
        ]
        
        for restaurant_data in sample_restaurants:
            restaurant = RestaurantData(**restaurant_data)
            self.restaurants[restaurant.restaurant_id] = restaurant
    
    async def is_available(self) -> bool:
        return True
    
    async def get_data(self, **kwargs) -> Any:
        return self.restaurants
    
    async def get_restaurant(self, restaurant_id: str) -> Optional[RestaurantData]:
        """Get restaurant - Connect to your restaurant database here"""
        return self.restaurants.get(restaurant_id)
    
    async def get_restaurants_near(
        self, 
        location: Dict[str, float], 
        radius_km: float = 5.0
    ) -> List[RestaurantData]:
        """Get nearby restaurants - Connect to your geospatial data here"""
        nearby_restaurants = []
        user_location = (location["lat"], location["lng"])
        
        for restaurant in self.restaurants.values():
            restaurant_location = (
                restaurant.address["lat"], 
                restaurant.address["lng"]
            )
            distance = geodesic(user_location, restaurant_location).kilometers
            
            if distance <= radius_km:
                nearby_restaurants.append(restaurant)
        
        return nearby_restaurants
    
    async def get_restaurant_capacity(self, restaurant_id: str) -> Dict[str, Any]:
        """Get current restaurant capacity - Connect to your real-time kitchen data"""
        restaurant = self.restaurants.get(restaurant_id)
        if not restaurant:
            return {}
        
        # Simulate real-time capacity data
        current_orders = random.randint(3, 15)  # Replace with real queue length
        max_capacity = 20
        capacity_utilization = min(current_orders / max_capacity, 1.0)
        
        return {
            "restaurant_id": restaurant_id,
            "current_orders": current_orders,
            "max_capacity": max_capacity,
            "capacity_utilization": capacity_utilization,
            "estimated_wait_time": capacity_utilization * restaurant.average_prep_time,
            "accepting_orders": capacity_utilization < 0.9
        }
    
    async def get_average_prep_times(self, restaurant_id: str) -> Dict[str, float]:
        """Get prep times by menu item - Connect to your historical prep time data"""
        restaurant = self.restaurants.get(restaurant_id)
        if not restaurant:
            return {}
        
        prep_times = {}
        for item in restaurant.menu_items:
            prep_times[item["item_id"]] = item.get("prep_time", restaurant.average_prep_time)
        
        return prep_times

class SampleDriverDataProvider(DriverDataProvider):
    """Sample driver data provider - Replace with your driver dataset"""
    
    def __init__(self):
        self.drivers = {}
        self._generate_sample_data()
    
    def _generate_sample_data(self):
        """Generate sample driver data - replace with your driver data loading"""
        sample_drivers = [
            {
                "driver_id": "driver_001",
                "current_location": {"lat": 37.7749, "lng": -122.4194},
                "status": "available",
                "vehicle_type": "bike",
                "rating": 4.8,
                "current_orders": [],
                "max_concurrent_orders": 1
            },
            {
                "driver_id": "driver_002", 
                "current_location": {"lat": 37.7849, "lng": -122.4094},
                "status": "available",
                "vehicle_type": "scooter", 
                "rating": 4.6,
                "current_orders": [],
                "max_concurrent_orders": 2
            },
            {
                "driver_id": "driver_003",
                "current_location": {"lat": 37.7649, "lng": -122.4494},
                "status": "busy",
                "vehicle_type": "car",
                "rating": 4.9,
                "current_orders": ["order_003"],
                "max_concurrent_orders": 3,
                "estimated_availability": datetime.now() + timedelta(minutes=15)
            }
        ]
        
        for driver_data in sample_drivers:
            driver = DriverData(**driver_data)
            self.drivers[driver.driver_id] = driver
    
    async def is_available(self) -> bool:
        return True
    
    async def get_data(self, **kwargs) -> Any:
        return self.drivers
    
    async def get_driver(self, driver_id: str) -> Optional[DriverData]:
        """Get driver - Connect to your driver database/API here"""
        return self.drivers.get(driver_id)
    
    async def get_available_drivers(
        self, 
        location: Dict[str, float], 
        radius_km: float = 10.0
    ) -> List[DriverData]:
        """Get available drivers - Connect to your driver location system"""
        available_drivers = []
        user_location = (location["lat"], location["lng"])
        
        for driver in self.drivers.values():
            if driver.status != "available" and len(driver.current_orders) >= driver.max_concurrent_orders:
                continue
            
            driver_location = (
                driver.current_location["lat"],
                driver.current_location["lng"]
            )
            distance = geodesic(user_location, driver_location).kilometers
            
            if distance <= radius_km:
                available_drivers.append(driver)
        
        return available_drivers
    
    async def get_driver_performance(self, driver_id: str) -> Dict[str, Any]:
        """Get driver performance - Connect to your driver analytics"""
        driver = self.drivers.get(driver_id)
        if not driver:
            return {}
        
        # Simulate performance data - replace with real metrics
        return {
            "driver_id": driver_id,
            "average_delivery_time": random.uniform(20, 35),  # minutes
            "completion_rate": random.uniform(0.92, 0.99),
            "customer_rating": driver.rating,
            "total_deliveries": random.randint(500, 2000),
            "on_time_rate": random.uniform(0.85, 0.98)
        }
    
    async def update_driver_status(self, driver_id: str, status: str) -> bool:
        """Update driver status - Connect to your driver management system"""
        driver = self.drivers.get(driver_id)
        if driver:
            driver.status = status
            return True
        return False

class SampleTrafficDataProvider(TrafficDataProvider):
    """Sample traffic data provider - Replace with Google Maps/traffic APIs"""
    
    async def is_available(self) -> bool:
        return True
    
    async def get_data(self, **kwargs) -> Any:
        return {"provider": "sample_traffic"}
    
    async def get_route_info(
        self, 
        from_location: Dict[str, float],
        to_location: Dict[str, float],
        vehicle_type: str = "bike"
    ) -> TrafficData:
        """Get route info - Connect to Google Maps API or traffic service here"""
        
        # Calculate basic distance using geodesic
        from_point = (from_location["lat"], from_location["lng"])
        to_point = (to_location["lat"], to_location["lng"])
        distance_km = geodesic(from_point, to_point).kilometers
        
        # Simulate traffic conditions and time estimation
        # Replace this with real API calls to Google Maps, MapBox, etc.
        base_speed = {
            "bike": 15,      # km/h
            "scooter": 25,   # km/h  
            "car": 30        # km/h (city traffic)
        }.get(vehicle_type, 15)
        
        # Simulate traffic impact
        traffic_multiplier = random.uniform(1.1, 2.0)  # Traffic delay factor
        weather_multiplier = random.uniform(1.0, 1.3)  # Weather impact
        
        estimated_time_hours = (distance_km / base_speed) * traffic_multiplier * weather_multiplier
        estimated_time_minutes = estimated_time_hours * 60
        
        traffic_conditions = "low" if traffic_multiplier < 1.3 else "medium" if traffic_multiplier < 1.7 else "high"
        
        return TrafficData(
            from_location=from_location,
            to_location=to_location,
            estimated_time=estimated_time_minutes,
            distance=distance_km,
            traffic_conditions=traffic_conditions,
            weather_impact=weather_multiplier - 1.0,  # 0.0 to 0.3
            route_complexity="simple" if distance_km < 2 else "moderate" if distance_km < 5 else "complex"
        )
    
    async def get_multi_stop_route(
        self,
        stops: List[Dict[str, float]],
        vehicle_type: str = "bike"
    ) -> List[TrafficData]:
        """Get multi-stop route - Connect to route optimization service"""
        routes = []
        
        for i in range(len(stops) - 1):
            route = await self.get_route_info(stops[i], stops[i + 1], vehicle_type)
            routes.append(route)
        
        return routes
    
    async def get_weather_impact(self, location: Dict[str, float]) -> Dict[str, Any]:
        """Get weather impact - Connect to weather API"""
        # Simulate weather data - replace with real weather API
        weather_conditions = random.choice(["clear", "cloudy", "light_rain", "heavy_rain", "snow"])
        
        impact_multipliers = {
            "clear": 1.0,
            "cloudy": 1.05,
            "light_rain": 1.15,
            "heavy_rain": 1.4,
            "snow": 1.8
        }
        
        return {
            "location": location,
            "weather_condition": weather_conditions,
            "impact_multiplier": impact_multipliers[weather_conditions],
            "visibility": random.uniform(0.7, 1.0),
            "road_conditions": "good" if weather_conditions in ["clear", "cloudy"] else "poor"
        }

class SampleHistoricalDataProvider(HistoricalDataProvider):
    """Sample historical data provider - Replace with your analytics database"""
    
    async def is_available(self) -> bool:
        return True
    
    async def get_data(self, **kwargs) -> Any:
        return {"provider": "sample_historical"}
    
    async def get_delivery_patterns(
        self,
        time_period: str = "7d", 
        location: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """Get delivery patterns - Connect to your analytics database"""
        
        # Generate sample historical delivery data
        # Replace this with queries to your data warehouse/analytics DB
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='H')
        
        sample_data = []
        for date in dates:
            hour = date.hour
            day_of_week = date.weekday()
            
            # Simulate realistic delivery patterns
            base_deliveries = 50
            hour_multiplier = 1.5 if 11 <= hour <= 14 or 18 <= hour <= 21 else 0.5 if 6 <= hour <= 10 else 0.2
            weekend_multiplier = 1.2 if day_of_week >= 5 else 1.0
            
            delivery_count = int(base_deliveries * hour_multiplier * weekend_multiplier * random.uniform(0.8, 1.2))
            avg_time = random.uniform(20, 45)  # minutes
            
            sample_data.append({
                "timestamp": date,
                "hour": hour,
                "day_of_week": day_of_week,
                "delivery_count": delivery_count,
                "avg_delivery_time": avg_time,
                "success_rate": random.uniform(0.92, 0.99)
            })
        
        return pd.DataFrame(sample_data)
    
    async def get_demand_patterns(
        self,
        restaurant_id: Optional[str] = None,
        time_period: str = "30d"
    ) -> pd.DataFrame:
        """Get demand patterns - Connect to your demand forecasting data"""
        
        # Generate sample demand data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        
        sample_data = []
        for date in dates:
            day_of_week = date.weekday()
            
            # Simulate demand patterns
            base_demand = 100
            weekend_multiplier = 1.4 if day_of_week >= 5 else 1.0
            
            demand = int(base_demand * weekend_multiplier * random.uniform(0.7, 1.3))
            
            sample_data.append({
                "date": date,
                "restaurant_id": restaurant_id or "all",
                "demand": demand,
                "day_of_week": day_of_week,
                "peak_hour_start": 11 + random.randint(0, 2),
                "peak_hour_end": 13 + random.randint(0, 2)
            })
        
        return pd.DataFrame(sample_data)
    
    async def get_driver_performance_history(
        self,
        driver_id: Optional[str] = None,
        time_period: str = "30d"
    ) -> pd.DataFrame:
        """Get driver performance history - Connect to your driver analytics"""
        
        # Generate sample driver performance data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        
        sample_data = []
        for date in dates:
            sample_data.append({
                "date": date,
                "driver_id": driver_id or "sample_driver",
                "deliveries_completed": random.randint(8, 25),
                "avg_delivery_time": random.uniform(18, 35),
                "customer_rating": random.uniform(4.2, 4.9),
                "on_time_rate": random.uniform(0.85, 0.98),
                "total_distance_km": random.uniform(50, 150)
            })
        
        return pd.DataFrame(sample_data)

# Easy replacement functions for your real data
class DatasetConnector:
    """Helper class to easily connect your real datasets"""
    
    @staticmethod
    def connect_order_dataset(connection_string: str, table_name: str = "orders") -> OrderDataProvider:
        """
        Replace SampleOrderDataProvider with your real order dataset
        
        Example usage:
        order_provider = DatasetConnector.connect_order_dataset(
            "postgresql://user:pass@host:5432/dbname", 
            "orders_table"
        )
        """
        # TODO: Implement your real order data connection here
        # For now, return sample provider
        return SampleOrderDataProvider()
    
    @staticmethod
    def connect_restaurant_dataset(connection_string: str, table_name: str = "restaurants") -> RestaurantDataProvider:
        """Replace SampleRestaurantDataProvider with your real restaurant dataset"""
        # TODO: Implement your real restaurant data connection here
        return SampleRestaurantDataProvider()
    
    @staticmethod
    def connect_driver_dataset(api_endpoint: str, api_key: str) -> DriverDataProvider:
        """Replace SampleDriverDataProvider with your real driver dataset"""
        # TODO: Implement your real driver data connection here
        return SampleDriverDataProvider()
    
    @staticmethod
    def connect_traffic_api(api_key: str, provider: str = "google_maps") -> TrafficDataProvider:
        """Replace SampleTrafficDataProvider with real traffic API"""
        # TODO: Implement real traffic API connection (Google Maps, MapBox, etc.)
        return SampleTrafficDataProvider()
    
    @staticmethod
    def connect_historical_data(warehouse_connection: str) -> HistoricalDataProvider:
        """Replace SampleHistoricalDataProvider with your data warehouse"""
        # TODO: Implement your data warehouse connection here
        return SampleHistoricalDataProvider()