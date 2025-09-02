
"""
Agentic PostgreSQL Writer for Fraud Detection Results and Agent Analysis
Handles both fraud detection results and CrewAI agent analysis outputs
"""

import logging
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

from config.settings import settings

logger = logging.getLogger(__name__)

class AgenticPostgreSQLWriter:
    """PostgreSQL writer for fraud detection and agent analysis results"""
    
    def __init__(self):
        self.connection_string = self._get_connection_string()
        self._setup_tables()
        
    def _get_connection_string(self) -> str:
        """Get PostgreSQL connection string from settings"""
        try:
            # Direct connection to fraud_detection database
            fraud_detection_conn = 'postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/fraud_detection'
            
            # Fallback to environment variable
            import os
            conn_str = os.getenv('POSTGRES_CONNECTION_STRING', fraud_detection_conn)
            
            return conn_str
            
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL connection string: {e}")
            raise
    
    def _setup_tables(self):
        """Create tables if they don't exist"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Read and execute the schema file
            schema_file = "/Users/mateusoliveira/Mateus/owshq/projects/pycharm/uberats-fraud-detection/database/agentic_fraud_schema.sql"
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            cursor.execute(schema_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("✅ Agentic fraud detection tables ready")
            
        except Exception as e:
            logger.error(f"❌ Error setting up tables: {e}")
            raise
    
    def write_fraud_results_batch(self, batch_df: DataFrame, batch_id: int):
        """Write fraud detection results to PostgreSQL"""
        try:
            # Convert Spark DataFrame to Python data
            batch_data = batch_df.collect()
            logger.info(f"🔍 DEBUG: Batch {batch_id} has {len(batch_data)} rows")
            
            if not batch_data:
                logger.info(f"Batch {batch_id}: No fraud results to write")
                return
            
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Prepare fraud detection results data
            fraud_records = []
            logger.info(f"🔍 DEBUG: Processing {len(batch_data)} rows for batch {batch_id}")
            for i, row in enumerate(batch_data):
                row_dict = row.asDict()
                logger.info(f"🔍 DEBUG: Row {i} keys: {list(row_dict.keys())}")
                logger.info(f"🔍 DEBUG: Row {i} data: order_id={row_dict.get('order_id')}, user_id={row_dict.get('user_id')}, total_amount={row_dict.get('total_amount')}")
                
                # Handle array fields (fraud_reasons)
                fraud_reasons = row_dict.get('fraud_reasons', [])
                if isinstance(fraud_reasons, list):
                    fraud_reasons_array = fraud_reasons
                else:
                    # Handle string representation of array
                    fraud_reasons_array = [str(fraud_reasons)] if fraud_reasons else []
                
                # Safe conversion functions
                def safe_float(val, default=0.0):
                    return float(val) if val is not None else default
                
                def safe_int(val, default=0):
                    return int(val) if val is not None else default
                
                def safe_str(val, default="unknown"):
                    return str(val) if val is not None else default
                
                fraud_record = (
                    row_dict.get('order_id'),
                    safe_str(row_dict.get('user_id')),
                    safe_float(row_dict.get('total_amount')),
                    safe_str(row_dict.get('payment_method')),
                    safe_int(row_dict.get('account_age_days')),
                    safe_int(row_dict.get('total_orders')),
                    safe_float(row_dict.get('avg_order_value')),
                    safe_float(row_dict.get('fraud_score')),
                    safe_str(row_dict.get('fraud_prediction'), 'UNKNOWN'),
                    safe_float(row_dict.get('confidence')),
                    fraud_reasons_array,
                    safe_float(row_dict.get('velocity_risk')),
                    safe_float(row_dict.get('amount_risk')),
                    safe_float(row_dict.get('account_risk')),
                    safe_float(row_dict.get('payment_risk')),
                    row_dict.get('triage_decision', 'AUTO_ALLOW'),
                    row_dict.get('priority_level'),
                    row_dict.get('requires_agent_analysis', False),
                    row_dict.get('processing_timestamp'),
                    row_dict.get('detection_timestamp'),
                    row_dict.get('routing_timestamp')
                )
                fraud_records.append(fraud_record)
            
            logger.info(f"🔍 DEBUG: Prepared {len(fraud_records)} fraud records for insertion")
            
            # Insert fraud detection results
            insert_fraud_sql = """
            INSERT INTO fraud_detection_results (
                order_id, user_id, total_amount, payment_method, account_age_days,
                total_orders, avg_order_value, fraud_score, fraud_prediction, confidence,
                fraud_reasons, velocity_risk, amount_risk, account_risk, payment_risk,
                triage_decision, priority_level, requires_agent_analysis,
                processing_timestamp, detection_timestamp, routing_timestamp
            ) VALUES %s
            ON CONFLICT (order_id) DO UPDATE SET
                fraud_score = EXCLUDED.fraud_score,
                fraud_prediction = EXCLUDED.fraud_prediction,
                triage_decision = EXCLUDED.triage_decision,
                requires_agent_analysis = EXCLUDED.requires_agent_analysis,
                detection_timestamp = EXCLUDED.detection_timestamp
            """
            
            execute_values(cursor, insert_fraud_sql, fraud_records)
            conn.commit()
            
            logger.info(f"✅ Batch {batch_id}: Inserted {len(fraud_records)} fraud detection results")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error writing fraud results batch {batch_id}: {e}")
    
    def write_agent_analysis_result(self, order_id: str, agent_result: Dict[str, Any]) -> bool:
        """Write single agent analysis result to PostgreSQL"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # First, get the fraud_result_id for this order
            cursor.execute(
                "SELECT id FROM fraud_detection_results WHERE order_id = %s",
                (order_id,)
            )
            fraud_result = cursor.fetchone()
            
            if not fraud_result:
                logger.warning(f"No fraud detection result found for order {order_id}")
                cursor.close()
                conn.close()
                return False
            
            fraud_result_id = fraud_result[0]
            
            # Extract agent analysis data
            agent_record = (
                order_id,
                fraud_result_id,
                float(agent_result.get('fraud_score', 0)) if agent_result.get('fraud_score') else None,
                agent_result.get('recommended_action'),
                float(agent_result.get('confidence', 0)) if agent_result.get('confidence') else None,
                agent_result.get('reasoning', '')[:1000],  # Truncate to 1000 chars
                agent_result.get('patterns_detected', []),
                agent_result.get('framework', 'crewai_with_prompts'),
                agent_result.get('prompt_version', '1.0'),
                int(agent_result.get('processing_time_ms', 0)),
                agent_result.get('success', True),
                agent_result.get('error'),
                ['fraud_analyst', 'risk_assessor', 'decision_maker', 'action_executor'],  # Default CrewAI agents
                4,  # 4 tasks completed (pattern, risk, decision, action)
                'sequential',  # CrewAI process type
                None,  # fraud_analyst_result - could be expanded later
                None,  # risk_assessor_result
                None,  # decision_maker_result  
                None   # action_executor_result
            )
            
            # Insert agent analysis result
            insert_agent_sql = """
            INSERT INTO agent_analysis_results (
                order_id, fraud_result_id, agent_fraud_score, agent_recommended_action,
                agent_confidence, agent_reasoning, patterns_detected, agent_framework,
                prompt_version, processing_time_ms, agent_success, agent_error,
                crew_agents_used, crew_tasks_completed, crew_process_type,
                fraud_analyst_result, risk_assessor_result, decision_maker_result, action_executor_result
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (order_id) DO UPDATE SET
                agent_fraud_score = EXCLUDED.agent_fraud_score,
                agent_recommended_action = EXCLUDED.agent_recommended_action,
                agent_confidence = EXCLUDED.agent_confidence,
                agent_reasoning = EXCLUDED.agent_reasoning,
                patterns_detected = EXCLUDED.patterns_detected,
                processing_time_ms = EXCLUDED.processing_time_ms,
                agent_success = EXCLUDED.agent_success,
                agent_analysis_timestamp = CURRENT_TIMESTAMP
            """
            
            cursor.execute(insert_agent_sql, agent_record)
            conn.commit()
            
            logger.info(f"✅ Agent analysis result saved for order {order_id}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error writing agent result for order {order_id}: {e}")
            return False
    
    def write_agent_analysis_batch(self, agent_results: List[Tuple[str, Dict[str, Any]]]) -> int:
        """Write batch of agent analysis results"""
        success_count = 0
        
        for order_id, agent_result in agent_results:
            if self.write_agent_analysis_result(order_id, agent_result):
                success_count += 1
        
        logger.info(f"✅ Batch agent analysis: {success_count}/{len(agent_results)} successfully written")
        return success_count
    
    def create_fraud_results_sink(self, fraud_df: DataFrame):
        """Create streaming sink for fraud detection results"""
        return fraud_df.writeStream \
            .outputMode("append") \
            .foreachBatch(self.write_fraud_results_batch) \
            .option("checkpointLocation", "/tmp/spark-streaming/fraud-results") \
            .trigger(processingTime="15 seconds") \
            .start()
    
    def get_fraud_detection_stats(self) -> Dict[str, Any]:
        """Get fraud detection statistics"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get daily summary
            cursor.execute("""
            SELECT * FROM daily_fraud_summary 
            WHERE detection_date = CURRENT_DATE
            """)
            daily_stats = cursor.fetchone()
            
            # Get agent performance
            cursor.execute("""
            SELECT * FROM agent_performance_metrics 
            WHERE analysis_date = CURRENT_DATE
            LIMIT 1
            """)
            agent_stats = cursor.fetchone()
            
            # Get high-risk alerts count
            cursor.execute("""
            SELECT COUNT(*) as high_risk_count 
            FROM high_risk_fraud_alerts
            WHERE DATE(fraud_detection_time) = CURRENT_DATE
            """)
            alerts_stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                "daily_summary": dict(daily_stats) if daily_stats else {},
                "agent_performance": dict(agent_stats) if agent_stats else {},
                "high_risk_alerts": dict(alerts_stats) if alerts_stats else {},
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting fraud detection stats: {e}")
            return {}
    
    def get_recent_high_risk_orders(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent high-risk orders requiring attention"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
            SELECT * FROM high_risk_fraud_alerts 
            ORDER BY priority_score DESC, fraud_detection_time DESC
            LIMIT %s
            """, (limit,))
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting high-risk orders: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            logger.info("✅ PostgreSQL connection test successful")
            return result[0] == 1
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection test failed: {e}")
            return False

# Global instance for easy access
agentic_postgres_writer = AgenticPostgreSQLWriter()