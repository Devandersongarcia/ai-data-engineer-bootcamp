#!/usr/bin/env python3
"""
Demonstrate Agent Actions - Simulate real agent outputs
Shows how agents react to GPS data and publish optimization results
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from confluent_kafka import Consumer, Producer
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data.models import GPSEvent, ETAPredictionResult, DriverAllocationResult, RouteOptimizationResult

# Load environment variables
load_dotenv()

class AgentActionDemo:
    """Demonstrates agent actions by simulating realistic responses to GPS data"""
    
    def __init__(self):
        # Kafka configuration
        self.kafka_config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
        }
        
        # Create producer for agent outputs
        self.producer = Producer(self.kafka_config)
        
        # Agent simulation stats
        self.agents_triggered = 0
        self.eta_predictions = 0
        self.route_optimizations = 0
        self.driver_allocations = 0
        
    async def start_demo(self):
        """Start the agent action demonstration"""
        print("🤖 UberEats Agent Action Demo")
        print("=" * 60)
        print("🎯 Simulating realistic agent responses to live GPS data")
        print("📊 Watch agents optimize deliveries in real-time")
        print("-" * 60)
        
        # Consumer configuration
        consumer_config = {
            **self.kafka_config,
            'group.id': 'agent-action-demo',
            'auto.offset.reset': 'latest'
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(['kafka-gps-data'])
        
        print("📡 Listening to GPS data...")
        print("🤖 Agents will react to interesting events")
        print()
        
        try:
            while True:
                msg = consumer.poll(1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    continue
                
                try:
                    # Parse GPS data
                    gps_data = json.loads(msg.value().decode('utf-8'))
                    gps_event = GPSEvent.from_kafka_message(gps_data)
                    
                    # Simulate agent reactions
                    await self._simulate_agent_reactions(gps_event)
                    
                except Exception as e:
                    print(f"Error processing GPS event: {e}")
                    
        except KeyboardInterrupt:
            print("\\n👋 Demo stopped by user")
        finally:
            consumer.close()
            
    async def _simulate_agent_reactions(self, gps_event: GPSEvent):
        """Simulate realistic agent reactions to GPS events"""
        
        # 1. ETA Agent - React to moving drivers with orders
        if (gps_event.trip_stage in ['to_pickup', 'to_destination'] and 
            gps_event.speed_kph > 10 and gps_event.order_id):
            await self._trigger_eta_prediction(gps_event)
        
        # 2. Route Agent - React to heavy traffic or high speeds
        if (gps_event.traffic_density == 'heavy' or gps_event.speed_kph > 90):
            await self._trigger_route_optimization(gps_event)
        
        # 3. Driver Allocation - React to idle drivers in busy zones
        if (gps_event.trip_stage == 'idle' and 
            gps_event.zone_type in ['business_district', 'city_center']):
            await self._trigger_driver_allocation(gps_event)
        
        # 4. Alert System - React to anomalies
        if gps_event.anomaly_flag:
            await self._trigger_anomaly_alert(gps_event)
    
    async def _trigger_eta_prediction(self, gps_event: GPSEvent):
        """Simulate ETA Prediction Agent"""
        self.eta_predictions += 1
        
        # Calculate realistic ETA based on current conditions
        base_time = 15  # minutes
        
        # Adjust for traffic
        traffic_multiplier = {
            'light': 0.8, 'moderate': 1.0, 'heavy': 1.4, 'severe': 1.8
        }.get(gps_event.traffic_density, 1.0)
        
        # Adjust for weather
        weather_multiplier = {
            'clear': 1.0, 'rain': 1.2, 'snow': 1.5, 'fog': 1.3
        }.get(gps_event.weather_condition, 1.0)
        
        estimated_minutes = base_time * traffic_multiplier * weather_multiplier
        
        # Create ETA prediction result
        eta_result = {
            'order_id': gps_event.order_id,
            'timestamp': datetime.now().isoformat(),
            'predicted_delivery_time': (datetime.now() + timedelta(minutes=estimated_minutes)).isoformat(),
            'confidence_score': 0.87,
            'total_time_minutes': estimated_minutes,
            'factors': [
                f"Current speed: {gps_event.speed_kph:.1f} km/h",
                f"Traffic: {gps_event.traffic_density}",
                f"Weather: {gps_event.weather_condition}",
                f"Zone: {gps_event.zone_name}"
            ],
            'agent_id': 'eta_prediction_agent'
        }
        
        # Publish to output topic
        self._publish_result('eta-predictions', eta_result, '⏱️ ETA Agent')
        
        print(f"⏱️ ETA AGENT: Predicted {estimated_minutes:.1f}min delivery for order {gps_event.order_id}")
        print(f"   📍 Driver in {gps_event.zone_name} | Traffic: {gps_event.traffic_density}")
    
    async def _trigger_route_optimization(self, gps_event: GPSEvent):
        """Simulate Route Optimization Agent"""
        self.route_optimizations += 1
        
        # Determine optimization reason
        reason = "heavy traffic" if gps_event.traffic_density == 'heavy' else "high speed detected"
        time_saved = 8.5 if gps_event.traffic_density == 'heavy' else 3.2
        
        route_result = {
            'driver_id': gps_event.driver_id,
            'timestamp': datetime.now().isoformat(),
            'optimized_route': [{
                'type': 'current_location',
                'lat': gps_event.latitude,
                'lng': gps_event.longitude,
                'zone': gps_event.zone_name,
                'reason': reason
            }],
            'total_distance_km': 12.3,
            'total_time_minutes': 18.5,
            'time_savings_minutes': time_saved,
            'efficiency_score': 0.84,
            'fuel_savings_estimate': 0.35,
            'agent_id': 'route_optimization_agent'
        }
        
        self._publish_result('route-optimizations', route_result, '🗺️ Route Agent')
        
        print(f"🗺️ ROUTE AGENT: Optimized route for driver {gps_event.driver_id[:8]}...")
        print(f"   🚦 Reason: {reason} | Time saved: {time_saved:.1f} min")
    
    async def _trigger_driver_allocation(self, gps_event: GPSEvent):
        """Simulate Driver Allocation Agent"""
        self.driver_allocations += 1
        
        allocation_result = {
            'order_id': f"order_{datetime.now().strftime('%H%M%S')}",
            'assigned_driver_id': gps_event.driver_id,
            'timestamp': datetime.now().isoformat(),
            'allocation_score': 0.92,
            'estimated_pickup_time': (datetime.now() + timedelta(minutes=5)).isoformat(),
            'reasoning': [
                f"Driver idle in high-demand {gps_event.zone_type}",
                f"Located in {gps_event.zone_name}",
                "Optimal distance to pickup location"
            ],
            'alternative_drivers': [],
            'agent_id': 'driver_allocation_agent'
        }
        
        self._publish_result('driver-allocations', allocation_result, '🎯 Driver Agent')
        
        print(f"🎯 DRIVER AGENT: Allocated driver {gps_event.driver_id[:8]}... to new order")
        print(f"   📍 Available in {gps_event.zone_name} ({gps_event.zone_type})")
    
    async def _trigger_anomaly_alert(self, gps_event: GPSEvent):
        """Simulate anomaly alert system"""
        severity = "critical" if gps_event.anomaly_flag == "GPS_SPOOFING" else "warning"
        
        alert = {
            'alert_id': f"anomaly_{datetime.now().strftime('%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'alert_type': 'anomaly',
            'severity': severity,
            'message': f"GPS anomaly detected: {gps_event.anomaly_details}",
            'affected_components': ['driver_tracking', 'route_optimization'],
            'recommended_actions': ['Verify driver location', 'Contact driver'],
            'agent_id': 'anomaly_detector'
        }
        
        self._publish_result('system-alerts', alert, '🚨 Alert System')
        
        print(f"🚨 ALERT SYSTEM: {gps_event.anomaly_flag} detected!")
        print(f"   ⚠️ {gps_event.anomaly_details}")
    
    def _publish_result(self, topic: str, result: dict, agent_name: str):
        """Publish agent result to Kafka topic"""
        try:
            message = json.dumps(result)
            self.producer.produce(
                topic=topic,
                value=message,
                callback=lambda err, msg: self._delivery_callback(err, msg, agent_name)
            )
            self.producer.poll(0)  # Trigger callbacks
            
        except Exception as e:
            print(f"   ❌ Failed to publish {agent_name} result: {e}")
    
    def _delivery_callback(self, err, msg, agent_name):
        """Callback for message delivery confirmation"""
        if err:
            print(f"   ❌ {agent_name} delivery failed: {err}")
        else:
            print(f"   ✅ {agent_name} result published to {msg.topic()}")
    
    def __del__(self):
        """Cleanup producer"""
        if hasattr(self, 'producer'):
            self.producer.flush()

async def main():
    """Main entry point"""
    demo = AgentActionDemo()
    await demo.start_demo()

if __name__ == "__main__":
    asyncio.run(main())