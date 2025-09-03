#!/usr/bin/env python3
"""
Agno-Enhanced Demo with app.agno.com Monitoring
UberEats delivery optimization agents with Agno monitoring integration
"""
import os
import sys
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from confluent_kafka import Consumer, Producer
from dotenv import load_dotenv

# Agno imports
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data.models import GPSEvent

load_dotenv()

class AgnoEnhancedDemo:
    """Demo with Agno monitoring integration"""
    
    def __init__(self):
        # Initialize Agno Agents with monitoring
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Route Optimization Agent
        self.route_agent = Agent(
            model=OpenAIChat(id=self.model),
            description="Especialista em otimização de rotas para o trânsito de São Paulo. Responde sempre em português brasileiro com nomes reais de ruas de SP.",
            name="UberEats Route Optimizer",
            monitoring=True,
            debug_mode=True
        )
        
        # ETA Prediction Agent
        self.eta_agent = Agent(
            model=OpenAIChat(id=self.model),
            description="Especialista em previsão de ETA para entregas em São Paulo. Responde sempre em português brasileiro.",
            name="UberEats ETA Predictor", 
            monitoring=True,
            debug_mode=True
        )
        
        # Driver Allocation Agent
        self.driver_agent = Agent(
            model=OpenAIChat(id=self.model),
            description="Especialista em alocação de entregadores para o UberEats em São Paulo. Responde sempre em português brasileiro.",
            name="UberEats Driver Allocator",
            monitoring=True,
            debug_mode=True
        )
        
        # System Alert Agent
        self.alert_agent = Agent(
            model=OpenAIChat(id=self.model),
            description="Sistema de alertas para anomalias na operação do UberEats São Paulo. Responde sempre em português brasileiro.",
            name="UberEats Alert System",
            monitoring=True,
            debug_mode=True
        )
        
        # Kafka producer for publishing results
        producer_config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD')
        }
        self.producer = Producer(producer_config)
        
        # Metrics
        self.agent_calls_made = 0
        self.results_published = 0
        self.errors_encountered = 0

    async def run_demo(self, max_events=8):
        """Run demo with Agno agent monitoring"""
        print("🤖 Demonstração UberEats com Monitoramento Agno")
        print("=" * 70)
        print(f"📊 Processando até {max_events} eventos GPS")
        print(f"📤 Publicando resultados com monitoramento em app.agno.com")
        print(f"🧠 Modelo: {self.model}")
        print()
        
        # Kafka consumer configuration
        consumer_config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
            'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
            'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
            'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
            'group.id': 'agno-enhanced-demo',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(['kafka-gps-data'])
        
        print("📡 Processando dados GPS com agentes Agno...")
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
                    
                    # Process with Agno agents
                    await self._process_with_agno_agents(gps_event)
                    
                    print()
                    await asyncio.sleep(1.5)
                    
                except Exception as e:
                    print(f"❌ Erro ao processar evento GPS: {e}")
                    self.errors_encountered += 1
                    
        finally:
            consumer.close()
            self.producer.flush()
            await self._print_summary()

    async def _process_with_agno_agents(self, gps_event: GPSEvent):
        """Process GPS event with Agno-monitored agents"""
        
        # Route Optimization Agent
        if gps_event.traffic_density in ['heavy', 'severe'] or gps_event.speed_kph > 60:
            route_prompt = f"""
Otimize a rota para este cenário de entrega:
- Zona: {gps_event.zone_name}
- Velocidade atual: {gps_event.speed_kph} km/h
- Trânsito: {gps_event.traffic_density}
- Clima: {gps_event.weather_condition}

Forneça UMA recomendação específica de rota com nomes de ruas de São Paulo (máx 40 palavras em português).
"""
            route_response = self.route_agent.run(route_prompt)
            
            route_result = {
                'optimization_id': f"route_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'optimization': route_response.content.strip(),
                'priority': 'high' if gps_event.traffic_density == 'heavy' else 'medium',
                'estimated_time_savings': '3-8 minutes'
            }
            
            await self._publish_to_topic('route-optimizations', route_result)
            print(f"   🗺️ Agente de Rota (Agno): {route_response.content.strip()[:60]}... (publicado)")
            self.agent_calls_made += 1
        
        # ETA Prediction Agent
        elif gps_event.trip_stage in ['to_pickup', 'to_destination'] and gps_event.speed_kph > 5:
            eta_prompt = f"""
Com base nos dados de GPS, forneça uma previsão de ETA (tempo estimado de chegada):
- Velocidade atual: {gps_event.speed_kph} km/h
- Zona: {gps_event.zone_name}
- Trânsito: {gps_event.traffic_density}
- Estágio da viagem: {gps_event.trip_stage}

Forneça uma estimativa realista de ETA em minutos com breve justificativa (máx 30 palavras em português).
"""
            eta_response = self.eta_agent.run(eta_prompt)
            
            eta_result = {
                'prediction_id': f"eta_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'prediction': eta_response.content.strip(),
                'confidence': 0.85,
                'factors': {
                    'current_speed': gps_event.speed_kph,
                    'traffic_density': gps_event.traffic_density,
                    'weather': gps_event.weather_condition
                }
            }
            
            await self._publish_to_topic('eta-predictions', eta_result)
            print(f"   ⏱️ Agente ETA (Agno): {eta_response.content.strip()[:60]}... (publicado)")
            self.agent_calls_made += 1
        
        # Driver Allocation Agent
        elif gps_event.trip_stage == 'idle' and gps_event.zone_type in ['business_district', 'commercial']:
            driver_prompt = f"""
Alocação de entregador para motorista inativo:
- Zona: {gps_event.zone_name} ({gps_event.zone_type})
- Horário: {datetime.now().strftime('%H:%M')}
- Trânsito: {gps_event.traffic_density}

Recomende a melhor estratégia de alocação para UberEats em São Paulo (máx 30 palavras em português).
"""
            driver_response = self.driver_agent.run(driver_prompt)
            
            driver_result = {
                'allocation_id': f"driver_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'allocation': driver_response.content.strip(),
                'priority_score': 0.75,
                'expected_orders': 2
            }
            
            await self._publish_to_topic('driver-allocations', driver_result)
            print(f"   🎯 Agente de Motorista (Agno): {driver_response.content.strip()[:60]}... (publicado)")
            self.agent_calls_made += 1
        
        # System Alert for anomalies
        if gps_event.anomaly_flag:
            alert_prompt = f"""
Gere um alerta para anomalia detectada:
- Tipo de anomalia: {gps_event.anomaly_flag}
- Zona: {gps_event.zone_name}
- Motorista: {str(gps_event.driver_id)[:8]}
- Detalhes: {gps_event.anomaly_details or 'Sem detalhes adicionais'}

Forneça uma descrição do alerta e ação recomendada (máx 50 palavras em português).
"""
            alert_response = self.alert_agent.run(alert_prompt)
            
            alert_result = {
                'alert_id': f"anomaly_{int(time.time())}",
                'timestamp': datetime.now().isoformat(),
                'severity': 'high',
                'type': gps_event.anomaly_flag,
                'driver_id': gps_event.driver_id,
                'zone': gps_event.zone_name,
                'details': alert_response.content.strip(),
                'recommended_action': 'Investigar comportamento do motorista e precisão da localização'
            }
            
            await self._publish_to_topic('system-alerts', alert_result)
            print(f"   🚨 Sistema de Alerta (Agno): alerta {gps_event.anomaly_flag} emitido (publicado)")
            self.agent_calls_made += 1

    async def _publish_to_topic(self, topic: str, data: dict):
        """Publish agent result to Kafka topic"""
        try:
            message = json.dumps(data)
            self.producer.produce(topic, value=message)
            self.results_published += 1
        except Exception as e:
            print(f"   ❌ Falha ao publicar no tópico {topic}: {e}")
            self.errors_encountered += 1

    async def _print_summary(self):
        """Print demo summary"""
        print("🎯 Resumo da Demonstração com Agno")
        print("-" * 50)
        print(f"🤖 Chamadas dos Agentes Agno: {self.agent_calls_made}")
        print(f"📤 Resultados Publicados: {self.results_published}")
        print(f"❌ Erros: {self.errors_encountered}")
        
        if self.agent_calls_made > 0:
            success_rate = ((self.agent_calls_made - self.errors_encountered) / self.agent_calls_made) * 100
            print(f"✅ Taxa de Sucesso: {success_rate:.1f}%")
        
        print()
        print("📊 Resultados publicados nos tópicos:")
        print("   • eta-predictions")
        print("   • route-optimizations") 
        print("   • driver-allocations")
        print("   • system-alerts")
        print()
        print("💡 Verifique app.agno.com/sessions para ver a atividade dos agentes!")
        print("📱 Dashboard local: streamlit run interface/main.py")

async def main():
    """Main entry point"""
    demo = AgnoEnhancedDemo()
    await demo.run_demo(max_events=8)

if __name__ == "__main__":
    print("🚚 Demonstração UberEats com Monitoramento Agno")
    print(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demonstração interrompida pelo usuário")
    except Exception as e:
        print(f"\n💥 Erro na demonstração: {e}")