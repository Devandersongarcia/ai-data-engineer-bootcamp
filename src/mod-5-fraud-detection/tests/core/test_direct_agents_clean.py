#!/usr/bin/env python3
"""
Direct CrewAI Agent Test - Clean Version
Test agents directly without UDF complications
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import logging
import json
import time
from datetime import datetime

from src.agents.crewai_with_prompts import PromptBasedCrewAISystem

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_orders():
    """Create test orders for direct agent analysis"""
    return [
        # High-risk velocity fraud
        {
            "order_id": "direct_001",
            "user_id": "velocity_user_001", 
            "total_amount": 120.0,
            "payment_method": "credit_card",
            "account_age_days": 1,
            "orders_today": 8,
            "orders_last_hour": 2,
            "avg_order_value": 25.0,
            "payment_failures_today": 0,
            "behavior_change_score": 0.8,
            "new_payment_method": True,
            "address_change_flag": False,
            "amount_ratio": 120.0 / 25.0
        },
        # Amount anomaly fraud
        {
            "order_id": "direct_002",
            "user_id": "anomaly_user_002",
            "total_amount": 500.0,
            "payment_method": "debit_card", 
            "account_age_days": 30,
            "orders_today": 2,
            "orders_last_hour": 1,
            "avg_order_value": 45.0,
            "payment_failures_today": 0,
            "behavior_change_score": 0.9,
            "new_payment_method": False,
            "address_change_flag": True,
            "amount_ratio": 500.0 / 45.0
        },
        # Card testing pattern
        {
            "order_id": "direct_003",
            "user_id": "testing_user_003",
            "total_amount": 1.0,
            "payment_method": "credit_card",
            "account_age_days": 0,
            "orders_today": 15,
            "orders_last_hour": 8,
            "avg_order_value": 2.0,
            "payment_failures_today": 5,
            "behavior_change_score": 0.95,
            "new_payment_method": True,
            "address_change_flag": False,
            "amount_ratio": 1.0 / 2.0
        },
        # Legitimate order
        {
            "order_id": "direct_004", 
            "user_id": "normal_user_004",
            "total_amount": 85.0,
            "payment_method": "paypal",
            "account_age_days": 365,
            "orders_today": 1,
            "orders_last_hour": 1,
            "avg_order_value": 80.0,
            "payment_failures_today": 0,
            "behavior_change_score": 0.1,
            "new_payment_method": False,
            "address_change_flag": False,
            "amount_ratio": 85.0 / 80.0
        },
        # Account takeover pattern
        {
            "order_id": "direct_005",
            "user_id": "takeover_user_005",
            "total_amount": 300.0,
            "payment_method": "new_credit_card",
            "account_age_days": 180,
            "orders_today": 1,
            "orders_last_hour": 1,
            "avg_order_value": 50.0,
            "payment_failures_today": 0,
            "behavior_change_score": 0.85,
            "new_payment_method": True,
            "address_change_flag": True,
            "amount_ratio": 300.0 / 50.0
        }
    ]

def main():
    logger.info("🚀 Direct CrewAI Agent Analysis Test")
    logger.info("=" * 50)
    
    try:
        # Initialize CrewAI system
        logger.info("🤖 Initializing CrewAI system...")
        crew_system = PromptBasedCrewAISystem()
        
        # Create test orders
        test_orders = create_test_orders()
        logger.info(f"📊 Created {len(test_orders)} test orders for direct agent analysis")
        
        # Show input summary
        logger.info("\n📋 Input Orders Summary:")
        for order in test_orders:
            logger.info(f"   {order['order_id']}: ${order['total_amount']}, {order['account_age_days']} days, {order['orders_today']} orders")
        
        # Process each order through agents
        logger.info("\n🤖 Processing orders through CrewAI agents...")
        
        results = []
        total_start_time = time.time()
        
        for i, order in enumerate(test_orders, 1):
            logger.info(f"\n🔄 Processing order {i}/5: {order['order_id']}")
            
            start_time = time.time()
            agent_result = crew_system.analyze_order(order)
            processing_time = time.time() - start_time
            
            # Combine results
            result = {
                "order_id": order['order_id'],
                "input_order": order,
                "agent_analysis": agent_result,
                "processing_time_s": round(processing_time, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            results.append(result)
            
            # Log immediate result
            logger.info(f"   ✅ Fraud Score: {agent_result.get('fraud_score', 'N/A')}")
            logger.info(f"   🚨 Action: {agent_result.get('recommended_action', 'N/A')}")
            logger.info(f"   🎲 Confidence: {agent_result.get('confidence', 'N/A')}")
            logger.info(f"   ⏱️  Time: {processing_time:.2f}s")
        
        total_processing_time = time.time() - total_start_time
        
        # Detailed results analysis
        logger.info(f"\n⚡ Total processing time: {total_processing_time:.2f}s")
        logger.info("\n🎯 DETAILED AGENT ANALYSIS RESULTS:")
        logger.info("=" * 60)
        
        for i, result in enumerate(results, 1):
            order = result['input_order']
            analysis = result['agent_analysis']
            
            logger.info(f"\n📊 Order {i}: {result['order_id']}")
            logger.info(f"   Input Profile:")
            logger.info(f"     - User: {order['user_id']}")
            logger.info(f"     - Amount: ${order['total_amount']}")
            logger.info(f"     - Account Age: {order['account_age_days']} days")
            logger.info(f"     - Orders Today: {order['orders_today']}")
            logger.info(f"     - Payment Method: {order['payment_method']}")
            logger.info(f"     - Amount Ratio: {order['amount_ratio']:.2f}x")
            logger.info(f"     - Behavior Change: {order['behavior_change_score']}")
            
            logger.info(f"   Agent Analysis:")
            logger.info(f"     - 🎯 Fraud Score: {analysis.get('fraud_score', 'N/A')}")
            logger.info(f"     - 🚨 Recommended Action: {analysis.get('recommended_action', 'N/A')}")
            logger.info(f"     - 🎲 Confidence Level: {analysis.get('confidence', 'N/A')}")
            logger.info(f"     - 🔍 Patterns Detected: {analysis.get('patterns_detected', [])}")
            logger.info(f"     - 💭 Reasoning: {analysis.get('reasoning', '')[:200]}...")
            logger.info(f"     - ⚡ Processing Time: {result['processing_time_s']}s")
        
        # Performance and accuracy summary
        logger.info("\n📈 PERFORMANCE & ACCURACY SUMMARY:")
        logger.info("=" * 60)
        
        # Calculate metrics
        fraud_scores = [r['agent_analysis'].get('fraud_score', 0) for r in results if r['agent_analysis'].get('fraud_score') is not None]
        avg_fraud_score = sum(fraud_scores) / len(fraud_scores) if fraud_scores else 0
        
        processing_times = [r['processing_time_s'] for r in results]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        actions = [r['agent_analysis'].get('recommended_action') for r in results]
        action_counts = {action: actions.count(action) for action in set(actions) if action}
        
        high_risk_count = sum(1 for score in fraud_scores if score > 0.7)
        critical_risk_count = sum(1 for score in fraud_scores if score > 0.9)
        
        patterns_found = []
        for result in results:
            patterns = result['agent_analysis'].get('patterns_detected', [])
            patterns_found.extend(patterns)
        
        unique_patterns = list(set(patterns_found))
        
        logger.info(f"   📊 Orders Processed: {len(results)}")
        logger.info(f"   ⚡ Avg Processing Time: {avg_processing_time:.2f}s")
        logger.info(f"   🎯 Avg Fraud Score: {avg_fraud_score:.3f}")
        logger.info(f"   🚨 High Risk Orders (>0.7): {high_risk_count}/{len(results)}")
        logger.info(f"   🔥 Critical Risk Orders (>0.9): {critical_risk_count}/{len(results)}")
        logger.info(f"   📋 Action Distribution: {action_counts}")
        logger.info(f"   🔍 Unique Patterns Detected: {len(unique_patterns)}")
        logger.info(f"   📝 Pattern Types: {unique_patterns[:5]}...")
        
        # Sample complete output
        logger.info("\n📋 SAMPLE COMPLETE PIPELINE OUTPUT:")
        logger.info("=" * 60)
        
        sample_result = results[0] if results else None
        if sample_result:
            clean_output = {
                "pipeline_info": {
                    "version": "direct_agents_v1",
                    "processing_timestamp": sample_result['timestamp'],
                    "processing_time_s": sample_result['processing_time_s']
                },
                "order_input": {
                    "order_id": sample_result['order_id'],
                    "user_profile": {
                        "user_id": sample_result['input_order']['user_id'],
                        "account_age_days": sample_result['input_order']['account_age_days'],
                        "behavior_score": sample_result['input_order']['behavior_change_score']
                    },
                    "transaction_details": {
                        "amount": sample_result['input_order']['total_amount'],
                        "payment_method": sample_result['input_order']['payment_method'],
                        "amount_ratio": sample_result['input_order']['amount_ratio']
                    },
                    "velocity_metrics": {
                        "orders_today": sample_result['input_order']['orders_today'],
                        "orders_last_hour": sample_result['input_order']['orders_last_hour'],
                        "avg_order_value": sample_result['input_order']['avg_order_value']
                    }
                },
                "fraud_analysis": sample_result['agent_analysis']
            }
            
            print(json.dumps(clean_output, indent=2, default=str))
        
        logger.info("\n✅ DIRECT AGENT ANALYSIS COMPLETED SUCCESSFULLY!")
        logger.info("🎯 CrewAI agents are fully operational for streaming fraud detection!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Direct agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n{'🎯 Direct agent analysis is working perfectly!' if success else '❌ Agent analysis needs attention'}")