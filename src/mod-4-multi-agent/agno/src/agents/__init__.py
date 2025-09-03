"""
UberEats Delivery Optimization Agent System
Real-time optimization agents for GPS-driven delivery intelligence
"""
from .base_agent import UberEatsBaseAgent

# Core optimization agents
from .eta_prediction_agent import SmartETAPredictionAgent
from .driver_allocation_agent import DriverAllocationAgent
from .route_optimization_agent import RouteOptimizationAgent

# Strategic optimization agents
from .delivery_optimization_planner import DeliveryOptimizationPlanner, DeliveryPlan, OptimizationContext
from .delivery_process_supervisor import DeliveryProcessSupervisor, ProcessExecution, ExecutionStatus

__all__ = [
    # Base agent
    'UberEatsBaseAgent',
    
    # Core optimization agents (GPS-driven)
    'SmartETAPredictionAgent',     # ⏱️ Real-time ETA predictions
    'DriverAllocationAgent',       # 🎯 Smart driver assignments
    'RouteOptimizationAgent',      # 🗺️ Traffic-aware routing
    
    # Strategic optimization agents
    'DeliveryOptimizationPlanner', # 📋 Delivery strategy planning
    'DeliveryProcessSupervisor',   # 🤖 Process coordination
    
    # Data classes
    'DeliveryPlan',
    'OptimizationContext', 
    'ProcessExecution',
    'ExecutionStatus'
]