#!/usr/bin/env python3
"""
Kafka Topic Management Script for Confluent Cloud
Checks and creates required topics for the fraud detection system
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from kafka import KafkaAdminClient, KafkaConsumer
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, KafkaError
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_kafka_admin_client():
    """Create Kafka admin client for Confluent Cloud"""
    kafka_config = settings.kafka.get_kafka_connection_config()
    
    # Convert to kafka-python format
    admin_config = {
        'bootstrap_servers': kafka_config['bootstrap.servers'],
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'PLAIN',
        'sasl_plain_username': kafka_config['sasl.username'],
        'sasl_plain_password': kafka_config['sasl.password'],
    }
    
    return KafkaAdminClient(**admin_config)

def list_topics():
    """List all available topics"""
    try:
        admin_client = get_kafka_admin_client()
        metadata = admin_client.describe_cluster()
        topics = admin_client.list_topics()
        
        logger.info("📋 Available Kafka Topics:")
        for topic in sorted(topics):
            logger.info(f"   - {topic}")
            
        return topics
        
    except Exception as e:
        logger.error(f"❌ Failed to list topics: {e}")
        return set()

def check_topic_exists(topic_name: str) -> bool:
    """Check if a specific topic exists"""
    try:
        consumer_config = settings.kafka.get_kafka_connection_config()
        consumer_config.update({
            'group_id': 'topic-checker',
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': False,
        })
        
        # Convert to kafka-python format
        consumer_config_formatted = {
            'bootstrap_servers': consumer_config['bootstrap.servers'],
            'security_protocol': 'SASL_SSL',
            'sasl_mechanism': 'PLAIN',
            'sasl_plain_username': consumer_config['sasl.username'],
            'sasl_plain_password': consumer_config['sasl.password'],
            'group_id': 'topic-checker',
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': False,
        }
        
        consumer = KafkaConsumer(**consumer_config_formatted)
        topics = consumer.list_consumer_group_offsets().keys() if hasattr(consumer, 'list_consumer_group_offsets') else set()
        
        # Alternative method - check metadata
        metadata = consumer.list_consumer_group_offsets() if hasattr(consumer, 'list_consumer_group_offsets') else {}
        all_topics = set(consumer.topics()) if hasattr(consumer, 'topics') else set()
        
        consumer.close()
        
        exists = topic_name in all_topics
        logger.info(f"🔍 Topic '{topic_name}' exists: {exists}")
        return exists
        
    except Exception as e:
        logger.error(f"❌ Failed to check topic '{topic_name}': {e}")
        return False

def create_topic(topic_name: str, num_partitions: int = 3, replication_factor: int = 3):
    """Create a new Kafka topic"""
    try:
        admin_client = get_kafka_admin_client()
        
        topic = NewTopic(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            topic_configs={
                'cleanup.policy': 'delete',
                'retention.ms': '604800000',  # 7 days
                'max.message.bytes': '1048576',  # 1MB
            }
        )
        
        logger.info(f"🚀 Creating topic '{topic_name}' with {num_partitions} partitions...")
        
        result = admin_client.create_topics([topic])
        
        # Wait for creation
        for topic_name, future in result.items():
            try:
                future.result()  # Block until topic is created
                logger.info(f"✅ Topic '{topic_name}' created successfully")
                return True
            except TopicAlreadyExistsError:
                logger.info(f"✅ Topic '{topic_name}' already exists")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create topic '{topic_name}': {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Failed to create topic '{topic_name}': {e}")
        return False

def verify_fraud_detection_topics():
    """Verify all required topics for fraud detection system"""
    logger.info("🔧 Verifying Fraud Detection Kafka Topics")
    logger.info("=" * 50)
    
    required_topics = {
        settings.kafka.input_topics: "Input orders from UberEats simulator",
        settings.kafka.output_topic: "Fraud detection results and alerts"
    }
    
    # List all topics first
    all_topics = list_topics()
    
    logger.info(f"\n📝 Required Topics Check:")
    topics_status = {}
    
    for topic, description in required_topics.items():
        logger.info(f"\n🔍 Checking topic: '{topic}'")
        logger.info(f"   Purpose: {description}")
        
        exists = topic in all_topics
        topics_status[topic] = exists
        
        if exists:
            logger.info(f"   Status: ✅ EXISTS")
        else:
            logger.warning(f"   Status: ❌ MISSING")
            
            # Offer to create missing topic
            logger.info(f"   🚀 Creating missing topic '{topic}'...")
            created = create_topic(topic)
            topics_status[topic] = created
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Topics Status Summary:")
    
    all_ready = True
    for topic, ready in topics_status.items():
        status = "✅ READY" if ready else "❌ FAILED"
        logger.info(f"   {topic}: {status}")
        if not ready:
            all_ready = False
    
    if all_ready:
        logger.info("\n🎉 All required topics are ready for fraud detection!")
        logger.info("   You can now run the fraud detection system.")
    else:
        logger.warning("\n⚠️ Some topics are missing or failed to create.")
        logger.warning("   Check your Confluent Cloud configuration and permissions.")
    
    return all_ready

def main():
    """Main topic management function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kafka Topic Management for Fraud Detection")
    parser.add_argument("--action", choices=["list", "check", "create", "verify"], 
                       default="verify", help="Action to perform")
    parser.add_argument("--topic", help="Topic name for check/create actions")
    parser.add_argument("--partitions", type=int, default=3, help="Number of partitions for create")
    
    args = parser.parse_args()
    
    logger.info("🚀 Kafka Topic Management for Enhanced Fraud Detection")
    logger.info(f"   Confluent Cloud: {settings.kafka.bootstrap_servers}")
    logger.info("=" * 60)
    
    try:
        if args.action == "list":
            list_topics()
            
        elif args.action == "check":
            if not args.topic:
                logger.error("❌ --topic required for check action")
                return False
            return check_topic_exists(args.topic)
            
        elif args.action == "create":
            if not args.topic:
                logger.error("❌ --topic required for create action")
                return False
            return create_topic(args.topic, args.partitions)
            
        elif args.action == "verify":
            return verify_fraud_detection_topics()
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)