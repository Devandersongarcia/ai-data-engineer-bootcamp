#!/usr/bin/env python3
"""
Quick test to show agent activity
"""
import os
import sys
import json
from pathlib import Path
from confluent_kafka import Consumer
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data.models import GPSEvent

load_dotenv()

def quick_agent_test():
    """Quick test showing what agents would do"""
    print("🤖 Quick Agent Action Test")
    print("=" * 50)
    
    config = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
        'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
        'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
        'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
        'group.id': 'quick-test',
        'auto.offset.reset': 'latest'
    }
    
    consumer = Consumer(config)
    consumer.subscribe(['kafka-gps-data'])
    
    print("📡 Reading GPS data... (will process 5 events)")
    
    processed = 0
    while processed < 5:
        msg = consumer.poll(5.0)
        
        if msg is None:
            print("⏰ No new messages, trying historical data...")
            # Switch to reading from beginning
            consumer.close()
            config['auto.offset.reset'] = 'earliest'
            config['group.id'] = 'quick-test-historical'
            consumer = Consumer(config)
            consumer.subscribe(['kafka-gps-data'])
            continue
            
        if msg.error():
            continue
            
        try:
            gps_data = json.loads(msg.value().decode('utf-8'))
            gps_event = GPSEvent.from_kafka_message(gps_data)
            processed += 1
            
            print(f"\n📍 GPS Event #{processed}:")
            print(f"   🚗 Driver: {gps_event.driver_id[:8]}...")
            print(f"   📍 Location: {gps_event.zone_name} ({gps_event.zone_type})")
            print(f"   🏃 Speed: {gps_event.speed_kph} km/h")
            print(f"   📊 Stage: {gps_event.trip_stage}")
            print(f"   🚦 Traffic: {gps_event.traffic_density}")
            
            # Show what agents would do
            print("   🤖 Agent Reactions:")
            
            # ETA Agent
            if gps_event.trip_stage in ['to_pickup', 'to_destination'] and gps_event.speed_kph > 10:
                eta_mins = 15 * (1.4 if gps_event.traffic_density == 'heavy' else 1.0)
                print(f"      ⏱️ ETA Agent: Would predict {eta_mins:.1f}min delivery")
            
            # Route Agent  
            if gps_event.traffic_density == 'heavy':
                print(f"      🗺️ Route Agent: Would reroute due to heavy traffic")
            elif gps_event.speed_kph > 80:
                print(f"      🗺️ Route Agent: Would optimize high-speed route")
            
            # Driver Agent
            if gps_event.trip_stage == 'idle' and gps_event.zone_type in ['business_district', 'city_center']:
                print(f"      🎯 Driver Agent: Would allocate to new order (idle in {gps_event.zone_type})")
            
            # Alert System
            if gps_event.anomaly_flag:
                print(f"      🚨 Alert System: Would issue {gps_event.anomaly_flag} alert!")
            
            if processed < 5:
                print("      💭 No special conditions triggered")
                
        except Exception as e:
            print(f"Error: {e}")
    
    consumer.close()
    print(f"\n🎯 Test completed! Processed {processed} GPS events.")
    print("💡 In the full system, these reactions happen automatically!")

if __name__ == "__main__":
    quick_agent_test()