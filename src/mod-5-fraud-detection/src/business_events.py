"""
Business Event Logging System for UberEats Fraud Detection
Captures critical fraud detection business events with rich context
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from src.correlation import get_correlation_id, get_order_context, CorrelationLogger

class FraudEventType(Enum):
    """Types of fraud detection business events"""
    
    # Order Processing Events
    ORDER_RECEIVED = "order_received"
    ORDER_VALIDATED = "order_validated"
    ORDER_ENRICHED = "order_enriched"
    
    # Risk Assessment Events
    RISK_ANALYSIS_STARTED = "risk_analysis_started"
    RISK_SCORE_CALCULATED = "risk_score_calculated"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"
    
    # Fraud Detection Events
    FRAUD_PATTERN_DETECTED = "fraud_pattern_detected"
    FRAUD_RULE_TRIGGERED = "fraud_rule_triggered"
    AGENT_RECOMMENDATION = "agent_recommendation"
    
    # Decision Events
    ORDER_APPROVED = "order_approved"
    ORDER_REJECTED = "order_rejected"
    ORDER_FLAGGED = "order_flagged"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    
    # Security Events
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    ACCOUNT_COMPROMISE = "account_compromise"
    PAYMENT_FRAUD = "payment_fraud"
    DELIVERY_FRAUD = "delivery_fraud"
    PROMO_ABUSE = "promo_abuse"
    
    # Compliance Events
    AUDIT_TRAIL_CREATED = "audit_trail_created"
    COMPLIANCE_CHECK = "compliance_check"
    REGULATORY_REPORT = "regulatory_report"

class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionType(Enum):
    """Recommended actions"""
    APPROVE = "approve"
    REJECT = "reject"
    FLAG = "flag"
    MONITOR = "monitor"
    MANUAL_REVIEW = "manual_review"
    BLOCK_USER = "block_user"
    BLOCK_PAYMENT = "block_payment"

@dataclass
class FraudPatternInfo:
    """Information about detected fraud patterns"""
    pattern_name: str
    confidence_score: float
    pattern_type: str
    evidence: List[str]
    severity: RiskLevel
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['severity'] = self.severity.value
        return result

@dataclass
class RiskAssessment:
    """Risk assessment information"""
    risk_score: float
    risk_level: RiskLevel
    contributing_factors: List[str]
    mitigation_actions: List[ActionType]
    confidence: float
    model_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['risk_level'] = self.risk_level.value
        result['mitigation_actions'] = [action.value for action in self.mitigation_actions]
        return result

@dataclass
class BusinessEventContext:
    """Context information for business events"""
    event_id: str
    event_type: FraudEventType
    timestamp: str
    source_component: str
    
    # Order context
    order_id: Optional[str] = None
    user_id: Optional[str] = None
    restaurant_id: Optional[str] = None
    order_amount: Optional[float] = None
    
    # Session context
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Processing context
    batch_id: Optional[str] = None
    processing_stage: Optional[str] = None
    model_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['event_type'] = self.event_type.value
        return result

class BusinessEventLogger:
    """Logger for fraud detection business events"""
    
    def __init__(self, component: str):
        self.component = component
        self.logger = CorrelationLogger(f'business_events.{component}')
        self.event_counter = 0
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        self.event_counter += 1
        timestamp = int(time.time() * 1000)
        return f"evt_{self.component}_{timestamp}_{self.event_counter:04d}"
    
    def _create_base_context(self, event_type: FraudEventType, **kwargs) -> BusinessEventContext:
        """Create base event context"""
        context = BusinessEventContext(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            source_component=self.component
        )
        
        # Enrich from correlation context
        order_context = get_order_context()
        if order_context:
            context.order_id = order_context.get('order_id')
            context.user_id = order_context.get('user_id')
            context.restaurant_id = order_context.get('restaurant_id')
            context.order_amount = order_context.get('amount')
        
        # Update with provided kwargs
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        return context
    
    def log_order_received(self, order_data: Dict[str, Any]):
        """Log order received event"""
        context = self._create_base_context(
            FraudEventType.ORDER_RECEIVED,
            order_id=order_data.get('order_id'),
            user_id=order_data.get('user_id'),
            restaurant_id=order_data.get('restaurant_id'),
            order_amount=order_data.get('total_amount')
        )
        
        self.logger.info(
            f"Order received: {context.order_id}",
            business_event=context.to_dict(),
            order_details={
                'total_amount': order_data.get('total_amount'),
                'payment_method': order_data.get('payment_method'),
                'item_count': order_data.get('item_count'),
                'delivery_address': order_data.get('delivery_address', {}).get('city'),
                'promo_codes': order_data.get('promo_codes', [])
            }
        )
    
    def log_risk_assessment(self, risk_assessment: RiskAssessment, **context_data):
        """Log risk assessment event"""
        context = self._create_base_context(
            FraudEventType.RISK_SCORE_CALCULATED,
            **context_data
        )
        
        log_level = logging.WARNING if risk_assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else logging.INFO
        
        if log_level >= logging.WARNING:
            self.logger.warning(
                f"Risk assessment completed - Score: {risk_assessment.risk_score:.3f}, Level: {risk_assessment.risk_level.value}",
                business_event=context.to_dict(),
                risk_assessment=risk_assessment.to_dict()
            )
        else:
            self.logger.info(
                f"Risk assessment completed - Score: {risk_assessment.risk_score:.3f}, Level: {risk_assessment.risk_level.value}",
                business_event=context.to_dict(),
                risk_assessment=risk_assessment.to_dict()
            )
    
    def log_fraud_pattern_detected(self, pattern_info: FraudPatternInfo, **context_data):
        """Log fraud pattern detection event"""
        context = self._create_base_context(
            FraudEventType.FRAUD_PATTERN_DETECTED,
            **context_data
        )
        
        self.logger.warning(
            f"Fraud pattern detected: {pattern_info.pattern_name} (confidence: {pattern_info.confidence_score:.3f})",
            business_event=context.to_dict(),
            fraud_pattern=pattern_info.to_dict(),
            alert_priority="high" if pattern_info.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL] else "medium"
        )
    
    def log_decision_made(self, action: ActionType, reason: str, confidence: float, **context_data):
        """Log fraud detection decision"""
        context = self._create_base_context(
            FraudEventType.ORDER_APPROVED if action == ActionType.APPROVE else 
            FraudEventType.ORDER_REJECTED if action == ActionType.REJECT else
            FraudEventType.ORDER_FLAGGED,
            **context_data
        )
        
        log_level = logging.WARNING if action in [ActionType.REJECT, ActionType.BLOCK_USER] else logging.INFO
        
        if log_level >= logging.WARNING:
            self.logger.warning(
                f"Decision made: {action.value.upper()} - {reason}",
                business_event=context.to_dict(),
                decision={
                    'action': action.value,
                    'reason': reason,
                    'confidence': confidence,
                    'automated': confidence > 0.8
                }
            )
        else:
            self.logger.info(
                f"Decision made: {action.value.upper()} - {reason}",
                business_event=context.to_dict(),
                decision={
                    'action': action.value,
                    'reason': reason,
                    'confidence': confidence,
                    'automated': confidence > 0.8
                }
            )
    
    def log_agent_recommendation(self, agent_name: str, recommendation: Dict[str, Any], **context_data):
        """Log agent recommendation event"""
        context = self._create_base_context(
            FraudEventType.AGENT_RECOMMENDATION,
            **context_data
        )
        
        self.logger.info(
            f"Agent recommendation: {agent_name} → {recommendation.get('action', 'unknown')}",
            business_event=context.to_dict(),
            agent_analysis={
                'agent_name': agent_name,
                'recommendation': recommendation.get('action'),
                'confidence': recommendation.get('confidence'),
                'reasoning': recommendation.get('reasoning', '')[:200],  # Truncate for performance
                'risk_factors': recommendation.get('risk_factors', [])
            }
        )
    
    def log_suspicious_behavior(self, behavior_type: str, details: Dict[str, Any], severity: RiskLevel, **context_data):
        """Log suspicious behavior detection"""
        context = self._create_base_context(
            FraudEventType.SUSPICIOUS_BEHAVIOR,
            **context_data
        )
        
        log_level = logging.CRITICAL if severity == RiskLevel.CRITICAL else logging.WARNING
        
        if log_level >= logging.CRITICAL:
            self.logger.critical(
                f"Suspicious behavior detected: {behavior_type}",
                business_event=context.to_dict(),
                suspicious_behavior={
                    'behavior_type': behavior_type,
                    'severity': severity.value,
                    'details': details,
                    'requires_immediate_action': severity == RiskLevel.CRITICAL
                }
            )
        else:
            self.logger.warning(
                f"Suspicious behavior detected: {behavior_type}",
                business_event=context.to_dict(),
                suspicious_behavior={
                    'behavior_type': behavior_type,
                    'severity': severity.value,
                    'details': details,
                    'requires_immediate_action': severity == RiskLevel.CRITICAL
                }
            )
    
    def log_compliance_event(self, compliance_type: str, status: str, details: Dict[str, Any], **context_data):
        """Log compliance and audit events"""
        context = self._create_base_context(
            FraudEventType.AUDIT_TRAIL_CREATED,
            **context_data
        )
        
        self.logger.info(
            f"Compliance event: {compliance_type} - {status}",
            business_event=context.to_dict(),
            compliance_info={
                'compliance_type': compliance_type,
                'status': status,
                'details': details,
                'audit_required': True
            }
        )
    
    def log_performance_anomaly(self, metric_name: str, current_value: float, threshold: float, **context_data):
        """Log performance anomaly detection"""
        context = self._create_base_context(
            FraudEventType.SUSPICIOUS_BEHAVIOR,
            **context_data
        )
        
        self.logger.warning(
            f"Performance anomaly: {metric_name} = {current_value:.2f} (threshold: {threshold:.2f})",
            business_event=context.to_dict(),
            performance_anomaly={
                'metric_name': metric_name,
                'current_value': current_value,
                'threshold': threshold,
                'deviation_percent': ((current_value - threshold) / threshold) * 100
            }
        )

# Specialized event loggers for different components

class OrderProcessingEventLogger(BusinessEventLogger):
    """Event logger for order processing pipeline"""
    
    def __init__(self):
        super().__init__('order_processing')
    
    def log_order_validation_failed(self, order_id: str, validation_errors: List[str]):
        """Log order validation failure"""
        self.log_decision_made(
            ActionType.REJECT,
            f"Validation failed: {', '.join(validation_errors)}",
            confidence=1.0,
            order_id=order_id
        )

class AgentEventLogger(BusinessEventLogger):
    """Event logger for CrewAI agents"""
    
    def __init__(self):
        super().__init__('agents')
    
    def log_agent_collaboration(self, primary_agent: str, collaborating_agents: List[str], task: str):
        """Log agent collaboration events"""
        context = self._create_base_context(
            FraudEventType.AGENT_RECOMMENDATION,
            processing_stage="agent_collaboration"
        )
        
        self.logger.debug(
            f"Agent collaboration: {primary_agent} working with {len(collaborating_agents)} agents",
            business_event=context.to_dict(),
            collaboration={
                'primary_agent': primary_agent,
                'collaborating_agents': collaborating_agents,
                'task': task
            }
        )

class RiskEngineEventLogger(BusinessEventLogger):
    """Event logger for risk engine"""
    
    def __init__(self):
        super().__init__('risk_engine')
    
    def log_model_prediction(self, model_name: str, model_version: str, prediction: Dict[str, Any]):
        """Log ML model prediction"""
        context = self._create_base_context(
            FraudEventType.RISK_SCORE_CALCULATED,
            model_version=model_version
        )
        
        self.logger.info(
            f"Model prediction: {model_name} → risk_score={prediction.get('risk_score', 0):.3f}",
            business_event=context.to_dict(),
            model_prediction={
                'model_name': model_name,
                'model_version': model_version,
                'prediction': prediction,
                'feature_importance': prediction.get('feature_importance', {})
            }
        )

# Factory functions for common event loggers

def get_order_event_logger() -> OrderProcessingEventLogger:
    """Get order processing event logger"""
    return OrderProcessingEventLogger()

def get_agent_event_logger() -> AgentEventLogger:
    """Get agent event logger"""
    return AgentEventLogger()

def get_risk_event_logger() -> RiskEngineEventLogger:
    """Get risk engine event logger"""
    return RiskEngineEventLogger()

def get_business_event_logger(component: str) -> BusinessEventLogger:
    """Get generic business event logger"""
    return BusinessEventLogger(component)