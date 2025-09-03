"""
Kafka configuration and connection management for Confluent Cloud
"""
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class KafkaConfig:
    """Kafka configuration for Confluent Cloud"""
    bootstrap_servers: str
    security_protocol: str = "SASL_SSL"
    sasl_mechanisms: str = "PLAIN"
    sasl_username: str = ""
    sasl_password: str = ""
    session_timeout_ms: int = 30000
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False
    group_id: str = "ubereats-agents"

class KafkaConnectionManager:
    """Manages Kafka connections and configurations for UberEats agents"""
    
    def __init__(self):
        self.config = self._load_kafka_config()
        self.consumer = None
        self.producer = None
        self.admin_client = None
    
    def _load_kafka_config(self) -> KafkaConfig:
        """Load Kafka configuration from environment variables"""
        return KafkaConfig(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            security_protocol=os.getenv('KAFKA_SECURITY_PROTOCOL', 'SASL_SSL'),
            sasl_mechanisms=os.getenv('KAFKA_SASL_MECHANISMS', 'PLAIN'),
            sasl_username=os.getenv('KAFKA_SASL_USERNAME', ''),
            sasl_password=os.getenv('KAFKA_SASL_PASSWORD', ''),
            session_timeout_ms=int(os.getenv('KAFKA_SESSION_TIMEOUT_MS', '30000')),
            auto_offset_reset=os.getenv('KAFKA_AUTO_OFFSET_RESET', 'earliest'),
            enable_auto_commit=os.getenv('KAFKA_ENABLE_AUTO_COMMIT', 'false').lower() == 'true',
            group_id=os.getenv('KAFKA_GROUP_ID', 'ubereats-agents')
        )
    
    def get_consumer_config(self, group_id: Optional[str] = None) -> Dict[str, Any]:
        """Get consumer configuration dictionary"""
        config = {
            'bootstrap.servers': self.config.bootstrap_servers,
            'security.protocol': self.config.security_protocol,
            'sasl.mechanisms': self.config.sasl_mechanisms,
            'sasl.username': self.config.sasl_username,
            'sasl.password': self.config.sasl_password,
            'group.id': group_id or self.config.group_id,
            'session.timeout.ms': self.config.session_timeout_ms,
            'auto.offset.reset': self.config.auto_offset_reset,
            'enable.auto.commit': self.config.enable_auto_commit,
            'enable.partition.eof': False,
            'default.topic.config': {'auto.offset.reset': self.config.auto_offset_reset}
        }
        
        # Remove empty credentials for local development
        if not self.config.sasl_username or not self.config.sasl_password:
            config.pop('sasl.username', None)
            config.pop('sasl.password', None)
            if self.config.bootstrap_servers == 'localhost:9092':
                config['security.protocol'] = 'PLAINTEXT'
                config.pop('sasl.mechanisms', None)
        
        return config
    
    def get_producer_config(self) -> Dict[str, Any]:
        """Get producer configuration dictionary"""
        config = {
            'bootstrap.servers': self.config.bootstrap_servers,
            'security.protocol': self.config.security_protocol,
            'sasl.mechanisms': self.config.sasl_mechanisms,
            'sasl.username': self.config.sasl_username,
            'sasl.password': self.config.sasl_password,
            'acks': 'all',
            'retries': 3,
            'retry.backoff.ms': 1000,
            'linger.ms': 100,
            'batch.size': 16384,
            'compression.type': 'snappy'
        }
        
        # Remove empty credentials for local development
        if not self.config.sasl_username or not self.config.sasl_password:
            config.pop('sasl.username', None)
            config.pop('sasl.password', None)
            if self.config.bootstrap_servers == 'localhost:9092':
                config['security.protocol'] = 'PLAINTEXT'
                config.pop('sasl.mechanisms', None)
        
        return config
    
    def create_consumer(self, group_id: Optional[str] = None) -> Consumer:
        """Create a new Kafka consumer"""
        try:
            consumer_config = self.get_consumer_config(group_id)
            consumer = Consumer(consumer_config)
            logger.info(f"Created Kafka consumer with group_id: {group_id or self.config.group_id}")
            return consumer
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            raise
    
    def create_producer(self) -> Producer:
        """Create a new Kafka producer"""
        try:
            producer_config = self.get_producer_config()
            producer = Producer(producer_config)
            logger.info("Created Kafka producer")
            return producer
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise
    
    def create_admin_client(self) -> AdminClient:
        """Create admin client for topic management"""
        try:
            admin_config = {
                'bootstrap.servers': self.config.bootstrap_servers,
                'security.protocol': self.config.security_protocol,
            }
            
            if self.config.sasl_username and self.config.sasl_password:
                admin_config.update({
                    'sasl.mechanisms': self.config.sasl_mechanisms,
                    'sasl.username': self.config.sasl_username,
                    'sasl.password': self.config.sasl_password,
                })
            elif self.config.bootstrap_servers == 'localhost:9092':
                admin_config['security.protocol'] = 'PLAINTEXT'
            
            admin_client = AdminClient(admin_config)
            logger.info("Created Kafka admin client")
            return admin_client
        except Exception as e:
            logger.error(f"Failed to create Kafka admin client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test Kafka connection"""
        try:
            admin_client = self.create_admin_client()
            # Try to get cluster metadata as connection test
            metadata = admin_client.list_topics(timeout=10)
            logger.info(f"Kafka connection successful. Found {len(metadata.topics)} topics")
            return True
        except Exception as e:
            logger.error(f"Kafka connection test failed: {e}")
            return False

# Global connection manager instance
kafka_manager = KafkaConnectionManager()

# Topic definitions for UberEats data
KAFKA_TOPICS = {
    # Input topics (from your existing data)
    "GPS_TOPIC": "gps-events",
    "ORDERS_TOPIC": "orders-events", 
    "DRIVERS_TOPIC": "drivers-events",
    "RESTAURANTS_TOPIC": "restaurants-events",
    "TRAFFIC_TOPIC": "traffic-events",
    
    # Output topics (agent analysis results)
    "ETA_PREDICTIONS": "eta-predictions",
    "DRIVER_ALLOCATIONS": "driver-allocations", 
    "ROUTE_OPTIMIZATIONS": "route-optimizations",
    "DELIVERY_PLANS": "delivery-plans",
    "SYSTEM_ALERTS": "system-alerts",
    "AGENT_METRICS": "agent-metrics"
}