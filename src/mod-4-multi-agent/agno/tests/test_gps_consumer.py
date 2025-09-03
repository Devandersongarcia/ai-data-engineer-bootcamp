#!/usr/bin/env python3
"""
Test GPS data consumer - read real messages from kafka-gps-data
"""
import os
import json
from confluent_kafka import Consumer
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data.models import GPSEvent

# Load environment variables
load_dotenv()

def test_gps_consumer():
    """Test consuming real GPS data from kafka-gps-data topic"""
    
    print("🚚 Testing GPS Data Consumer...")
    print("=" * 60)
    
    # Configuration
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
        'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
        'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
        'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
        'group.id': 'gps-test-consumer',
        'auto.offset.reset': 'latest'
    }
    
    # Create consumer
    consumer = Consumer(config)
    
    # Subscribe to GPS topic
    gps_topic = os.getenv('GPS_TOPIC', 'kafka-gps-data')
    consumer.subscribe([gps_topic])
    
    print(f"📡 Subscribed to: {gps_topic}")
    print("🔄 Waiting for GPS messages (60 second timeout)...")
    print("-" * 60)
    
    try:
        messages_processed = 0
        
        while messages_processed < 10:  # Process up to 10 messages
            msg = consumer.poll(60.0)  # 60 second timeout
            
            if msg is None:
                print("⏰ No messages received within timeout")
                break
            
            if msg.error():
                print(f"❌ Consumer error: {msg.error()}")
                continue
            
            try:
                # Parse message
                raw_data = json.loads(msg.value().decode('utf-8'))
                messages_processed += 1
                
                print(f"\n📍 GPS Message #{messages_processed}:")
                print(f"  🆔 GPS ID: {raw_data.get('gps_id')}")
                print(f"  🚗 Driver: {raw_data.get('driver_id')}")
                print(f"  📦 Order: {raw_data.get('order_id') or 'None'}")
                print(f"  📍 Location: ({raw_data.get('latitude')}, {raw_data.get('longitude')})")
                print(f"  🏃 Speed: {raw_data.get('speed_kph')} km/h")
                print(f"  🧭 Heading: {raw_data.get('heading_degrees')}°")
                print(f"  🚦 Traffic: {raw_data.get('traffic_density')}")
                print(f"  🌍 Zone: {raw_data.get('zone_name')} ({raw_data.get('zone_type')})")
                print(f"  📊 Trip Stage: {raw_data.get('trip_stage')}")
                print(f"  ⚠️ Anomaly: {raw_data.get('anomaly_flag') or 'None'}")
                print(f"  ⏰ Timestamp: {raw_data.get('gps_timestamp')}")
                
                # Test parsing with our GPSEvent model
                try:
                    gps_event = GPSEvent.from_kafka_message(raw_data)
                    print(f"  ✅ Successfully parsed with GPSEvent model")
                    
                    # Show some analytics
                    if gps_event.anomaly_flag:
                        print(f"  🚨 ANOMALY DETECTED: {gps_event.anomaly_details}")
                    
                    if gps_event.speed_kph > 80:
                        print(f"  ⚡ HIGH SPEED: {gps_event.speed_kph} km/h on {gps_event.road_type}")
                    
                except Exception as parse_error:
                    print(f"  ❌ Failed to parse with GPSEvent: {parse_error}")
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                
        print(f"\n🎯 Processed {messages_processed} GPS messages successfully!")
        
    except KeyboardInterrupt:
        print("\n👋 Consumer stopped by user")
    finally:
        consumer.close()

if __name__ == "__main__":
    test_gps_consumer()