"""
Delivery Process Supervisor - Orchestrates and monitors delivery plan execution
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .base_agent import UberEatsBaseAgent
from .delivery_optimization_planner import DeliveryPlan, OptimizationContext
from ..observability.langfuse_config import observe_ubereats_operation

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Delivery plan execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionStep:
    """Individual step in delivery process execution"""
    step_id: str
    agent_type: str  # "eta_prediction", "driver_allocation", "route_optimization"
    status: ExecutionStatus
    input_data: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


@dataclass
class ProcessExecution:
    """Complete delivery process execution tracking"""
    execution_id: str
    plan_id: str
    status: ExecutionStatus
    steps: List[ExecutionStep]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None
    success_metrics: Optional[Dict[str, Any]] = None
    error_log: List[str] = None


class DeliveryProcessSupervisor(UberEatsBaseAgent):
    """
    Supervisor that orchestrates delivery plan execution by:
    - Coordinating specialized agents (ETA, driver allocation, routing)
    - Monitoring execution progress and quality
    - Handling exceptions and implementing fallbacks
    - Providing real-time status and adjustments
    
    Focus: Execution coordination, not strategic planning
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_id="delivery_process_supervisor",
            instructions="Delivery process supervisor initialized. Loading dynamic instructions...",
            enable_reasoning=True,
            enable_memory=True,
            **kwargs
        )
        
        # Initialize with dynamic prompt
        self._initialize_dynamic_instructions()
        
        self.active_executions = {}
        self.execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0.0,
            "agent_performance": {
                "eta_prediction": {"calls": 0, "successes": 0, "avg_time": 0.0},
                "driver_allocation": {"calls": 0, "successes": 0, "avg_time": 0.0},
                "route_optimization": {"calls": 0, "successes": 0, "avg_time": 0.0}
            }
        }
    
    def _initialize_dynamic_instructions(self):
        """Load instructions from Langfuse prompt management"""
        try:
            self.update_instructions_from_prompt("delivery_process_supervisor", {
                "context": "UberEats delivery execution system",
                "role": "Process supervisor and coordinator"
            })
            logger.debug("Delivery process supervisor instructions updated from dynamic prompt")
        except Exception as e:
            logger.warning(f"Failed to load dynamic instructions, using fallback: {e}")
    
    @observe_ubereats_operation(
        operation_type="process_execution",
        include_args=True,
        include_result=True,
        capture_metrics=True
    )
    async def execute_delivery_plan(
        self,
        plan: DeliveryPlan,
        specialized_agents: Dict[str, Any]
    ) -> ProcessExecution:
        """
        Execute a delivery plan using specialized agents
        
        Args:
            plan: DeliveryPlan from the optimization planner
            specialized_agents: Dictionary of available specialized agents
                {
                    "eta_prediction": ETAPredictionAgent,
                    "driver_allocation": DriverAllocationAgent,
                    "route_optimization": RouteOptimizationAgent
                }
        """
        execution_id = f"exec_{plan.plan_id}_{datetime.now().strftime('%H%M%S')}"
        
        # Create execution tracking
        execution = ProcessExecution(
            execution_id=execution_id,
            plan_id=plan.plan_id,
            status=ExecutionStatus.PENDING,
            steps=[],
            created_at=datetime.now(),
            error_log=[]
        )
        
        self.active_executions[execution_id] = execution
        logger.info(f"Starting execution {execution_id} for plan {plan.plan_id}")
        
        try:
            execution.status = ExecutionStatus.IN_PROGRESS
            execution.started_at = datetime.now()
            
            # Execute plan based on strategy
            if plan.strategy == "single_order":
                await self._execute_single_order_strategy(execution, plan, specialized_agents)
            elif plan.strategy == "batch_optimization":
                await self._execute_batch_optimization_strategy(execution, plan, specialized_agents)
            elif plan.strategy == "peak_hour_optimization":
                await self._execute_peak_hour_strategy(execution, plan, specialized_agents)
            else:
                raise ValueError(f"Unknown strategy: {plan.strategy}")
            
            # Mark as completed
            execution.completed_at = datetime.now()
            execution.total_duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            execution.status = ExecutionStatus.COMPLETED
            
            # Calculate success metrics
            execution.success_metrics = self._calculate_success_metrics(execution, plan)
            
            # Update global metrics
            self.execution_metrics["total_executions"] += 1
            self.execution_metrics["successful_executions"] += 1
            
            logger.info(f"Execution {execution_id} completed successfully in {execution.total_duration_seconds:.2f}s")
            
        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}")
            execution.status = ExecutionStatus.FAILED
            execution.error_log.append(str(e))
            execution.completed_at = datetime.now()
            
            if execution.started_at:
                execution.total_duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            
            self.execution_metrics["total_executions"] += 1
            self.execution_metrics["failed_executions"] += 1
            
            # Attempt fallback execution
            await self._attempt_fallback_execution(execution, plan, specialized_agents)
        
        return execution
    
    async def _execute_single_order_strategy(
        self,
        execution: ProcessExecution,
        plan: DeliveryPlan,
        agents: Dict[str, Any]
    ):
        """Execute single order strategy"""
        logger.debug(f"Executing single order strategy for {len(plan.order_ids)} orders")
        
        for order_id in plan.order_ids:
            # Step 1: ETA Prediction
            eta_step = await self._execute_agent_step(
                execution, "eta_prediction", agents.get("eta_prediction"),
                {"order_id": order_id, "strategy": "single_order"}
            )
            
            if eta_step.status != ExecutionStatus.COMPLETED:
                raise Exception(f"ETA prediction failed for order {order_id}: {eta_step.error_message}")
            
            # Step 2: Driver Allocation
            driver_step = await self._execute_agent_step(
                execution, "driver_allocation", agents.get("driver_allocation"),
                {"order_id": order_id, "eta_data": eta_step.result}
            )
            
            if driver_step.status != ExecutionStatus.COMPLETED:
                raise Exception(f"Driver allocation failed for order {order_id}: {driver_step.error_message}")
            
            # Step 3: Route Optimization (for single order, just validation)
            route_step = await self._execute_agent_step(
                execution, "route_optimization", agents.get("route_optimization"),
                {"order_id": order_id, "driver_data": driver_step.result, "strategy": "validate"}
            )
    
    async def _execute_batch_optimization_strategy(
        self,
        execution: ProcessExecution,
        plan: DeliveryPlan,
        agents: Dict[str, Any]
    ):
        """Execute batch optimization strategy"""
        logger.debug(f"Executing batch optimization for {len(plan.order_ids)} orders")
        
        # Step 1: Batch ETA Prediction for all orders
        eta_step = await self._execute_agent_step(
            execution, "eta_prediction", agents.get("eta_prediction"),
            {"order_ids": plan.order_ids, "strategy": "batch"}
        )
        
        if eta_step.status != ExecutionStatus.COMPLETED:
            raise Exception(f"Batch ETA prediction failed: {eta_step.error_message}")
        
        # Step 2: Optimal Driver Allocation for batch
        driver_step = await self._execute_agent_step(
            execution, "driver_allocation", agents.get("driver_allocation"),
            {"order_ids": plan.order_ids, "eta_data": eta_step.result, "strategy": "batch_optimal"}
        )
        
        if driver_step.status != ExecutionStatus.COMPLETED:
            raise Exception(f"Batch driver allocation failed: {driver_step.error_message}")
        
        # Step 3: Multi-stop Route Optimization
        route_step = await self._execute_agent_step(
            execution, "route_optimization", agents.get("route_optimization"),
            {
                "order_ids": plan.order_ids,
                "driver_assignments": driver_step.result,
                "strategy": "multi_stop_optimization"
            }
        )
        
        if route_step.status != ExecutionStatus.COMPLETED:
            logger.warning(f"Route optimization failed, using driver assignments: {route_step.error_message}")
    
    async def _execute_peak_hour_strategy(
        self,
        execution: ProcessExecution,
        plan: DeliveryPlan,
        agents: Dict[str, Any]
    ):
        """Execute peak hour optimization strategy"""
        logger.debug(f"Executing peak hour strategy for {len(plan.order_ids)} orders")
        
        # Peak hours require more careful resource management
        # Step 1: Priority-based ETA prediction
        eta_step = await self._execute_agent_step(
            execution, "eta_prediction", agents.get("eta_prediction"),
            {"order_ids": plan.order_ids, "strategy": "peak_hour", "priority_score": plan.priority_score}
        )
        
        # Step 2: Load-balanced driver allocation
        driver_step = await self._execute_agent_step(
            execution, "driver_allocation", agents.get("driver_allocation"),
            {
                "order_ids": plan.order_ids,
                "eta_data": eta_step.result,
                "strategy": "load_balanced",
                "peak_hour_mode": True
            }
        )
        
        # Step 3: Traffic-aware route optimization
        route_step = await self._execute_agent_step(
            execution, "route_optimization", agents.get("route_optimization"),
            {
                "order_ids": plan.order_ids,
                "driver_assignments": driver_step.result,
                "strategy": "traffic_aware",
                "peak_hour_conditions": True
            }
        )
    
    async def _execute_agent_step(
        self,
        execution: ProcessExecution,
        agent_type: str,
        agent: Any,
        input_data: Dict[str, Any]
    ) -> ExecutionStep:
        """Execute a single agent step with monitoring and error handling"""
        step_id = f"{agent_type}_{len(execution.steps) + 1}"
        
        step = ExecutionStep(
            step_id=step_id,
            agent_type=agent_type,
            status=ExecutionStatus.PENDING,
            input_data=input_data,
            started_at=datetime.now()
        )
        
        execution.steps.append(step)
        
        try:
            if not agent:
                raise ValueError(f"Agent {agent_type} not available")
            
            step.status = ExecutionStatus.IN_PROGRESS
            logger.debug(f"Executing step {step_id} with agent {agent_type}")
            
            # Call the appropriate agent method based on type
            if agent_type == "eta_prediction":
                if "order_ids" in input_data:  # Batch processing
                    result = await self._call_eta_agent_batch(agent, input_data)
                else:  # Single order
                    result = await self._call_eta_agent_single(agent, input_data)
            
            elif agent_type == "driver_allocation":
                result = await self._call_driver_allocation_agent(agent, input_data)
            
            elif agent_type == "route_optimization":
                result = await self._call_route_optimization_agent(agent, input_data)
            
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            step.result = result
            step.status = ExecutionStatus.COMPLETED
            step.completed_at = datetime.now()
            step.duration_seconds = (step.completed_at - step.started_at).total_seconds()
            
            # Update agent performance metrics
            self._update_agent_metrics(agent_type, True, step.duration_seconds)
            
            logger.debug(f"Step {step_id} completed in {step.duration_seconds:.2f}s")
            
        except Exception as e:
            step.error_message = str(e)
            step.status = ExecutionStatus.FAILED
            step.completed_at = datetime.now()
            step.duration_seconds = (step.completed_at - step.started_at).total_seconds()
            
            self._update_agent_metrics(agent_type, False, step.duration_seconds)
            logger.error(f"Step {step_id} failed: {e}")
        
        return step
    
    async def _call_eta_agent_single(self, agent: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call ETA prediction agent for single order"""
        # Simplified mock implementation - replace with actual agent method calls
        return {
            "order_id": input_data["order_id"],
            "estimated_pickup_time": datetime.now() + timedelta(minutes=15),
            "estimated_delivery_time": datetime.now() + timedelta(minutes=35),
            "confidence_score": 0.85
        }
    
    async def _call_eta_agent_batch(self, agent: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call ETA prediction agent for batch orders"""
        results = {}
        for order_id in input_data["order_ids"]:
            results[order_id] = {
                "estimated_pickup_time": datetime.now() + timedelta(minutes=12),
                "estimated_delivery_time": datetime.now() + timedelta(minutes=28),
                "confidence_score": 0.82
            }
        return {"batch_results": results}
    
    async def _call_driver_allocation_agent(self, agent: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call driver allocation agent"""
        # Simplified mock implementation
        if "order_ids" in input_data:
            # Batch allocation
            allocations = {}
            for i, order_id in enumerate(input_data["order_ids"]):
                allocations[order_id] = {
                    "driver_id": f"driver_{i % 3 + 1}",
                    "allocation_score": 0.85,
                    "estimated_pickup_time": datetime.now() + timedelta(minutes=10)
                }
            return {"allocations": allocations}
        else:
            # Single allocation
            return {
                "order_id": input_data["order_id"],
                "driver_id": "driver_1",
                "allocation_score": 0.88,
                "estimated_pickup_time": datetime.now() + timedelta(minutes=10)
            }
    
    async def _call_route_optimization_agent(self, agent: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call route optimization agent"""
        # Simplified mock implementation
        return {
            "optimized_routes": [
                {
                    "driver_id": "driver_1",
                    "total_distance_km": 12.5,
                    "total_time_minutes": 35.0,
                    "efficiency_score": 0.82
                }
            ],
            "total_savings_minutes": 8.5
        }
    
    def _update_agent_metrics(self, agent_type: str, success: bool, duration: float):
        """Update performance metrics for an agent"""
        metrics = self.execution_metrics["agent_performance"][agent_type]
        metrics["calls"] += 1
        if success:
            metrics["successes"] += 1
        
        # Update average time
        current_avg = metrics["avg_time"]
        call_count = metrics["calls"]
        metrics["avg_time"] = ((current_avg * (call_count - 1)) + duration) / call_count
    
    def _calculate_success_metrics(self, execution: ProcessExecution, plan: DeliveryPlan) -> Dict[str, Any]:
        """Calculate success metrics for completed execution"""
        total_steps = len(execution.steps)
        successful_steps = sum(1 for step in execution.steps if step.status == ExecutionStatus.COMPLETED)
        
        return {
            "step_success_rate": (successful_steps / max(1, total_steps)) * 100,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": total_steps - successful_steps,
            "execution_efficiency": successful_steps / max(1, execution.total_duration_seconds or 1),
            "met_time_estimate": execution.total_duration_seconds <= plan.estimated_total_time if execution.total_duration_seconds else False
        }
    
    async def _attempt_fallback_execution(
        self,
        execution: ProcessExecution,
        plan: DeliveryPlan,
        agents: Dict[str, Any]
    ):
        """Attempt fallback execution if primary execution fails"""
        if not plan.fallback_options:
            return
        
        logger.info(f"Attempting fallback execution for {execution.execution_id}")
        
        # Try the first fallback option
        fallback = plan.fallback_options[0]
        execution.error_log.append(f"Attempting fallback: {fallback['strategy']}")
        
        try:
            if fallback["strategy"] == "sequential_single_order":
                await self._execute_single_order_strategy(execution, plan, agents)
                execution.status = ExecutionStatus.COMPLETED
                execution.error_log.append("Fallback execution successful")
                
        except Exception as e:
            execution.error_log.append(f"Fallback execution also failed: {e}")
            execution.status = ExecutionStatus.FAILED
    
    @observe_ubereats_operation(
        operation_type="execution_monitoring",
        include_args=True,
        include_result=True,
        capture_metrics=False
    )
    async def monitor_execution(self, execution_id: str) -> Dict[str, Any]:
        """Monitor ongoing execution progress"""
        if execution_id not in self.active_executions:
            return {"error": f"Execution {execution_id} not found"}
        
        execution = self.active_executions[execution_id]
        
        # Calculate progress
        total_steps = len(execution.steps)
        completed_steps = sum(1 for step in execution.steps if step.status == ExecutionStatus.COMPLETED)
        progress_percent = (completed_steps / max(1, total_steps)) * 100 if total_steps > 0 else 0
        
        return {
            "execution_id": execution_id,
            "status": execution.status.value,
            "progress_percent": progress_percent,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": execution.steps[-1].agent_type if execution.steps else None,
            "duration_seconds": (datetime.now() - execution.started_at).total_seconds() if execution.started_at else 0,
            "errors": execution.error_log
        }
    
    def get_supervisor_stats(self) -> Dict[str, Any]:
        """Get supervisor performance statistics"""
        total_executions = self.execution_metrics["total_executions"]
        success_rate = (
            self.execution_metrics["successful_executions"] / max(1, total_executions)
        ) * 100
        
        return {
            "total_executions": total_executions,
            "successful_executions": self.execution_metrics["successful_executions"],
            "failed_executions": self.execution_metrics["failed_executions"],
            "success_rate": f"{success_rate:.1f}%",
            "active_executions": len(self.active_executions),
            "agent_performance": self.execution_metrics["agent_performance"]
        }