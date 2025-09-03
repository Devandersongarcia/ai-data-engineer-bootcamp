#!/usr/bin/env python3
"""
Quick agent triggers - Simple examples to activate specific agents
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from agno.agent import Agent
from agno.models.openai import OpenAIChat

load_dotenv()

def trigger_eta_agent():
    """Quick ETA agent trigger"""
    print("⏱️ Triggering ETA Agent...")
    
    eta_agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        description="Especialista em previsão de tempo de chegada para entregas em São Paulo",
        name="UberEats ETA Predictor",
        monitoring=True
    )
    
    response = eta_agent.run("""
    Calcule o ETA para esta entrega urgente:
    - De Vila Madalena para Itaim Bibi  
    - Distância: 4.2km
    - Trânsito: muito pesado (rush hour)
    - Horário: 18:30 (sexta-feira)
    - Chuva moderada
    
    Quanto tempo para chegar? (resposta em português, máx 20 palavras)
    """)
    
    print(f"✅ ETA Response: {response.content}")
    return response

def trigger_driver_allocation():
    """Quick driver allocation trigger"""
    print("\n🚗 Triggering Driver Allocation Agent...")
    
    allocation_agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        description="Especialista em alocação inteligente de motoristas para zonas de São Paulo",
        name="UberEats Driver Allocator",
        monitoring=True
    )
    
    response = allocation_agent.run("""
    URGENTE - Alocar motoristas agora:
    - 20 motoristas disponíveis
    - ALTA DEMANDA: Vila Madalena (15 pedidos), Pinheiros (12 pedidos)
    - DEMANDA NORMAL: Itaim Bibi (4 pedidos), Moema (2 pedidos)
    - Horário: 20:00 (sexta-feira)
    
    Como distribuir os motoristas? (resposta em português, máx 25 palavras)
    """)
    
    print(f"✅ Allocation Response: {response.content}")
    return response

def trigger_system_alert():
    """Quick system alert trigger"""
    print("\n🚨 Triggering System Alert Agent...")
    
    alert_agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        description="Especialista em monitoramento e alertas críticos do sistema UberEats",
        name="UberEats System Monitor",
        monitoring=True
    )
    
    response = alert_agent.run("""
    🚨 SITUAÇÃO CRÍTICA DETECTADA:
    - Motorista ID: abc123
    - Localização: Avenida Paulista
    - PARADO há 60 minutos
    - Pedido ativo há 2 horas
    - Cliente reclamando
    - Sem resposta do motorista há 45min
    
    Que ação tomar AGORA? (resposta urgente em português, máx 20 palavras)
    """)
    
    print(f"🚨 Alert Response: {response.content}")
    return response

def trigger_route_optimization():
    """Quick route optimization trigger"""
    print("\n🗺️ Triggering Route Optimization Agent...")
    
    route_agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        description="Especialista em otimização de rotas para o trânsito de São Paulo",
        name="UberEats Route Optimizer",
        monitoring=True
    )
    
    response = route_agent.run("""
    OTIMIZAR ROTA URGENTE:
    - Saída: Vila Olimpia
    - Destino: Centro (Praça da República)
    - Trânsito: CAÓTICO (Marginal parada)
    - Horário: 18:45 (rush extremo)
    - Entrega em 30min MAX
    
    Melhor rota alternativa? (nomes de ruas de SP, máx 25 palavras)
    """)
    
    print(f"🗺️ Route Response: {response.content}")
    return response

def main():
    """Run quick agent triggers"""
    print("🚀 Quick Agent Triggers")
    print("=" * 40)
    
    # Trigger each agent type with realistic scenarios
    trigger_eta_agent()
    trigger_driver_allocation()
    trigger_system_alert()
    trigger_route_optimization()
    
    print(f"\n🎯 All agents triggered successfully!")
    print(f"📊 Check dashboard: http://localhost:8503")  
    print(f"🔍 Check Agno: app.agno.com/sessions")

if __name__ == "__main__":
    main()