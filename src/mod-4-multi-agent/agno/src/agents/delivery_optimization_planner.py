"""
Delivery Optimization Planner - Strategic planning for optimal delivery operations
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base_agent import UberEatsBaseAgent
from ..observability.langfuse_config import observe_ubereats_operation

logger = logging.getLogger(__name__)


@dataclass
class DeliveryPlan:
    """Comprehensive delivery optimization plan"""
    plan_id: str
    order_ids: List[str]
    strategy: str  # "single_order", "batch_optimization", "peak_hour_optimization"
    priority_score: float
    estimated_total_time: float
    estimated_cost: float
    efficiency_rating: str  # "high", "medium", "low"
    recommendations: List[str]
    constraints: List[str]
    fallback_options: List[Dict[str, Any]]
    created_at: datetime


@dataclass
class OptimizationContext:
    """Context for delivery optimization decisions"""
    current_time: datetime
    weather_conditions: str
    traffic_status: str
    driver_availability: int
    restaurant_capacity: Dict[str, float]
    order_volume: str  # "low", "medium", "high"
    special_events: List[str]


class DeliveryOptimizationPlanner(UberEatsBaseAgent):
    """
    Strategic planner that creates optimal delivery plans by analyzing:
    - Order patterns and priorities
    - Resource availability (drivers, restaurants)
    - External conditions (traffic, weather)
    - Business constraints and objectives
    
    Focus: High-level strategic planning, not execution details
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="delivery_optimization_planner",
            instructions="Delivery optimization planner initialized. Loading dynamic instructions...",
            enable_reasoning=True,
            enable_memory=True,
            **kwargs
        )
        
        # Initialize with dynamic prompt
        self._initialize_dynamic_instructions()
        
        self.active_plans = {}
        self.optimization_metrics = {
            "plans_created": 0,
            "avg_efficiency_score": 0.0,
            "successful_optimizations": 0,
            "total_time_saved": 0.0
        }
    
    def _initialize_dynamic_instructions(self):
        """Load instructions from Langfuse prompt management"""
        try:
            self.update_instructions_from_prompt("delivery_optimization_planner", {
                "context": "UberEats delivery optimization system",
                "role": "Strategic planner for delivery operations"
            })
            logger.debug("Delivery optimization planner instructions updated from dynamic prompt")
        except Exception as e:
            logger.warning(f"Failed to load dynamic instructions, using fallback: {e}")
    
    @observe_ubereats_operation(
        operation_type="delivery_planning",
        include_args=True,
        include_result=True,
        capture_metrics=True
    )
    async def create_delivery_plan(
        self,
        orders: List[Dict[str, Any]],
        context: OptimizationContext
    ) -> DeliveryPlan:
        """
        Create strategic delivery plan for given orders and context
        """
        try:
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Analyze orders and determine optimization strategy
            strategy = self._determine_optimization_strategy(orders, context)
            
            # Calculate priority score based on business rules
            priority_score = self._calculate_priority_score(orders, context)
            
            # Estimate plan metrics
            time_estimate = await self._estimate_total_time(orders, strategy, context)
            cost_estimate = self._estimate_total_cost(orders, strategy)
            efficiency_rating = self._rate_efficiency(time_estimate, cost_estimate, len(orders))
            
            # Generate recommendations
            recommendations = self._generate_recommendations(orders, context, strategy)
            
            # Identify constraints
            constraints = self._identify_constraints(orders, context)
            
            # Create fallback options
            fallback_options = self._create_fallback_options(orders, context)
            
            plan = DeliveryPlan(
                plan_id=plan_id,
                order_ids=[order.get("id", f"order_{i}") for i, order in enumerate(orders)],
                strategy=strategy,
                priority_score=priority_score,
                estimated_total_time=time_estimate,
                estimated_cost=cost_estimate,
                efficiency_rating=efficiency_rating,
                recommendations=recommendations,
                constraints=constraints,
                fallback_options=fallback_options,
                created_at=datetime.now()
            )
            
            # Store plan for tracking
            self.active_plans[plan_id] = plan
            self.optimization_metrics["plans_created"] += 1
            
            logger.info(f"Created delivery plan {plan_id} with strategy: {strategy}")
            return plan
            
        except Exception as e:
            logger.error(f"Error creating delivery plan: {e}")
            return self._create_fallback_plan(orders)
    
    def _determine_optimization_strategy(
        self,
        orders: List[Dict[str, Any]],
        context: OptimizationContext
    ) -> str:
        """Determine the best optimization strategy for given orders and context"""
        
        # Single order - simple strategy
        if len(orders) == 1:
            return "single_order"
        
        # Peak hours - batch optimization for efficiency
        if context.order_volume == "high" or context.current_time.hour in [12, 13, 18, 19, 20]:
            return "peak_hour_optimization"
        
        # Multiple orders with good conditions - batch optimization
        if len(orders) <= 5 and context.driver_availability > 2:
            return "batch_optimization"
        
        # Default to single order processing for complex scenarios
        return "single_order"
    
    def _calculate_priority_score(
        self,
        orders: List[Dict[str, Any]],
        context: OptimizationContext
    ) -> float:
        """Calculate priority score (0.0-1.0) based on business rules"""
        base_score = 0.5
        
        # Higher priority for premium customers
        if any(order.get("customer_tier") == "premium" for order in orders):
            base_score += 0.2
        
        # Higher priority for time-sensitive orders
        if any(order.get("special_instructions", "").lower().find("urgent") != -1 for order in orders):
            base_score += 0.15
        
        # Lower priority during low-demand periods
        if context.order_volume == "low":
            base_score -= 0.1
        
        # Weather and traffic adjustments
        if context.weather_conditions in ["rain", "snow"]:
            base_score += 0.1
        if context.traffic_status == "heavy":
            base_score += 0.05
        
        return min(1.0, max(0.0, base_score))
    
    async def _estimate_total_time(
        self,
        orders: List[Dict[str, Any]],
        strategy: str,
        context: OptimizationContext
    ) -> float:
        """Estimate total time for delivery plan execution"""
        
        if strategy == "single_order":
            # Simple estimation for single orders
            return 30.0 + (5.0 * len(orders))  # Base + per order
        
        elif strategy == "batch_optimization":
            # More complex estimation for batched orders
            base_time = 25.0  # Efficient batching reduces base time
            per_order_time = 12.0  # Shared travel time
            return base_time + (per_order_time * len(orders))
        
        elif strategy == "peak_hour_optimization":
            # Peak hour adjustments
            base_time = 35.0  # Higher base due to congestion
            per_order_time = 15.0  # Longer per-order time
            return base_time + (per_order_time * len(orders))
        
        return 40.0  # Fallback
    
    def _estimate_total_cost(self, orders: List[Dict[str, Any]], strategy: str) -> float:
        """Estimate total cost for delivery plan"""
        base_cost = 2.99  # Base delivery fee
        
        if strategy == "batch_optimization":
            # Cost savings from batching
            return base_cost + (1.50 * len(orders))
        elif strategy == "peak_hour_optimization":
            # Higher costs during peak
            return base_cost + (2.50 * len(orders))
        else:
            # Standard pricing
            return base_cost + (1.99 * len(orders))
    
    def _rate_efficiency(self, time_estimate: float, cost_estimate: float, order_count: int) -> str:
        """Rate the efficiency of the delivery plan"""
        efficiency_score = order_count / (time_estimate * 0.01 + cost_estimate * 0.1)
        
        if efficiency_score > 2.0:
            return "high"
        elif efficiency_score > 1.0:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(
        self,
        orders: List[Dict[str, Any]],
        context: OptimizationContext,
        strategy: str
    ) -> List[str]:
        """Generate actionable recommendations for the delivery plan"""
        recommendations = []
        
        if strategy == "batch_optimization":
            recommendations.append("Batch orders by geographic proximity")
            recommendations.append("Coordinate pickup times to minimize driver wait")
        
        if context.traffic_status == "heavy":
            recommendations.append("Use alternative routes to avoid traffic")
            recommendations.append("Consider bike/scooter delivery for short distances")
        
        if context.weather_conditions in ["rain", "snow"]:
            recommendations.append("Add weather delay buffer to ETA")
            recommendations.append("Prioritize covered vehicle types")
        
        if context.driver_availability < len(orders):
            recommendations.append("Consider delayed scheduling for some orders")
            recommendations.append("Alert supervisor about driver shortage")
        
        return recommendations
    
    def _identify_constraints(
        self,
        orders: List[Dict[str, Any]],
        context: OptimizationContext
    ) -> List[str]:
        """Identify constraints that limit optimization options"""
        constraints = []
        
        if context.driver_availability < len(orders):
            constraints.append(f"Limited drivers: {context.driver_availability} available for {len(orders)} orders")
        
        # Check for special dietary requirements
        special_orders = [o for o in orders if o.get("special_instructions", "").lower().find("allergy") != -1]
        if special_orders:
            constraints.append(f"Special handling required for {len(special_orders)} orders with dietary restrictions")
        
        # Distance constraints
        long_distance_orders = [o for o in orders if o.get("distance_km", 0) > 15]
        if long_distance_orders:
            constraints.append(f"{len(long_distance_orders)} orders exceed standard delivery radius")
        
        return constraints
    
    def _create_fallback_options(
        self,
        orders: List[Dict[str, Any]],
        context: OptimizationContext
    ) -> List[Dict[str, Any]]:
        """Create fallback options if primary plan fails"""
        fallbacks = []
        
        # Option 1: Sequential single-order processing
        fallbacks.append({
            "strategy": "sequential_single_order",
            "description": "Process orders one by one if batching fails",
            "estimated_time": 45.0 * len(orders),
            "trade_offs": ["Higher individual delivery time", "Lower driver utilization", "More predictable"]
        })
        
        # Option 2: Delayed batch processing
        if len(orders) > 1:
            fallbacks.append({
                "strategy": "delayed_batch",
                "description": "Wait for more drivers or better conditions",
                "estimated_time": self._estimate_total_time(orders, "batch_optimization", context) + 15,
                "trade_offs": ["Delayed start", "Better resource utilization", "Risk of further delays"]
            })
        
        return fallbacks
    
    def _create_fallback_plan(self, orders: List[Dict[str, Any]]) -> DeliveryPlan:
        """Create basic fallback plan when optimization fails"""
        return DeliveryPlan(
            plan_id=f"fallback_{datetime.now().strftime('%H%M%S')}",
            order_ids=[order.get("id", f"order_{i}") for i, order in enumerate(orders)],
            strategy="single_order",
            priority_score=0.5,
            estimated_total_time=40.0 * len(orders),
            estimated_cost=2.99 + (1.99 * len(orders)),
            efficiency_rating="low",
            recommendations=["Use basic single-order processing", "Monitor for optimization opportunities"],
            constraints=["Optimization failed - using safe fallback"],
            fallback_options=[],
            created_at=datetime.now()
        )
    
    @observe_ubereats_operation(
        operation_type="plan_analysis",
        include_args=True,
        include_result=True,
        capture_metrics=True
    )
    async def analyze_plan_performance(self, plan_id: str, actual_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how well a delivery plan performed vs predictions"""
        if plan_id not in self.active_plans:
            return {"error": f"Plan {plan_id} not found"}
        
        plan = self.active_plans[plan_id]
        
        # Compare predictions vs actual results
        actual_time = actual_results.get("actual_delivery_time", 0)
        actual_cost = actual_results.get("actual_cost", 0)
        
        time_accuracy = abs(plan.estimated_total_time - actual_time) / plan.estimated_total_time
        cost_accuracy = abs(plan.estimated_cost - actual_cost) / plan.estimated_cost
        
        analysis = {
            "plan_id": plan_id,
            "strategy_used": plan.strategy,
            "time_prediction_accuracy": 1.0 - time_accuracy,
            "cost_prediction_accuracy": 1.0 - cost_accuracy,
            "overall_success": actual_results.get("success", False),
            "lessons_learned": [],
            "recommendations_for_future": []
        }
        
        # Generate lessons learned
        if time_accuracy > 0.2:
            analysis["lessons_learned"].append(f"Time estimation was off by {time_accuracy*100:.1f}%")
        if cost_accuracy > 0.15:
            analysis["lessons_learned"].append(f"Cost estimation was off by {cost_accuracy*100:.1f}%")
        
        # Update metrics
        if actual_results.get("success", False):
            self.optimization_metrics["successful_optimizations"] += 1
        
        logger.info(f"Plan {plan_id} analysis complete: {analysis['time_prediction_accuracy']:.2f} time accuracy")
        return analysis
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get current optimization performance statistics"""
        total_plans = self.optimization_metrics["plans_created"]
        success_rate = (
            self.optimization_metrics["successful_optimizations"] / max(1, total_plans)
        ) * 100
        
        return {
            "total_plans_created": total_plans,
            "successful_optimizations": self.optimization_metrics["successful_optimizations"],
            "success_rate": f"{success_rate:.1f}%",
            "active_plans": len(self.active_plans),
            "average_efficiency": self.optimization_metrics["avg_efficiency_score"],
            "total_time_saved_minutes": self.optimization_metrics["total_time_saved"]
        }