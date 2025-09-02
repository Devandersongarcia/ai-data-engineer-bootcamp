"""
Transaction Boundary Logging for UberEats Fraud Detection
Provides comprehensive transaction tracking with performance metrics and audit trails
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from src.correlation import get_correlation_id, get_order_context, CorrelationLogger

class TransactionType(Enum):
    """Transaction types for fraud detection pipeline"""
    ORDER_INGESTION = "order_ingestion"
    DATA_ENRICHMENT = "data_enrichment" 
    FEATURE_EXTRACTION = "feature_extraction"
    AGENT_ANALYSIS = "agent_analysis"
    RISK_SCORING = "risk_scoring"
    DECISION_ENGINE = "decision_engine"
    NOTIFICATION = "notification"
    AUDIT_LOG = "audit_log"

class TransactionStatus(Enum):
    """Transaction status enumeration"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRY = "retry"

@dataclass
class TransactionMetrics:
    """Transaction performance and business metrics"""
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    records_processed: int = 0
    bytes_processed: int = 0
    error_count: int = 0
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TransactionContext:
    """Transaction context information"""
    transaction_id: str
    transaction_type: TransactionType
    parent_transaction_id: Optional[str] = None
    user_id: Optional[str] = None
    order_id: Optional[str] = None
    batch_id: Optional[str] = None
    component: Optional[str] = None
    version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['transaction_type'] = self.transaction_type.value
        return result

class TransactionLogger:
    """Transaction boundary logger with performance tracking"""
    
    def __init__(self, 
                 transaction_type: TransactionType,
                 transaction_id: Optional[str] = None,
                 parent_transaction_id: Optional[str] = None,
                 component: Optional[str] = None):
        self.context = TransactionContext(
            transaction_id=transaction_id or self._generate_transaction_id(),
            transaction_type=transaction_type,
            parent_transaction_id=parent_transaction_id,
            component=component or transaction_type.value
        )
        
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.status: TransactionStatus = TransactionStatus.STARTED
        self.metrics = TransactionMetrics(duration_ms=0.0)
        self.checkpoints: List[Dict[str, Any]] = []
        
        self.logger = CorrelationLogger(f'transaction.{transaction_type.value}')
        
    @staticmethod
    def _generate_transaction_id() -> str:
        """Generate unique transaction ID"""
        timestamp = int(time.time() * 1000)
        return f"txn_{timestamp}_{hash(time.time()) % 10000:04d}"
    
    def start(self, **context_data) -> 'TransactionLogger':
        """Start transaction tracking"""
        self.start_time = time.time()
        self.status = TransactionStatus.IN_PROGRESS
        
        # Update context with additional data
        for key, value in context_data.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        
        # Enrich from correlation context
        order_context = get_order_context()
        if order_context:
            self.context.order_id = order_context.get('order_id')
            self.context.user_id = order_context.get('user_id')
        
        self._log_transaction_start()
        return self
    
    def checkpoint(self, checkpoint_name: str, **checkpoint_data):
        """Log transaction checkpoint"""
        if not self.start_time:
            return
            
        checkpoint_time = time.time()
        duration_from_start = (checkpoint_time - self.start_time) * 1000
        
        checkpoint = {
            'checkpoint_name': checkpoint_name,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'duration_from_start_ms': round(duration_from_start, 2),
            'data': checkpoint_data
        }
        
        self.checkpoints.append(checkpoint)
        
        self.logger.debug(
            f"Transaction checkpoint: {checkpoint_name}",
            transaction_context=self.context.to_dict(),
            checkpoint=checkpoint
        )
    
    def update_metrics(self, **metrics_data):
        """Update transaction metrics"""
        for key, value in metrics_data.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
    
    def success(self, **success_data) -> Dict[str, Any]:
        """Complete transaction successfully"""
        return self._complete(TransactionStatus.SUCCESS, **success_data)
    
    def failure(self, error: Exception, **failure_data) -> Dict[str, Any]:
        """Complete transaction with failure"""
        failure_data['error'] = {
            'type': type(error).__name__,
            'message': str(error),
            'traceback': self._get_traceback_summary(error)
        }
        return self._complete(TransactionStatus.FAILED, **failure_data)
    
    def timeout(self, **timeout_data) -> Dict[str, Any]:
        """Complete transaction with timeout"""
        return self._complete(TransactionStatus.TIMEOUT, **timeout_data)
    
    def _complete(self, status: TransactionStatus, **completion_data) -> Dict[str, Any]:
        """Complete transaction with given status"""
        if not self.start_time:
            return {}
            
        self.end_time = time.time()
        self.status = status
        self.metrics.duration_ms = (self.end_time - self.start_time) * 1000
        
        transaction_result = {
            'transaction_id': self.context.transaction_id,
            'status': status.value,
            'duration_ms': round(self.metrics.duration_ms, 2),
            'success': status == TransactionStatus.SUCCESS
        }
        
        self._log_transaction_end(completion_data)
        
        return transaction_result
    
    def _log_transaction_start(self):
        """Log transaction start event"""
        self.logger.info(
            f"Transaction started: {self.context.transaction_type.value}",
            business_event={
                'type': 'TRANSACTION_START',
                'transaction_id': self.context.transaction_id,
                'transaction_type': self.context.transaction_type.value,
                'parent_transaction_id': self.context.parent_transaction_id,
                'component': self.context.component,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            transaction_context=self.context.to_dict()
        )
    
    def _log_transaction_end(self, completion_data: Dict[str, Any]):
        """Log transaction completion event"""
        log_level = logging.INFO if self.status == TransactionStatus.SUCCESS else logging.ERROR
        
        business_event = {
            'type': 'TRANSACTION_END',
            'transaction_id': self.context.transaction_id,
            'transaction_type': self.context.transaction_type.value,
            'status': self.status.value,
            'duration_ms': round(self.metrics.duration_ms, 2),
            'checkpoints_count': len(self.checkpoints),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add metrics if available
        if self.metrics.records_processed > 0:
            business_event['records_processed'] = self.metrics.records_processed
        
        if self.metrics.error_count > 0:
            business_event['error_count'] = self.metrics.error_count
        
        if log_level >= logging.ERROR:
            self.logger.error(
                f"Transaction completed: {self.context.transaction_type.value} - {self.status.value.upper()}",
                business_event=business_event,
                transaction_context=self.context.to_dict(),
                transaction_metrics=self.metrics.to_dict(),
                checkpoints=self.checkpoints[-5:],  # Last 5 checkpoints
                completion_data=completion_data
            )
        else:
            self.logger.info(
                f"Transaction completed: {self.context.transaction_type.value} - {self.status.value.upper()}",
                business_event=business_event,
                transaction_context=self.context.to_dict(),
                transaction_metrics=self.metrics.to_dict(),
                checkpoints=self.checkpoints[-5:],  # Last 5 checkpoints
                completion_data=completion_data
            )
    
    def _get_traceback_summary(self, error: Exception) -> str:
        """Get concise traceback summary"""
        import traceback
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        return ''.join(tb_lines[-3:]).strip()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type:
            self.failure(exc_val)
        else:
            self.success()

class BatchTransactionLogger:
    """Logger for batch processing transactions"""
    
    def __init__(self, batch_id: str, batch_size: int, transaction_type: TransactionType):
        self.batch_id = batch_id
        self.batch_size = batch_size
        self.transaction_type = transaction_type
        self.logger = CorrelationLogger(f'batch.{transaction_type.value}')
        
        self.start_time: Optional[float] = None
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.individual_transactions: List[str] = []
    
    def start_batch(self):
        """Start batch processing"""
        self.start_time = time.time()
        
        self.logger.info(
            f"Batch processing started: {self.transaction_type.value}",
            business_event={
                'type': 'BATCH_START',
                'batch_id': self.batch_id,
                'batch_size': self.batch_size,
                'transaction_type': self.transaction_type.value,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            batch_context={
                'batch_id': self.batch_id,
                'batch_size': self.batch_size,
                'processing_type': 'batch'
            }
        )
    
    def log_item_processed(self, item_id: str, success: bool, transaction_id: Optional[str] = None):
        """Log individual item processing"""
        self.processed_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            
        if transaction_id:
            self.individual_transactions.append(transaction_id)
    
    def complete_batch(self, **completion_data):
        """Complete batch processing"""
        if not self.start_time:
            return
            
        duration_ms = (time.time() - self.start_time) * 1000
        success_rate = (self.success_count / self.processed_count) if self.processed_count > 0 else 0
        
        self.logger.info(
            f"Batch processing completed: {self.transaction_type.value}",
            business_event={
                'type': 'BATCH_END',
                'batch_id': self.batch_id,
                'transaction_type': self.transaction_type.value,
                'duration_ms': round(duration_ms, 2),
                'processed_count': self.processed_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': round(success_rate, 3),
                'throughput_per_second': round(self.processed_count / (duration_ms / 1000), 2) if duration_ms > 0 else 0,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            batch_metrics={
                'batch_size': self.batch_size,
                'processed_count': self.processed_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': success_rate,
                'duration_ms': duration_ms
            },
            completion_data=completion_data
        )

def create_transaction_logger(transaction_type: TransactionType, **kwargs) -> TransactionLogger:
    """Factory function to create transaction logger"""
    return TransactionLogger(transaction_type, **kwargs)

def create_batch_logger(batch_id: str, batch_size: int, transaction_type: TransactionType) -> BatchTransactionLogger:
    """Factory function to create batch transaction logger"""
    return BatchTransactionLogger(batch_id, batch_size, transaction_type)

# Convenience functions for common transaction types

def log_order_ingestion() -> TransactionLogger:
    """Create logger for order ingestion transaction"""
    return create_transaction_logger(TransactionType.ORDER_INGESTION, component="kafka_ingestion")

def log_data_enrichment() -> TransactionLogger:
    """Create logger for data enrichment transaction"""
    return create_transaction_logger(TransactionType.DATA_ENRICHMENT, component="enrichment_service")

def log_agent_analysis() -> TransactionLogger:
    """Create logger for agent analysis transaction"""  
    return create_transaction_logger(TransactionType.AGENT_ANALYSIS, component="crewai_agents")

def log_risk_scoring() -> TransactionLogger:
    """Create logger for risk scoring transaction"""
    return create_transaction_logger(TransactionType.RISK_SCORING, component="risk_engine")

def log_decision_engine() -> TransactionLogger:
    """Create logger for decision engine transaction"""
    return create_transaction_logger(TransactionType.DECISION_ENGINE, component="decision_service")