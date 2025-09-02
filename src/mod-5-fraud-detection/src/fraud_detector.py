"""Main Fraud Detection Coordinator

This module orchestrates the complete fraud detection pipeline,
integrating RAG systems, multi-agent analysis, and action execution
for comprehensive fraud prevention.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.models.order import OrderData
from src.models.fraud_result import FraudResult
from src.models.action_result import ActionResult
from src.agents.fraud_agents import FraudDetectionAgents
from src.agents.workflows import FraudDetectionWorkflow
import sys
from pathlib import Path
rag_path = Path(__file__).parent.parent / "rag"
sys.path.insert(0, str(rag_path))
from rag_system import FraudRAGSystem
from src.actions.action_engine import FraudActionEngine
from src.utils.input_validator import validate_order_data, ValidationErrorType
from config.settings import settings

logger = logging.getLogger(__name__)

class FraudDetector:
    """Main fraud detection system coordinator.
    
    Orchestrates the complete fraud detection pipeline from order analysis
    through action execution, integrating RAG systems, multi-agent workflows,
    and performance monitoring.
    
    Attributes:
        rag_system: RAG system for context-aware analysis
        agents: Multi-agent fraud detection system
        workflow: Workflow orchestrator for agent coordination
        action_engine: Action execution engine for fraud responses
    """
    
    def __init__(self):
        logger.info("Initializing FraudDetector system")
        
        self.rag_system = FraudRAGSystem()
        logger.info("RAG system initialized")
        
        self.agents = FraudDetectionAgents(self.rag_system)
        logger.info("Agent system initialized")
        
        self.workflow = FraudDetectionWorkflow(self.agents)
        logger.info("Workflow orchestrator initialized")
        
        self.action_engine = FraudActionEngine()
        logger.info("Action engine initialized")
        
        self.detection_count = 0
        self.total_processing_time = 0.0
        self.system_start_time = datetime.now()
        
        logger.info("FraudDetector system fully initialized")
    
    async def detect_fraud(self, order_data: OrderData) -> Dict[str, Any]:
        """Execute fraud detection on a single order.
        
        Args:
            order_data: Order information for fraud analysis
            
        Returns:
            Complete fraud detection result including analysis,
            recommended action, and performance metrics
            
        Raises:
            Exception: If fraud detection pipeline fails
        """
        detection_start_time = time.time()
        
        logger.info(f"Starting fraud detection for order {order_data.order_id}")
        
        # Input validation and sanitization
        order_dict = order_data.__dict__ if hasattr(order_data, '__dict__') else order_data
        validation_result = validate_order_data(order_dict)
        
        if not validation_result.is_valid:
            logger.error(f"Input validation failed for order {order_data.order_id}: "
                        f"{len(validation_result.errors)} errors")
            
            # Log validation errors for security monitoring
            security_errors = [e for e in validation_result.errors 
                             if e.error_type == ValidationErrorType.SECURITY_VIOLATION]
            if security_errors:
                logger.critical(f"SECURITY: Potential attack detected in order {order_data.order_id}: "
                              f"{[e.message for e in security_errors]}")
            
            # Return error result for invalid input
            return {
                "order_id": getattr(order_data, 'order_id', 'unknown'),
                "user_id": getattr(order_data, 'user_key', 'unknown'),
                "error": "Input validation failed",
                "validation_errors": [
                    {
                        "field": e.field_name,
                        "type": e.error_type.value,
                        "message": e.message
                    }
                    for e in validation_result.errors
                ],
                "fraud_analysis": {
                    "fraud_score": 0.9,  # High risk for invalid input
                    "recommended_action": "BLOCK",  # Block invalid inputs
                    "reasoning": "Input validation failed - potentially malicious data"
                },
                "action_result": {
                    "action_taken": "VALIDATION_FAILED",
                    "status": "BLOCKED",
                    "error_message": "Input validation failed"
                },
                "total_processing_time_ms": int((time.time() - detection_start_time) * 1000),
                "detection_timestamp": datetime.now().isoformat(),
                "system_version": "1.0.0"
            }
        
        # Log validation warnings for monitoring
        if validation_result.warnings:
            logger.warning(f"Input validation warnings for order {order_data.order_id}: "
                         f"{validation_result.warnings}")
        
        # Use sanitized data for fraud detection
        logger.info(f"Input validation passed for order {order_data.order_id}")
        
        try:
            fraud_result = await self.workflow.analyze_fraud_async(order_data)
            action_result = await self.action_engine.execute_fraud_action(fraud_result, order_data)
            
            total_processing_time = int((time.time() - detection_start_time) * 1000)
            
            final_result = {
                "order_id": order_data.order_id,
                "user_id": order_data.user_key,
                "fraud_analysis": fraud_result.to_dict(),
                "action_result": action_result.to_dict(),
                "total_processing_time_ms": total_processing_time,
                "detection_timestamp": datetime.now().isoformat(),
                "system_version": "1.0.0"
            }
            
            self.detection_count += 1
            self.total_processing_time += (total_processing_time / 1000)
            
            logger.info(f"Fraud detection completed for order {order_data.order_id} in {total_processing_time}ms")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error in fraud detection for order {order_data.order_id}: {e}")
            
            error_result = {
                "order_id": order_data.order_id,
                "user_id": order_data.user_key,
                "error": str(e),
                "fraud_analysis": {
                    "fraud_score": 0.5,  # Medium risk when we can't determine
                    "recommended_action": "MONITOR",  # Safe default - never auto-allow on error
                    "reasoning": f"Detection error - requires manual review: {str(e)}"
                },
                "action_result": {
                    "action_taken": "ERROR",
                    "status": "FAILED",
                    "error_message": str(e)
                },
                "total_processing_time_ms": int((time.time() - detection_start_time) * 1000),
                "detection_timestamp": datetime.now().isoformat(),
                "system_version": "1.0.0"
            }
            
            return error_result
    
    async def detect_fraud_batch(self, order_data_list: List[OrderData]) -> List[Dict[str, Any]]:
        """Execute fraud detection on multiple orders concurrently.
        
        Args:
            order_data_list: List of orders for batch processing
            
        Returns:
            List of fraud detection results for all orders
            
        This method processes orders concurrently for improved throughput
        while maintaining individual error handling per order.
        """
        logger.info(f"Starting batch fraud detection for {len(order_data_list)} orders")
        
        batch_start_time = time.time()
        
        try:
            detection_tasks = [
                self.detect_fraud(order_data) 
                for order_data in order_data_list
            ]
            
            results = await asyncio.gather(*detection_tasks, return_exceptions=True)
            
            successful_results = []
            error_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_result = {
                        "order_id": order_data_list[i].order_id,
                        "user_id": order_data_list[i].user_key,
                        "error": str(result),
                        "status": "FAILED"
                    }
                    error_results.append(error_result)
                    logger.error(f"Batch detection failed for order {order_data_list[i].order_id}: {result}")
                else:
                    successful_results.append(result)
            
            batch_processing_time = time.time() - batch_start_time
            
            logger.info(f"Batch fraud detection completed: {len(successful_results)}/{len(order_data_list)} successful in {batch_processing_time:.3f}s")
            
            return successful_results + error_results
            
        except Exception as e:
            logger.error(f"Error in batch fraud detection: {e}")
            
            return [
                {
                    "order_id": order_data.order_id,
                    "user_id": order_data.user_key,
                    "error": f"Batch processing error: {str(e)}",
                    "status": "FAILED"
                }
                for order_data in order_data_list
            ]
    
    def validate_order_data(self, order_data: OrderData) -> Dict[str, Any]:
        """Validate order data before processing.
        
        Args:
            order_data: Order data to validate
            
        Returns:
            Validation result with status, errors, and warnings
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        required_checks = [
            (not order_data.order_id, "order_id is required"),
            (not order_data.user_key, "user_key is required"),
            (order_data.total_amount <= 0, "total_amount must be greater than 0")
        ]
        
        for condition, error_msg in required_checks:
            if condition:
                validation_result["errors"].append(error_msg)
        
        warning_checks = [
            (order_data.order_creation_speed_ms and order_data.order_creation_speed_ms < 100,
             "Extremely fast order creation speed detected"),
            (order_data.orders_today > 50, "Unusually high daily order count"),
            (order_data.payment_failures_today > 10, "High payment failure count")
        ]
        
        for condition, warning_msg in warning_checks:
            if condition:
                validation_result["warnings"].append(warning_msg)
        
        validation_result["valid"] = len(validation_result["errors"]) == 0
        return validation_result
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status.
        
        Returns:
            System health metrics including component status,
            performance indicators, and operational statistics
        """
        try:
            rag_validation = self.rag_system.validate_system()
            
            agent_health = {
                "pattern_analyzer_ready": self.agents.pattern_analyzer is not None,
                "risk_assessor_ready": self.agents.risk_assessor is not None,
                "decision_maker_ready": self.agents.decision_maker is not None,
                "action_executor_ready": self.agents.action_executor is not None
            }
            
            action_stats = self.action_engine.get_action_statistics()
            avg_processing_time = (self.total_processing_time / self.detection_count) if self.detection_count > 0 else 0
            
            health_status = {
                "system_status": "healthy" if all([
                    rag_validation.get("system_ready", False),
                    all(agent_health.values()),
                    avg_processing_time < 1.0  # Under 1 second average
                ]) else "degraded",
                "uptime_seconds": (datetime.now() - self.system_start_time).total_seconds(),
                "detections_processed": self.detection_count,
                "avg_processing_time_seconds": avg_processing_time,
                "rag_system": rag_validation,
                "agent_system": agent_health,
                "action_engine": {
                    "total_actions": action_stats.get("total_actions", 0),
                    "success_rate": action_stats.get("success_rate", 0.0),
                    "avg_execution_time_ms": action_stats.get("avg_execution_time_ms", 0.0)
                },
                "performance_targets": {
                    "max_processing_time_ms": settings.fraud.max_detection_latency_ms,
                    "min_accuracy": settings.fraud.min_system_accuracy,
                    "current_performance": "within_targets" if avg_processing_time < 0.2 else "above_target"
                }
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "system_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics across all system components.
        
        Returns:
            Comprehensive performance metrics including throughput,
            latency, SLA compliance, and component-specific statistics
        """
        try:
            rag_metrics = self.rag_system.get_performance_metrics()
            workflow_stats = self.workflow.get_workflow_statistics()
            action_stats = self.action_engine.get_action_statistics()
            
            avg_processing_time = (self.total_processing_time / self.detection_count) if self.detection_count > 0 else 0
            throughput = self.detection_count / max((datetime.now() - self.system_start_time).total_seconds(), 1)
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "system_metrics": {
                    "total_detections": self.detection_count,
                    "avg_processing_time_seconds": avg_processing_time,
                    "throughput_per_second": throughput,
                    "uptime_seconds": (datetime.now() - self.system_start_time).total_seconds()
                },
                "rag_metrics": rag_metrics,
                "workflow_metrics": workflow_stats,
                "action_metrics": action_stats,
                "sla_compliance": {
                    "target_latency_ms": settings.fraud.max_detection_latency_ms,
                    "current_avg_latency_ms": avg_processing_time * 1000,
                    "within_sla": avg_processing_time * 1000 < settings.fraud.max_detection_latency_ms,
                    "target_accuracy": settings.fraud.min_system_accuracy
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_system_end_to_end(self) -> Dict[str, Any]:
        """Execute comprehensive end-to-end system test.
        
        Returns:
            Test results including status, duration, and validation metrics
            
        Creates a test order, processes it through the complete fraud
        detection pipeline, and validates all components are functioning.
        """
        logger.info("Running end-to-end system test")
        
        try:
            test_order = OrderData(
                order_id="test_order_123",
                user_key="test_user_456",
                restaurant_key="test_restaurant_789",
                total_amount=25.50,
                item_count=2,
                account_age_days=30,
                orders_today=1,
                payment_method="credit_card"
            )
            
            start_time = time.time()
            result = await self.detect_fraud(test_order)
            test_time = time.time() - start_time
            
            test_result = {
                "test_status": "passed" if "error" not in result else "failed",
                "test_duration_seconds": test_time,
                "detection_completed": True,
                "fraud_score_returned": "fraud_analysis" in result,
                "action_executed": "action_result" in result,
                "within_latency_target": test_time < (settings.fraud.max_detection_latency_ms / 1000),
                "test_timestamp": datetime.now().isoformat(),
                "result_summary": {
                    "fraud_score": result.get("fraud_analysis", {}).get("fraud_score", 0.0),
                    "recommended_action": result.get("fraud_analysis", {}).get("recommended_action", "UNKNOWN"),
                    "processing_time_ms": result.get("total_processing_time_ms", 0)
                }
            }
            
            logger.info(f"End-to-end test completed: {test_result['test_status']} in {test_time:.3f}s")
            
            return test_result
            
        except Exception as e:
            logger.error(f"End-to-end test failed: {e}")
            return {
                "test_status": "failed",
                "error": str(e),
                "test_timestamp": datetime.now().isoformat()
            }
    
    def reset_performance_counters(self) -> None:
        """Reset performance tracking counters for fresh metrics collection."""
        self.detection_count = 0
        self.total_processing_time = 0.0
        self.system_start_time = datetime.now()
        logger.info("Performance counters reset")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the fraud detection system.
        
        Performs cleanup of resources including cached data,
        thread pools, and connection cleanup.
        """
        logger.info("Shutting down fraud detection system")
        
        try:
            if hasattr(self.rag_system, 'clear_cache'):
                self.rag_system.clear_cache()
            
            if hasattr(self.action_engine, 'thread_pool'):
                self.action_engine.thread_pool.shutdown(wait=True)
            
            logger.info("Fraud detection system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")
            raise