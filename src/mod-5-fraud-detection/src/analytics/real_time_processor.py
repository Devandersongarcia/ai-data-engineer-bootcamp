"""
Real-time Analytics Processor
Connects to Spark streaming pipeline and processes analytics data
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analytics.data_models import (
    AnalyticsDataModel, FraudMetrics, StreamingMetrics, 
    UserRiskProfile, PatternAnalytics, TimeSeriesMetric
)
from config.settings import settings

logger = logging.getLogger(__name__)

class RealTimeAnalyticsProcessor:
    """Processes real-time analytics from Spark streaming pipeline"""
    
    def __init__(self):
        self.data_model = AnalyticsDataModel()
        self.redis_client = self._init_redis()
        self.running = False
        self.processing_thread = None
        
        # Metrics aggregation
        self.order_buffer = deque(maxlen=1000)
        self.metrics_buffer = deque(maxlen=100)
        self.pattern_counters = defaultdict(int)
        
        # Performance tracking
        self.last_update = datetime.now()
        self.update_interval = 30  # seconds
        
        logger.info("🔍 RealTimeAnalyticsProcessor initialized")
    
    def _init_redis(self):
        """Initialize Redis connection for real-time data"""
        if not REDIS_AVAILABLE:
            logger.info("📊 Redis not available, using in-memory analytics processing")
            return None
        
        try:
            redis_client = redis.from_url(
                settings.redis.url,
                password=settings.redis.password if settings.redis.password else None,
                db=settings.redis.db
            )
            redis_client.ping()
            logger.info("✅ Connected to Redis for analytics")
            return redis_client
        except Exception as e:
            logger.info(f"📊 Redis not available ({e}), using in-memory analytics processing")
            return None
    
    def start_processing(self):
        """Start real-time processing thread"""
        if self.running:
            logger.warning("Analytics processor already running")
            return
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("✅ Real-time analytics processing started")
    
    def stop_processing(self):
        """Stop real-time processing"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("🛑 Real-time analytics processing stopped")
    
    def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Update metrics every interval
                if (datetime.now() - self.last_update).seconds >= self.update_interval:
                    self._update_metrics()
                    self.last_update = datetime.now()
                
                # Process new data from Redis/memory
                self._process_new_data()
                
                time.sleep(1)  # 1 second processing cycle
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(5)
    
    def _process_new_data(self):
        """Process new data from streaming pipeline"""
        if not self.redis_client:
            # Simulate data processing for demo
            self._simulate_streaming_data()
            return
        
        try:
            # Read from Redis streams/queues
            # This connects to your Spark pipeline output
            data = self._read_from_redis_streams()
            
            for item in data:
                self._process_order_result(item)
                
        except Exception as e:
            logger.error(f"Error processing new data: {e}")
    
    def _read_from_redis_streams(self) -> List[Dict[str, Any]]:
        """Read from Redis streams (connected to Spark output)"""
        try:
            # Read from fraud detection results stream
            result = self.redis_client.xread({
                'fraud_results': '$'  # Read new messages
            }, count=10, block=100)
            
            data = []
            for stream, messages in result:
                for message_id, fields in messages:
                    try:
                        # Decode and parse message
                        order_data = {}
                        for key, value in fields.items():
                            order_data[key.decode()] = json.loads(value.decode())
                        data.append(order_data)
                    except Exception as e:
                        logger.error(f"Error parsing Redis message: {e}")
            
            return data
            
        except Exception as e:
            logger.debug(f"Redis read error (normal if no new data): {e}")
            return []
    
    def _simulate_streaming_data(self):
        """Simulate streaming data for development"""
        import random
        
        # Simulate 1-5 orders per processing cycle
        num_orders = random.randint(1, 5)
        
        for _ in range(num_orders):
            # Create realistic fraud detection result
            order_result = {
                'order_id': f"sim_{int(time.time())}_{random.randint(1000, 9999)}",
                'user_id': f"user_{random.randint(100, 999)}",
                'total_amount': round(random.uniform(15.0, 300.0), 2),
                'fraud_score': random.uniform(0.0, 1.0),
                'recommended_action': random.choices([
                    'ALLOW', 'MONITOR', 'CHALLENGE', 'BLOCK'
                ], weights=[60, 25, 10, 5])[0],
                'patterns_detected': random.choices([
                    ['velocity_fraud'], ['payment_fraud'], ['new_user_risk'], 
                    ['account_takeover'], []
                ], weights=[10, 15, 20, 5, 50])[0],
                'processing_time_ms': random.randint(50, 500),
                'agent_analysis': random.choice([True, False]),
                'timestamp': datetime.now().isoformat()
            }
            
            self._process_order_result(order_result)
    
    def _process_order_result(self, order_data: Dict[str, Any]):
        """Process a single order result"""
        try:
            # Add to order buffer
            self.order_buffer.append(order_data)
            
            # Update pattern counters
            patterns = order_data.get('patterns_detected', [])
            for pattern in patterns:
                self.pattern_counters[pattern] += 1
            
            # Update user profiles
            self._update_user_profile(order_data)
            
            # Add time series data
            self._add_time_series_data(order_data)
            
        except Exception as e:
            logger.error(f"Error processing order result: {e}")
    
    def _update_user_profile(self, order_data: Dict[str, Any]):
        """Update user risk profile"""
        user_id = order_data.get('user_id')
        if not user_id:
            return
        
        # Get existing profile or create new
        existing_profile = self.data_model.user_profiles.get(user_id)
        
        if existing_profile:
            # Update existing profile
            existing_profile.total_orders += 1
            existing_profile.last_order = datetime.now()
            existing_profile.risk_score = order_data.get('fraud_score', 0.5)
            
            # Update fraud history if fraud detected
            if order_data.get('recommended_action') in ['BLOCK', 'CHALLENGE']:
                existing_profile.fraud_history.append({
                    'order_id': order_data.get('order_id'),
                    'fraud_score': order_data.get('fraud_score'),
                    'timestamp': datetime.now().isoformat(),
                    'action': order_data.get('recommended_action')
                })
        else:
            # Create new profile
            profile = UserRiskProfile(
                user_id=user_id,
                total_orders=1,
                avg_order_value=order_data.get('total_amount', 0),
                fraud_history=[],
                risk_score=order_data.get('fraud_score', 0.5),
                account_age_days=30,  # Default
                last_order=datetime.now()
            )
            self.data_model.add_user_profile(profile)
    
    def _add_time_series_data(self, order_data: Dict[str, Any]):
        """Add time series metrics"""
        timestamp = datetime.now()
        
        # Fraud score time series
        fraud_metric = TimeSeriesMetric(
            timestamp=timestamp,
            metric_name='fraud_score',
            metric_value=order_data.get('fraud_score', 0.5),
            metadata={'order_id': order_data.get('order_id')}
        )
        self.data_model.add_time_series_point(fraud_metric)
        
        # Processing time series
        processing_time = order_data.get('processing_time_ms', 0)
        latency_metric = TimeSeriesMetric(
            timestamp=timestamp,
            metric_name='processing_latency_ms',
            metric_value=processing_time,
            metadata={'agent_analysis': order_data.get('agent_analysis', False)}
        )
        self.data_model.add_time_series_point(latency_metric)
    
    def _update_metrics(self):
        """Update aggregated metrics"""
        try:
            # Calculate fraud metrics from recent orders
            recent_orders = list(self.order_buffer)
            if not recent_orders:
                return
            
            total_orders = len(recent_orders)
            fraud_detected = sum(1 for order in recent_orders 
                               if order.get('recommended_action') in ['BLOCK', 'CHALLENGE'])
            
            fraud_rate = fraud_detected / total_orders if total_orders > 0 else 0
            
            # Pattern detection counts
            velocity_fraud = self.pattern_counters.get('velocity_fraud', 0)
            payment_fraud = self.pattern_counters.get('payment_fraud', 0)
            account_takeover = self.pattern_counters.get('account_takeover', 0)
            new_user_fraud = self.pattern_counters.get('new_user_risk', 0)
            
            # Agent performance
            agent_orders = [order for order in recent_orders if order.get('agent_analysis')]
            agent_analyses = len(agent_orders)
            avg_agent_time = sum(order.get('processing_time_ms', 0) for order in agent_orders) / len(agent_orders) if agent_orders else 0
            
            # Financial metrics
            total_value = sum(order.get('total_amount', 0) for order in recent_orders)
            blocked_value = sum(order.get('total_amount', 0) for order in recent_orders 
                              if order.get('recommended_action') == 'BLOCK')
            
            # Create fraud metrics
            fraud_metrics = FraudMetrics(
                total_orders=total_orders,
                fraud_detected=fraud_detected,
                fraud_rate=fraud_rate,
                high_risk_orders=sum(1 for order in recent_orders if order.get('fraud_score', 0) > 0.7),
                medium_risk_orders=sum(1 for order in recent_orders if 0.3 < order.get('fraud_score', 0) <= 0.7),
                low_risk_orders=sum(1 for order in recent_orders if order.get('fraud_score', 0) <= 0.3),
                agent_analyses=agent_analyses,
                avg_agent_response_time=avg_agent_time,
                agent_success_rate=0.95,  # Calculate based on actual feedback
                velocity_fraud=velocity_fraud,
                payment_fraud=payment_fraud,
                account_takeover=account_takeover,
                new_user_fraud=new_user_fraud,
                total_order_value=total_value,
                blocked_fraud_value=blocked_value,
                potential_loss_prevented=blocked_value * 0.8  # Estimated
            )
            
            # Create streaming metrics
            avg_processing_time = sum(order.get('processing_time_ms', 0) for order in recent_orders) / len(recent_orders)
            
            streaming_metrics = StreamingMetrics(
                records_per_second=total_orders / 30,  # Last 30 seconds
                batches_processed=max(1, total_orders // 10),  # Estimate batch count
                avg_batch_size=10,  # Typical batch size
                avg_batch_processing_time=avg_processing_time,
                end_to_end_latency_ms=avg_processing_time,
                enrichment_latency_ms=avg_processing_time * 0.3,
                agent_latency_ms=avg_agent_time,
                error_rate=0.02  # 2% error rate estimate
            )
            
            # Update data model
            self.data_model.update_fraud_metrics(fraud_metrics)
            self.data_model.update_streaming_metrics(streaming_metrics)
            
            logger.debug(f"📊 Metrics updated: {total_orders} orders, {fraud_rate:.1%} fraud rate")
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    def get_current_data(self) -> AnalyticsDataModel:
        """Get current analytics data model"""
        return self.data_model
    
    def get_recent_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent orders for detailed analysis"""
        return list(self.order_buffer)[-limit:]
    
    def reset_pattern_counters(self):
        """Reset pattern counters (useful for periodic resets)"""
        self.pattern_counters.clear()
        logger.info("Pattern counters reset")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'orders_in_buffer': len(self.order_buffer),
            'patterns_detected': dict(self.pattern_counters),
            'users_tracked': len(self.data_model.user_profiles),
            'time_series_points': len(self.data_model.time_series),
            'redis_connected': self.redis_client is not None,
            'processing_active': self.running,
            'last_update': self.last_update.isoformat()
        }