#!/usr/bin/env python3
"""
Trigger specific UberEats agent types with realistic scenarios
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from confluent_kafka import Producer
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from data.models import GPSEvent

load_dotenv()

class AgentTriggerDemo:
    """Demo to trigger different agent types with specific scenarios"""
    
    def __init__(self):
        self.producer = Producer({
            'bootstrap.servers': os.getenv('CONFLUENT_BOOTSTRAP_SERVERS'),
            'sasl.mechanisms': 'PLAIN',
            'security.protocol': 'SASL_SSL',
            'sasl.username': os.getenv('CONFLUENT_API_KEY'),
            'sasl.password': os.getenv('CONFLUENT_API_SECRET'),
        })
        
        # Initialize agents
        self.eta_agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Especialista em previsão de tempo de chegada para entregas em São Paulo",
            name="UberEats ETA Predictor",
            monitoring=True,
            debug_mode=True
        )
        
        self.allocation_agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Especialista em alocação inteligente de motoristas para zonas de São Paulo",
            name="UberEats Driver Allocator", 
            monitoring=True,
            debug_mode=True
        )
        
        self.alerts_agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Especialista em monitoramento e alertas do sistema UberEats",
            name="UberEats System Monitor",
            monitoring=True,
            debug_mode=True
        )

    def trigger_eta_predictions(self):
        """Trigger ETA prediction agents with delivery scenarios"""
        print("⏱️ Triggering ETA Prediction Agents...")
        
        eta_scenarios = [
            {
                "origin": "Vila_Madalena",
                "destination": "Pinheiros", 
                "distance_km": 2.8,
                "current_traffic": "heavy",
                "time_of_day": "19:30",
                "weather": "rain"
            },
            {
                "origin": "Itaim_Bibi",
                "destination": "Vila_Olimpia",
                "distance_km": 1.5, 
                "current_traffic": "moderate",
                "time_of_day": "12:15",
                "weather": "clear"
            },
            {
                "origin": "Centro",
                "destination": "Moema",
                "distance_km": 8.2,
                "current_traffic": "very_heavy",
                "time_of_day": "18:00",
                "weather": "fog"
            }
        ]
        
        for i, scenario in enumerate(eta_scenarios, 1):
            print(f"\n📍 ETA Scenario {i}:")
            print(f"   From: {scenario['origin']} → To: {scenario['destination']}")
            print(f"   Distance: {scenario['distance_km']}km | Traffic: {scenario['current_traffic']}")
            
            prompt = f"""
            Calcule o ETA preciso para esta entrega:
            - Origem: {scenario['origin']}
            - Destino: {scenario['destination']}
            - Distância: {scenario['distance_km']}km
            - Trânsito atual: {scenario['current_traffic']}
            - Horário: {scenario['time_of_day']}
            - Clima: {scenario['weather']}
            
            Forneça ETA em minutos considerando condições do trânsito de São Paulo (máx 30 palavras).
            """
            
            response = self.eta_agent.run(prompt)
            eta_result = {
                "message_id": f"eta_{int(time.time())}_{i}",
                "agent_type": "ETA Prediction",
                "scenario": scenario,
                "eta_minutes": response.content,
                "timestamp": datetime.now().isoformat(),
                "confidence": "high"
            }
            
            # Publish to eta-predictions topic
            self.producer.produce(
                'eta-predictions',
                key=eta_result["message_id"],
                value=json.dumps(eta_result)
            )
            
            print(f"   ✅ ETA: {response.content[:80]}...")
            time.sleep(2)  # Avoid rate limiting
        
        self.producer.flush()
        print(f"\n🎯 Published {len(eta_scenarios)} ETA predictions to Kafka")

    def trigger_driver_allocation(self):
        """Trigger driver allocation with demand scenarios"""
        print("\n🚗 Triggering Driver Allocation Agents...")
        
        allocation_scenarios = [
            {
                "available_drivers": 15,
                "high_demand_zones": {
                    "Vila_Madalena": 12,
                    "Itaim_Bibi": 8
                },
                "normal_zones": {
                    "Pinheiros": 3,
                    "Moema": 2
                },
                "time": "20:30",
                "day": "Friday"
            },
            {
                "available_drivers": 8,
                "high_demand_zones": {
                    "Centro": 15,
                    "Vila_Olimpia": 6
                },
                "normal_zones": {
                    "Jardins": 2
                },
                "time": "12:00", 
                "day": "Sunday"
            },
            {
                "available_drivers": 25,
                "high_demand_zones": {
                    "Moema": 10,
                    "Brooklin": 8,
                    "Vila_Olimpia": 7
                },
                "normal_zones": {
                    "Pinheiros": 1,
                    "Vila_Madalena": 2
                },
                "time": "19:00",
                "day": "Saturday"
            }
        ]
        
        for i, scenario in enumerate(allocation_scenarios, 1):
            print(f"\n📊 Allocation Scenario {i}:")
            print(f"   Available Drivers: {scenario['available_drivers']}")
            print(f"   High Demand: {scenario['high_demand_zones']}")
            print(f"   Time: {scenario['time']} ({scenario['day']})")
            
            high_demand_text = ", ".join([f"{zone} ({orders} pedidos)" for zone, orders in scenario['high_demand_zones'].items()])
            normal_demand_text = ", ".join([f"{zone} ({orders} pedidos)" for zone, orders in scenario['normal_zones'].items()])
            
            prompt = f"""
            Otimize a alocação de motoristas para:
            - {scenario['available_drivers']} motoristas disponíveis
            - Zonas alta demanda: {high_demand_text}
            - Zonas normais: {normal_demand_text}
            - Horário: {scenario['time']} ({scenario['day']})
            
            Forneça estratégia de alocação específica (máx 40 palavras).
            """
            
            response = self.allocation_agent.run(prompt)
            allocation_result = {
                "message_id": f"allocation_{int(time.time())}_{i}",
                "agent_type": "Driver Allocation",
                "scenario": scenario,
                "allocation_strategy": response.content,
                "timestamp": datetime.now().isoformat(),
                "efficiency_score": 85 + (i * 3)
            }
            
            # Publish to driver-allocations topic
            self.producer.produce(
                'driver-allocations',
                key=allocation_result["message_id"],
                value=json.dumps(allocation_result)
            )
            
            print(f"   ✅ Strategy: {response.content[:80]}...")
            time.sleep(2)
        
        self.producer.flush()
        print(f"\n🎯 Published {len(allocation_scenarios)} allocation strategies to Kafka")

    def trigger_system_alerts(self):
        """Trigger system alerts with anomaly scenarios"""
        print("\n🚨 Triggering System Alert Agents...")
        
        alert_scenarios = [
            {
                "driver_id": "driver_abc123",
                "anomaly": "stuck_driver",
                "location": "Itaim_Bibi", 
                "stuck_duration": 45,
                "order_active_time": 80,
                "last_communication": 35
            },
            {
                "driver_id": "driver_def456",
                "anomaly": "unusual_route",
                "location": "Vila_Olimpia",
                "expected_destination": "Pinheiros",
                "current_detour": "Centro",
                "extra_distance": 12.5
            },
            {
                "driver_id": "driver_ghi789",
                "anomaly": "speed_violation", 
                "location": "Marginal_Tiete",
                "current_speed": 85,
                "speed_limit": 60,
                "duration": 8
            },
            {
                "system": "order_processing",
                "anomaly": "high_cancellation_rate",
                "zone": "Vila_Madalena",
                "cancellation_rate": 45,
                "normal_rate": 12,
                "time_window": 30
            }
        ]
        
        for i, scenario in enumerate(alert_scenarios, 1):
            print(f"\n⚠️ Alert Scenario {i}:")
            
            if "driver_id" in scenario:
                print(f"   Driver: {scenario['driver_id']} | Anomaly: {scenario['anomaly']}")
                print(f"   Location: {scenario['location']}")
                
                if scenario['anomaly'] == 'stuck_driver':
                    prompt = f"""
                    ALERTA CRÍTICO - Motorista parado:
                    - Motorista: {scenario['driver_id']}
                    - Local: {scenario['location']}
                    - Parado há: {scenario['stuck_duration']} minutos
                    - Pedido ativo há: {scenario['order_active_time']} minutos
                    - Sem comunicação há: {scenario['last_communication']} minutos
                    
                    Gere alerta urgente com ações recomendadas (máx 35 palavras).
                    """
                elif scenario['anomaly'] == 'unusual_route':
                    prompt = f"""
                    ALERTA - Rota suspeita:
                    - Motorista: {scenario['driver_id']}
                    - Deveria ir para: {scenario['expected_destination']}
                    - Atual direção: {scenario['current_detour']}
                    - Desvio extra: {scenario['extra_distance']}km
                    
                    Analise e gere alerta apropriado (máx 30 palavras).
                    """
                elif scenario['anomaly'] == 'speed_violation':
                    prompt = f"""
                    ALERTA - Excesso de velocidade:
                    - Motorista: {scenario['driver_id']}
                    - Local: {scenario['location']}
                    - Velocidade: {scenario['current_speed']} km/h (limite: {scenario['speed_limit']} km/h)
                    - Duração: {scenario['duration']} minutos
                    
                    Gere alerta de segurança (máx 25 palavras).
                    """
            else:
                # System alert
                print(f"   System: {scenario['system']} | Issue: {scenario['anomaly']}")
                prompt = f"""
                ALERTA SISTEMA - Alta taxa de cancelamento:
                - Sistema: {scenario['system']}
                - Zona afetada: {scenario['zone']}
                - Taxa atual: {scenario['cancellation_rate']}% (normal: {scenario['normal_rate']}%)
                - Janela: últimos {scenario['time_window']} minutos
                
                Analise e recomende ações (máx 30 palavras).
                """
            
            response = self.alerts_agent.run(prompt)
            alert_result = {
                "message_id": f"alert_{int(time.time())}_{i}",
                "agent_type": "System Alert",
                "scenario": scenario,
                "alert_message": response.content,
                "timestamp": datetime.now().isoformat(),
                "severity": "high" if "CRÍTICO" in prompt else "medium"
            }
            
            # Publish to system-alerts topic
            self.producer.produce(
                'system-alerts',
                key=alert_result["message_id"],
                value=json.dumps(alert_result)
            )
            
            print(f"   🚨 Alert: {response.content[:80]}...")
            time.sleep(2)
        
        self.producer.flush()
        print(f"\n🎯 Published {len(alert_scenarios)} system alerts to Kafka")

def main():
    """Run agent trigger demonstrations"""
    print("🎯 UberEats Agent Trigger Demo")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    demo = AgentTriggerDemo()
    
    try:
        # Trigger each agent type
        demo.trigger_eta_predictions()
        time.sleep(3)
        
        demo.trigger_driver_allocation()  
        time.sleep(3)
        
        demo.trigger_system_alerts()
        
        print(f"\n🎉 SUCCESS: All agent types triggered!")
        print(f"📊 Check your dashboard at http://localhost:8503")
        print(f"🔍 Check app.agno.com/sessions for monitoring data")
        print(f"📡 All results published to respective Kafka topics")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()