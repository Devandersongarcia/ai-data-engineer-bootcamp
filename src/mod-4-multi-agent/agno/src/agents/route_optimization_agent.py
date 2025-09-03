# src/agents/route_optimization_agent.py - Route Optimization Agent
import asyncio
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from agno.agent import Agent

from .base_agent import UberEatsBaseAgent
from ..data.interfaces import data_manager, TrafficData, DriverData, OrderData


@dataclass
class OptimizedRoute:
    """Optimized route result"""
    driver_id: str
    total_distance_km: float
    total_time_minutes: float
    stops: List[Dict[str, Any]]  # Ordered list of pickup/delivery stops
    efficiency_score: float
    fuel_savings_estimate: float
    time_savings_minutes: float
    route_complexity: str


@dataclass
class RouteStop:
    """Individual stop in a route"""
    stop_id: str
    stop_type: str  # "pickup" or "delivery"
    order_id: str
    location: Dict[str, float]
    estimated_arrival: datetime
    estimated_duration_minutes: float  # Time at stop
    priority: int  # 1 = highest priority


class RouteOptimizationAgent(UberEatsBaseAgent):
    """
    Advanced route optimization agent that handles:
    - Multi-order pickup and delivery sequencing
    - Real-time traffic optimization
    - Vehicle-specific route planning
    - Dynamic re-routing for delays
    - Fuel/time efficiency maximization
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="route_optimization_agent",
            instructions="""
            You are an expert route optimization agent for UberEats drivers.
            
            Your responsibilities:
            1. Optimize multi-stop routes for maximum efficiency
            2. Balance pickup timing with delivery freshness
            3. Minimize total travel time and distance
            4. Handle real-time traffic and weather conditions
            5. Optimize for different vehicle types (bike, scooter, car)
            6. Provide dynamic re-routing recommendations
            7. Maximize driver earnings through efficient routing
            
            Key optimization principles:
            - Hot food items should be delivered quickly after pickup
            - Group nearby pickups and deliveries when possible
            - Avoid backtracking and inefficient routing patterns
            - Consider traffic patterns and road conditions
            - Balance driver workload with customer satisfaction
            - Account for restaurant preparation times
            - Optimize for peak hours and demand patterns
            
            Route planning considerations:
            - Order priorities (VIP customers, time-sensitive items)
            - Restaurant pickup windows and prep times
            - Customer delivery preferences
            - Driver break schedules and shift limits
            - Vehicle capacity and speed limitations
            - Weather impact on different vehicle types
            
            Always provide detailed efficiency analysis and alternative routes.
            """,
            model_name="claude-sonnet-4",
            enable_reasoning=True,
            enable_memory=True,
            **kwargs
        )
        self.route_history = {}
        self.optimization_cache = {}
    
    async def optimize_route(
        self,
        driver_id: str,
        new_orders: List[str],
        current_route: Optional[List[Dict[str, Any]]] = None,
        optimization_goals: List[str] = None
    ) -> OptimizedRoute:
        """
        Optimize route for a driver with new orders
        """
        try:
            # Default optimization goals
            if optimization_goals is None:
                optimization_goals = [
                    "minimize_total_time",
                    "maximize_food_freshness", 
                    "minimize_distance",
                    "balance_workload"
                ]
            
            # Gather required data
            driver_data = await data_manager.get_driver_data(driver_id)
            if not driver_data:
                raise ValueError(f"Driver {driver_id} not found")
            
            # Get order details
            orders_data = []
            for order_id in new_orders:
                order = await data_manager.get_order_data(order_id)
                if order:
                    orders_data.append(order)
            
            if not orders_data:
                raise ValueError("No valid orders to optimize")
            
            # Get current route stops
            current_stops = current_route or []
            
            # Build optimization request
            optimization_data = await self._prepare_optimization_data(
                driver_data, orders_data, current_stops, optimization_goals
            )
            
            # Use reasoning for route optimization
            optimization_request = {
                "task": "optimize_delivery_route",
                "driver_info": {
                    "driver_id": driver_id,
                    "location": driver_data.current_location,
                    "vehicle_type": driver_data.vehicle_type,
                    "current_orders": driver_data.current_orders,
                    "max_capacity": driver_data.max_concurrent_orders
                },
                "orders": [self._order_to_dict(order) for order in orders_data],
                "current_route": current_stops,
                "optimization_goals": optimization_goals,
                "constraints": await self._get_routing_constraints()
            }
            
            reasoning_result = await self.run(optimization_request)
            
            # Create optimized route
            optimized_route = await self._build_optimized_route(
                driver_data, orders_data, optimization_data, reasoning_result
            )
            
            # Cache and store result
            await self._store_route_optimization(driver_id, optimized_route)
            
            return optimized_route
            
        except Exception as e:
            await self.log_structured({
                "event": "route_optimization_error",
                "driver_id": driver_id,
                "orders": new_orders,
                "error": str(e)
            })
            
            # Return fallback route
            return await self._create_fallback_route(driver_id, new_orders)
    
    async def optimize_multi_driver_routes(
        self,
        driver_orders: Dict[str, List[str]],  # driver_id -> order_ids
        global_optimization: bool = True
    ) -> Dict[str, OptimizedRoute]:
        """
        Optimize routes for multiple drivers simultaneously
        """
        try:
            optimized_routes = {}
            
            if global_optimization:
                # Global optimization considering inter-driver transfers
                global_request = {
                    "task": "global_route_optimization",
                    "driver_orders": driver_orders,
                    "optimization_type": "system_wide_efficiency"
                }
                
                global_result = await self.run(global_request)
            
            # Optimize each driver's route
            for driver_id, order_ids in driver_orders.items():
                route = await self.optimize_route(driver_id, order_ids)
                optimized_routes[driver_id] = route
            
            return optimized_routes
            
        except Exception as e:
            await self.log_structured({
                "event": "multi_driver_optimization_error",
                "error": str(e)
            })
            return {}
    
    async def _prepare_optimization_data(
        self,
        driver: DriverData,
        orders: List[OrderData],
        current_stops: List[Dict[str, Any]],
        goals: List[str]
    ) -> Dict[str, Any]:
        """Prepare all data needed for route optimization"""
        
        # Get restaurant locations and prep times
        restaurant_data = {}
        for order in orders:
            if order.restaurant_id not in restaurant_data:
                restaurant = await data_manager.get_restaurant_data(order.restaurant_id)
                restaurant_data[order.restaurant_id] = restaurant
        
        # Calculate all route segments
        route_segments = await self._calculate_route_segments(
            driver, orders, restaurant_data
        )
        
        # Get traffic and weather data
        traffic_data = await self._get_traffic_data_for_routes(route_segments)
        
        # Analyze current time context
        time_context = self._analyze_time_context()
        
        return {
            "driver": driver,
            "orders": orders,
            "restaurants": restaurant_data,
            "route_segments": route_segments,
            "traffic_data": traffic_data,
            "time_context": time_context,
            "current_stops": current_stops,
            "optimization_goals": goals
        }
    
    async def _calculate_route_segments(
        self,
        driver: DriverData,
        orders: List[OrderData],
        restaurants: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate all possible route segments"""
        
        segments = []
        all_locations = []
        
        # Add driver's current location
        all_locations.append({
            "id": f"driver_{driver.driver_id}",
            "type": "driver_location",
            "location": driver.current_location
        })
        
        # Add restaurant pickup locations
        for order in orders:
            restaurant = restaurants.get(order.restaurant_id)
            if restaurant:
                all_locations.append({
                    "id": f"pickup_{order.order_id}",
                    "type": "pickup",
                    "order_id": order.order_id,
                    "restaurant_id": order.restaurant_id,
                    "location": restaurant.address,
                    "prep_time": restaurant.average_prep_time,
                    "items": order.items
                })
        
        # Add delivery locations
        for order in orders:
            all_locations.append({
                "id": f"delivery_{order.order_id}",
                "type": "delivery",
                "order_id": order.order_id,
                "location": order.delivery_address,
                "priority": self._calculate_order_priority(order)
            })
        
        # Calculate distances and times between all location pairs
        for i, from_loc in enumerate(all_locations):
            for j, to_loc in enumerate(all_locations):
                if i != j:
                    route_info = await data_manager.get_route_data(
                        from_loc["location"],
                        to_loc["location"],
                        driver.vehicle_type
                    )
                    
                    if route_info:
                        segments.append({
                            "from": from_loc,
                            "to": to_loc,
                            "route_info": route_info,
                            "priority": to_loc.get("priority", 5)
                        })
        
        return segments
    
    def _calculate_order_priority(self, order: OrderData) -> int:
        """Calculate order priority (1=highest, 10=lowest)"""
        priority = 5  # Default
        
        # VIP customers or special orders
        if hasattr(order, 'customer_type') and order.customer_type == 'vip':
            priority = 1
        
        # Time-sensitive items (hot food should be delivered quickly)
        hot_items = ['pizza', 'burger', 'hot', 'soup', 'coffee']
        if any(any(keyword in item.get('name', '').lower() for keyword in hot_items) 
               for item in order.items):
            priority = min(priority, 3)
        
        # Order age (older orders get higher priority)
        order_age = (datetime.now() - order.order_time).total_seconds() / 60  # minutes
        if order_age > 30:
            priority = min(priority, 2)
        elif order_age > 15:
            priority = min(priority, 4)
        
        return priority
    
    async def _get_traffic_data_for_routes(
        self,
        route_segments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get traffic data for all route segments"""
        
        traffic_summary = {
            "overall_conditions": "medium",
            "high_traffic_routes": [],
            "weather_impact": 0.0,
            "peak_hour_multiplier": 1.0
        }
        
        # Analyze traffic conditions
        high_traffic_count = 0
        total_weather_impact = 0.0
        
        for segment in route_segments:
            route_info = segment.get("route_info")
            if route_info:
                if route_info.traffic_conditions == "high":
                    high_traffic_count += 1
                    traffic_summary["high_traffic_routes"].append(segment)
                
                total_weather_impact += route_info.weather_impact
        
        # Calculate overall conditions
        if len(route_segments) > 0:
            high_traffic_ratio = high_traffic_count / len(route_segments)
            if high_traffic_ratio > 0.6:
                traffic_summary["overall_conditions"] = "high"
            elif high_traffic_ratio < 0.2:
                traffic_summary["overall_conditions"] = "low"
            
            traffic_summary["weather_impact"] = total_weather_impact / len(route_segments)
        
        # Peak hour analysis
        current_hour = datetime.now().hour
        if current_hour in [11, 12, 13, 18, 19, 20, 21]:  # Peak hours
            traffic_summary["peak_hour_multiplier"] = 1.3
        
        return traffic_summary
    
    def _analyze_time_context(self) -> Dict[str, Any]:
        """Analyze current time context for optimization"""
        now = datetime.now()
        
        return {
            "current_hour": now.hour,
            "day_of_week": now.weekday(),
            "is_weekend": now.weekday() >= 5,
            "is_lunch_rush": 11 <= now.hour <= 14,
            "is_dinner_rush": 17 <= now.hour <= 21,
            "is_late_night": now.hour >= 22 or now.hour <= 6
        }
    
    async def _get_routing_constraints(self) -> Dict[str, Any]:
        """Get routing constraints and preferences"""
        
        return {
            "max_route_time_minutes": 90,  # Maximum total route time
            "max_food_wait_time_minutes": 30,  # Max time food waits after pickup
            "max_stops_per_route": 6,  # Maximum stops in a single route
            "min_stop_duration_minutes": 2,  # Minimum time at each stop
            "vehicle_constraints": {
                "bike": {"max_distance_km": 15, "weather_sensitive": True},
                "scooter": {"max_distance_km": 25, "weather_sensitive": False},
                "car": {"max_distance_km": 50, "weather_sensitive": False}
            }
        }
    
    def _order_to_dict(self, order: OrderData) -> Dict[str, Any]:
        """Convert order to dictionary for reasoning"""
        return {
            "order_id": order.order_id,
            "restaurant_id": order.restaurant_id,
            "customer_id": order.customer_id,
            "items": order.items,
            "order_time": order.order_time.isoformat(),
            "total_amount": order.total_amount,
            "delivery_address": order.delivery_address,
            "special_instructions": order.special_instructions,
            "status": order.status
        }
    
    async def _build_optimized_route(
        self,
        driver: DriverData,
        orders: List[OrderData],
        optimization_data: Dict[str, Any],
        reasoning_result: str
    ) -> OptimizedRoute:
        """Build the optimized route from reasoning result"""
        
        # Create route stops (this would be more sophisticated in reality)
        stops = []
        total_distance = 0.0
        total_time = 0.0
        current_time = datetime.now()
        
        # Start from driver location
        current_location = driver.current_location
        
        # Simple optimization: pickup all orders, then deliver by priority
        # In reality, this would be much more sophisticated
        
        # Phase 1: Pickups
        pickup_stops = []
        for order in orders:
            restaurant = optimization_data["restaurants"].get(order.restaurant_id)
            if restaurant:
                # Calculate route to restaurant
                route_to_restaurant = None
                for segment in optimization_data["route_segments"]:
                    if (segment["from"]["type"] == "driver_location" and
                        segment["to"]["order_id"] == order.order_id and
                        segment["to"]["type"] == "pickup"):
                        route_to_restaurant = segment["route_info"]
                        break
                
                if route_to_restaurant:
                    current_time += timedelta(minutes=route_to_restaurant.estimated_time)
                    total_distance += route_to_restaurant.distance
                    total_time += route_to_restaurant.estimated_time
                    
                    pickup_stops.append(RouteStop(
                        stop_id=f"pickup_{order.order_id}",
                        stop_type="pickup",
                        order_id=order.order_id,
                        location=restaurant.address,
                        estimated_arrival=current_time,
                        estimated_duration_minutes=3.0,  # Standard pickup time
                        priority=self._calculate_order_priority(order)
                    ))
                    
                    current_time += timedelta(minutes=3)
                    current_location = restaurant.address
        
        # Phase 2: Deliveries (sorted by priority)
        delivery_stops = []
        for order in sorted(orders, key=lambda x: self._calculate_order_priority(x)):
            # Find route from current location to delivery
            delivery_route = None
            for segment in optimization_data["route_segments"]:
                if (segment["to"]["order_id"] == order.order_id and
                    segment["to"]["type"] == "delivery"):
                    delivery_route = segment["route_info"]
                    break
            
            if delivery_route:
                current_time += timedelta(minutes=delivery_route.estimated_time)
                total_distance += delivery_route.distance
                total_time += delivery_route.estimated_time
                
                delivery_stops.append(RouteStop(
                    stop_id=f"delivery_{order.order_id}",
                    stop_type="delivery", 
                    order_id=order.order_id,
                    location=order.delivery_address,
                    estimated_arrival=current_time,
                    estimated_duration_minutes=2.0,  # Standard delivery time
                    priority=self._calculate_order_priority(order)
                ))
                
                current_time += timedelta(minutes=2)
                current_location = order.delivery_address
        
        # Combine stops
        all_stops = pickup_stops + delivery_stops
        
        # Calculate efficiency metrics
        efficiency_score = self._calculate_route_efficiency(
            all_stops, total_distance, total_time
        )
        
        # Estimate savings (compared to individual deliveries)
        baseline_time = len(orders) * 25  # 25 minutes per individual delivery
        time_savings = max(0, baseline_time - total_time)
        
        return OptimizedRoute(
            driver_id=driver.driver_id,
            total_distance_km=total_distance,
            total_time_minutes=total_time,
            stops=[{
                "stop_id": stop.stop_id,
                "stop_type": stop.stop_type,
                "order_id": stop.order_id,
                "location": stop.location,
                "estimated_arrival": stop.estimated_arrival.isoformat(),
                "estimated_duration_minutes": stop.estimated_duration_minutes,
                "priority": stop.priority
            } for stop in all_stops],
            efficiency_score=efficiency_score,
            fuel_savings_estimate=max(0, (baseline_time - total_time) * 0.5),  # Rough estimate
            time_savings_minutes=time_savings,
            route_complexity="moderate" if len(all_stops) > 4 else "simple"
        )
    
    def _calculate_route_efficiency(
        self,
        stops: List[RouteStop],
        total_distance: float,
        total_time: float
    ) -> float:
        """Calculate route efficiency score (0-100)"""
        
        base_score = 50.0
        
        # Efficiency based on stops per distance
        if total_distance > 0:
            stops_per_km = len(stops) / total_distance
            if stops_per_km > 0.5:  # More than 0.5 stops per km is good
                base_score += 20
            elif stops_per_km < 0.2:  # Less than 0.2 stops per km is inefficient
                base_score -= 15
        
        # Time efficiency (should be less than 15 minutes per stop)
        if len(stops) > 0:
            time_per_stop = total_time / len(stops)
            if time_per_stop < 12:
                base_score += 15
            elif time_per_stop > 20:
                base_score -= 20
        
        # Priority handling (higher priority orders first gets bonus)
        if len(stops) > 1:
            delivery_stops = [s for s in stops if s.stop_type == "delivery"]
            if delivery_stops:
                priorities = [s.priority for s in delivery_stops]
                if priorities == sorted(priorities):  # Delivered in priority order
                    base_score += 15
        
        return max(0, min(100, base_score))
    
    async def _store_route_optimization(
        self,
        driver_id: str,
        route: OptimizedRoute
    ):
        """Store route optimization for learning"""
        
        self.route_history[f"{driver_id}_{datetime.now().isoformat()}"] = {
            "route": route,
            "timestamp": datetime.now(),
            "actual_performance": None  # To be updated later
        }
        
        await self.log_structured({
            "event": "route_optimized",
            "driver_id": driver_id,
            "total_distance_km": route.total_distance_km,
            "total_time_minutes": route.total_time_minutes,
            "efficiency_score": route.efficiency_score,
            "stops_count": len(route.stops)
        })
    
    async def _create_fallback_route(
        self,
        driver_id: str,
        order_ids: List[str]
    ) -> OptimizedRoute:
        """Create a simple fallback route"""
        
        return OptimizedRoute(
            driver_id=driver_id,
            total_distance_km=20.0,  # Rough estimate
            total_time_minutes=60.0,  # Conservative estimate
            stops=[],
            efficiency_score=30.0,  # Low efficiency for fallback
            fuel_savings_estimate=0.0,
            time_savings_minutes=0.0,
            route_complexity="unknown"
        )
    
    async def update_route_performance(
        self,
        route_id: str,
        actual_total_time: float,
        actual_total_distance: float,
        completed_stops: List[Dict[str, Any]],
        driver_feedback: Optional[str] = None
    ):
        """Update route with actual performance data"""
        
        # Find the route in history
        route_entry = None
        for key, entry in self.route_history.items():
            if key.startswith(route_id):
                route_entry = entry
                break
        
        if route_entry:
            predicted_time = route_entry["route"].total_time_minutes
            predicted_distance = route_entry["route"].total_distance_km
            
            time_accuracy = abs(actual_total_time - predicted_time)
            distance_accuracy = abs(actual_total_distance - predicted_distance)
            
            performance = {
                "actual_total_time": actual_total_time,
                "actual_total_distance": actual_total_distance,
                "time_accuracy_minutes": time_accuracy,
                "distance_accuracy_km": distance_accuracy,
                "completed_stops": completed_stops,
                "driver_feedback": driver_feedback,
                "success": time_accuracy < 15 and distance_accuracy < 5  # Within reasonable bounds
            }
            
            route_entry["actual_performance"] = performance
            
            await self.log_structured({
                "event": "route_performance_updated",
                "route_id": route_id,
                "time_accuracy": time_accuracy,
                "distance_accuracy": distance_accuracy,
                "success": performance["success"]
            })
    
    async def get_route_optimization_stats(self) -> Dict[str, Any]:
        """Get route optimization performance statistics"""
        
        completed_routes = [
            entry for entry in self.route_history.values()
            if entry.get("actual_performance") is not None
        ]
        
        if not completed_routes:
            return {"message": "No completed routes yet"}
        
        # Calculate statistics
        time_accuracies = [entry["actual_performance"]["time_accuracy_minutes"] for entry in completed_routes]
        distance_accuracies = [entry["actual_performance"]["distance_accuracy_km"] for entry in completed_routes]
        success_rate = sum(1 for entry in completed_routes if entry["actual_performance"]["success"]) / len(completed_routes)
        
        # Calculate efficiency improvements
        predicted_times = [entry["route"].total_time_minutes for entry in completed_routes]
        actual_times = [entry["actual_performance"]["actual_total_time"] for entry in completed_routes]
        
        return {
            "total_optimized_routes": len(completed_routes),
            "success_rate": success_rate,
            "average_time_accuracy_minutes": sum(time_accuracies) / len(time_accuracies),
            "average_distance_accuracy_km": sum(distance_accuracies) / len(distance_accuracies),
            "average_predicted_time": sum(predicted_times) / len(predicted_times),
            "average_actual_time": sum(actual_times) / len(actual_times),
            "average_efficiency_score": sum(entry["route"].efficiency_score for entry in completed_routes) / len(completed_routes)
        }
    
    async def reoptimize_route_realtime(
        self,
        driver_id: str,
        current_route: OptimizedRoute,
        delays: List[Dict[str, Any]] = None,
        new_traffic_data: Dict[str, Any] = None
    ) -> OptimizedRoute:
        """Re-optimize route in real-time based on delays or new information"""
        
        try:
            reoptimization_request = {
                "task": "realtime_route_reoptimization",
                "driver_id": driver_id,
                "current_route": {
                    "stops": current_route.stops,
                    "total_time": current_route.total_time_minutes,
                    "efficiency_score": current_route.efficiency_score
                },
                "delays": delays or [],
                "traffic_updates": new_traffic_data or {},
                "current_time": datetime.now().isoformat()
            }
            
            reasoning_result = await self.run(reoptimization_request)
            
            # Create reoptimized route (simplified for this example)
            # In reality, this would involve complex re-calculation
            reoptimized_route = OptimizedRoute(
                driver_id=current_route.driver_id,
                total_distance_km=current_route.total_distance_km * 1.1,  # Slightly longer due to delays
                total_time_minutes=current_route.total_time_minutes + sum(delay.get("minutes", 0) for delay in (delays or [])),
                stops=current_route.stops,  # Could be reordered
                efficiency_score=max(0, current_route.efficiency_score - 10),  # Reduced due to delays
                fuel_savings_estimate=current_route.fuel_savings_estimate,
                time_savings_minutes=max(0, current_route.time_savings_minutes - 5),
                route_complexity=current_route.route_complexity
            )
            
            await self.log_structured({
                "event": "route_reoptimized",
                "driver_id": driver_id,
                "delay_minutes": sum(delay.get("minutes", 0) for delay in (delays or [])),
                "new_total_time": reoptimized_route.total_time_minutes
            })
            
            return reoptimized_route
            
        except Exception as e:
            await self.log_structured({
                "event": "realtime_reoptimization_error",
                "driver_id": driver_id,
                "error": str(e)
            })
            return current_route  # Return original route on error