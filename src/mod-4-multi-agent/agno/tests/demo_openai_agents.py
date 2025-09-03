#!/usr/bin/env python3
"""
Demo: OpenAI-Powered Delivery Optimization Agents
Shows how GPT-4o-mini processes real GPS data for delivery optimization
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from confluent_kafka import Consumer
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data.models import GPSEvent

# Load environment variables
load_dotenv()

class OpenAIDeliveryAgent:
    """OpenAI-powered delivery optimization agent"""
    
    def __init__(self, agent_type: str, system_prompt: str):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.processed_count = 0
        
    async def process_gps_event(self, gps_event: GPSEvent) -> str:
        """Process GPS event with OpenAI"""
        try:
            # Create context-rich prompt
            prompt = self._create_gps_prompt(gps_event)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3  # Lower for consistent optimization
            )
            
            self.processed_count += 1
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error: {e}"
    
    def _create_gps_prompt(self, gps_event: GPSEvent) -> str:
        """Create rich prompt from GPS data"""
        return f"""
GPS Event Analysis:
- Location: {gps_event.zone_name} ({gps_event.zone_type})
- Driver Status: {gps_event.driver_status}, Stage: {gps_event.trip_stage}
- Speed: {gps_event.speed_kph} km/h
- Traffic: {gps_event.traffic_density}
- Weather: {gps_event.weather_condition}
- Order ID: {gps_event.order_id or 'None'}
- Distance to destination: {gps_event.distance_to_destination_km or 'N/A'} km
{f"- ANOMALY: {gps_event.anomaly_flag} - {gps_event.anomaly_details}" if gps_event.anomaly_flag else ""}

Analyze this situation and provide optimization recommendations.
"""

class OpenAIAgentDemo:
    """Demo of OpenAI agents processing real GPS data"""
    
    def __init__(self):
        # Initialize specialized agents
        self.eta_agent = OpenAIDeliveryAgent(
            "ETA Prediction",
            """You are an ETA prediction specialist for UberEats delivery optimization.
            Analyze GPS data and provide accurate delivery time estimates.
            Consider traffic, weather, distance, and driver behavior.
            Provide time estimates in minutes with confidence levels."""
        )
        
        self.route_agent = OpenAIDeliveryAgent(
            "Route Optimization", 
            """You are a route optimization specialist for UberEats delivery.
            Analyze traffic patterns and GPS data to suggest optimal routes.
            Focus on time savings, fuel efficiency, and traffic avoidance.
            Provide specific routing recommendations."""
        )
        
        self.driver_agent = OpenAIDeliveryAgent(
            "Driver Allocation",
            """You are a driver allocation specialist for UberEats.
            Analyze driver locations and availability to optimize assignments.
            Consider zone demand, driver proximity, and business efficiency.
            Provide allocation strategies and priority recommendations."""
        )
        
        self.anomaly_agent = OpenAIDeliveryAgent(
            "Anomaly Detection",
            """You are a security and anomaly detection specialist for UberEats.
            Analyze GPS data for suspicious patterns, fraud, or data integrity issues.
            Identify potential problems and recommend security actions.
            Focus on driver safety and system integrity."""
        )
    
    async def start_demo(self):
        """Start OpenAI agent demonstration"""
        print("🤖 OpenAI-Powered UberEats Delivery Optimization Demo")
        print("=" * 70)
        print("🧠 Using GPT-4o-mini for real-time delivery decisions")
        print("📡 Processing live GPS data from São Paulo")
        print("-" * 70)
        
        # Kafka configuration
        config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
            'group.id': 'openai-agents-demo',
            'auto.offset.reset': 'earliest'
        }
        
        consumer = Consumer(config)
        consumer.subscribe(['kafka-gps-data'])
        
        print("📡 OpenAI agents listening to GPS stream...")
        print("🎯 Will process 3 events to demonstrate AI-powered optimization")
        print()
        
        processed = 0
        try:
            while processed < 3:
                msg = consumer.poll(5.0)
                
                if msg is None:
                    print("⏰ Waiting for GPS messages...")
                    continue
                    
                if msg.error():
                    continue
                    
                try:
                    # Parse GPS data
                    gps_data = json.loads(msg.value().decode('utf-8'))
                    gps_event = GPSEvent.from_kafka_message(gps_data)
                    processed += 1
                    
                    print(f"📍 GPS EVENT #{processed}")
                    print(f"   🚗 Driver: {gps_event.driver_id[:8]}...")
                    print(f"   📍 Zone: {gps_event.zone_name} ({gps_event.zone_type})")
                    print(f"   🏃 Speed: {gps_event.speed_kph} km/h | Traffic: {gps_event.traffic_density}")
                    print(f"   📊 Status: {gps_event.driver_status} | Stage: {gps_event.trip_stage}")
                    if gps_event.order_id:
                        print(f"   📦 Order: {gps_event.order_id}")
                    if gps_event.anomaly_flag:
                        print(f"   🚨 Anomaly: {gps_event.anomaly_flag}")
                    print()
                    
                    # Determine which agents should process this event
                    agents_to_process = []
                    
                    # ETA Agent: Moving drivers with orders
                    if (gps_event.trip_stage in ['to_pickup', 'to_destination'] and 
                        gps_event.speed_kph > 10 and gps_event.order_id):
                        agents_to_process.append(('eta_agent', '⏱️ ETA Prediction'))
                    
                    # Route Agent: Heavy traffic or high speed
                    if (gps_event.traffic_density in ['heavy', 'severe'] or 
                        gps_event.speed_kph > 90):
                        agents_to_process.append(('route_agent', '🗺️ Route Optimization'))
                    
                    # Driver Agent: Idle drivers in business areas
                    if (gps_event.trip_stage == 'idle' and 
                        gps_event.zone_type in ['business_district', 'city_center']):
                        agents_to_process.append(('driver_agent', '🎯 Driver Allocation'))
                    
                    # Anomaly Agent: Any anomaly detected
                    if gps_event.anomaly_flag:
                        agents_to_process.append(('anomaly_agent', '🚨 Anomaly Detection'))
                    
                    if agents_to_process:
                        print("🤖 OPENAI AGENTS ACTIVATED:")
                        for agent_attr, agent_name in agents_to_process:
                            agent = getattr(self, agent_attr)
                            print(f"   🔄 Processing with {agent_name}...")
                            
                            response = await agent.process_gps_event(gps_event)
                            print(f"   🧠 {agent_name} AI Response:")
                            print(f"      {response}")
                            print()
                    else:
                        print("💤 No triggers activated for this GPS event")
                    
                    print("-" * 50)
                    print()
                    
                except Exception as e:
                    print(f"❌ Error processing GPS event: {e}")
        
        except KeyboardInterrupt:
            print("\n👋 Demo stopped by user")
        finally:
            consumer.close()
            
            # Show processing stats
            print("\n📊 OpenAI Agent Processing Summary:")
            print(f"   ⏱️ ETA Agent: {self.eta_agent.processed_count} events")
            print(f"   🗺️ Route Agent: {self.route_agent.processed_count} events") 
            print(f"   🎯 Driver Agent: {self.driver_agent.processed_count} events")
            print(f"   🚨 Anomaly Agent: {self.anomaly_agent.processed_count} events")
            print(f"   📈 Total OpenAI API calls: {sum([
                self.eta_agent.processed_count,
                self.route_agent.processed_count,
                self.driver_agent.processed_count, 
                self.anomaly_agent.processed_count
            ])}")
            
            print("\n🎉 OpenAI agents successfully optimized São Paulo deliveries!")

async def main():
    """Main entry point"""
    demo = OpenAIAgentDemo()
    await demo.start_demo()

if __name__ == "__main__":
    asyncio.run(main())