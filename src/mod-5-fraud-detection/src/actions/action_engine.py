"""
Fraud action execution engine
"""

import asyncio
import time
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import json

from src.models.fraud_result import FraudResult, FraudDecision
from src.models.action_result import (
    ActionResult, ActionType, ActionStatus, ActionExecutionSummary,
    BlockOrderResult, FlagForReviewResult, MonitorUserResult, SendAlertResult
)
from src.models.order import OrderData
from config.settings import settings

logger = logging.getLogger(__name__)

class FraudActionEngine:
    """Execute fraud prevention actions with high performance"""
    
    def __init__(self):
        self.fraud_config = settings.fraud
        self.action_history = []
        self.execution_summary = ActionExecutionSummary()
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # Action handlers
        self.action_handlers = {
            FraudDecision.BLOCK: self._handle_block_action,
            FraudDecision.FLAG: self._handle_flag_action,
            FraudDecision.REQUIRE_HUMAN: self._handle_flag_action,  # Same as FLAG
            FraudDecision.MONITOR: self._handle_monitor_action,
            FraudDecision.ALLOW: self._handle_allow_action
        }
        
        logger.info("FraudActionEngine initialized")
    
    async def execute_fraud_action(self, fraud_result: FraudResult, order_data: OrderData) -> ActionResult:
        """Execute appropriate fraud action based on decision"""
        action_start_time = time.time()
        action_id = str(uuid.uuid4())
        
        logger.info(f"Executing fraud action for order {order_data.order_id}: {fraud_result.recommended_action}")
        
        try:
            # Get action handler
            handler = self.action_handlers.get(fraud_result.recommended_action)
            if not handler:
                raise ValueError(f"No handler for action: {fraud_result.recommended_action}")
            
            # Execute action
            action_result = await handler(action_id, fraud_result, order_data)
            
            # Update execution summary
            self.execution_summary.add_action_result(action_result)
            self.action_history.append(action_result)
            
            # Keep history manageable
            if len(self.action_history) > 1000:
                self.action_history = self.action_history[-1000:]
            
            execution_time = int((time.time() - action_start_time) * 1000)
            logger.info(f"Action executed in {execution_time}ms: {action_result.status}")
            
            return action_result
            
        except Exception as e:
            logger.error(f"Error executing fraud action for order {order_data.order_id}: {e}")
            
            # Create failed action result
            failed_result = ActionResult(
                action_id=action_id,
                action_type=self._get_action_type(fraud_result.recommended_action),
                order_id=order_data.order_id,
                user_id=order_data.user_key,
                status=ActionStatus.FAILED,
                error_message=str(e),
                execution_time_ms=int((time.time() - action_start_time) * 1000)
            )
            
            self.execution_summary.add_action_result(failed_result)
            return failed_result
    
    async def _handle_block_action(self, action_id: str, fraud_result: FraudResult, order_data: OrderData) -> BlockOrderResult:
        """Handle order blocking action"""
        start_time = time.time()
        
        logger.info(f"Blocking order {order_data.order_id}")
        
        try:
            block_result = BlockOrderResult(
                action_id=action_id,
                action_type=ActionType.BLOCK_ORDER,
                order_id=order_data.order_id,
                user_id=order_data.user_key,
                blocked_order_id=order_data.order_id
            )
            
            # Execute blocking actions in parallel
            blocking_tasks = [
                self._block_order_api(order_data),
                self._decline_payment(order_data),
                self._send_block_notification(order_data, fraud_result),
                self._log_block_action(order_data, fraud_result)
            ]
            
            results = await asyncio.gather(*blocking_tasks, return_exceptions=True)
            
            # Check results
            successful_actions = sum(1 for r in results if not isinstance(r, Exception))
            
            if successful_actions == len(blocking_tasks):
                block_result.mark_success(
                    {
                        "order_blocked": True,
                        "payment_declined": True,
                        "customer_notified": True,
                        "audit_logged": True,
                        "block_reason": fraud_result.reasoning
                    },
                    int((time.time() - start_time) * 1000)
                )
                
                # Estimate loss prevented
                block_result.estimated_loss_prevented_usd = order_data.total_amount
                
            else:
                # Partial success
                failed_tasks = [str(r) for r in results if isinstance(r, Exception)]
                block_result.mark_partial(
                    {"successful_actions": successful_actions, "total_actions": len(blocking_tasks)},
                    f"Some blocking actions failed: {'; '.join(failed_tasks)}",
                    int((time.time() - start_time) * 1000)
                )
            
            logger.info(f"Block action completed for order {order_data.order_id}: {block_result.status}")
            return block_result
            
        except Exception as e:
            logger.error(f"Error in block action for order {order_data.order_id}: {e}")
            block_result.mark_failed(str(e), int((time.time() - start_time) * 1000))
            return block_result
    
    async def _handle_flag_action(self, action_id: str, fraud_result: FraudResult, order_data: OrderData) -> FlagForReviewResult:
        """Handle flagging for manual review"""
        start_time = time.time()
        
        logger.info(f"Flagging order {order_data.order_id} for review")
        
        try:
            flag_result = FlagForReviewResult(
                action_id=action_id,
                action_type=ActionType.FLAG_FOR_REVIEW,
                order_id=order_data.order_id,
                user_id=order_data.user_key,
                priority="high" if fraud_result.fraud_score > 0.8 else "medium",
                review_deadline=datetime.now() + timedelta(hours=2)
            )
            
            # Execute flagging actions
            flagging_tasks = [
                self._add_to_review_queue(order_data, fraud_result),
                self._send_review_alert(order_data, fraud_result),
                self._update_user_risk_score(order_data, fraud_result),
                self._log_flag_action(order_data, fraud_result)
            ]
            
            results = await asyncio.gather(*flagging_tasks, return_exceptions=True)
            
            successful_actions = sum(1 for r in results if not isinstance(r, Exception))
            
            if successful_actions == len(flagging_tasks):
                flag_result.mark_success(
                    {
                        "added_to_review_queue": True,
                        "review_alert_sent": True,
                        "user_risk_updated": True,
                        "audit_logged": True,
                        "flag_reason": fraud_result.reasoning,
                        "priority": flag_result.priority
                    },
                    int((time.time() - start_time) * 1000)
                )
            else:
                failed_tasks = [str(r) for r in results if isinstance(r, Exception)]
                flag_result.mark_partial(
                    {"successful_actions": successful_actions},
                    f"Some flagging actions failed: {'; '.join(failed_tasks)}",
                    int((time.time() - start_time) * 1000)
                )
            
            return flag_result
            
        except Exception as e:
            logger.error(f"Error in flag action for order {order_data.order_id}: {e}")
            flag_result.mark_failed(str(e), int((time.time() - start_time) * 1000))
            return flag_result
    
    async def _handle_monitor_action(self, action_id: str, fraud_result: FraudResult, order_data: OrderData) -> MonitorUserResult:
        """Handle user monitoring action"""
        start_time = time.time()
        
        logger.info(f"Adding user {order_data.user_key} to monitoring")
        
        try:
            monitor_result = MonitorUserResult(
                action_id=action_id,
                action_type=ActionType.MONITOR_USER,
                order_id=order_data.order_id,
                user_id=order_data.user_key,
                monitoring_duration_hours=24,
                monitoring_level="enhanced" if fraud_result.fraud_score > 0.6 else "standard"
            )
            
            # Execute monitoring actions
            monitoring_tasks = [
                self._add_to_monitoring_list(order_data, fraud_result),
                self._set_monitoring_criteria(order_data, fraud_result),
                self._log_monitor_action(order_data, fraud_result)
            ]
            
            results = await asyncio.gather(*monitoring_tasks, return_exceptions=True)
            
            successful_actions = sum(1 for r in results if not isinstance(r, Exception))
            
            if successful_actions == len(monitoring_tasks):
                monitor_result.mark_success(
                    {
                        "user_added_to_monitoring": True,
                        "monitoring_criteria_set": True,
                        "audit_logged": True,
                        "monitoring_level": monitor_result.monitoring_level,
                        "monitoring_duration": monitor_result.monitoring_duration_hours
                    },
                    int((time.time() - start_time) * 1000)
                )
            else:
                failed_tasks = [str(r) for r in results if isinstance(r, Exception)]
                monitor_result.mark_partial(
                    {"successful_actions": successful_actions},
                    f"Some monitoring actions failed: {'; '.join(failed_tasks)}",
                    int((time.time() - start_time) * 1000)
                )
            
            return monitor_result
            
        except Exception as e:
            logger.error(f"Error in monitor action for order {order_data.order_id}: {e}")
            monitor_result.mark_failed(str(e), int((time.time() - start_time) * 1000))
            return monitor_result
    
    async def _handle_allow_action(self, action_id: str, fraud_result: FraudResult, order_data: OrderData) -> ActionResult:
        """Handle allow action (minimal processing)"""
        start_time = time.time()
        
        logger.info(f"Allowing order {order_data.order_id}")
        
        try:
            allow_result = ActionResult(
                action_id=action_id,
                action_type=ActionType.LOG_DECISION,
                order_id=order_data.order_id,
                user_id=order_data.user_key
            )
            
            # Just log the decision
            await self._log_allow_action(order_data, fraud_result)
            
            allow_result.mark_success(
                {
                    "order_allowed": True,
                    "decision_logged": True,
                    "fraud_score": fraud_result.fraud_score
                },
                int((time.time() - start_time) * 1000)
            )
            
            return allow_result
            
        except Exception as e:
            logger.error(f"Error in allow action for order {order_data.order_id}: {e}")
            allow_result.mark_failed(str(e), int((time.time() - start_time) * 1000))
            return allow_result
    
    # Individual action implementations
    async def _block_order_api(self, order_data: OrderData) -> Dict[str, Any]:
        """Block order via API call"""
        # In production, this would call the actual order service API
        await asyncio.sleep(0.01)  # Simulate API call
        logger.info(f"Order blocking API called for {order_data.order_id}")
        return {"order_blocked": True, "block_timestamp": datetime.now().isoformat()}
    
    async def _decline_payment(self, order_data: OrderData) -> Dict[str, Any]:
        """Decline payment for blocked order"""
        await asyncio.sleep(0.01)  # Simulate payment API call
        logger.info(f"Payment declined for order {order_data.order_id}")
        return {"payment_declined": True, "decline_timestamp": datetime.now().isoformat()}
    
    async def _send_block_notification(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Send notification about blocked order"""
        await asyncio.sleep(0.005)  # Simulate notification service
        logger.info(f"Block notification sent for order {order_data.order_id}")
        return {"notification_sent": True, "channels": ["email", "sms"]}
    
    async def _add_to_review_queue(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Add order to manual review queue"""
        await asyncio.sleep(0.005)  # Simulate queue service
        logger.info(f"Added order {order_data.order_id} to review queue")
        return {"added_to_queue": True, "queue_position": 1, "estimated_review_time": "2 hours"}
    
    async def _send_review_alert(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Send alert to review team"""
        await asyncio.sleep(0.005)  # Simulate alerting service
        logger.info(f"Review alert sent for order {order_data.order_id}")
        return {"alert_sent": True, "recipients": ["fraud-team@company.com"]}
    
    async def _update_user_risk_score(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Update user risk score"""
        await asyncio.sleep(0.005)  # Simulate user service API
        logger.info(f"Risk score updated for user {order_data.user_key}")
        return {"risk_score_updated": True, "new_score": fraud_result.fraud_score}
    
    async def _add_to_monitoring_list(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Add user to monitoring list"""
        await asyncio.sleep(0.005)  # Simulate monitoring service
        logger.info(f"User {order_data.user_key} added to monitoring")
        return {"monitoring_added": True, "monitoring_id": str(uuid.uuid4())}
    
    async def _set_monitoring_criteria(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Set monitoring criteria for user"""
        criteria = [
            "order_frequency",
            "payment_methods", 
            "delivery_locations"
        ]
        
        if fraud_result.fraud_score > 0.7:
            criteria.extend(["order_amounts", "device_fingerprints"])
        
        await asyncio.sleep(0.005)  # Simulate criteria service
        logger.info(f"Monitoring criteria set for user {order_data.user_key}")
        return {"criteria_set": True, "criteria": criteria}
    
    # Logging methods
    async def _log_block_action(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Log block action for audit"""
        audit_entry = {
            "action": "BLOCK",
            "order_id": order_data.order_id,
            "user_id": order_data.user_key,
            "fraud_score": fraud_result.fraud_score,
            "reasoning": fraud_result.reasoning,
            "timestamp": datetime.now().isoformat()
        }
        
        # In production, this would write to audit log system
        logger.info(f"Block action logged: {json.dumps(audit_entry)}")
        return {"audit_logged": True}
    
    async def _log_flag_action(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Log flag action for audit"""
        audit_entry = {
            "action": "FLAG",
            "order_id": order_data.order_id,
            "user_id": order_data.user_key,
            "fraud_score": fraud_result.fraud_score,
            "reasoning": fraud_result.reasoning,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Flag action logged: {json.dumps(audit_entry)}")
        return {"audit_logged": True}
    
    async def _log_monitor_action(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Log monitor action for audit"""
        audit_entry = {
            "action": "MONITOR",
            "order_id": order_data.order_id,
            "user_id": order_data.user_key,
            "fraud_score": fraud_result.fraud_score,
            "reasoning": fraud_result.reasoning,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Monitor action logged: {json.dumps(audit_entry)}")
        return {"audit_logged": True}
    
    async def _log_allow_action(self, order_data: OrderData, fraud_result: FraudResult) -> Dict[str, Any]:
        """Log allow action for audit"""
        audit_entry = {
            "action": "ALLOW",
            "order_id": order_data.order_id,
            "user_id": order_data.user_key,
            "fraud_score": fraud_result.fraud_score,
            "reasoning": fraud_result.reasoning,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Allow action logged: {json.dumps(audit_entry)}")
        return {"audit_logged": True}
    
    def _get_action_type(self, decision: FraudDecision) -> ActionType:
        """Map fraud decision to action type"""
        mapping = {
            FraudDecision.BLOCK: ActionType.BLOCK_ORDER,
            FraudDecision.FLAG: ActionType.FLAG_FOR_REVIEW,
            FraudDecision.REQUIRE_HUMAN: ActionType.FLAG_FOR_REVIEW,  # Same as FLAG
            FraudDecision.MONITOR: ActionType.MONITOR_USER,
            FraudDecision.ALLOW: ActionType.LOG_DECISION
        }
        return mapping.get(decision, ActionType.LOG_DECISION)
    
    def get_execution_summary(self) -> ActionExecutionSummary:
        """Get action execution summary"""
        return self.execution_summary
    
    def get_recent_actions(self, limit: int = 50) -> List[ActionResult]:
        """Get recent action results"""
        return self.action_history[-limit:]
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """Get action execution statistics"""
        if not self.action_history:
            return {
                "total_actions": 0,
                "success_rate": 0.0,
                "avg_execution_time_ms": 0.0,
                "actions_by_type": {},
                "actions_by_status": {}
            }
        
        total_actions = len(self.action_history)
        successful_actions = sum(1 for a in self.action_history if a.is_successful())
        
        # Execution times
        execution_times = [a.execution_time_ms for a in self.action_history if a.execution_time_ms > 0]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Actions by type
        actions_by_type = {}
        for action in self.action_history:
            action_type = action.action_type.value
            actions_by_type[action_type] = actions_by_type.get(action_type, 0) + 1
        
        # Actions by status
        actions_by_status = {}
        for action in self.action_history:
            status = action.status.value
            actions_by_status[status] = actions_by_status.get(status, 0) + 1
        
        return {
            "total_actions": total_actions,
            "success_rate": successful_actions / total_actions,
            "avg_execution_time_ms": avg_execution_time,
            "actions_by_type": actions_by_type,
            "actions_by_status": actions_by_status,
            "total_loss_prevented_usd": sum(a.estimated_loss_prevented_usd for a in self.action_history)
        }
    
    async def execute_bulk_actions(self, fraud_results: List[FraudResult], order_data_list: List[OrderData]) -> List[ActionResult]:
        """Execute multiple fraud actions in parallel"""
        logger.info(f"Executing {len(fraud_results)} fraud actions in bulk")
        
        # Create tasks for parallel execution
        action_tasks = [
            self.execute_fraud_action(fraud_result, order_data)
            for fraud_result, order_data in zip(fraud_results, order_data_list)
        ]
        
        # Execute all actions concurrently
        start_time = time.time()
        results = await asyncio.gather(*action_tasks, return_exceptions=True)
        
        execution_time = time.time() - start_time
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        logger.info(f"Bulk action execution completed in {execution_time:.3f}s: {len(successful_results)}/{len(results)} successful")
        
        # Return only successful results, log exceptions
        action_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Bulk action {i} failed: {result}")
                # Create error result
                error_result = ActionResult(
                    action_id=str(uuid.uuid4()),
                    action_type=ActionType.LOG_DECISION,
                    order_id=order_data_list[i].order_id,
                    user_id=order_data_list[i].user_key,
                    status=ActionStatus.FAILED,
                    error_message=str(result)
                )
                action_results.append(error_result)
            else:
                action_results.append(result)
        
        return action_results