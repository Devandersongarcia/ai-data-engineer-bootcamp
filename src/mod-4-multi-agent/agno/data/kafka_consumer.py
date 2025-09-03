"""
Kafka Consumer for ingesting data from Confluent Cloud topics
"""
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Consumer, KafkaException, KafkaError

from .kafka_config import kafka_manager, KAFKA_TOPICS
from .models import parse_kafka_message, GPSEvent, OrderEvent, DriverEvent, RestaurantEvent, TrafficEvent

logger = logging.getLogger(__name__)

class UberEatsKafkaConsumer:
    """
    Kafka consumer for UberEats real-time data processing
    Handles GPS, orders, drivers, restaurants, and traffic events
    """
    
    def __init__(self, group_id: str = "ubereats-agents-consumer"):
        self.group_id = group_id
        self.consumer = None
        self.running = False
        self.message_handlers = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.processed_count = 0
        self.error_count = 0
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def register_message_handler(self, topic: str, handler: Callable[[Any], Any]):
        """Register a message handler for a specific topic"""
        self.message_handlers[topic] = handler
        logger.info(f"Registered handler for topic: {topic}")
    
    def register_multiple_handlers(self, handlers: Dict[str, Callable]):
        """Register multiple message handlers"""
        for topic, handler in handlers.items():
            self.register_message_handler(topic, handler)
    
    async def start_consuming(self, topics: List[str], batch_size: int = 100, timeout: float = 1.0):
        """
        Start consuming messages from specified topics
        
        Args:
            topics: List of Kafka topics to subscribe to
            batch_size: Number of messages to process in each batch
            timeout: Consumer poll timeout in seconds
        """
        logger.info(f"Starting Kafka consumer for topics: {topics}")
        
        try:
            # Create consumer
            self.consumer = kafka_manager.create_consumer(self.group_id)
            
            # Subscribe to topics
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
            
            self.running = True
            
            # Start consuming messages
            await self._consume_messages_loop(batch_size, timeout)
            
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
            self.error_count += 1
            raise
        finally:
            await self._cleanup()
    
    async def _consume_messages_loop(self, batch_size: int, timeout: float):
        """Main message consumption loop"""
        message_batch = []
        
        while self.running:
            try:
                # Poll for messages
                msg = self.consumer.poll(timeout=timeout)
                
                if msg is None:
                    # Process batch if we have messages
                    if message_batch:
                        await self._process_message_batch(message_batch)
                        message_batch = []
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"End of partition reached {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        self.error_count += 1
                    continue
                
                # Add message to batch
                message_batch.append(msg)
                
                # Process batch when it reaches the specified size
                if len(message_batch) >= batch_size:
                    await self._process_message_batch(message_batch)
                    message_batch = []
                    
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, stopping consumer...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in message consumption loop: {e}")
                self.error_count += 1
                # Continue processing other messages
                continue
        
        # Process remaining messages in batch
        if message_batch:
            await self._process_message_batch(message_batch)
    
    async def _process_message_batch(self, messages: List[Any]):
        """Process a batch of messages concurrently"""
        try:
            # Process messages concurrently
            tasks = []
            for msg in messages:
                task = asyncio.create_task(self._process_single_message(msg))
                tasks.append(task)
            
            # Wait for all messages to be processed
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful processing
            successful_count = sum(1 for result in results if not isinstance(result, Exception))
            self.processed_count += successful_count
            
            # Log errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing message {i}: {result}")
                    self.error_count += 1
            
            # Commit offsets for successfully processed messages
            if successful_count > 0:
                try:
                    self.consumer.commit(asynchronous=False)
                    logger.debug(f"Committed offsets for {len(messages)} messages")
                except Exception as e:
                    logger.error(f"Error committing offsets: {e}")
            
            logger.info(f"Processed batch: {successful_count}/{len(messages)} successful")
            
        except Exception as e:
            logger.error(f"Error processing message batch: {e}")
            self.error_count += len(messages)
    
    async def _process_single_message(self, msg):
        """Process a single Kafka message"""
        try:
            topic = msg.topic()
            partition = msg.partition()
            offset = msg.offset()
            
            logger.debug(f"Processing message from {topic}[{partition}] at offset {offset}")
            
            # Parse the message
            parsed_data = parse_kafka_message(topic, msg.value())
            if parsed_data is None:
                logger.warning(f"Failed to parse message from {topic}")
                return
            
            # Handle the message based on topic
            if topic in self.message_handlers:
                handler = self.message_handlers[topic]
                # Run handler in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, handler, parsed_data)
            else:
                logger.warning(f"No handler registered for topic: {topic}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down consumer...")
        self.running = False
    
    async def _cleanup(self):
        """Cleanup resources"""
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka consumer closed")
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")
        
        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("Thread pool executor shutdown")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'success_rate': (self.processed_count / max(1, self.processed_count + self.error_count)) * 100,
            'running': self.running,
            'registered_handlers': list(self.message_handlers.keys())
        }

# Convenience functions for common use cases

async def start_gps_consumer(handler: Callable[[GPSEvent], Any], group_id: str = "gps-consumer"):
    """Start consumer specifically for GPS events"""
    consumer = UberEatsKafkaConsumer(group_id)
    consumer.register_message_handler(KAFKA_TOPICS["GPS_TOPIC"], handler)
    await consumer.start_consuming([KAFKA_TOPICS["GPS_TOPIC"]])

async def start_orders_consumer(handler: Callable[[OrderEvent], Any], group_id: str = "orders-consumer"):
    """Start consumer specifically for order events"""
    consumer = UberEatsKafkaConsumer(group_id)
    consumer.register_message_handler(KAFKA_TOPICS["ORDERS_TOPIC"], handler)
    await consumer.start_consuming([KAFKA_TOPICS["ORDERS_TOPIC"]])

async def start_drivers_consumer(handler: Callable[[DriverEvent], Any], group_id: str = "drivers-consumer"):
    """Start consumer specifically for driver events"""
    consumer = UberEatsKafkaConsumer(group_id)
    consumer.register_message_handler(KAFKA_TOPICS["DRIVERS_TOPIC"], handler)
    await consumer.start_consuming([KAFKA_TOPICS["DRIVERS_TOPIC"]])

async def start_multi_topic_consumer(
    handlers: Dict[str, Callable],
    topics: List[str] = None,
    group_id: str = "multi-topic-consumer"
):
    """Start consumer for multiple topics with different handlers"""
    consumer = UberEatsKafkaConsumer(group_id)
    
    # Register handlers
    consumer.register_multiple_handlers(handlers)
    
    # Use provided topics or all topics with handlers
    consume_topics = topics or list(handlers.keys())
    
    await consumer.start_consuming(consume_topics)

# Example message handlers (to be customized based on your needs)

def example_gps_handler(gps_event: GPSEvent):
    """Example handler for GPS events"""
    logger.info(f"GPS Update: Driver {gps_event.driver_id} at ({gps_event.lat}, {gps_event.lng}) - {gps_event.status}")
    # Add your GPS processing logic here
    # e.g., update driver location, trigger ETA recalculation, etc.

def example_order_handler(order_event: OrderEvent):
    """Example handler for order events"""
    logger.info(f"Order Update: {order_event.order_id} - {order_event.status} - ${order_event.total_amount}")
    # Add your order processing logic here
    # e.g., trigger delivery planning, driver allocation, etc.

def example_driver_handler(driver_event: DriverEvent):
    """Example handler for driver events"""
    logger.info(f"Driver Update: {driver_event.driver_id} - {driver_event.status} - {len(driver_event.active_orders)} orders")
    # Add your driver processing logic here
    # e.g., update availability, rebalance allocations, etc.

def example_restaurant_handler(restaurant_event: RestaurantEvent):
    """Example handler for restaurant events"""
    logger.info(f"Restaurant Update: {restaurant_event.restaurant_id} - capacity: {restaurant_event.current_capacity:.2f}")
    # Add your restaurant processing logic here
    # e.g., adjust ETA predictions, capacity planning, etc.

def example_traffic_handler(traffic_event: TrafficEvent):
    """Example handler for traffic events"""
    logger.info(f"Traffic Update: Area {traffic_event.area_id} - {traffic_event.traffic_level} - {traffic_event.weather_conditions}")
    # Add your traffic processing logic here
    # e.g., update route optimizations, ETA adjustments, etc.