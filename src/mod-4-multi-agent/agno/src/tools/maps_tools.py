# src/tools/maps_tools.py - Maps and Weather Tools for UberEats Agents
import logging
import requests
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from agno.tools import Function
from pydantic import BaseModel, Field
from geopy.distance import geodesic

from ..config.settings import settings

logger = logging.getLogger(__name__)


class RouteInput(BaseModel):
    """Input schema for route calculations"""
    origin: str = Field(..., description="Origin address or coordinates (lat,lng)")
    destination: str = Field(..., description="Destination address or coordinates (lat,lng)")
    mode: str = Field(default="driving", description="Travel mode: driving, walking, bicycling, transit")
    optimize: bool = Field(default=True, description="Whether to optimize for traffic")
    alternatives: bool = Field(default=False, description="Return alternative routes")


class GeocodeInput(BaseModel):
    """Input schema for geocoding"""
    address: str = Field(..., description="Address to geocode")
    reverse: bool = Field(default=False, description="Whether this is reverse geocoding (lat,lng to address)")


class WeatherInput(BaseModel):
    """Input schema for weather data"""
    location: str = Field(..., description="Location for weather data (city name or lat,lng)")
    units: str = Field(default="metric", description="Units: metric, imperial, kelvin")
    forecast: bool = Field(default=False, description="Whether to get forecast or current weather")


class GoogleMapsTool(Function):
    """
    Google Maps integration for routing and geocoding
    
    Enables agents to:
    - Calculate optimal routes with real-time traffic
    - Get accurate travel time estimates  
    - Geocode addresses to coordinates
    - Find nearby restaurants or delivery locations
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="google_maps_tool",
            description="Get routing, directions, and geocoding data from Google Maps",
            input_schema=RouteInput
        )
        self.api_key = api_key or getattr(settings, 'google_maps_api_key', None)
        self.base_url = "https://maps.googleapis.com/maps/api"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Google Maps API request"""
        try:
            # Determine operation type based on input
            if "origin" in input_data and "destination" in input_data:
                return self._get_directions(input_data)
            elif "address" in input_data:
                return self._geocode_address(input_data)
            else:
                return {
                    "success": False,
                    "error": "Invalid input: provide either (origin, destination) for directions or (address) for geocoding"
                }
                
        except Exception as e:
            logger.error(f"Google Maps API error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_directions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get directions between two points"""
        route_input = RouteInput(**input_data)
        
        if not self.api_key:
            # Simulate Google Maps response for demo
            return self._simulate_directions_response(route_input)
        
        # In production, use Google Maps Directions API:
        # url = f"{self.base_url}/directions/json"
        # params = {
        #     "origin": route_input.origin,
        #     "destination": route_input.destination,
        #     "mode": route_input.mode,
        #     "departure_time": "now",
        #     "traffic_model": "best_guess",
        #     "alternatives": route_input.alternatives,
        #     "key": self.api_key
        # }
        # 
        # response = requests.get(url, params=params)
        # data = response.json()
        
        return self._simulate_directions_response(route_input)
    
    def _simulate_directions_response(self, route_input: RouteInput) -> Dict[str, Any]:
        """Simulate Google Maps directions response"""
        # Parse coordinates if provided
        try:
            if "," in route_input.origin:
                origin_lat, origin_lng = map(float, route_input.origin.split(","))
            else:
                # Mock coordinates for common addresses
                origin_lat, origin_lng = 37.7749, -122.4194  # San Francisco
            
            if "," in route_input.destination:
                dest_lat, dest_lng = map(float, route_input.destination.split(","))
            else:
                dest_lat, dest_lng = 37.7849, -122.4094  # Slightly different location
        except:
            origin_lat, origin_lng = 37.7749, -122.4194
            dest_lat, dest_lng = 37.7849, -122.4094
        
        # Calculate distance using geodesic
        distance_km = geodesic((origin_lat, origin_lng), (dest_lat, dest_lng)).kilometers
        
        # Estimate travel time based on mode
        speed_kmh = {
            "driving": 30,  # City driving with traffic
            "walking": 5,
            "bicycling": 15,
            "transit": 20
        }.get(route_input.mode, 30)
        
        duration_minutes = (distance_km / speed_kmh) * 60
        
        # Add traffic multiplier if optimizing
        if route_input.optimize and route_input.mode == "driving":
            traffic_multiplier = 1.3  # 30% slower due to traffic
            duration_minutes *= traffic_multiplier
        
        return {
            "success": True,
            "origin": route_input.origin,
            "destination": route_input.destination,
            "distance": {
                "value": int(distance_km * 1000),  # meters
                "text": f"{distance_km:.1f} km"
            },
            "duration": {
                "value": int(duration_minutes * 60),  # seconds  
                "text": f"{int(duration_minutes)} mins"
            },
            "duration_in_traffic": {
                "value": int(duration_minutes * 60),
                "text": f"{int(duration_minutes)} mins"
            },
            "traffic_conditions": "moderate",
            "polyline": "mock_polyline_data",
            "provider": "google_maps_simulation"
        }
    
    def _geocode_address(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Geocode an address to coordinates"""
        geocode_input = GeocodeInput(**input_data)
        
        # Simulate geocoding response
        if not geocode_input.reverse:
            # Address to coordinates
            return {
                "success": True,
                "address": geocode_input.address,
                "geometry": {
                    "location": {
                        "lat": 37.7749,
                        "lng": -122.4194
                    }
                },
                "formatted_address": f"{geocode_input.address}, San Francisco, CA, USA",
                "place_id": f"mock_place_id_{hash(geocode_input.address)}",
                "provider": "google_maps_simulation"
            }
        else:
            # Coordinates to address
            return {
                "success": True,
                "coordinates": geocode_input.address,
                "formatted_address": "123 Market St, San Francisco, CA 94103, USA",
                "address_components": {
                    "street_number": "123",
                    "route": "Market St",
                    "locality": "San Francisco",
                    "administrative_area_level_1": "CA",
                    "postal_code": "94103",
                    "country": "USA"
                },
                "provider": "google_maps_simulation"
            }


class WeatherTool(Function):
    """
    Weather data tool for delivery optimization
    
    Enables agents to:
    - Check weather conditions affecting deliveries
    - Adjust ETA predictions for rain/snow
    - Alert about severe weather impacts
    - Optimize driver assignments based on weather
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="weather_tool",
            description="Get current weather and forecast data for delivery optimization",
            input_schema=WeatherInput
        )
        self.api_key = api_key or getattr(settings, 'weather_api_key', None)
        self.base_url = "http://api.openweathermap.org/data/2.5"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather data"""
        try:
            weather_input = WeatherInput(**input_data)
            
            if not self.api_key:
                return self._simulate_weather_response(weather_input)
            
            # In production, use OpenWeatherMap API:
            # endpoint = "forecast" if weather_input.forecast else "weather"
            # url = f"{self.base_url}/{endpoint}"
            # 
            # params = {
            #     "q": weather_input.location,
            #     "appid": self.api_key,
            #     "units": weather_input.units
            # }
            # 
            # response = requests.get(url, params=params)
            # data = response.json()
            
            return self._simulate_weather_response(weather_input)
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _simulate_weather_response(self, weather_input: WeatherInput) -> Dict[str, Any]:
        """Simulate weather API response"""
        import random
        
        conditions = ["clear", "partly_cloudy", "cloudy", "light_rain", "heavy_rain", "snow"]
        current_condition = random.choice(conditions[:4])  # Bias toward better weather
        
        # Weather impact on delivery times
        delivery_impact = {
            "clear": 1.0,
            "partly_cloudy": 1.05,
            "cloudy": 1.1,
            "light_rain": 1.2,
            "heavy_rain": 1.5,
            "snow": 1.8
        }
        
        temp = random.randint(15, 25) if weather_input.units == "metric" else random.randint(59, 77)
        
        base_response = {
            "success": True,
            "location": weather_input.location,
            "current": {
                "temperature": temp,
                "condition": current_condition,
                "description": current_condition.replace("_", " ").title(),
                "humidity": random.randint(40, 80),
                "wind_speed": round(random.uniform(5, 20), 1),
                "visibility": random.randint(8, 10) if current_condition in ["clear", "partly_cloudy"] else random.randint(3, 7)
            },
            "delivery_impact": {
                "multiplier": delivery_impact[current_condition],
                "severity": "low" if delivery_impact[current_condition] <= 1.1 else "medium" if delivery_impact[current_condition] <= 1.3 else "high",
                "recommendations": self._get_weather_recommendations(current_condition)
            },
            "units": weather_input.units,
            "provider": "weather_simulation"
        }
        
        if weather_input.forecast:
            # Add 5-day forecast
            base_response["forecast"] = []
            for i in range(5):
                day_condition = random.choice(conditions[:4])
                base_response["forecast"].append({
                    "day": i + 1,
                    "condition": day_condition,
                    "temp_high": temp + random.randint(-3, 3),
                    "temp_low": temp + random.randint(-8, -2),
                    "delivery_impact_multiplier": delivery_impact[day_condition]
                })
        
        return base_response
    
    def _get_weather_recommendations(self, condition: str) -> List[str]:
        """Get delivery recommendations based on weather"""
        recommendations = {
            "clear": ["Optimal delivery conditions"],
            "partly_cloudy": ["Good delivery conditions", "Monitor cloud cover"],
            "cloudy": ["Acceptable conditions", "Prepare for possible rain"],
            "light_rain": ["Increase delivery time estimates by 20%", "Advise drivers to drive carefully"],
            "heavy_rain": ["Increase delivery time estimates by 50%", "Consider delaying non-urgent deliveries"],
            "snow": ["Increase delivery time estimates by 80%", "Use only experienced drivers", "Consider temporary service suspension"]
        }
        return recommendations.get(condition, ["Monitor weather conditions"])


# Pre-configured tool instances
google_maps_tool = GoogleMapsTool()
weather_tool = WeatherTool()

# Utility functions for common operations
def calculate_delivery_time_with_weather(base_time_minutes: float, weather_condition: str) -> float:
    """Calculate adjusted delivery time based on weather"""
    multipliers = {
        "clear": 1.0,
        "partly_cloudy": 1.05,
        "cloudy": 1.1,
        "light_rain": 1.2,
        "heavy_rain": 1.5,
        "snow": 1.8
    }
    return base_time_minutes * multipliers.get(weather_condition, 1.0)

def get_optimal_vehicle_for_weather(weather_condition: str) -> Dict[str, Any]:
    """Recommend optimal vehicle type based on weather"""
    recommendations = {
        "clear": {"preferred": ["bike", "scooter", "car"], "avoid": []},
        "partly_cloudy": {"preferred": ["bike", "scooter", "car"], "avoid": []},
        "cloudy": {"preferred": ["scooter", "car"], "avoid": []},
        "light_rain": {"preferred": ["car", "scooter"], "avoid": ["bike"]},
        "heavy_rain": {"preferred": ["car"], "avoid": ["bike", "scooter"]},
        "snow": {"preferred": ["car"], "avoid": ["bike", "scooter"]}
    }
    return recommendations.get(weather_condition, {"preferred": ["car"], "avoid": ["bike", "scooter"]})