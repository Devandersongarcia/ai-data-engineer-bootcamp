#!/usr/bin/env python3
"""
Rate-Limited Demo with Agent Result Publishing
Generates GPS data and publishes agent results to output topics for dashboard monitoring
"""
import os
import sys
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from confluent_kafka import Consumer, Producer
from openai import OpenAI
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data.models import GPSEvent

load_dotenv()

class AgentPublishingDemo:
    """Demo that publishes agent results to output topics"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Kafka producer for publishing agent results
        producer_config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD')
        }
        self.producer = Producer(producer_config)
        
        self.api_calls_made = 0
        self.results_published = 0
        self.errors_encountered = 0

    async def run_demo(self, max_events=8):
        """Run demo with agent result publishing"""
        print("🤖 Demonstração dos Agentes OpenAI com Integração ao Dashboard")
        print("=" * 70)
        print(f"📊 Processando até {max_events} eventos GPS")
        print(f"📤 Publicando resultados dos agentes para tópicos de saída")
        print(f"🧠 Modelo: {self.model}")
        print()
        
        # Kafka consumer configuration
        consumer_config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
            'group.id': 'agent-publishing-demo',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(['kafka-gps-data'])
        
        print("📡 Processando dados GPS com publicação dos agentes...")
        print()
        
        processed = 0
        
        try:
            while processed < max_events:
                msg = consumer.poll(timeout=3.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    continue
                
                try:
                    # Parse GPS data
                    gps_data = json.loads(msg.value().decode('utf-8'))
                    gps_event = GPSEvent.from_kafka_message(gps_data)
                    processed += 1
                    
                    print(f"📍 Evento GPS #{processed}")
                    print(f"   🚗 Motorista: {str(gps_event.driver_id)[:8]}...")
                    print(f"   📍 Zona: {gps_event.zone_name} ({gps_event.zone_type})")
                    print(f"   🏃 Velocidade: {gps_event.speed_kph} km/h | Estágio: {gps_event.trip_stage}")
                    print(f"   🚦 Trânsito: {gps_event.traffic_density}")
                    
                    # Process with agents and publish results
                    await self._process_and_publish_agent_results(gps_event)
                    
                    print()
                    
                    # Small delay between events
                    await asyncio.sleep(1.5)
                    
                except Exception as e:
                    print(f"❌ Erro ao processar evento GPS: {e}")
                    self.errors_encountered += 1
                    
        finally:
            consumer.close()
            self.producer.flush()
            await self._print_summary()

    async def _process_and_publish_agent_results(self, gps_event: GPSEvent):
        """Process GPS event with agents and publish results"""
        
        # ETA Prediction Agent
        if gps_event.trip_stage in ['to_pickup', 'to_destination'] and gps_event.speed_kph > 5:
            eta_result = await self._get_eta_prediction(gps_event)
            if eta_result:
                await self._publish_to_topic('eta-predictions', eta_result)
                print(f"   ⏱️ Agente ETA: {eta_result['prediction']} (publicado)")
        
        # Route Optimization Agent  
        elif gps_event.traffic_density in ['heavy', 'severe'] or gps_event.speed_kph > 60:
            route_result = await self._get_route_optimization(gps_event)
            if route_result:
                await self._publish_to_topic('route-optimizations', route_result)
                print(f"   🗺️ Agente de Rota: {route_result['optimization']} (publicado)")
        
        # Driver Allocation Agent
        elif gps_event.trip_stage == 'idle' and gps_event.zone_type in ['business_district', 'commercial']:
            driver_result = await self._get_driver_allocation(gps_event)
            if driver_result:
                await self._publish_to_topic('driver-allocations', driver_result)
                print(f"   🎯 Agente de Motorista: {driver_result['allocation']} (publicado)")
        
        # System Alert for anomalies
        if gps_event.anomaly_flag:
            alert_result = {
                'alert_id': f"anomaly_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'severity': 'high',
                'type': gps_event.anomaly_flag,
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'details': gps_event.anomaly_details or f"{gps_event.anomaly_flag} detected",
                'recommended_action': 'Investigate driver behavior and location accuracy'
            }
            await self._publish_to_topic('system-alerts', alert_result)
            print(f"   🚨 Sistema de Alerta: alerta {gps_event.anomaly_flag} emitido (publicado)")

    async def _get_eta_prediction(self, gps_event: GPSEvent):
        """Get ETA prediction from OpenAI"""
        try:
            prompt = f"""
Com base nos dados de GPS, forneça uma previsão de ETA (tempo estimado de chegada):
- Velocidade atual: {gps_event.speed_kph} km/h
- Zona: {gps_event.zone_name}
- Trânsito: {gps_event.traffic_density}
- Estágio da viagem: {gps_event.trip_stage}

Forneça uma estimativa realista de ETA em minutos com breve justificativa (máx 30 palavras em português).
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em previsão de ETA para entregas em São Paulo. Responda sempre em português brasileiro."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,
                temperature=0.3
            )
            
            self.api_calls_made += 1
            
            return {
                'prediction_id': f"eta_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'prediction': response.choices[0].message.content.strip(),
                'confidence': 0.85,
                'factors': {
                    'current_speed': gps_event.speed_kph,
                    'traffic_density': gps_event.traffic_density,
                    'weather': gps_event.weather_condition
                }
            }
            
        except Exception as e:
            self.errors_encountered += 1
            return None

    async def _get_route_optimization(self, gps_event: GPSEvent):
        """Get route optimization from OpenAI"""
        try:
            prompt = f"""
Otimize a rota para este cenário de entrega:
- Zona: {gps_event.zone_name}
- Velocidade atual: {gps_event.speed_kph} km/h
- Trânsito: {gps_event.traffic_density}
- Clima: {gps_event.weather_condition}

Forneça UMA recomendação específica de rota com nomes de ruas de São Paulo (máx 40 palavras em português).
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em otimização de rotas para o trânsito de São Paulo. Responda sempre em português brasileiro com nomes reais de ruas de SP."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            self.api_calls_made += 1
            
            return {
                'optimization_id': f"route_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'optimization': response.choices[0].message.content.strip(),
                'priority': 'high' if gps_event.traffic_density == 'heavy' else 'medium',
                'estimated_time_savings': '3-8 minutes'
            }
            
        except Exception as e:
            self.errors_encountered += 1
            return None

    async def _get_driver_allocation(self, gps_event: GPSEvent):
        """Get driver allocation recommendation from OpenAI"""
        try:
            prompt = f"""
Alocação de entregador para motorista inativo:
- Zona: {gps_event.zone_name} ({gps_event.zone_type})
- Horário: {datetime.now().strftime('%H:%M')}
- Trânsito: {gps_event.traffic_density}

Recomende a melhor estratégia de alocação para UberEats em São Paulo (máx 30 palavras em português).
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em alocação de entregadores para o UberEats em São Paulo. Responda sempre em português brasileiro."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,
                temperature=0.3
            )
            
            self.api_calls_made += 1
            
            return {
                'allocation_id': f"driver_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'allocation': response.choices[0].message.content.strip(),
                'priority_score': 0.75,
                'expected_orders': 2
            }
            
        except Exception as e:
            self.errors_encountered += 1
            return None

    async def _publish_to_topic(self, topic: str, data: dict):
        """Publish agent result to Kafka topic"""
        try:
            message = json.dumps(data)
            self.producer.produce(topic, value=message)
            self.results_published += 1
            # Don't flush after every message to improve performance
            
        except Exception as e:
            print(f"   ❌ Failed to publish to {topic}: {e}")
            self.errors_encountered += 1

    async def _print_summary(self):
        """Print demo summary"""
        print("🎯 Resumo da Demonstração")
        print("-" * 50)
        print(f"🤖 Chamadas da API OpenAI: {self.api_calls_made}")
        print(f"📤 Resultados Publicados: {self.results_published}")
        print(f"❌ Erros: {self.errors_encountered}")
        
        if self.api_calls_made > 0:
            success_rate = ((self.api_calls_made - self.errors_encountered) / self.api_calls_made) * 100
            print(f"✅ Taxa de Sucesso: {success_rate:.1f}%")
            
            estimated_cost = self.api_calls_made * 0.0002
            print(f"💰 Custo Estimado: ${estimated_cost:.4f}")
        
        print()
        print("📊 Resultados publicados nos tópicos:")
        print("   • eta-predictions")
        print("   • route-optimizations") 
        print("   • driver-allocations")
        print("   • system-alerts")
        print()
        print("💡 Verifique o monitor do dashboard (Opção 1) para ver a atividade dos agentes!")

async def main():
    """Main entry point"""
    demo = AgentPublishingDemo()
    await demo.run_demo(max_events=8)

if __name__ == "__main__":
    print("🚚 Demonstração dos Agentes UberEats com Integração ao Dashboard")
    print(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demonstração interrompida pelo usuário")
    except Exception as e:
        print(f"\n💥 Erro na demonstração: {e}")