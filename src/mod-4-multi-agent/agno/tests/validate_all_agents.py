#!/usr/bin/env python3
"""
Validate all UberEats agent types (Route, ETA, Driver Allocation, System Alerts)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from agno.agent import Agent
from agno.models.openai import OpenAIChat

def test_route_optimization_agent():
    """Test Route Optimization Agent"""
    print("🗺️ Testing Route Optimization Agent...")
    try:
        route_agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Especialista em otimização de rotas para o trânsito de São Paulo",
            name="UberEats Route Optimizer",
            monitoring=True,
            debug_mode=True
        )
        
        response = route_agent.run("""
        Otimize a rota para este cenário:
        - Zona: Vila_Madalena  
        - Velocidade: 8 km/h
        - Trânsito: heavy
        Forneça uma recomendação específica (máx 30 palavras).
        """)
        
        print(f"   ✅ Route Agent Response: {response.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"   ❌ Route Agent Failed: {e}")
        return False

def test_eta_prediction_agent():
    """Test ETA Prediction Agent"""
    print("\n⏱️ Testing ETA Prediction Agent...")
    try:
        eta_agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Especialista em previsão de tempo de chegada considerando trânsito de São Paulo",
            name="UberEats ETA Predictor",
            monitoring=True,
            debug_mode=True
        )
        
        response = eta_agent.run("""
        Calcule o ETA para esta entrega:
        - De: Vila_Madalena para Pinheiros
        - Distância: 3.2km  
        - Trânsito atual: moderate
        - Hora: 19:30 (rush hour)
        Forneça ETA estimado em minutos (máx 25 palavras).
        """)
        
        print(f"   ✅ ETA Agent Response: {response.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"   ❌ ETA Agent Failed: {e}")
        return False

def test_driver_allocation_agent():
    """Test Driver Allocation Agent"""
    print("\n🚗 Testing Driver Allocation Agent...")
    try:
        allocation_agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Especialista em alocação inteligente de motoristas para zonas de São Paulo",
            name="UberEats Driver Allocator",
            monitoring=True,
            debug_mode=True
        )
        
        response = allocation_agent.run("""
        Aloque motoristas para esta situação:
        - 12 motoristas disponíveis
        - Zonas com alta demanda: Vila_Madalena (8 pedidos), Itaim_Bibi (6 pedidos)  
        - Zonas normais: Pinheiros (2 pedidos)
        - Hora: 20:00
        Forneça recomendação de alocação (máx 30 palavras).
        """)
        
        print(f"   ✅ Driver Allocation Agent Response: {response.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"   ❌ Driver Allocation Agent Failed: {e}")
        return False

def test_system_alerts_agent():
    """Test System Alerts Agent"""  
    print("\n🚨 Testing System Alerts Agent...")
    try:
        alerts_agent = Agent(
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Especialista em análise de anomalias e alertas do sistema UberEats",
            name="UberEats System Monitor",
            monitoring=True,
            debug_mode=True
        )
        
        response = alerts_agent.run("""
        Analise esta situação anômala:
        - Motorista parado por 45min em Itaim_Bibi
        - Velocidade: 0 km/h  
        - Pedido ativo há 1h20min
        - Sem comunicação há 30min
        Gere alerta apropriado (máx 25 palavras).
        """)
        
        print(f"   ✅ System Alerts Agent Response: {response.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"   ❌ System Alerts Agent Failed: {e}")
        return False

def main():
    """Main validation function"""
    print("🧪 Validating All UberEats Agent Types")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test each agent type
    results = {
        "Route Optimization": test_route_optimization_agent(),
        "ETA Prediction": test_eta_prediction_agent(), 
        "Driver Allocation": test_driver_allocation_agent(),
        "System Alerts": test_system_alerts_agent()
    }
    
    # Summary
    print(f"\n🎯 Agent Validation Results")
    print("-" * 40)
    
    working_agents = 0
    total_agents = len(results)
    
    for agent_type, is_working in results.items():
        status = "✅ WORKING" if is_working else "❌ FAILED"
        print(f"   {agent_type}: {status}")
        if is_working:
            working_agents += 1
    
    print(f"\n📊 Summary: {working_agents}/{total_agents} agents working")
    success_rate = (working_agents / total_agents) * 100
    print(f"✅ Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 ALL AGENTS ARE WORKING PERFECTLY!")
        print("💡 Check app.agno.com/sessions for monitoring data")
    elif success_rate >= 75:
        print(f"\n⚠️ MOST AGENTS WORKING - {4 - working_agents} agents need attention")
    else:
        print(f"\n🚨 MULTIPLE AGENTS OFFLINE - Immediate attention required")

if __name__ == "__main__":
    main()