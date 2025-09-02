#!/usr/bin/env python3
"""
Process Agent Analysis Backlog
Process existing high-risk orders that require agent analysis
"""

import sys
import logging
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_agent_backlog():
    """Process existing orders that require agent analysis"""
    
    try:
        from src.agents.crewai_with_prompts import PromptBasedCrewAISystem
        from src.database.unified_postgres_writer import unified_postgres_writer
        
        # Initialize CrewAI system
        logger.info("🤖 Initializing CrewAI Agent System for backlog processing...")
        crew_system = PromptBasedCrewAISystem()
        
        # Connect to database
        conn = psycopg2.connect('postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/fraud_detection')
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get unprocessed high-risk orders (limit to 10 for testing)
        logger.info("🔍 Finding orders requiring agent analysis...")
        cursor.execute("""
            SELECT f.order_id, f.user_id, f.total_amount, f.payment_method, 
                   f.account_age_days, f.total_orders, f.avg_order_value,
                   f.fraud_score, f.fraud_prediction, f.priority_level
            FROM fraud_detection_results f
            LEFT JOIN agent_analysis_results a ON f.order_id = a.order_id
            WHERE f.requires_agent_analysis = true 
            AND f.triage_decision = 'AGENT_ANALYSIS'
            AND a.id IS NULL  -- Not yet processed by agents
            ORDER BY f.fraud_score DESC, f.created_at DESC
            LIMIT 10
        """)
        
        unprocessed_orders = cursor.fetchall()
        logger.info(f"📋 Found {len(unprocessed_orders)} orders requiring agent analysis")
        
        if not unprocessed_orders:
            logger.info("✅ No orders require agent analysis")
            cursor.close()
            conn.close()
            return
        
        # Process each order with agents
        processed_count = 0
        for order in unprocessed_orders:
            try:
                logger.info(f"🎯 Processing order: {order['order_id']} (fraud_score: {order['fraud_score']:.3f})")
                
                # Prepare order data for agent analysis
                order_data = {
                    "order_id": order['order_id'],
                    "user_id": order['user_id'] or "unknown",
                    "total_amount": float(order['total_amount']) if order['total_amount'] else 0.0,
                    "payment_method": order['payment_method'] or "unknown",
                    "account_age_days": int(order['account_age_days']) if order['account_age_days'] else 30,
                    "orders_today": int(order['total_orders']) if order['total_orders'] else 1,
                    "orders_last_hour": max(1, int(order['total_orders'] or 1) // 4),
                    "avg_order_value": float(order['avg_order_value']) if order['avg_order_value'] else 35.0,
                    "payment_failures_today": 0 if order['fraud_score'] < 0.5 else 2,
                    "behavior_change_score": min(float(order['fraud_score']), 0.8),
                    "new_payment_method": int(order['account_age_days'] or 30) <= 7,
                    "address_change_flag": False
                }
                
                # Run agent analysis
                start_time = datetime.now()
                agent_result = crew_system.analyze_order(order_data)
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Prepare result for database
                agent_result_dict = {
                    "fraud_score": agent_result.get("fraud_score", order['fraud_score']),
                    "recommended_action": agent_result.get("recommended_action", "MONITOR"),
                    "confidence": agent_result.get("confidence", 0.6),
                    "patterns_detected": agent_result.get("patterns_detected", []),
                    "reasoning": agent_result.get("reasoning", "")[:1000],  # Truncate for database
                    "processing_time_ms": processing_time,
                    "framework": agent_result.get("framework", "crewai_with_prompts"),
                    "success": True
                }
                
                # Save to database
                success = unified_postgres_writer.write_agent_analysis_result(order['order_id'], agent_result_dict)
                
                if success:
                    processed_count += 1
                    logger.info(f"✅ Order {order['order_id']}: {agent_result_dict['recommended_action']} "
                              f"(confidence: {agent_result_dict['confidence']:.2f}, time: {processing_time}ms)")
                else:
                    logger.error(f"❌ Failed to save agent result for order {order['order_id']}")
                
            except Exception as e:
                logger.error(f"❌ Error processing order {order['order_id']}: {e}")
        
        cursor.close()
        conn.close()
        
        logger.info(f"🎉 Backlog processing completed: {processed_count}/{len(unprocessed_orders)} orders processed")
        
    except Exception as e:
        logger.error(f"❌ Error in backlog processing: {e}")

if __name__ == "__main__":
    process_agent_backlog()