#!/usr/bin/env python3
"""
Rate-Limited Demo for Better Agent Processing
Generates GPS data at a controlled pace to prevent overwhelming Confluent Cloud
"""
import os
import sys
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from confluent_kafka import Consumer
from openai import OpenAI
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data.models import GPSEvent

load_dotenv()

class RateLimitedOpenAIAgent:
    """Rate-limited OpenAI agent for better performance"""
    
    def __init__(self, agent_type: str, system_prompt: str):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.last_call_time = 0
        self.min_interval = 1.0  # Minimum 1 second between API calls
        self.call_count = 0

    async def process_gps_event(self, gps_event: GPSEvent) -> dict:
        """Process GPS event with rate limiting"""
        
        # Implement rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_call_time
        
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        
        try:
            # Create focused prompt
            prompt = f"""
GPS Event Analysis:
- Driver: {str(gps_event.driver_id)[:8]}...
- Location: {gps_event.zone_name} ({gps_event.zone_type})  
- Speed: {gps_event.speed_kph} km/h
- Trip Stage: {gps_event.trip_stage}
- Traffic: {gps_event.traffic_density}
- Weather: {gps_event.weather_condition}

Provide ONE specific optimization recommendation (max 50 words):
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,  # Limit response size
                temperature=0.3   # Lower temperature for consistent responses
            )
            
            self.last_call_time = time.time()
            self.call_count += 1
            
            return {
                'agent_type': self.agent_type,
                'decision': response.choices[0].message.content.strip(),
                'gps_context': {
                    'driver_id': gps_event.driver_id,
                    'zone': gps_event.zone_name,
                    'speed': gps_event.speed_kph,
                    'stage': gps_event.trip_stage,
                    'traffic': gps_event.traffic_density
                },
                'processing_time': time.time() - current_time,
                'call_number': self.call_count
            }
            
        except Exception as e:
            return {
                'agent_type': self.agent_type,
                'error': str(e),
                'gps_context': {
                    'driver_id': gps_event.driver_id,
                    'zone': gps_event.zone_name
                }
            }

class RateLimitedDemo:
    """Rate-limited demo system"""
    
    def __init__(self):
        self.agents = self._initialize_agents()
        self.processed_events = 0
        self.api_calls_made = 0
        self.errors_encountered = 0
        
    def _initialize_agents(self):
        """Initialize OpenAI agents with rate limiting"""
        return {
            'route_optimizer': RateLimitedOpenAIAgent(
                "🗺️ Route Optimizer",
                "You are a route optimization specialist. Analyze GPS data and provide specific routing recommendations for São Paulo delivery drivers. Focus on traffic conditions and efficiency."
            ),
            'eta_predictor': RateLimitedOpenAIAgent(
                "⏱️ ETA Predictor", 
                "You are an ETA prediction specialist. Analyze GPS data to provide accurate delivery time estimates considering traffic, distance, and driver behavior patterns in São Paulo."
            ),
            'driver_allocator': RateLimitedOpenAIAgent(
                "🎯 Driver Allocator",
                "You are a driver allocation specialist. Analyze GPS data to make optimal driver assignment decisions based on location, availability, and demand patterns in São Paulo."
            )
        }

    async def start_demo(self, max_events=20, processing_delay=2.0):
        """Start rate-limited demo"""
        print("🤖 Rate-Limited OpenAI Agents Demo")
        print("=" * 60)
        print(f"📊 Processing up to {max_events} GPS events")
        print(f"⏱️ {processing_delay}s delay between events")
        print(f"🧠 Model: {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}")
        print()
        
        # Kafka configuration
        config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
            'group.id': 'rate-limited-demo',
            'auto.offset.reset': 'earliest',  # Start with historical data
            'enable.auto.commit': True
        }
        
        consumer = Consumer(config)
        consumer.subscribe(['kafka-gps-data'])
        
        print("📡 Loading GPS data from Kafka (processing historical events)...")
        print()
        
        consecutive_empty_polls = 0
        max_empty_polls = 10
        
        try:
            while self.processed_events < max_events:
                # Poll for messages
                msg = consumer.poll(timeout=3.0)
                
                if msg is None:
                    consecutive_empty_polls += 1
                    if consecutive_empty_polls >= max_empty_polls:
                        print("⏰ No new GPS data available, switching to historical data...")
                        # Switch to reading from beginning
                        consumer.close()
                        config['auto.offset.reset'] = 'earliest'
                        config['group.id'] = 'rate-limited-demo-historical'
                        consumer = Consumer(config)
                        consumer.subscribe(['kafka-gps-data'])
                        consecutive_empty_polls = 0
                    continue
                
                if msg.error():
                    print(f"❌ Consumer error: {msg.error()}")
                    continue
                
                consecutive_empty_polls = 0
                
                try:
                    # Parse GPS data
                    gps_data = json.loads(msg.value().decode('utf-8'))
                    gps_event = GPSEvent.from_kafka_message(gps_data)
                    self.processed_events += 1
                    
                    print(f"📍 GPS Event #{self.processed_events}")
                    print(f"   🚗 Driver: {str(gps_event.driver_id)[:8]}...")
                    print(f"   📍 Zone: {gps_event.zone_name} ({gps_event.zone_type})")
                    print(f"   🏃 Speed: {gps_event.speed_kph} km/h | Stage: {gps_event.trip_stage}")
                    print(f"   🚦 Traffic: {gps_event.traffic_density} | Weather: {gps_event.weather_condition}")
                    
                    # Process with relevant agent based on conditions
                    agent_decisions = await self._process_with_relevant_agents(gps_event)
                    
                    # Display agent decisions
                    if agent_decisions:
                        for decision in agent_decisions:
                            if 'error' in decision:
                                print(f"   ❌ {decision['agent_type']}: {decision['error']}")
                                self.errors_encountered += 1
                            else:
                                print(f"   {decision['agent_type']}: {decision['decision']}")
                                print(f"      ⚡ Response time: {decision['processing_time']:.2f}s")
                                self.api_calls_made += 1
                    
                    print()
                    
                    # Rate limiting delay
                    if self.processed_events < max_events:
                        print(f"⏳ Waiting {processing_delay}s before next event...")
                        await asyncio.sleep(processing_delay)
                        print()
                    
                except json.JSONDecodeError:
                    print("❌ Invalid JSON in GPS data")
                    continue
                except Exception as e:
                    print(f"❌ Error processing GPS event: {e}")
                    self.errors_encountered += 1
                    continue
                    
        finally:
            consumer.close()
            await self._print_summary()
    
    async def _process_with_relevant_agents(self, gps_event: GPSEvent):
        """Process GPS event with relevant agents only"""
        decisions = []
        
        # Route optimization for heavy traffic or high speeds
        if (gps_event.traffic_density in ['heavy', 'severe'] or 
            gps_event.speed_kph > 60 or
            gps_event.trip_stage in ['to_pickup', 'to_destination']):
            
            decision = await self.agents['route_optimizer'].process_gps_event(gps_event)
            decisions.append(decision)
        
        # ETA prediction for active deliveries
        elif (gps_event.trip_stage in ['to_pickup', 'to_destination'] and 
              gps_event.speed_kph > 5):
            
            decision = await self.agents['eta_predictor'].process_gps_event(gps_event)
            decisions.append(decision)
        
        # Driver allocation for idle drivers in business areas
        elif (gps_event.trip_stage == 'idle' and 
              gps_event.zone_type in ['business_district', 'commercial']):
            
            decision = await self.agents['driver_allocator'].process_gps_event(gps_event)
            decisions.append(decision)
        
        return decisions
    
    async def _print_summary(self):
        """Print demo summary"""
        print("🎯 Demo Summary")
        print("-" * 40)
        print(f"📊 GPS Events Processed: {self.processed_events}")
        print(f"🤖 OpenAI API Calls Made: {self.api_calls_made}")
        print(f"❌ Errors Encountered: {self.errors_encountered}")
        
        if self.api_calls_made > 0:
            success_rate = ((self.api_calls_made - self.errors_encountered) / self.api_calls_made) * 100
            print(f"✅ Success Rate: {success_rate:.1f}%")
            
            # Estimate cost (rough)
            estimated_cost = self.api_calls_made * 0.0002  # ~$0.0002 per API call for gpt-4o-mini
            print(f"💰 Estimated Cost: ${estimated_cost:.4f}")
        
        print()
        print("💡 Tips for better performance:")
        print("   • Lower processing delays for faster demos")
        print("   • Higher delays for Confluent Cloud rate limits")
        print("   • Monitor OpenAI API usage in your dashboard")

async def main():
    """Main entry point"""
    demo = RateLimitedDemo()
    
    # Customizable parameters
    max_events = 5       # Number of GPS events to process
    processing_delay = 2.0  # Seconds between events (adjust based on your rate limits)
    
    await demo.start_demo(max_events, processing_delay)

if __name__ == "__main__":
    print("🚚 UberEats Rate-Limited OpenAI Demo")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"\n💥 Demo error: {e}")