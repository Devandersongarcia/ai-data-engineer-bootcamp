#!/usr/bin/env python3
"""
Test GPS data consumer - read historical messages from kafka-gps-data
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

def test_historical_gps_data():
    """Test reading historical GPS data from the beginning"""
    
    print("📚 Reading Historical GPS Data...")
    print("=" * 60)
    
    # Configuration - read from earliest
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
        'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
        'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
        'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
        'group.id': 'gps-historical-test',
        'auto.offset.reset': 'earliest',  # Read from beginning
        'enable.auto.commit': False
    }
    
    # Create consumer
    consumer = Consumer(config)
    
    # Subscribe to GPS topic
    gps_topic = os.getenv('GPS_TOPIC', 'kafka-gps-data')
    consumer.subscribe([gps_topic])
    
    print(f"📡 Subscribed to: {gps_topic}")
    print("📚 Reading historical messages from beginning...")
    print("-" * 60)
    
    try:
        messages_processed = 0
        anomalies_found = 0
        high_speed_count = 0
        zones_seen = set()
        
        while messages_processed < 50:  # Process up to 50 messages
            msg = consumer.poll(5.0)  # 5 second timeout
            
            if msg is None:
                print(f"⏰ Timeout reached. Processed {messages_processed} messages.")
                break
            
            if msg.error():
                print(f"❌ Consumer error: {msg.error()}")
                continue
            
            try:
                # Parse message
                raw_data = json.loads(msg.value().decode('utf-8'))
                messages_processed += 1
                
                # Parse with our model
                gps_event = GPSEvent.from_kafka_message(raw_data)
                
                # Collect analytics
                if gps_event.anomaly_flag:
                    anomalies_found += 1
                    
                if gps_event.speed_kph > 80:
                    high_speed_count += 1
                    
                zones_seen.add(gps_event.zone_name)
                
                # Print every 10th message details
                if messages_processed % 10 == 0:
                    print(f"\n📍 GPS Message #{messages_processed}:")
                    print(f"  🚗 Driver: {gps_event.driver_id}")
                    print(f"  📍 Location: ({gps_event.latitude:.4f}, {gps_event.longitude:.4f})")
                    print(f"  🏃 Speed: {gps_event.speed_kph:.1f} km/h")
                    print(f"  🌍 Zone: {gps_event.zone_name} ({gps_event.zone_type})")
                    print(f"  📊 Trip Stage: {gps_event.trip_stage}")
                    if gps_event.anomaly_flag:
                        print(f"  🚨 ANOMALY: {gps_event.anomaly_flag} - {gps_event.anomaly_details}")
                
            except Exception as e:
                print(f"❌ Error processing message {messages_processed}: {e}")
                
        print(f"\n📊 ANALYTICS SUMMARY:")
        print(f"  📈 Total messages processed: {messages_processed}")
        print(f"  🚨 Anomalies detected: {anomalies_found}")
        print(f"  ⚡ High speed events (>80 km/h): {high_speed_count}")
        print(f"  🌍 Unique zones seen: {len(zones_seen)}")
        print(f"  📍 Zone names: {', '.join(sorted(list(zones_seen))[:10])}")  # Show first 10
        
        print(f"\n🎯 Historical data analysis completed!")
        
    except KeyboardInterrupt:
        print("\n👋 Consumer stopped by user")
    finally:
        consumer.close()

if __name__ == "__main__":
    test_historical_gps_data()