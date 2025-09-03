#!/usr/bin/env python3
"""
Test supervision and planning agents functionality
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.agents.delivery_process_supervisor import DeliveryProcessSupervisor, ExecutionStatus
from src.agents.delivery_optimization_planner import DeliveryOptimizationPlanner, OptimizationContext

def test_planner_functionality():
    """Test if delivery optimization planner works"""
    print("🎯 Testing Delivery Optimization Planner...")
    
    try:
        planner = DeliveryOptimizationPlanner()
        print("   ✅ Planner initialized successfully")
        
        # Test strategy determination
        mock_orders = [
            {"id": "order_1", "customer_tier": "premium"},
            {"id": "order_2", "special_instructions": "urgent delivery"}
        ]
        
        mock_context = OptimizationContext(
            current_time=datetime.now(),
            weather_conditions="clear",
            traffic_status="moderate", 
            driver_availability=5,
            restaurant_capacity={"rest_1": 0.8},
            order_volume="medium",
            special_events=[]
        )
        
        strategy = planner._determine_optimization_strategy(mock_orders, mock_context)
        print(f"   ✅ Strategy determination works: {strategy}")
        
        priority_score = planner._calculate_priority_score(mock_orders, mock_context)
        print(f"   ✅ Priority calculation works: {priority_score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Planner test failed: {e}")
        return False

def test_supervisor_functionality():
    """Test if delivery process supervisor works"""
    print("\n🔍 Testing Delivery Process Supervisor...")
    
    try:
        supervisor = DeliveryProcessSupervisor()
        print("   ✅ Supervisor initialized successfully")
        
        # Test agent metrics update
        supervisor._update_agent_metrics("eta_prediction", True, 2.5)
        print("   ✅ Agent metrics update works")
        
        # Test stats retrieval
        stats = supervisor.get_supervisor_stats()
        print(f"   ✅ Stats retrieval works: {stats['success_rate']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Supervisor test failed: {e}")
        return False

async def test_planner_async_functionality():
    """Test async functionality of planner"""
    print("\n⚡ Testing Planner Async Functionality...")
    
    try:
        planner = DeliveryOptimizationPlanner()
        
        mock_orders = [{"id": "order_1", "customer_tier": "standard"}]
        mock_context = OptimizationContext(
            current_time=datetime.now(),
            weather_conditions="clear",
            traffic_status="light",
            driver_availability=3,
            restaurant_capacity={},
            order_volume="low", 
            special_events=[]
        )
        
        # Test plan creation
        plan = await planner.create_delivery_plan(mock_orders, mock_context)
        print(f"   ✅ Plan creation works: {plan.plan_id}")
        print(f"   📊 Strategy: {plan.strategy}")
        print(f"   ⭐ Priority Score: {plan.priority_score:.2f}")
        print(f"   ⏱️ Estimated Time: {plan.estimated_total_time:.1f} min")
        print(f"   💰 Estimated Cost: R$ {plan.estimated_cost:.2f}")
        print(f"   📈 Efficiency: {plan.efficiency_rating}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Async planner test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Supervisor and Planner Components")
    print("=" * 60)
    
    results = {
        "planner_sync": test_planner_functionality(),
        "supervisor_sync": test_supervisor_functionality(),
    }
    
    # Run async test
    try:
        results["planner_async"] = asyncio.run(test_planner_async_functionality())
    except Exception as e:
        print(f"   ❌ Async test setup failed: {e}")
        results["planner_async"] = False
    
    # Summary
    print(f"\n🎯 Test Results Summary")
    print("-" * 40)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    success_rate = (passed_tests / total_tests) * 100
    print(f"\n📊 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
    
    if success_rate == 100:
        print("🎉 ALL TESTS PASSED - Supervisor and Planner are working correctly!")
    elif success_rate >= 75:
        print("⚠️ MOSTLY WORKING - Some minor issues detected")
    else:
        print("🚨 MULTIPLE FAILURES - Components need attention")

if __name__ == "__main__":
    main()