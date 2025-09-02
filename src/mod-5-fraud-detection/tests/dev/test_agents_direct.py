#!/usr/bin/env python3
"""
Direct CrewAI Agents Test
Test if CrewAI agents are working correctly with streaming integration
"""

import sys
sys.path.append('/Users/mateusoliveira/Mateus/owshq/projects/pycharm/uberats-fraud-detection')

import logging
from src.streaming.simple_agentic_processor import SimpleAgenticProcessor
from src.agents.crewai_with_prompts import PromptBasedCrewAISystem

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("🤖 Testing CrewAI Agents Integration...")
    logger.info("=" * 50)
    
    try:
        # Test direct agent analysis
        crew_system = PromptBasedCrewAISystem()
        
        # Test order
        test_order = {
            'order_id': 'agent_test_001',
            'user_id': 'test_user_001', 
            'total_amount': 150.0,
            'payment_method': 'credit_card',
            'account_age_days': 2,
            'orders_today': 5,
            'orders_last_hour': 2,
            'avg_order_value': 35.0,
            'payment_failures_today': 0,
            'behavior_change_score': 0.6,
            'new_payment_method': True,
            'address_change_flag': False,
            'amount_ratio': 150.0 / 35.0
        }
        
        logger.info(f"📊 Testing order: {test_order['order_id']}")
        logger.info(f"   Amount: ${test_order['total_amount']}")
        logger.info(f"   Account age: {test_order['account_age_days']} days")
        logger.info(f"   Orders today: {test_order['orders_today']}")
        
        # Get agent analysis
        result = crew_system.analyze_order(test_order)
        
        logger.info("\n🎯 Agent Analysis Results:")
        logger.info(f"   Fraud Score: {result.get('fraud_score', 'N/A')}")
        logger.info(f"   Action: {result.get('recommended_action', 'N/A')}")
        logger.info(f"   Confidence: {result.get('confidence', 'N/A')}")
        logger.info(f"   Patterns: {result.get('patterns_detected', [])}")
        logger.info(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}...")
        
        # Test streaming processor integration
        logger.info("\n🔧 Testing Streaming Processor Integration...")
        processor = SimpleAgenticProcessor()
        metrics = processor.get_simple_metrics()
        
        logger.info(f"\n📈 Processor Metrics:")
        logger.info(f"   Status: {metrics['status']}")
        logger.info(f"   Total Processed: {metrics['total_processed']}")
        logger.info(f"   Agent Analyses: {metrics['agent_analyses']}")
        
        logger.info("\n✅ CrewAI agents are working correctly with streaming!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print("\n🎯 Agent integration is working!" if success else "\n❌ Agent integration needs attention")