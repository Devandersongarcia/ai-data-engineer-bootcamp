"""
Analytics Data Models
Defines data structures and metrics for advanced analytics dashboard
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

@dataclass
class FraudMetrics:
    """Core fraud detection metrics"""
    # Real-time metrics
    total_orders: int = 0
    fraud_detected: int = 0
    fraud_rate: float = 0.0
    false_positives: int = 0
    false_positive_rate: float = 0.0
    
    # Risk distribution
    high_risk_orders: int = 0
    medium_risk_orders: int = 0
    low_risk_orders: int = 0
    
    # Agent performance
    agent_analyses: int = 0
    avg_agent_response_time: float = 0.0
    agent_success_rate: float = 0.0
    
    # Pattern detection
    velocity_fraud: int = 0
    payment_fraud: int = 0
    account_takeover: int = 0
    new_user_fraud: int = 0
    
    # Financial impact
    total_order_value: float = 0.0
    blocked_fraud_value: float = 0.0
    potential_loss_prevented: float = 0.0
    
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class StreamingMetrics:
    """Spark streaming performance metrics"""
    # Throughput metrics
    records_per_second: float = 0.0
    batches_processed: int = 0
    avg_batch_size: float = 0.0
    avg_batch_processing_time: float = 0.0
    
    # Latency metrics
    end_to_end_latency_ms: float = 0.0
    enrichment_latency_ms: float = 0.0
    agent_latency_ms: float = 0.0
    
    # Resource utilization
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    kafka_lag: int = 0
    
    # Error rates
    processing_errors: int = 0
    error_rate: float = 0.0
    
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class UserRiskProfile:
    """User risk analytics"""
    user_id: str
    total_orders: int
    avg_order_value: float
    fraud_history: List[Dict[str, Any]]
    risk_score: float
    account_age_days: int
    last_order: Optional[datetime] = None
    risk_trend: str = "stable"  # increasing, decreasing, stable

@dataclass
class PatternAnalytics:
    """Fraud pattern analytics"""
    pattern_type: str
    detection_count: int
    success_rate: float
    false_positive_rate: float
    avg_confidence: float
    trend: str = "stable"
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

@dataclass
class TimeSeriesMetric:
    """Time series data point"""
    timestamp: datetime
    metric_name: str
    metric_value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class AnalyticsDataModel:
    """Centralized analytics data model"""
    
    def __init__(self):
        self.fraud_metrics = FraudMetrics()
        self.streaming_metrics = StreamingMetrics()
        self.user_profiles: Dict[str, UserRiskProfile] = {}
        self.pattern_analytics: Dict[str, PatternAnalytics] = {}
        self.time_series: List[TimeSeriesMetric] = []
        
        # Historical data storage
        self.metrics_history: List[FraudMetrics] = []
        self.streaming_history: List[StreamingMetrics] = []
    
    def update_fraud_metrics(self, new_metrics: FraudMetrics):
        """Update fraud metrics and store history"""
        self.metrics_history.append(self.fraud_metrics)
        self.fraud_metrics = new_metrics
        
        # Keep last 1000 records
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def update_streaming_metrics(self, new_metrics: StreamingMetrics):
        """Update streaming metrics and store history"""
        self.streaming_history.append(self.streaming_metrics)
        self.streaming_metrics = new_metrics
        
        # Keep last 1000 records
        if len(self.streaming_history) > 1000:
            self.streaming_history = self.streaming_history[-1000:]
    
    def add_user_profile(self, profile: UserRiskProfile):
        """Add or update user profile"""
        self.user_profiles[profile.user_id] = profile
    
    def add_pattern_analytics(self, pattern: PatternAnalytics):
        """Add or update pattern analytics"""
        self.pattern_analytics[pattern.pattern_type] = pattern
    
    def add_time_series_point(self, metric: TimeSeriesMetric):
        """Add time series data point"""
        self.time_series.append(metric)
        
        # Keep last 10000 points
        if len(self.time_series) > 10000:
            self.time_series = self.time_series[-10000:]
    
    def get_fraud_trend(self, hours: int = 24) -> pd.DataFrame:
        """Get fraud rate trend for last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff]
        if not recent_metrics:
            return pd.DataFrame()
        
        data = []
        for metric in recent_metrics:
            data.append({
                'timestamp': metric.timestamp,
                'fraud_rate': metric.fraud_rate,
                'total_orders': metric.total_orders,
                'fraud_detected': metric.fraud_detected
            })
        
        return pd.DataFrame(data)
    
    def get_performance_trend(self, hours: int = 24) -> pd.DataFrame:
        """Get streaming performance trend"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [m for m in self.streaming_history if m.timestamp >= cutoff]
        if not recent_metrics:
            return pd.DataFrame()
        
        data = []
        for metric in recent_metrics:
            data.append({
                'timestamp': metric.timestamp,
                'latency_ms': metric.end_to_end_latency_ms,
                'throughput_rps': metric.records_per_second,
                'error_rate': metric.error_rate
            })
        
        return pd.DataFrame(data)
    
    def get_top_risk_users(self, limit: int = 10) -> List[UserRiskProfile]:
        """Get top risk users"""
        sorted_users = sorted(
            self.user_profiles.values(), 
            key=lambda x: x.risk_score, 
            reverse=True
        )
        return sorted_users[:limit]
    
    def get_pattern_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """Get pattern detection effectiveness"""
        effectiveness = {}
        for pattern_type, analytics in self.pattern_analytics.items():
            effectiveness[pattern_type] = {
                'detection_count': analytics.detection_count,
                'success_rate': analytics.success_rate,
                'false_positive_rate': analytics.false_positive_rate,
                'avg_confidence': analytics.avg_confidence
            }
        return effectiveness
    
    def generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate system alerts based on current metrics"""
        alerts = []
        
        # High fraud rate alert
        if self.fraud_metrics.fraud_rate > 0.15:  # 15% threshold
            alerts.append({
                'type': 'HIGH_FRAUD_RATE',
                'severity': 'CRITICAL',
                'message': f'Fraud rate is {self.fraud_metrics.fraud_rate:.1%} (threshold: 15%)',
                'timestamp': datetime.now()
            })
        
        # High latency alert
        if self.streaming_metrics.end_to_end_latency_ms > 5000:  # 5 second threshold
            alerts.append({
                'type': 'HIGH_LATENCY',
                'severity': 'WARNING', 
                'message': f'End-to-end latency is {self.streaming_metrics.end_to_end_latency_ms:.0f}ms',
                'timestamp': datetime.now()
            })
        
        # Low throughput alert
        if self.streaming_metrics.records_per_second < 10:
            alerts.append({
                'type': 'LOW_THROUGHPUT',
                'severity': 'WARNING',
                'message': f'Throughput is {self.streaming_metrics.records_per_second:.1f} records/sec',
                'timestamp': datetime.now()
            })
        
        # Agent performance alert
        if self.fraud_metrics.agent_success_rate < 0.8:  # 80% threshold
            alerts.append({
                'type': 'AGENT_PERFORMANCE',
                'severity': 'WARNING',
                'message': f'Agent success rate is {self.fraud_metrics.agent_success_rate:.1%}',
                'timestamp': datetime.now()
            })
        
        return alerts