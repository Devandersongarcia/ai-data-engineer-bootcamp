"""
Kafka Producer for publishing agent analysis results to Confluent Cloud
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Producer, KafkaException

from .kafka_config import kafka_manager, KAFKA_TOPICS
from .models import (
    ETAPredictionResult, DriverAllocationResult, RouteOptimizationResult,
    DeliveryPlanResult, SystemAlert, AgentMetrics, serialize_result_to_kafka
)

logger = logging.getLogger(__name__)

class UberEatsKafkaProducer:
    """
    Kafka producer for publishing UberEats agent analysis results
    Handles ETA predictions, driver allocations, route optimizations, and system metrics
    """
    
    def __init__(self):
        self.producer = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.pending_messages = 0
        self.delivered_count = 0
        self.error_count = 0
        self.stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'topics_used': set()
        }
    
    async def initialize(self):
        """Initialize the Kafka producer"""
        try:
            self.producer = kafka_manager.create_producer()
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation"""
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            self.error_count += 1
            self.stats['messages_failed'] += 1
        else:
            logger.debug(f"Message delivered to {msg.topic()}[{msg.partition()}] at offset {msg.offset()}")
            self.delivered_count += 1
            self.stats['messages_delivered'] += 1
        
        self.pending_messages -= 1
    
    async def _produce_async(self, topic: str, value: bytes, key: Optional[str] = None, headers: Optional[Dict] = None):
        """Produce message asynchronously with error handling"""
        try:
            # Add metadata headers
            if headers is None:
                headers = {}
            
            headers.update({
                'timestamp': datetime.now().isoformat(),
                'producer_id': 'ubereats-agents-producer',
                'message_id': str(uuid.uuid4())
            })
            
            # Produce message
            self.producer.produce(
                topic=topic,
                value=value,
                key=key,
                headers=headers,
                callback=self._delivery_callback
            )
            
            self.pending_messages += 1
            self.stats['messages_sent'] += 1
            self.stats['topics_used'].add(topic)
            
            # Trigger delivery reports
            self.producer.poll(0)
            
        except Exception as e:
            logger.error(f"Error producing message to {topic}: {e}")
            self.error_count += 1
            self.stats['messages_failed'] += 1
            raise
    
    async def publish_eta_prediction(self, result: ETAPredictionResult):
        """Publish ETA prediction result"""
        try:
            topic = KAFKA_TOPICS["ETA_PREDICTIONS"]
            message = serialize_result_to_kafka(result)
            key = result.order_id
            
            await self._produce_async(topic, message, key)
            logger.info(f"Published ETA prediction for order {result.order_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish ETA prediction: {e}")
            raise
    
    async def publish_driver_allocation(self, result: DriverAllocationResult):
        """Publish driver allocation result"""
        try:
            topic = KAFKA_TOPICS["DRIVER_ALLOCATIONS"]
            message = serialize_result_to_kafka(result)
            key = result.order_id
            
            await self._produce_async(topic, message, key)
            logger.info(f"Published driver allocation for order {result.order_id} -> driver {result.assigned_driver_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish driver allocation: {e}")
            raise
    
    async def publish_route_optimization(self, result: RouteOptimizationResult):
        """Publish route optimization result"""
        try:
            topic = KAFKA_TOPICS["ROUTE_OPTIMIZATIONS"]
            message = serialize_result_to_kafka(result)
            key = result.driver_id
            
            await self._produce_async(topic, message, key)
            logger.info(f"Published route optimization for driver {result.driver_id} - {result.time_savings_minutes:.1f}min savings")
            
        except Exception as e:
            logger.error(f"Failed to publish route optimization: {e}")
            raise
    
    async def publish_delivery_plan(self, result: DeliveryPlanResult):
        """Publish delivery plan result"""
        try:
            topic = KAFKA_TOPICS["DELIVERY_PLANS"]
            message = serialize_result_to_kafka(result)
            key = result.plan_id
            
            await self._produce_async(topic, message, key)
            logger.info(f"Published delivery plan {result.plan_id} - strategy: {result.strategy}, orders: {len(result.order_ids)}")
            
        except Exception as e:
            logger.error(f"Failed to publish delivery plan: {e}")
            raise
    
    async def publish_system_alert(self, alert: SystemAlert):
        """Publish system alert"""
        try:
            topic = KAFKA_TOPICS["SYSTEM_ALERTS"]
            message = serialize_result_to_kafka(alert)
            key = f"{alert.agent_id}_{alert.alert_type}"
            
            await self._produce_async(topic, message, key)
            logger.warning(f"Published {alert.severity} alert from {alert.agent_id}: {alert.message}")
            
        except Exception as e:
            logger.error(f"Failed to publish system alert: {e}")
            raise
    
    async def publish_agent_metrics(self, metrics: AgentMetrics):
        """Publish agent performance metrics"""
        try:
            topic = KAFKA_TOPICS["AGENT_METRICS"]
            message = serialize_result_to_kafka(metrics)
            key = metrics.agent_id
            
            await self._produce_async(topic, message, key)
            logger.debug(f"Published metrics for {metrics.agent_id} - {metrics.requests_processed} requests, {metrics.success_rate:.1f}% success")
            
        except Exception as e:
            logger.error(f"Failed to publish agent metrics: {e}")
            raise
    
    async def publish_batch_results(self, results: List[Any], result_type: str):
        """Publish multiple results in batch for efficiency"""
        try:
            tasks = []
            
            for result in results:
                if result_type == "eta_predictions":
                    task = self.publish_eta_prediction(result)
                elif result_type == "driver_allocations":
                    task = self.publish_driver_allocation(result)
                elif result_type == "route_optimizations":
                    task = self.publish_route_optimization(result)
                elif result_type == "delivery_plans":
                    task = self.publish_delivery_plan(result)
                else:
                    logger.warning(f"Unknown result type: {result_type}")
                    continue
                
                tasks.append(task)
            
            # Execute batch publishing
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log batch results
            successful = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"Batch published {successful}/{len(results)} {result_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish batch results: {e}")
            raise
    
    async def flush_and_wait(self, timeout: float = 30.0):
        """Flush all pending messages and wait for delivery"""
        try:
            logger.info("Flushing pending messages...")
            
            # Flush messages with timeout
            remaining = self.producer.flush(timeout)
            
            if remaining > 0:
                logger.warning(f"{remaining} messages were not delivered within timeout")
            else:
                logger.info("All messages successfully delivered")
            
        except Exception as e:
            logger.error(f"Error flushing messages: {e}")
            raise
    
    async def close(self):
        """Close the producer and cleanup resources"""
        try:
            if self.producer:
                await self.flush_and_wait()
                # Note: confluent_kafka Producer doesn't have an explicit close method
                self.producer = None
                logger.info("Kafka producer closed")
            
            if self.executor:
                self.executor.shutdown(wait=True)
                logger.info("Thread pool executor shutdown")
                
        except Exception as e:
            logger.error(f"Error closing producer: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics"""
        return {
            'messages_sent': self.stats['messages_sent'],
            'messages_delivered': self.stats['messages_delivered'], 
            'messages_failed': self.stats['messages_failed'],
            'pending_messages': self.pending_messages,
            'delivery_rate': (self.stats['messages_delivered'] / max(1, self.stats['messages_sent'])) * 100,
            'topics_used': list(self.stats['topics_used'])
        }

# Global producer instance
_producer_instance = None

async def get_producer() -> UberEatsKafkaProducer:
    """Get or create global producer instance"""
    global _producer_instance
    
    if _producer_instance is None:
        _producer_instance = UberEatsKafkaProducer()
        await _producer_instance.initialize()
    
    return _producer_instance

# Convenience functions for quick publishing

async def publish_eta_prediction(order_id: str, predicted_pickup_time: datetime, 
                                predicted_delivery_time: datetime, confidence_score: float,
                                total_time_minutes: float, factors: List[str]):
    """Convenience function to publish ETA prediction"""
    result = ETAPredictionResult(
        order_id=order_id,
        timestamp=datetime.now(),
        predicted_pickup_time=predicted_pickup_time,
        predicted_delivery_time=predicted_delivery_time,
        confidence_score=confidence_score,
        total_time_minutes=total_time_minutes,
        factors=factors
    )
    
    producer = await get_producer()
    await producer.publish_eta_prediction(result)

async def publish_driver_allocation(order_id: str, assigned_driver_id: str, 
                                  allocation_score: float, estimated_pickup_time: datetime,
                                  reasoning: List[str], alternative_drivers: List[Dict] = None):
    """Convenience function to publish driver allocation"""
    result = DriverAllocationResult(
        order_id=order_id,
        assigned_driver_id=assigned_driver_id,
        timestamp=datetime.now(),
        allocation_score=allocation_score,
        estimated_pickup_time=estimated_pickup_time,
        reasoning=reasoning,
        alternative_drivers=alternative_drivers or []
    )
    
    producer = await get_producer()
    await producer.publish_driver_allocation(result)

async def publish_route_optimization(driver_id: str, optimized_route: List[Dict],
                                   total_distance_km: float, total_time_minutes: float,
                                   time_savings_minutes: float, efficiency_score: float):
    """Convenience function to publish route optimization"""
    result = RouteOptimizationResult(
        driver_id=driver_id,
        timestamp=datetime.now(),
        optimized_route=optimized_route,
        total_distance_km=total_distance_km,
        total_time_minutes=total_time_minutes,
        time_savings_minutes=time_savings_minutes,
        efficiency_score=efficiency_score,
        fuel_savings_estimate=time_savings_minutes * 0.1  # Rough estimate
    )
    
    producer = await get_producer()
    await producer.publish_route_optimization(result)

async def publish_system_alert(agent_id: str, alert_type: str, severity: str, 
                              message: str, affected_components: List[str] = None,
                              recommended_actions: List[str] = None):
    """Convenience function to publish system alert"""
    alert = SystemAlert(
        alert_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        alert_type=alert_type,
        severity=severity,
        message=message,
        affected_components=affected_components or [],
        recommended_actions=recommended_actions or [],
        agent_id=agent_id
    )
    
    producer = await get_producer()
    await producer.publish_system_alert(alert)

async def publish_agent_metrics(agent_id: str, requests_processed: int, avg_response_time: float,
                               success_rate: float, error_count: int, memory_usage_mb: float = 0.0,
                               cpu_usage_percent: float = 0.0):
    """Convenience function to publish agent metrics"""
    metrics = AgentMetrics(
        agent_id=agent_id,
        timestamp=datetime.now(),
        requests_processed=requests_processed,
        avg_response_time=avg_response_time,
        success_rate=success_rate,
        error_count=error_count,
        memory_usage_mb=memory_usage_mb,
        cpu_usage_percent=cpu_usage_percent
    )
    
    producer = await get_producer()
    await producer.publish_agent_metrics(metrics)