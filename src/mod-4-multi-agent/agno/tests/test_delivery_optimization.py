#!/usr/bin/env python3
"""
Test script for delivery optimization system
Demonstrates the planner/supervisor architecture with realistic scenarios
"""
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.delivery_optimization_planner import (
    DeliveryOptimizationPlanner, 
    OptimizationContext
)
from src.agents.delivery_process_supervisor import (
    DeliveryProcessSupervisor
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeliveryOptimizationDemo:
    """Demo class showcasing the delivery optimization system"""
    
    def __init__(self):
        self.planner = None
        self.supervisor = None
        self.mock_agents = {}
    
    async def initialize(self):
        """Initialize the optimization system"""
        logger.info("🚀 Initializing Delivery Optimization System")
        
        # Initialize planner and supervisor
        self.planner = DeliveryOptimizationPlanner()
        self.supervisor = DeliveryProcessSupervisor()
        
        # Create mock specialized agents for demo
        self.mock_agents = {
            "eta_prediction": MockETAAgent(),
            "driver_allocation": MockDriverAgent(),
            "route_optimization": MockRouteAgent()
        }
        
        logger.info("✅ System initialized successfully")
    
    async def run_scenarios(self):
        """Run different delivery optimization scenarios"""
        logger.info("\n📋 Running Delivery Optimization Scenarios")
        print("=" * 80)
        
        # Scenario 1: Single Order (Simple)
        await self.scenario_single_order()
        
        # Scenario 2: Batch Orders (Medium complexity)  
        await self.scenario_batch_orders()
        
        # Scenario 3: Peak Hour Rush (High complexity)
        await self.scenario_peak_hour_rush()
        
        # Show final statistics
        self.show_system_statistics()
    
    async def scenario_single_order(self):
        """Scenario 1: Single order optimization"""
        print("\n🏪 Scenario 1: Single Order Optimization")
        print("-" * 50)
        
        # Create sample order
        orders = [
            {
                "id": "order_001",
                "customer_id": "customer_123",
                "restaurant_id": "restaurant_456", 
                "items": [{"name": "Burger Combo", "prep_time": 8}],
                "delivery_address": {"lat": 37.7749, "lng": -122.4194},
                "customer_tier": "standard",
                "distance_km": 3.2
            }
        ]
        
        # Create context for current conditions
        context = OptimizationContext(
            current_time=datetime.now(),
            weather_conditions="clear",
            traffic_status="light",
            driver_availability=5,
            restaurant_capacity={"restaurant_456": 0.3},
            order_volume="low",
            special_events=[]
        )
        
        # Step 1: Create delivery plan
        print("📝 Creating delivery plan...")
        plan = await self.planner.create_delivery_plan(orders, context)
        
        print(f"   ✅ Plan created: {plan.plan_id}")
        print(f"   📊 Strategy: {plan.strategy}")
        print(f"   ⏱️ Estimated time: {plan.estimated_total_time:.1f} minutes")
        print(f"   💰 Estimated cost: ${plan.estimated_cost:.2f}")
        print(f"   🎯 Efficiency: {plan.efficiency_rating}")
        print(f"   📋 Recommendations: {len(plan.recommendations)}")
        
        # Step 2: Execute the plan
        print("\n🔄 Executing delivery plan...")
        execution = await self.supervisor.execute_delivery_plan(plan, self.mock_agents)
        
        print(f"   ✅ Execution completed: {execution.status.value}")
        print(f"   📈 Success rate: {execution.success_metrics['step_success_rate']:.1f}%")
        print(f"   ⏱️ Actual time: {execution.total_duration_seconds:.2f}s")
        print(f"   🔧 Steps executed: {execution.success_metrics['successful_steps']}/{execution.success_metrics['total_steps']}")
    
    async def scenario_batch_orders(self):
        """Scenario 2: Batch order optimization"""
        print("\n📦 Scenario 2: Batch Order Optimization")
        print("-" * 50)
        
        # Create multiple orders for batching
        orders = [
            {
                "id": "order_002", 
                "customer_id": "customer_124",
                "restaurant_id": "restaurant_456",
                "items": [{"name": "Pizza", "prep_time": 12}],
                "delivery_address": {"lat": 37.7849, "lng": -122.4094},
                "distance_km": 2.8
            },
            {
                "id": "order_003",
                "customer_id": "customer_125", 
                "restaurant_id": "restaurant_457",
                "items": [{"name": "Sushi Roll", "prep_time": 6}],
                "delivery_address": {"lat": 37.7649, "lng": -122.4294},
                "distance_km": 4.1
            },
            {
                "id": "order_004",
                "customer_id": "customer_126",
                "restaurant_id": "restaurant_456",
                "items": [{"name": "Salad Bowl", "prep_time": 5}],
                "delivery_address": {"lat": 37.7749, "lng": -122.4094}, 
                "distance_km": 2.5
            }
        ]
        
        context = OptimizationContext(
            current_time=datetime.now(),
            weather_conditions="light_rain",
            traffic_status="medium",
            driver_availability=3,
            restaurant_capacity={"restaurant_456": 0.6, "restaurant_457": 0.4},
            order_volume="medium",
            special_events=[]
        )
        
        # Create and execute plan
        print("📝 Creating batch optimization plan...")
        plan = await self.planner.create_delivery_plan(orders, context)
        
        print(f"   ✅ Plan created: {plan.plan_id}")
        print(f"   📊 Strategy: {plan.strategy}")
        print(f"   🎯 Priority score: {plan.priority_score:.2f}")
        print(f"   ⏱️ Estimated time: {plan.estimated_total_time:.1f} minutes")
        print(f"   💰 Estimated cost: ${plan.estimated_cost:.2f}")
        print(f"   📋 Constraints: {len(plan.constraints)}")
        
        if plan.recommendations:
            print(f"   💡 Top recommendation: {plan.recommendations[0]}")
        
        print("\n🔄 Executing batch optimization...")
        execution = await self.supervisor.execute_delivery_plan(plan, self.mock_agents)
        
        print(f"   ✅ Execution: {execution.status.value}")
        print(f"   📈 Success rate: {execution.success_metrics['step_success_rate']:.1f}%") 
        print(f"   ⏱️ Duration: {execution.total_duration_seconds:.2f}s")
        
        # Monitor execution progress (demo)
        monitoring_result = await self.supervisor.monitor_execution(execution.execution_id)
        print(f"   📊 Final progress: {monitoring_result['progress_percent']:.1f}%")
    
    async def scenario_peak_hour_rush(self):
        """Scenario 3: Peak hour optimization"""
        print("\n🚨 Scenario 3: Peak Hour Rush Optimization")
        print("-" * 50)
        
        # Create high-priority orders during peak time
        orders = [
            {
                "id": "order_005",
                "customer_id": "customer_127", 
                "restaurant_id": "restaurant_458",
                "items": [{"name": "Dinner Special", "prep_time": 15}],
                "delivery_address": {"lat": 37.7949, "lng": -122.3994},
                "customer_tier": "premium",
                "special_instructions": "urgent delivery requested",
                "distance_km": 5.2
            },
            {
                "id": "order_006",
                "customer_id": "customer_128",
                "restaurant_id": "restaurant_459", 
                "items": [{"name": "Family Meal", "prep_time": 18}],
                "delivery_address": {"lat": 37.7549, "lng": -122.4394},
                "distance_km": 6.8
            }
        ]
        
        context = OptimizationContext(
            current_time=datetime.now().replace(hour=19, minute=30),  # Peak dinner time
            weather_conditions="clear",
            traffic_status="heavy",
            driver_availability=1,  # Limited drivers
            restaurant_capacity={"restaurant_458": 0.9, "restaurant_459": 0.8},  # Busy kitchens
            order_volume="high",
            special_events=["local_event_downtown"]
        )
        
        print("📝 Creating peak hour optimization plan...")
        plan = await self.planner.create_delivery_plan(orders, context)
        
        print(f"   ✅ Plan created: {plan.plan_id}")
        print(f"   📊 Strategy: {plan.strategy}")
        print(f"   🚨 Priority score: {plan.priority_score:.2f} (high)")
        print(f"   ⏱️ Estimated time: {plan.estimated_total_time:.1f} minutes")
        print(f"   ⚠️ Constraints identified: {len(plan.constraints)}")
        
        for constraint in plan.constraints:
            print(f"      • {constraint}")
        
        print(f"   🔄 Fallback options: {len(plan.fallback_options)}")
        
        print("\n🔄 Executing peak hour optimization...")
        execution = await self.supervisor.execute_delivery_plan(plan, self.mock_agents)
        
        print(f"   ✅ Execution: {execution.status.value}")
        print(f"   📈 Success rate: {execution.success_metrics['step_success_rate']:.1f}%")
        print(f"   ⏱️ Duration: {execution.total_duration_seconds:.2f}s")
        
        if execution.error_log:
            print(f"   ⚠️ Challenges handled: {len(execution.error_log)}")
        
        # Analyze plan performance
        plan_analysis = await self.planner.analyze_plan_performance(
            plan.plan_id,
            {"actual_delivery_time": 45.5, "actual_cost": 8.97, "success": True}
        )
        print(f"   📊 Plan accuracy: {plan_analysis['time_prediction_accuracy']:.2f}")
    
    def show_system_statistics(self):
        """Show final system performance statistics"""
        print("\n📊 System Performance Statistics")
        print("=" * 80)
        
        # Planner statistics
        planner_stats = self.planner.get_optimization_stats()
        print("🎯 Delivery Optimization Planner:")
        print(f"   • Total plans created: {planner_stats['total_plans_created']}")
        print(f"   • Success rate: {planner_stats['success_rate']}")
        print(f"   • Active plans: {planner_stats['active_plans']}")
        
        # Supervisor statistics  
        supervisor_stats = self.supervisor.get_supervisor_stats()
        print("\n🔧 Delivery Process Supervisor:")
        print(f"   • Total executions: {supervisor_stats['total_executions']}")
        print(f"   • Success rate: {supervisor_stats['success_rate']}")
        print(f"   • Active executions: {supervisor_stats['active_executions']}")
        
        # Agent performance
        print("\n🤖 Agent Performance:")
        for agent_type, perf in supervisor_stats['agent_performance'].items():
            if perf['calls'] > 0:
                success_rate = (perf['successes'] / perf['calls']) * 100
                print(f"   • {agent_type}: {perf['calls']} calls, {success_rate:.1f}% success, {perf['avg_time']:.2f}s avg")
        
        print("\n✅ Delivery optimization system demonstrated successfully!")
        print("   Key benefits:")
        print("   • Robust planning with multiple strategies")
        print("   • Coordinated execution with fallback handling")
        print("   • Real-time monitoring and performance tracking")
        print("   • Simple architecture - not over-engineered")


# Mock agents for demonstration
class MockETAAgent:
    """Mock ETA prediction agent for demo"""
    async def predict(self, *args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate processing
        return {"estimated_time": 25.0, "confidence": 0.85}


class MockDriverAgent:
    """Mock driver allocation agent for demo"""
    async def allocate(self, *args, **kwargs):
        await asyncio.sleep(0.05)  # Simulate processing
        return {"driver_id": "driver_123", "allocation_score": 0.92}


class MockRouteAgent:
    """Mock route optimization agent for demo"""
    async def optimize(self, *args, **kwargs):
        await asyncio.sleep(0.08)  # Simulate processing
        return {"route_efficiency": 0.88, "time_savings": 7.5}


async def main():
    """Main demo execution"""
    demo = DeliveryOptimizationDemo()
    
    try:
        await demo.initialize()
        await demo.run_scenarios()
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())