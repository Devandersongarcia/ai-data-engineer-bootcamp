#!/usr/bin/env python3
"""
Test Action Engine Integration with CrewAI Agents
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import logging
import asyncio
from datetime import datetime

from src.actions.action_engine import FraudActionEngine
from src.models.fraud_result import FraudResult, FraudDecision, FraudPatternType
from src.models.order import OrderData

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_action_engine_with_agents():
    """Test action engine with various agent recommendations"""
    
    logger.info("🚀 Testing Action Engine with Agent Recommendations")
    logger.info("=" * 60)
    
    # Initialize action engine
    action_engine = FraudActionEngine()
    
    # Test cases with different agent recommendations
    test_cases = [
        {
            "name": "High Risk - BLOCK",
            "recommendation": FraudDecision.BLOCK,
            "fraud_score": 0.95,
            "reasoning": "Multiple velocity fraud indicators detected by agents"
        },
        {
            "name": "Medium Risk - FLAG", 
            "recommendation": FraudDecision.FLAG,
            "fraud_score": 0.75,
            "reasoning": "Suspicious patterns requiring human review"
        },
        {
            "name": "Medium Risk - REQUIRE_HUMAN",
            "recommendation": FraudDecision.REQUIRE_HUMAN,
            "fraud_score": 0.70,
            "reasoning": "Agent detected anomalies requiring human judgment"
        },
        {
            "name": "Low Risk - MONITOR",
            "recommendation": FraudDecision.MONITOR,
            "fraud_score": 0.45,
            "reasoning": "Minor patterns detected, monitor user behavior"
        },
        {
            "name": "Legitimate - ALLOW",
            "recommendation": FraudDecision.ALLOW,
            "fraud_score": 0.15,
            "reasoning": "All agent checks passed, legitimate transaction"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        logger.info(f"\n🧪 Testing: {test_case['name']}")
        
        # Create test order
        order_data = OrderData(
            order_id=f"test_{test_case['name'].lower().replace(' ', '_').replace('-', '_')}",
            user_key=f"user_{test_case['name'][:4].lower()}",
            restaurant_key="test_restaurant",
            total_amount=100.0 if test_case['recommendation'] != FraudDecision.BLOCK else 500.0,
            item_count=2,
            driver_key="test_driver"
        )
        
        # Create fraud result with agent recommendation
        fraud_result = FraudResult(
            order_id=order_data.order_id,
            user_id=order_data.user_key,
            fraud_score=test_case['fraud_score'],
            recommended_action=test_case['recommendation'],
            action_confidence=0.85,
            reasoning=test_case['reasoning']
        )
        
        # Add pattern based on recommendation
        if test_case['recommendation'] == FraudDecision.BLOCK:
            fraud_result.primary_pattern = FraudPatternType.VELOCITY_FRAUD
        elif test_case['recommendation'] in [FraudDecision.FLAG, FraudDecision.REQUIRE_HUMAN]:
            fraud_result.primary_pattern = FraudPatternType.ACCOUNT_TAKEOVER
        
        try:
            # Execute action
            start_time = asyncio.get_event_loop().time()
            action_result = await action_engine.execute_fraud_action(fraud_result, order_data)
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Log result
            logger.info(f"   ✅ Action: {action_result.action_type.value}")
            logger.info(f"   📊 Status: {action_result.status.value}")
            logger.info(f"   ⏱️  Time: {execution_time:.2f}ms")
            logger.info(f"   💾 Details: {len(action_result.result_data) if action_result.result_data else 0} details")
            
            results.append({
                "test_case": test_case['name'],
                "recommendation": test_case['recommendation'].value,
                "action_result": action_result,
                "execution_time_ms": execution_time
            })
            
        except Exception as e:
            logger.error(f"   ❌ Failed: {e}")
            results.append({
                "test_case": test_case['name'],
                "recommendation": test_case['recommendation'].value,
                "error": str(e),
                "execution_time_ms": 0
            })
    
    # Summary
    logger.info(f"\n📈 ACTION ENGINE TEST SUMMARY:")
    logger.info("=" * 60)
    
    successful_tests = [r for r in results if 'error' not in r]
    failed_tests = [r for r in results if 'error' in r]
    
    logger.info(f"   📊 Tests Run: {len(results)}")
    logger.info(f"   ✅ Successful: {len(successful_tests)}")
    logger.info(f"   ❌ Failed: {len(failed_tests)}")
    
    if successful_tests:
        avg_time = sum(r['execution_time_ms'] for r in successful_tests) / len(successful_tests)
        logger.info(f"   ⚡ Avg Execution Time: {avg_time:.2f}ms")
    
    # Action statistics
    action_stats = action_engine.get_action_statistics()
    logger.info(f"\n📊 Action Engine Statistics:")
    logger.info(f"   Total Actions: {action_stats['total_actions']}")
    logger.info(f"   Success Rate: {action_stats['success_rate']:.1%}")
    logger.info(f"   Actions by Type: {action_stats['actions_by_type']}")
    logger.info(f"   Actions by Status: {action_stats['actions_by_status']}")
    
    # Test REQUIRE_HUMAN mapping
    logger.info(f"\n🔍 REQUIRE_HUMAN Mapping Test:")
    require_human_results = [r for r in successful_tests if r['recommendation'] == 'REQUIRE_HUMAN']
    if require_human_results:
        result = require_human_results[0]
        action_type = result['action_result'].action_type.value
        logger.info(f"   ✅ REQUIRE_HUMAN → {action_type} (should be flag_for_review)")
        success = action_type == "flag_for_review"
        logger.info(f"   {'✅' if success else '❌'} Mapping works correctly: {success}")
    else:
        logger.warning("   ⚠️ No REQUIRE_HUMAN test result found")
    
    return len(failed_tests) == 0

async def main():
    """Run action engine tests"""
    try:
        success = await test_action_engine_with_agents()
        return success
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\n{'✅ Action engine integration working correctly!' if success else '❌ Action engine integration needs fixes'}")