#!/usr/bin/env python3
"""
Step 4: Start Agno Fraud Analysis Agents
"""
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

async def main():
    print("🤖 Starting Agno Fraud Analysis Agents...")
    
    try:
        from agents.fraud_agents import FraudAgentSystem
        
        # Initialize agent system
        agent_system = FraudAgentSystem()
        print("✅ Agno agents initialized")
        
        # Test agents with sample data
        test_order = {
            "order_id": "test_001",
            "user_id": "user_123",
            "total_amount": 150.00,
            "payment_method": "credit_card",
            "restaurant_id": "rest_456"
        }
        
        print("🧪 Testing fraud detection...")
        result = await agent_system.analyze_order(test_order)
        
        print(f"📊 Test result: {result.get('fraud_analysis', {}).get('recommended_action', 'Unknown')}")
        print("✅ Agno agents ready for fraud detection")
        
        return agent_system
        
    except Exception as e:
        print(f"❌ Agno initialization failed: {e}")
        return None

if __name__ == "__main__":
    agent_system = asyncio.run(main())
    if agent_system:
        print("🚀 Agno agents running. Ready to process fraud detection requests.")
        print("Use the API or call agent_system.analyze_order() directly")
    else:
        sys.exit(1)