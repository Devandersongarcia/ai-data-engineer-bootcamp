#!/usr/bin/env python3
"""
Real-time Agent Monitoring Dashboard
See your UberEats agents in action with live data visualization
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
from confluent_kafka import Consumer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AgentMonitor:
    """Real-time monitoring dashboard for UberEats agents"""
    
    def __init__(self):
        self.gps_events = deque(maxlen=100)
        self.agent_activities = deque(maxlen=50)
        self.zone_stats = defaultdict(int)
        self.anomaly_alerts = deque(maxlen=20)
        self.speed_analytics = []
        self.processing_stats = {
            'total_gps_events': 0,
            'anomalies_detected': 0,
            'high_speed_events': 0,
            'zones_covered': set(),
            'active_drivers': set(),
            'trip_stages': defaultdict(int)
        }
        
    async def start_monitoring(self):
        """Start the monitoring dashboard"""
        print("🎯 UberEats Agent Activity Monitor")
        print("=" * 80)
        print("📊 Real-time agent processing visualization")
        print("🚀 Watching your agents optimize deliveries in São Paulo")
        print("-" * 80)
        
        # Configuration for multiple consumers
        config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
            'group.id': 'agent-monitor-dashboard',
            'auto.offset.reset': 'latest'
        }
        
        try:
            # Monitor input streams
            input_consumer = Consumer(config)
            input_consumer.subscribe(['kafka-gps-data', 'kafka-orders', 'kafka-drivers'])
            
            # Monitor output streams (agent results)
            output_config = {**config, 'group.id': 'agent-output-monitor'}
            output_consumer = Consumer(output_config)
            output_topics = [
                'eta-predictions', 'driver-allocations', 
                'route-optimizations', 'system-alerts'
            ]
            output_consumer.subscribe(output_topics)
            
            print("🔍 Monitoring Topics:")
            print("   📥 INPUT: kafka-gps-data, kafka-orders, kafka-drivers")  
            print("   📤 OUTPUT: eta-predictions, driver-allocations, route-optimizations")
            print()
            
            # Start monitoring loop
            last_dashboard_update = datetime.now()
            
            while True:
                # Monitor input data
                self._monitor_input_stream(input_consumer)
                
                # Monitor agent outputs
                self._monitor_agent_outputs(output_consumer)
                
                # Update dashboard every 10 seconds
                if datetime.now() - last_dashboard_update > timedelta(seconds=10):
                    self._update_dashboard()
                    last_dashboard_update = datetime.now()
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\\n👋 Monitoring stopped by user")
        finally:
            input_consumer.close()
            output_consumer.close()
    
    def _monitor_input_stream(self, consumer):
        """Monitor input data streams"""
        msg = consumer.poll(0.1)
        
        if msg is None:
            return
            
        if msg.error():
            return
            
        try:
            topic = msg.topic()
            data = json.loads(msg.value().decode('utf-8'))
            
            if topic == 'kafka-gps-data':
                self._process_gps_event(data)
            elif topic == 'kafka-orders':
                self._process_order_event(data)
            elif topic == 'kafka-drivers':
                self._process_driver_event(data)
                
        except Exception as e:
            pass  # Silent handling for demo
    
    def _monitor_agent_outputs(self, consumer):
        """Monitor agent output topics"""
        msg = consumer.poll(0.1)
        
        if msg is None:
            return
            
        if msg.error():
            return
            
        try:
            topic = msg.topic()
            data = json.loads(msg.value().decode('utf-8'))
            
            # Record agent activity
            activity = {
                'timestamp': datetime.now(),
                'agent_type': self._get_agent_type_from_topic(topic),
                'topic': topic,
                'data': data
            }
            self.agent_activities.append(activity)
            
        except Exception as e:
            pass
    
    def _process_gps_event(self, data):
        """Process GPS event for monitoring"""
        self.processing_stats['total_gps_events'] += 1
        
        # Track zones
        zone = data.get('zone_name', 'Unknown')
        self.zone_stats[zone] += 1
        self.processing_stats['zones_covered'].add(zone)
        
        # Track drivers
        driver_id = data.get('driver_id')
        if driver_id:
            self.processing_stats['active_drivers'].add(driver_id)
        
        # Track trip stages
        trip_stage = data.get('trip_stage', 'unknown')
        self.processing_stats['trip_stages'][trip_stage] += 1
        
        # Check for anomalies
        if data.get('anomaly_flag'):
            self.processing_stats['anomalies_detected'] += 1
            anomaly = {
                'timestamp': datetime.now(),
                'driver_id': driver_id,
                'flag': data.get('anomaly_flag'),
                'details': data.get('anomaly_details'),
                'zone': zone
            }
            self.anomaly_alerts.append(anomaly)
        
        # Check for high speed
        speed = float(data.get('speed_kph', 0))
        if speed > 80:
            self.processing_stats['high_speed_events'] += 1
        
        # Store recent GPS event
        gps_event = {
            'timestamp': datetime.now(),
            'driver_id': driver_id,
            'location': (data.get('latitude'), data.get('longitude')),
            'speed': speed,
            'zone': zone,
            'trip_stage': trip_stage,
            'anomaly': data.get('anomaly_flag')
        }
        self.gps_events.append(gps_event)
    
    def _process_order_event(self, data):
        """Process order event"""
        # Add order processing logic here
        pass
        
    def _process_driver_event(self, data):
        """Process driver event"""  
        # Add driver processing logic here
        pass
    
    def _get_agent_type_from_topic(self, topic):
        """Map topic to agent type"""
        mapping = {
            'eta-predictions': '⏱️ ETA Agent',
            'driver-allocations': '🎯 Driver Agent', 
            'route-optimizations': '🗺️ Route Agent',
            'system-alerts': '🚨 Alert System'
        }
        return mapping.get(topic, '🤖 Agent')
    
    def _update_dashboard(self):
        """Update the monitoring dashboard"""
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🎯 UberEats Agent Activity Monitor - LIVE")
        print("=" * 80)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Processing Statistics
        print("📊 PROCESSING STATS:")
        print(f"   📍 GPS Events: {self.processing_stats['total_gps_events']:,}")
        print(f"   🚗 Active Drivers: {len(self.processing_stats['active_drivers'])}")
        print(f"   🌍 Zones Covered: {len(self.processing_stats['zones_covered'])}")
        print(f"   🚨 Anomalies: {self.processing_stats['anomalies_detected']}")
        print(f"   ⚡ High Speed Events: {self.processing_stats['high_speed_events']}")
        print()
        
        # Zone Activity (Top 5)
        print("🌍 TOP ACTIVE ZONES:")
        top_zones = sorted(self.zone_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        for zone, count in top_zones:
            bar = "█" * min(20, count // 5)  # Simple bar chart
            print(f"   📍 {zone:<15} {count:>4} {bar}")
        print()
        
        # Trip Stage Distribution
        print("📊 TRIP STAGES:")
        for stage, count in self.processing_stats['trip_stages'].items():
            percentage = (count / max(1, self.processing_stats['total_gps_events'])) * 100
            print(f"   {stage:<15} {count:>4} ({percentage:>5.1f}%)")
        print()
        
        # Recent Agent Activities
        print("🤖 RECENT AGENT ACTIVITIES:")
        recent_activities = list(self.agent_activities)[-5:]
        for activity in reversed(recent_activities):
            time_str = activity['timestamp'].strftime('%H:%M:%S')
            agent_type = activity['agent_type']
            print(f"   [{time_str}] {agent_type} processed data")
        
        if not recent_activities:
            print("   ⏳ Waiting for agent outputs...")
        print()
        
        # Recent Anomalies
        if self.anomaly_alerts:
            print("🚨 RECENT ANOMALIES:")
            recent_anomalies = list(self.anomaly_alerts)[-3:]
            for anomaly in reversed(recent_anomalies):
                time_str = anomaly['timestamp'].strftime('%H:%M:%S')
                print(f"   [{time_str}] {anomaly['flag']} - Driver {anomaly['driver_id'][:8]}...")
                print(f"      📍 {anomaly['zone']} - {anomaly['details']}")
        print()
        
        # Recent GPS Events
        print("📍 RECENT GPS ACTIVITY:")
        recent_gps = list(self.gps_events)[-5:]
        for event in reversed(recent_gps):
            time_str = event['timestamp'].strftime('%H:%M:%S')
            driver_short = event['driver_id'][:8] if event['driver_id'] else 'Unknown'
            anomaly_flag = f" ⚠️ {event['anomaly']}" if event['anomaly'] else ""
            print(f"   [{time_str}] Driver {driver_short} in {event['zone']}")
            print(f"      🏃 {event['speed']:.1f} km/h | Stage: {event['trip_stage']}{anomaly_flag}")
        print()
        
        print("-" * 80)
        print("💡 TIP: Your agents are processing this data in real-time!")
        print("🔄 Dashboard updates every 10 seconds | Press Ctrl+C to stop")

async def main():
    """Main entry point"""
    monitor = AgentMonitor()
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())