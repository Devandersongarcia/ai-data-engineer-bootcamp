#!/usr/bin/env python3
"""
Debug GPS data consumption from Kafka
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime
from confluent_kafka import Consumer
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

load_dotenv()

def test_gps_data_consumption():
    """Test consuming GPS data directly from Kafka"""
    print("🔍 Debug: Testing GPS Data Consumption")
    print("=" * 50)
    
    # Kafka configuration
    consumer_config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
        'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
        'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
        'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
        'group.id': f'debug-gps-consumer-{int(datetime.now().timestamp())}',
        'auto.offset.reset': 'earliest'
    }
    
    print(f"📡 Connecting to: {consumer_config['bootstrap.servers']}")
    print(f"👤 Username: {consumer_config['sasl.username']}")
    print(f"📝 Group ID: {consumer_config['group.id']}")
    print()
    
    try:
        consumer = Consumer(consumer_config)
        consumer.subscribe(['kafka-gps-data'])
        print("✅ Successfully connected and subscribed to 'kafka-gps-data'")
        print("🔍 Polling for GPS messages (30 seconds)...")
        print()
        
        message_count = 0
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < 30:
            msg = consumer.poll(timeout=2.0)
            
            if msg is None:
                print(".", end="", flush=True)
                continue
                
            if msg.error():
                print(f"\n❌ Consumer error: {msg.error()}")
                continue
            
            message_count += 1
            
            try:
                # Parse message
                data = json.loads(msg.value().decode('utf-8'))
                print(f"\n📍 GPS Message #{message_count}:")
                print(f"   🔑 Keys: {list(data.keys())}")
                
                # Show key GPS fields
                if 'driver_id' in data:
                    print(f"   🚗 Driver: {str(data['driver_id'])[:8]}...")
                if 'latitude' in data and 'longitude' in data:
                    print(f"   📍 Location: ({data['latitude']:.4f}, {data['longitude']:.4f})")
                if 'speed_kph' in data:
                    print(f"   🏃 Speed: {data['speed_kph']} km/h")
                if 'zone_name' in data:
                    print(f"   🏘️ Zone: {data['zone_name']}")
                if 'trip_stage' in data:
                    print(f"   🎯 Stage: {data['trip_stage']}")
                if 'traffic_density' in data:
                    print(f"   🚦 Traffic: {data['traffic_density']}")
                    
                # Show timestamp info
                if 'timestamp' in data:
                    print(f"   ⏰ Timestamp: {data['timestamp']}")
                    
                print(f"   📊 Message size: {len(msg.value())} bytes")
                
            except json.JSONDecodeError as e:
                print(f"\n❌ JSON decode error: {e}")
                print(f"   Raw message: {msg.value()}")
            except Exception as e:
                print(f"\n❌ Processing error: {e}")
        
        consumer.close()
        
        print(f"\n\n🎯 Results:")
        print(f"   📨 Messages received: {message_count}")
        print(f"   ⏱️ Test duration: 30 seconds")
        
        if message_count == 0:
            print("\n⚠️ No GPS messages found. Possible issues:")
            print("   1. No active GPS data generators running")
            print("   2. Topic 'kafka-gps-data' is empty")
            print("   3. Kafka configuration issues")
            print("\n💡 Try running: python tests/agno_demo_with_monitoring.py")
        else:
            print(f"\n✅ GPS data is flowing! Found {message_count} messages")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gps_data_consumption()