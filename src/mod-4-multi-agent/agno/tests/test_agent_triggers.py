#!/usr/bin/env python3
"""
Test Agent Trigger Conditions - Interactive Tool
Shows exactly when agents trigger and what conditions cause activation
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

load_dotenv()

class TriggerTester:
    """Interactive tool to test and understand agent trigger conditions"""
    
    def __init__(self):
        self.trigger_stats = {
            'eta_agent': 0,
            'route_agent': 0,
            'driver_agent': 0,
            'anomaly_system': 0,
            'no_triggers': 0
        }
        
    def start_testing(self):
        """Start interactive trigger testing"""
        print("🎯 Agent Trigger Condition Tester")
        print("=" * 60)
        print("🔍 Analyzes real GPS data to show when agents activate")
        print("📊 Learn the exact conditions that trigger each agent")
        print("-" * 60)
        
        config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
            'group.id': 'trigger-tester',
            'auto.offset.reset': 'earliest'
        }
        
        consumer = Consumer(config)
        consumer.subscribe(['kafka-gps-data'])
        
        print("📡 Analyzing GPS events for trigger conditions...")
        print("🎯 Will process 20 events to show trigger patterns")
        print()
        
        processed = 0
        while processed < 20:
            msg = consumer.poll(2.0)
            
            if msg is None:
                print("⏰ Waiting for messages...")
                continue
                
            if msg.error():
                continue
                
            try:
                gps_data = json.loads(msg.value().decode('utf-8'))
                gps_event = GPSEvent.from_kafka_message(gps_data)
                processed += 1
                
                print(f"\\n📍 EVENT #{processed}")
                print(f"   🚗 Driver: {gps_event.driver_id[:8]}...")
                print(f"   📍 Zone: {gps_event.zone_name} ({gps_event.zone_type})")
                print(f"   🏃 Speed: {gps_event.speed_kph} km/h")
                print(f"   📊 Stage: {gps_event.trip_stage}")
                print(f"   🚦 Traffic: {gps_event.traffic_density}")
                print(f"   📦 Order: {gps_event.order_id or 'None'}")
                if gps_event.anomaly_flag:
                    print(f"   🚨 Anomaly: {gps_event.anomaly_flag}")
                
                # Test all trigger conditions
                triggers = self._test_all_triggers(gps_event)
                
                if triggers:
                    print("   🤖 AGENTS TRIGGERED:")
                    for trigger in triggers:
                        print(f"      {trigger}")
                else:
                    print("   💤 No agents triggered")
                    self.trigger_stats['no_triggers'] += 1
                
            except Exception as e:
                print(f"   ❌ Error processing event: {e}")
        
        # Summary statistics
        self._show_trigger_summary()
        consumer.close()
    
    def _test_all_triggers(self, gps_event: GPSEvent) -> list:
        """Test all agent trigger conditions"""
        triggers = []
        
        # 1. ETA Prediction Agent
        if self._test_eta_trigger(gps_event):
            triggers.append("⏱️ ETA Agent: Moving driver with active order")
            self.trigger_stats['eta_agent'] += 1
            
        # 2. Route Optimization Agent  
        route_reason = self._test_route_trigger(gps_event)
        if route_reason:
            triggers.append(f"🗺️ Route Agent: {route_reason}")
            self.trigger_stats['route_agent'] += 1
            
        # 3. Driver Allocation Agent
        if self._test_allocation_trigger(gps_event):
            triggers.append(f"🎯 Driver Agent: Idle in {gps_event.zone_type}")
            self.trigger_stats['driver_agent'] += 1
            
        # 4. Anomaly Detection
        if self._test_anomaly_trigger(gps_event):
            triggers.append(f"🚨 Alert System: {gps_event.anomaly_flag} detected")
            self.trigger_stats['anomaly_system'] += 1
            
        return triggers
    
    def _test_eta_trigger(self, gps_event: GPSEvent) -> bool:
        """Test ETA agent trigger conditions"""
        return (gps_event.trip_stage in ['to_pickup', 'to_destination'] and 
                gps_event.speed_kph > 10 and 
                gps_event.order_id)
    
    def _test_route_trigger(self, gps_event: GPSEvent) -> str:
        """Test route agent trigger conditions"""
        if gps_event.traffic_density in ['heavy', 'severe']:
            return f"{gps_event.traffic_density} traffic detected"
        elif gps_event.speed_kph > 90:
            return f"High speed ({gps_event.speed_kph} km/h) optimization"
        return None
    
    def _test_allocation_trigger(self, gps_event: GPSEvent) -> bool:
        """Test driver allocation agent trigger conditions"""
        return (gps_event.trip_stage == 'idle' and 
                gps_event.zone_type in ['business_district', 'city_center'])
    
    def _test_anomaly_trigger(self, gps_event: GPSEvent) -> bool:
        """Test anomaly detection trigger conditions"""
        return gps_event.anomaly_flag is not None
    
    def _show_trigger_summary(self):
        """Show summary of trigger statistics"""
        total = sum(self.trigger_stats.values())
        
        print("\\n" + "=" * 60)
        print("📊 TRIGGER ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"📈 Total Events Analyzed: {total}")
        print()
        
        print("🤖 Agent Activation Rates:")
        for agent, count in self.trigger_stats.items():
            if agent != 'no_triggers':
                percentage = (count / total * 100) if total > 0 else 0
                bar = "█" * min(20, int(percentage))
                agent_name = {
                    'eta_agent': '⏱️ ETA Agent',
                    'route_agent': '🗺️ Route Agent', 
                    'driver_agent': '🎯 Driver Agent',
                    'anomaly_system': '🚨 Alert System'
                }.get(agent, agent)
                print(f"   {agent_name:<20} {count:>3} ({percentage:>5.1f}%) {bar}")
        
        no_trigger_pct = (self.trigger_stats['no_triggers'] / total * 100) if total > 0 else 0
        print(f"   💤 No triggers        {self.trigger_stats['no_triggers']:>3} ({no_trigger_pct:>5.1f}%)")
        
        print()
        print("💡 INSIGHTS:")
        
        # Traffic analysis
        if self.trigger_stats['route_agent'] > total * 0.3:
            print("   🚦 High traffic activity - Route agent very active")
        
        # Business district activity  
        if self.trigger_stats['driver_agent'] > total * 0.2:
            print("   🏢 Many idle drivers in business districts")
            
        # Delivery activity
        if self.trigger_stats['eta_agent'] > total * 0.1:
            print("   📦 Active delivery operations detected")
            
        # Security status
        if self.trigger_stats['anomaly_system'] == 0:
            print("   ✅ No anomalies detected - GPS data looks clean")
        else:
            print("   ⚠️ GPS anomalies detected - security monitoring active")
            
        print()
        print("🎯 BUSINESS RECOMMENDATIONS:")
        
        most_active = max(self.trigger_stats.items(), key=lambda x: x[1] if x[0] != 'no_triggers' else 0)
        
        if most_active[0] == 'route_agent':
            print("   📈 Focus on traffic optimization - high congestion detected")
        elif most_active[0] == 'driver_agent':  
            print("   👥 Optimize driver allocation - many idle drivers available")
        elif most_active[0] == 'eta_agent':
            print("   ⏰ Focus on delivery time accuracy - high order volume")
            
        print()
        print("=" * 60)

def main():
    """Main entry point"""
    tester = TriggerTester()
    tester.start_testing()

if __name__ == "__main__":
    main()