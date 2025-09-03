# src/agents/driver_allocation_agent.py - Driver Allocation Intelligence
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from agno.agent import Agent

from .base_agent import UberEatsBaseAgent
from ..data.interfaces import data_manager, DriverData, OrderData, TrafficData


@dataclass
class DriverAllocation:
    """Driver allocation result"""
    driver_id: str
    order_id: str
    allocation_score: float
    estimated_pickup_time: datetime
    estimated_delivery_time: datetime
    reasoning: List[str]
    confidence: float


@dataclass
class AllocationStrategy:
    """Driver allocation strategy configuration"""
    prioritize_distance: bool = True
    prioritize_rating: bool = True
    consider_current_orders: bool = True
    balance_workload: bool = True
    max_detour_minutes: float = 10.0
    min_driver_rating: float = 4.0


class DriverAllocationAgent(UberEatsBaseAgent):
    """
    Intelligent driver allocation agent that optimizes assignments based on:
    - Distance and travel time
    - Driver ratings and performance
    - Current workload and capacity
    - Multi-order efficiency
    - Customer satisfaction predictions
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="driver_allocation_agent",
            instructions="""
            You are an expert driver allocation agent for UberEats.
            
            Your responsibilities:
            1. Find optimal driver assignments for new orders
            2. Balance efficiency, customer satisfaction, and driver fairness
            3. Consider multi-order pickups and deliveries
            4. Optimize for minimum total delivery time
            5. Account for driver performance and ratings
            6. Handle peak hours and high demand scenarios
            7. Continuously learn from allocation outcomes
            
            Key optimization factors:
            - Total travel distance and time
            - Driver ratings and performance history
            - Current driver workload and capacity
            - Route efficiency for multi-order scenarios
            - Customer wait time minimization
            - Driver utilization balance
            - Traffic conditions and real-time data
            
            Decision criteria:
            - Minimize customer wait time (primary)
            - Maximize driver efficiency
            - Maintain high service quality
            - Ensure fair driver workload distribution
            - Consider driver preferences and constraints
            
            Always provide detailed reasoning for allocation decisions.
            """,
            model_name="claude-sonnet-4",
            enable_reasoning=True,
            enable_memory=True,
            **kwargs
        )
        self.allocation_history = {}
        self.driver_performance_cache = {}
        self.strategy = AllocationStrategy()
    
    async def allocate_driver(
        self,
        order_id: str,
        restaurant_location: Dict[str, float],
        delivery_location: Dict[str, float],
        priority_level: str = "normal",  # normal, high, urgent
        strategy_override: Optional[AllocationStrategy] = None
    ) -> Optional[DriverAllocation]:
        """
        Find the best driver for an order
        """
        try:
            strategy = strategy_override or self.strategy
            
            # Get available drivers
            available_drivers = await self._get_available_drivers(restaurant_location)
            
            if not available_drivers:
                await self.log_structured({
                    "event": "no_drivers_available",
                    "order_id": order_id,
                    "restaurant_location": restaurant_location
                })
                return None
            
            # Evaluate each driver
            evaluations = []
            for driver in available_drivers:
                evaluation = await self._evaluate_driver_for_order(
                    driver, order_id, restaurant_location, delivery_location, strategy
                )
                if evaluation:
                    evaluations.append(evaluation)
            
            if not evaluations:
                return None
            
            # Select best driver using reasoning
            best_allocation = await self._select_best_driver(
                evaluations, order_id, priority_level
            )
            
            # Store allocation for learning
            if best_allocation:
                await self._store_allocation(best_allocation, strategy)
            
            return best_allocation
            
        except Exception as e:
            await self.log_structured({
                "event": "driver_allocation_error",
                "order_id": order_id,
                "error": str(e)
            })
            return None
    
    async def allocate_multiple_orders(
        self,
        orders: List[Dict[str, Any]],
        strategy_override: Optional[AllocationStrategy] = None
    ) -> List[DriverAllocation]:
        """
        Optimize driver allocation for multiple orders simultaneously
        """
        try:
            strategy = strategy_override or self.strategy
            allocations = []
            
            # Sort orders by priority and time
            sorted_orders = sorted(
                orders,
                key=lambda x: (
                    x.get("priority_level", "normal") == "urgent",
                    x.get("priority_level", "normal") == "high", 
                    x.get("order_time", datetime.now())
                )
            )
            
            # Get all available drivers
            all_locations = [order["restaurant_location"] for order in sorted_orders]
            center_location = self._calculate_center_location(all_locations)
            available_drivers = await self._get_available_drivers(center_location, radius_km=15.0)
            
            # Use reasoning to optimize global allocation
            allocation_request = {
                "task": "optimize_multi_order_allocation",
                "orders": sorted_orders,
                "available_drivers": [
                    {
                        "driver_id": d.driver_id,
                        "location": d.current_location,
                        "vehicle_type": d.vehicle_type,
                        "rating": d.rating,
                        "current_orders": d.current_orders,
                        "max_capacity": d.max_concurrent_orders
                    }
                    for d in available_drivers
                ],
                "strategy": strategy.__dict__
            }
            
            optimization_result = await self.run(allocation_request)
            
            # Create individual allocations based on optimization
            for order in sorted_orders:
                allocation = await self.allocate_driver(
                    order["order_id"],
                    order["restaurant_location"], 
                    order["delivery_location"],
                    order.get("priority_level", "normal"),
                    strategy
                )
                if allocation:
                    allocations.append(allocation)
            
            return allocations
            
        except Exception as e:
            await self.log_structured({
                "event": "multi_order_allocation_error",
                "error": str(e)
            })
            return []
    
    async def _get_available_drivers(
        self,
        location: Dict[str, float],
        radius_km: float = 10.0
    ) -> List[DriverData]:
        """Get available drivers near location"""
        try:
            provider = await data_manager.get_provider("drivers")
            if hasattr(provider, 'get_available_drivers'):
                drivers = await provider.get_available_drivers(location, radius_km)
                
                # Filter by minimum rating
                qualified_drivers = [
                    d for d in drivers 
                    if d.rating >= self.strategy.min_driver_rating
                ]
                
                return qualified_drivers
        except:
            pass
        
        return []
    
    async def _evaluate_driver_for_order(
        self,
        driver: DriverData,
        order_id: str,
        restaurant_location: Dict[str, float],
        delivery_location: Dict[str, float],
        strategy: AllocationStrategy
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a specific driver for an order"""
        
        # Get route information
        pickup_route = await data_manager.get_route_data(
            driver.current_location,
            restaurant_location,
            driver.vehicle_type
        )
        
        delivery_route = await data_manager.get_route_data(
            restaurant_location,
            delivery_location,
            driver.vehicle_type
        )
        
        if not pickup_route or not delivery_route:
            return None
        
        # Calculate timing
        current_time = datetime.now()
        pickup_time = current_time + timedelta(minutes=pickup_route.estimated_time)
        delivery_time = pickup_time + timedelta(minutes=delivery_route.estimated_time)
        
        # Check if driver can handle additional order
        if len(driver.current_orders) >= driver.max_concurrent_orders:
            return None
        
        # Calculate evaluation score
        score_components = await self._calculate_allocation_score(
            driver, pickup_route, delivery_route, strategy
        )
        
        # Get driver performance data
        performance_data = await self._get_driver_performance(driver.driver_id)
        
        return {
            "driver": driver,
            "pickup_route": pickup_route,
            "delivery_route": delivery_route,
            "pickup_time": pickup_time,
            "delivery_time": delivery_time,
            "score_components": score_components,
            "total_score": sum(score_components.values()),
            "performance_data": performance_data
        }
    
    async def _calculate_allocation_score(
        self,
        driver: DriverData,
        pickup_route: TrafficData,
        delivery_route: TrafficData,
        strategy: AllocationStrategy
    ) -> Dict[str, float]:
        """Calculate multi-factor allocation score"""
        
        scores = {}
        
        # Distance/Time score (0-100, higher is better)
        total_time = pickup_route.estimated_time + delivery_route.estimated_time
        time_score = max(0, 100 - (total_time - 20) * 2)  # Penalty after 20 minutes
        scores["time_efficiency"] = time_score * (0.4 if strategy.prioritize_distance else 0.2)
        
        # Driver rating score (0-100)
        rating_score = (driver.rating / 5.0) * 100
        scores["driver_quality"] = rating_score * (0.3 if strategy.prioritize_rating else 0.1)
        
        # Workload balance score (0-100)
        capacity_utilization = len(driver.current_orders) / driver.max_concurrent_orders
        balance_score = (1 - capacity_utilization) * 100
        scores["workload_balance"] = balance_score * (0.2 if strategy.balance_workload else 0.05)
        
        # Route efficiency score for multi-orders
        if driver.current_orders and strategy.consider_current_orders:
            efficiency_score = await self._calculate_route_efficiency_score(
                driver, pickup_route, delivery_route
            )
            scores["route_efficiency"] = efficiency_score * 0.15
        else:
            scores["route_efficiency"] = 50.0  # Neutral score
        
        # Traffic conditions penalty
        traffic_penalty = 0
        if pickup_route.traffic_conditions == "high":
            traffic_penalty += 10
        if delivery_route.traffic_conditions == "high":
            traffic_penalty += 10
        scores["traffic_conditions"] = max(0, 50 - traffic_penalty)
        
        # Weather impact penalty
        weather_penalty = (pickup_route.weather_impact + delivery_route.weather_impact) * 25
        scores["weather_conditions"] = max(0, 50 - weather_penalty)
        
        return scores
    
    async def _calculate_route_efficiency_score(
        self,
        driver: DriverData,
        pickup_route: TrafficData,
        delivery_route: TrafficData
    ) -> float:
        """Calculate how efficiently this order fits with current routes"""
        
        if not driver.current_orders:
            return 50.0  # Neutral score for first order
        
        # This would be more sophisticated in a real implementation
        # For now, simulate based on location proximity and timing
        base_score = 50.0
        
        # Bonus for orders in similar area (reduce total driving)
        total_distance = pickup_route.distance + delivery_route.distance
        if total_distance < 5.0:  # Within 5km total
            base_score += 20
        elif total_distance < 10.0:  # Within 10km
            base_score += 10
        
        # Penalty for complex routes
        if pickup_route.route_complexity == "complex" or delivery_route.route_complexity == "complex":
            base_score -= 15
        
        return min(100, max(0, base_score))
    
    async def _get_driver_performance(self, driver_id: str) -> Dict[str, Any]:
        """Get cached or fetch driver performance data"""
        
        if driver_id in self.driver_performance_cache:
            cached_data = self.driver_performance_cache[driver_id]
            # Use cache if less than 1 hour old
            if (datetime.now() - cached_data["timestamp"]).seconds < 3600:
                return cached_data["data"]
        
        # Fetch fresh performance data
        try:
            provider = await data_manager.get_provider("drivers")
            if hasattr(provider, 'get_driver_performance'):
                performance = await provider.get_driver_performance(driver_id)
                
                # Cache the result
                self.driver_performance_cache[driver_id] = {
                    "data": performance,
                    "timestamp": datetime.now()
                }
                
                return performance
        except:
            pass
        
        return {}
    
    async def _select_best_driver(
        self,
        evaluations: List[Dict[str, Any]],
        order_id: str,
        priority_level: str
    ) -> Optional[DriverAllocation]:
        """Use reasoning to select the best driver"""
        
        # Sort by total score
        evaluations.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Use reasoning for final decision
        reasoning_request = {
            "task": "select_best_driver_allocation",
            "order_id": order_id,
            "priority_level": priority_level,
            "top_candidates": evaluations[:3],  # Top 3 candidates
            "evaluation_criteria": [
                "Minimize total delivery time",
                "Ensure high service quality",
                "Balance driver workloads",
                "Consider traffic and weather"
            ]
        }
        
        reasoning_result = await self.run(reasoning_request)
        
        # Select the top candidate (reasoning can influence this)
        best_evaluation = evaluations[0]
        driver = best_evaluation["driver"]
        
        # Create allocation result
        allocation = DriverAllocation(
            driver_id=driver.driver_id,
            order_id=order_id,
            allocation_score=best_evaluation["total_score"],
            estimated_pickup_time=best_evaluation["pickup_time"],
            estimated_delivery_time=best_evaluation["delivery_time"],
            reasoning=self._create_allocation_reasoning(best_evaluation),
            confidence=min(1.0, best_evaluation["total_score"] / 100.0)
        )
        
        return allocation
    
    def _create_allocation_reasoning(self, evaluation: Dict[str, Any]) -> List[str]:
        """Create human-readable reasoning for the allocation"""
        reasoning = []
        
        driver = evaluation["driver"]
        scores = evaluation["score_components"]
        
        # Driver quality reasoning
        if scores.get("driver_quality", 0) > 80:
            reasoning.append(f"High-rated driver ({driver.rating}/5.0) ensures quality service")
        elif scores.get("driver_quality", 0) < 60:
            reasoning.append(f"Driver rating ({driver.rating}/5.0) meets minimum requirements")
        
        # Time efficiency reasoning
        total_time = evaluation["pickup_route"].estimated_time + evaluation["delivery_route"].estimated_time
        if total_time < 25:
            reasoning.append(f"Fast delivery route ({total_time:.1f} minutes total)")
        elif total_time > 40:
            reasoning.append(f"Longer route required ({total_time:.1f} minutes) but acceptable")
        
        # Workload reasoning
        current_orders = len(driver.current_orders)
        if current_orders == 0:
            reasoning.append("Driver available with no current orders")
        else:
            reasoning.append(f"Driver has {current_orders} current order(s), good capacity utilization")
        
        # Traffic/weather considerations
        pickup_route = evaluation["pickup_route"]
        if pickup_route.traffic_conditions == "high":
            reasoning.append("Heavy traffic considered in timing estimates")
        if pickup_route.weather_impact > 0.2:
            reasoning.append("Weather impact factored into delivery time")
        
        # Vehicle type advantage
        if driver.vehicle_type == "car" and total_time > 30:
            reasoning.append("Car delivery provides reliability for longer route")
        elif driver.vehicle_type == "bike" and total_time < 20:
            reasoning.append("Bike delivery optimal for short distance route")
        
        return reasoning
    
    def _calculate_center_location(self, locations: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate center point of multiple locations"""
        if not locations:
            return {"lat": 37.7749, "lng": -122.4194}  # SF default
        
        avg_lat = sum(loc["lat"] for loc in locations) / len(locations)
        avg_lng = sum(loc["lng"] for loc in locations) / len(locations)
        
        return {"lat": avg_lat, "lng": avg_lng}
    
    async def _store_allocation(
        self,
        allocation: DriverAllocation,
        strategy: AllocationStrategy
    ):
        """Store allocation for learning and monitoring"""
        self.allocation_history[allocation.order_id] = {
            "allocation": allocation,
            "strategy": strategy,
            "timestamp": datetime.now(),
            "outcome": None  # To be updated later
        }
        
        await self.log_structured({
            "event": "driver_allocated",
            "order_id": allocation.order_id,
            "driver_id": allocation.driver_id,
            "allocation_score": allocation.allocation_score,
            "confidence": allocation.confidence
        })
    
    async def update_allocation_outcome(
        self,
        order_id: str,
        actual_pickup_time: datetime,
        actual_delivery_time: datetime,
        customer_rating: Optional[float] = None
    ):
        """Update allocation with actual outcome for learning"""
        
        if order_id in self.allocation_history:
            allocation_info = self.allocation_history[order_id]
            allocation = allocation_info["allocation"]
            
            # Calculate accuracy
            pickup_accuracy = abs((actual_pickup_time - allocation.estimated_pickup_time).total_seconds() / 60)
            delivery_accuracy = abs((actual_delivery_time - allocation.estimated_delivery_time).total_seconds() / 60)
            
            outcome = {
                "actual_pickup_time": actual_pickup_time,
                "actual_delivery_time": actual_delivery_time,
                "pickup_accuracy_minutes": pickup_accuracy,
                "delivery_accuracy_minutes": delivery_accuracy,
                "customer_rating": customer_rating,
                "success": pickup_accuracy < 10 and delivery_accuracy < 15  # Within reasonable bounds
            }
            
            allocation_info["outcome"] = outcome
            
            await self.log_structured({
                "event": "allocation_outcome_updated",
                "order_id": order_id,
                "pickup_accuracy": pickup_accuracy,
                "delivery_accuracy": delivery_accuracy,
                "success": outcome["success"]
            })
    
    async def get_allocation_performance_stats(self) -> Dict[str, Any]:
        """Get allocation performance statistics"""
        
        completed_allocations = [
            info for info in self.allocation_history.values()
            if info.get("outcome") is not None
        ]
        
        if not completed_allocations:
            return {"message": "No completed allocations yet"}
        
        # Calculate statistics
        pickup_accuracies = [info["outcome"]["pickup_accuracy_minutes"] for info in completed_allocations]
        delivery_accuracies = [info["outcome"]["delivery_accuracy_minutes"] for info in completed_allocations]
        success_rate = sum(1 for info in completed_allocations if info["outcome"]["success"]) / len(completed_allocations)
        
        customer_ratings = [
            info["outcome"]["customer_rating"] 
            for info in completed_allocations 
            if info["outcome"]["customer_rating"] is not None
        ]
        
        stats = {
            "total_allocations": len(completed_allocations),
            "success_rate": success_rate,
            "average_pickup_accuracy_minutes": sum(pickup_accuracies) / len(pickup_accuracies),
            "average_delivery_accuracy_minutes": sum(delivery_accuracies) / len(delivery_accuracies),
            "median_pickup_accuracy_minutes": sorted(pickup_accuracies)[len(pickup_accuracies) // 2],
            "median_delivery_accuracy_minutes": sorted(delivery_accuracies)[len(delivery_accuracies) // 2]
        }
        
        if customer_ratings:
            stats["average_customer_rating"] = sum(customer_ratings) / len(customer_ratings)
        
        return stats
    
    async def optimize_driver_strategy(self) -> AllocationStrategy:
        """Optimize allocation strategy based on historical performance"""
        
        performance_stats = await self.get_allocation_performance_stats()
        
        if performance_stats.get("total_allocations", 0) < 10:
            return self.strategy  # Need more data
        
        # Analyze performance and adjust strategy
        optimization_request = {
            "task": "optimize_allocation_strategy",
            "current_strategy": self.strategy.__dict__,
            "performance_stats": performance_stats,
            "recent_allocations": list(self.allocation_history.values())[-20:]  # Last 20
        }
        
        optimization_result = await self.run(optimization_request)
        
        # Create optimized strategy (this would be more sophisticated in reality)
        optimized_strategy = AllocationStrategy(
            prioritize_distance=performance_stats.get("success_rate", 0.5) < 0.8,
            prioritize_rating=performance_stats.get("average_customer_rating", 4.0) < 4.2,
            consider_current_orders=True,
            balance_workload=True,
            max_detour_minutes=self.strategy.max_detour_minutes,
            min_driver_rating=max(3.5, self.strategy.min_driver_rating - 0.1) if performance_stats.get("success_rate", 0.5) < 0.7 else self.strategy.min_driver_rating
        )
        
        await self.log_structured({
            "event": "strategy_optimized",
            "old_strategy": self.strategy.__dict__,
            "new_strategy": optimized_strategy.__dict__
        })
        
        self.strategy = optimized_strategy
        return optimized_strategy