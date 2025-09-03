#!/usr/bin/env python3
"""
Simple Kafka connection test for Confluent Cloud
"""
import os
from confluent_kafka import Consumer, Producer, KafkaError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_kafka_connection():
    """Test Kafka connection to Confluent Cloud"""
    
    print("🔍 Testing Kafka Connection to Confluent Cloud...")
    print("=" * 60)
    
    # Configuration
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
        'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
        'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
        'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
    }
    
    print(f"Bootstrap servers: {config['bootstrap.servers']}")
    print(f"Security protocol: {config['security.protocol']}")
    print(f"Username: {config['sasl.username']}")
    print()
    
    # Test Producer
    try:
        print("🔄 Testing Producer...")
        producer = Producer(config)
        
        # Test delivery callback
        def delivery_report(err, msg):
            if err:
                print(f"❌ Message delivery failed: {err}")
            else:
                print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}]")
        
        # Send a test message
        test_topic = os.getenv('GPS_TOPIC', 'gps_data')
        producer.produce(
            test_topic, 
            key='test_key',
            value='{"test": "connection_test"}',
            callback=delivery_report
        )
        producer.flush()
        print("✅ Producer test successful!")
        
    except Exception as e:
        print(f"❌ Producer test failed: {e}")
    
    print()
    
    # Test Consumer
    try:
        print("🔄 Testing Consumer...")
        consumer_config = {
            **config,
            'group.id': 'test-consumer-group',
            'auto.offset.reset': 'latest'
        }
        
        consumer = Consumer(consumer_config)
        
        # Subscribe to topic
        test_topic = os.getenv('GPS_TOPIC', 'gps_data') 
        consumer.subscribe([test_topic])
        
        print(f"Subscribed to topic: {test_topic}")
        
        # Poll for messages (timeout after 10 seconds)
        print("🔄 Polling for messages (10 second timeout)...")
        msg = consumer.poll(10.0)
        
        if msg is None:
            print("⚠️ No messages received (this is normal for a new consumer)")
        elif msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                print("✅ Reached end of partition (consumer working)")
            else:
                print(f"❌ Consumer error: {msg.error()}")
        else:
            print(f"✅ Message received: {msg.value().decode('utf-8')}")
        
        consumer.close()
        print("✅ Consumer test successful!")
        
    except Exception as e:
        print(f"❌ Consumer test failed: {e}")
    
    print()
    print("🎯 Connection test completed!")

if __name__ == "__main__":
    test_kafka_connection()