# src/data/interfaces.py - Data Integration Interfaces
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel
import pandas as pd

# Data Models for UberEats Ecosystem
class OrderData(BaseModel):
    """Order information structure"""
    order_id: str
    customer_id: str
    restaurant_id: str
    items: List[Dict[str, Any]]
    order_time: datetime
    total_amount: float
    delivery_address: Dict[str, Any]  # lat, lng, address
    special_instructions: Optional[str] = None
    payment_method: str
    status: str = "placed"

class RestaurantData(BaseModel):
    """Restaurant information structure"""
    restaurant_id: str
    name: str
    address: Dict[str, Any]  # lat, lng, address
    cuisine_type: str
    average_prep_time: float  # minutes
    current_capacity: float  # 0.0 to 1.0
    rating: float
    is_open: bool
    menu_items: List[Dict[str, Any]]

class DriverData(BaseModel):
    """Driver information structure"""
    driver_id: str
    current_location: Dict[str, float]  # lat, lng
    status: str  # available, busy, offline
    vehicle_type: str  # bike, scooter, car
    rating: float
    current_orders: List[str]
    max_concurrent_orders: int = 1
    estimated_availability: Optional[datetime] = None

class TrafficData(BaseModel):
    """Traffic and route information"""
    from_location: Dict[str, float]  # lat, lng
    to_location: Dict[str, float]  # lat, lng
    estimated_time: float  # minutes
    distance: float  # km
    traffic_conditions: str  # low, medium, high
    weather_impact: float  # 0.0 to 1.0 multiplier
    route_complexity: str  # simple, moderate, complex

class DeliveryPrediction(BaseModel):
    """Delivery time prediction result"""
    order_id: str
    predicted_eta: datetime
    confidence_interval: Dict[str, float]  # min, max minutes
    confidence_score: float  # 0.0 to 1.0
    key_factors: List[str]
    fallback_eta: datetime  # conservative estimate

# Abstract Data Provider Interfaces
class DataProvider(ABC):
    """Base interface for all data providers"""
    
    @abstractmethod
    async def get_data(self, **kwargs) -> Any:
        """Get data from the provider"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the data provider is available"""
        pass

class OrderDataProvider(DataProvider):
    """Interface for order data access"""
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[OrderData]:
        """Get order by ID"""
        pass
    
    @abstractmethod
    async def get_active_orders(self, restaurant_id: Optional[str] = None) -> List[OrderData]:
        """Get active orders, optionally filtered by restaurant"""
        pass
    
    @abstractmethod
    async def get_order_history(
        self, 
        customer_id: Optional[str] = None,
        restaurant_id: Optional[str] = None,
        hours_back: int = 24
    ) -> List[OrderData]:
        """Get historical orders"""
        pass

class RestaurantDataProvider(DataProvider):
    """Interface for restaurant data access"""
    
    @abstractmethod
    async def get_restaurant(self, restaurant_id: str) -> Optional[RestaurantData]:
        """Get restaurant information"""
        pass
    
    @abstractmethod
    async def get_restaurants_near(
        self, 
        location: Dict[str, float], 
        radius_km: float = 5.0
    ) -> List[RestaurantData]:
        """Get restaurants within radius"""
        pass
    
    @abstractmethod
    async def get_restaurant_capacity(self, restaurant_id: str) -> Dict[str, Any]:
        """Get current kitchen capacity and queue length"""
        pass
    
    @abstractmethod
    async def get_average_prep_times(self, restaurant_id: str) -> Dict[str, float]:
        """Get average preparation times by menu item"""
        pass

class DriverDataProvider(DataProvider):
    """Interface for driver data access"""
    
    @abstractmethod
    async def get_driver(self, driver_id: str) -> Optional[DriverData]:
        """Get driver information"""
        pass
    
    @abstractmethod
    async def get_available_drivers(
        self, 
        location: Dict[str, float], 
        radius_km: float = 10.0
    ) -> List[DriverData]:
        """Get available drivers near location"""
        pass
    
    @abstractmethod
    async def get_driver_performance(self, driver_id: str) -> Dict[str, Any]:
        """Get driver performance metrics"""
        pass
    
    @abstractmethod
    async def update_driver_status(self, driver_id: str, status: str) -> bool:
        """Update driver status"""
        pass

class TrafficDataProvider(DataProvider):
    """Interface for traffic and routing data"""
    
    @abstractmethod
    async def get_route_info(
        self, 
        from_location: Dict[str, float],
        to_location: Dict[str, float],
        vehicle_type: str = "bike"
    ) -> TrafficData:
        """Get route information including traffic"""
        pass
    
    @abstractmethod
    async def get_multi_stop_route(
        self,
        stops: List[Dict[str, float]],
        vehicle_type: str = "bike"
    ) -> List[TrafficData]:
        """Get optimized multi-stop route"""
        pass
    
    @abstractmethod
    async def get_weather_impact(self, location: Dict[str, float]) -> Dict[str, Any]:
        """Get weather impact on delivery times"""
        pass

class HistoricalDataProvider(DataProvider):
    """Interface for historical data analysis"""
    
    @abstractmethod
    async def get_delivery_patterns(
        self,
        time_period: str = "7d",
        location: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """Get historical delivery time patterns"""
        pass
    
    @abstractmethod
    async def get_demand_patterns(
        self,
        restaurant_id: Optional[str] = None,
        time_period: str = "30d"
    ) -> pd.DataFrame:
        """Get demand patterns by time/location"""
        pass
    
    @abstractmethod
    async def get_driver_performance_history(
        self,
        driver_id: Optional[str] = None,
        time_period: str = "30d"
    ) -> pd.DataFrame:
        """Get driver performance history"""
        pass

# Data Integration Manager
class DataIntegrationManager:
    """Manages all data providers and provides unified access"""
    
    def __init__(self):
        self.providers: Dict[str, DataProvider] = {}
        self.fallback_providers: Dict[str, DataProvider] = {}
    
    def register_provider(self, provider_type: str, provider: DataProvider):
        """Register a data provider"""
        self.providers[provider_type] = provider
    
    def register_fallback_provider(self, provider_type: str, provider: DataProvider):
        """Register a fallback data provider"""
        self.fallback_providers[provider_type] = provider
    
    async def get_provider(self, provider_type: str) -> Optional[DataProvider]:
        """Get an available provider"""
        primary_provider = self.providers.get(provider_type)
        
        if primary_provider and await primary_provider.is_available():
            return primary_provider
        
        fallback_provider = self.fallback_providers.get(provider_type)
        if fallback_provider and await fallback_provider.is_available():
            return fallback_provider
        
        return None
    
    async def get_order_data(self, order_id: str) -> Optional[OrderData]:
        """Get order data from available provider"""
        provider = await self.get_provider("orders")
        if isinstance(provider, OrderDataProvider):
            return await provider.get_order(order_id)
        return None
    
    async def get_restaurant_data(self, restaurant_id: str) -> Optional[RestaurantData]:
        """Get restaurant data from available provider"""
        provider = await self.get_provider("restaurants")
        if isinstance(provider, RestaurantDataProvider):
            return await provider.get_restaurant(restaurant_id)
        return None
    
    async def get_driver_data(self, driver_id: str) -> Optional[DriverData]:
        """Get driver data from available provider"""
        provider = await self.get_provider("drivers")
        if isinstance(provider, DriverDataProvider):
            return await provider.get_driver(driver_id)
        return None
    
    async def get_route_data(
        self, 
        from_location: Dict[str, float], 
        to_location: Dict[str, float],
        vehicle_type: str = "bike"
    ) -> Optional[TrafficData]:
        """Get route data from available provider"""
        provider = await self.get_provider("traffic")
        if isinstance(provider, TrafficDataProvider):
            return await provider.get_route_info(from_location, to_location, vehicle_type)
        return None

# Global data integration manager instance
data_manager = DataIntegrationManager()