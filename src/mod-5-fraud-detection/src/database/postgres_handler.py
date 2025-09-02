"""
PostgreSQL database handler for fraud detection results
Optimized for high-throughput fraud result storage and analytics
"""

import asyncio
import logging
import json
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import ThreadedConnectionPool

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from src.models.fraud_result import FraudResult, FraudPattern, AgentAnalysis
from src.logging_config import setup_logging
from src.correlation import get_correlation_id

class PostgreSQLHandler:
    """High-performance PostgreSQL handler for fraud detection results"""
    
    def __init__(self, connection_string: str = None):
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string or settings.postgresql.connection_string
        self.table_name = settings.postgresql.table_name
        self.batch_size = settings.postgresql.batch_size
        self.pool = None
        self.stats = {
            'total_inserts': 0,
            'total_batches': 0,
            'failed_inserts': 0,
            'avg_batch_time_ms': 0.0
        }
        
    def initialize_connection_pool(self) -> bool:
        """Initialize PostgreSQL connection pool"""
        try:
            self.pool = ThreadedConnectionPool(
                minconn=2,
                maxconn=settings.postgresql.pool_size,
                dsn=self.connection_string
            )
            self.logger.info(f"PostgreSQL connection pool initialized with {settings.postgresql.pool_size} connections")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL connection pool: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test PostgreSQL database connection"""
        try:
            conn = self.pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.logger.info("PostgreSQL connection test successful")
                return result[0] == 1
        except Exception as e:
            self.logger.error(f"PostgreSQL connection test failed: {str(e)}")
            return False
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def create_schema(self) -> bool:
        """Create database schema from SQL file"""
        try:
            schema_file = "/Users/mateusoliveira/Mateus/owshq/projects/pycharm/uberats-fraud-detection/database/fraud_results_schema.sql"
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            conn = self.pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
                conn.commit()
                
            self.logger.info("Database schema created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create database schema: {str(e)}")
            return False
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def insert_fraud_result(self, fraud_result: FraudResult) -> bool:
        """Insert single fraud result into database"""
        correlation_id = get_correlation_id()
        start_time = datetime.now()
        
        try:
            conn = self.pool.getconn()
            
            with conn.cursor() as cursor:
                # Insert main fraud result
                insert_query = """
                INSERT INTO fraud_results (
                    order_id, user_id, correlation_id, fraud_score, 
                    recommended_action, action_confidence, primary_pattern, reasoning,
                    processing_time_ms, total_processing_time_ms,
                    model_version, system_health_score,
                    openai_tokens_used, estimated_cost_usd, processed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """
                
                cursor.execute(insert_query, (
                    fraud_result.order_id,
                    fraud_result.user_id,
                    correlation_id,
                    float(fraud_result.fraud_score),
                    fraud_result.recommended_action.value,
                    float(fraud_result.action_confidence),
                    fraud_result.primary_pattern.value if fraud_result.primary_pattern else None,
                    fraud_result.reasoning,
                    fraud_result.processing_time_ms,
                    fraud_result.total_processing_time_ms,
                    fraud_result.model_version,
                    float(fraud_result.system_health_score),
                    fraud_result.openai_tokens_used,
                    float(fraud_result.estimated_cost_usd),
                    fraud_result.timestamp
                ))
                
                fraud_result_id = cursor.fetchone()[0]
                
                # Insert fraud patterns
                if fraud_result.detected_patterns:
                    pattern_data = [
                        (
                            fraud_result_id,
                            pattern.pattern_type.value,
                            float(pattern.confidence),
                            pattern.severity.value,
                            pattern.description,
                            json.dumps(pattern.indicators)
                        )
                        for pattern in fraud_result.detected_patterns
                    ]
                    
                    execute_values(
                        cursor,
                        """INSERT INTO fraud_patterns 
                           (fraud_result_id, pattern_type, confidence, severity, description, indicators)
                           VALUES %s""",
                        pattern_data
                    )
                
                # Insert agent analyses
                if fraud_result.agent_analyses:
                    analysis_data = [
                        (
                            fraud_result_id,
                            analysis.agent_name,
                            analysis.analysis_type,
                            json.dumps(analysis.result),
                            float(analysis.confidence),
                            analysis.processing_time_ms
                        )
                        for analysis in fraud_result.agent_analyses
                    ]
                    
                    execute_values(
                        cursor,
                        """INSERT INTO fraud_agent_analyses
                           (fraud_result_id, agent_name, analysis_type, result, confidence, processing_time_ms)
                           VALUES %s""",
                        analysis_data
                    )
                
                conn.commit()
                
                # Update statistics
                self.stats['total_inserts'] += 1
                processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                self.logger.info(
                    f"Fraud result inserted successfully",
                    extra={
                        'correlation_id': correlation_id,
                        'order_id': fraud_result.order_id,
                        'fraud_result_id': fraud_result_id,
                        'db_processing_time_ms': processing_time_ms,
                        'fraud_score': fraud_result.fraud_score,
                        'recommended_action': fraud_result.recommended_action.value
                    }
                )
                
                return True
                
        except Exception as e:
            self.stats['failed_inserts'] += 1
            self.logger.error(
                f"Failed to insert fraud result: {str(e)}",
                extra={
                    'correlation_id': correlation_id,
                    'order_id': fraud_result.order_id,
                    'error_type': type(e).__name__
                }
            )
            return False
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def insert_fraud_results_batch(self, fraud_results: List[FraudResult]) -> Tuple[int, int]:
        """Insert batch of fraud results - optimized for high throughput"""
        correlation_id = get_correlation_id()
        start_time = datetime.now()
        successful_inserts = 0
        failed_inserts = 0
        
        if not fraud_results:
            return 0, 0
        
        try:
            conn = self.pool.getconn()
            
            with conn.cursor() as cursor:
                # Prepare batch data for main fraud results
                main_data = []
                patterns_data = []
                analyses_data = []
                
                for fraud_result in fraud_results:
                    main_data.append((
                        fraud_result.order_id,
                        fraud_result.user_id,
                        correlation_id,
                        float(fraud_result.fraud_score),
                        fraud_result.recommended_action.value,
                        float(fraud_result.action_confidence),
                        fraud_result.primary_pattern.value if fraud_result.primary_pattern else None,
                        fraud_result.reasoning,
                        fraud_result.processing_time_ms,
                        fraud_result.total_processing_time_ms,
                        fraud_result.model_version,
                        float(fraud_result.system_health_score),
                        fraud_result.openai_tokens_used,
                        float(fraud_result.estimated_cost_usd),
                        fraud_result.timestamp
                    ))
                
                # Batch insert main fraud results
                insert_query = """
                INSERT INTO fraud_results (
                    order_id, user_id, correlation_id, fraud_score, 
                    recommended_action, action_confidence, primary_pattern, reasoning,
                    processing_time_ms, total_processing_time_ms,
                    model_version, system_health_score,
                    openai_tokens_used, estimated_cost_usd, processed_at
                ) VALUES %s RETURNING id
                """
                
                execute_values(cursor, insert_query, main_data, fetch=True)
                fraud_result_ids = [row[0] for row in cursor.fetchall()]
                successful_inserts = len(fraud_result_ids)
                
                # Prepare related data with fraud_result_ids
                for i, fraud_result in enumerate(fraud_results):
                    if i >= len(fraud_result_ids):
                        break
                        
                    fraud_result_id = fraud_result_ids[i]
                    
                    # Add patterns
                    for pattern in fraud_result.detected_patterns:
                        patterns_data.append((
                            fraud_result_id,
                            pattern.pattern_type.value,
                            float(pattern.confidence),
                            pattern.severity.value,
                            pattern.description,
                            json.dumps(pattern.indicators)
                        ))
                    
                    # Add agent analyses
                    for analysis in fraud_result.agent_analyses:
                        analyses_data.append((
                            fraud_result_id,
                            analysis.agent_name,
                            analysis.analysis_type,
                            json.dumps(analysis.result),
                            float(analysis.confidence),
                            analysis.processing_time_ms
                        ))
                
                # Batch insert patterns
                if patterns_data:
                    execute_values(
                        cursor,
                        """INSERT INTO fraud_patterns 
                           (fraud_result_id, pattern_type, confidence, severity, description, indicators)
                           VALUES %s""",
                        patterns_data
                    )
                
                # Batch insert analyses
                if analyses_data:
                    execute_values(
                        cursor,
                        """INSERT INTO fraud_agent_analyses
                           (fraud_result_id, agent_name, analysis_type, result, confidence, processing_time_ms)
                           VALUES %s""",
                        analyses_data
                    )
                
                conn.commit()
                
                # Update statistics
                self.stats['total_inserts'] += successful_inserts
                self.stats['total_batches'] += 1
                batch_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self.stats['avg_batch_time_ms'] = (
                    (self.stats['avg_batch_time_ms'] * (self.stats['total_batches'] - 1) + batch_time_ms) 
                    / self.stats['total_batches']
                )
                
                self.logger.info(
                    f"Batch fraud results inserted successfully",
                    extra={
                        'correlation_id': correlation_id,
                        'batch_size': len(fraud_results),
                        'successful_inserts': successful_inserts,
                        'failed_inserts': failed_inserts,
                        'patterns_inserted': len(patterns_data),
                        'analyses_inserted': len(analyses_data),
                        'batch_processing_time_ms': batch_time_ms
                    }
                )
                
        except Exception as e:
            failed_inserts = len(fraud_results)
            self.stats['failed_inserts'] += failed_inserts
            self.logger.error(
                f"Failed to insert fraud results batch: {str(e)}",
                extra={
                    'correlation_id': correlation_id,
                    'batch_size': len(fraud_results),
                    'error_type': type(e).__name__
                }
            )
        finally:
            if conn:
                self.pool.putconn(conn)
        
        return successful_inserts, failed_inserts
    
    def update_daily_cost_tracking(self, tokens_used: int, cost_usd: float) -> None:
        """Update daily cost tracking"""
        try:
            conn = self.pool.getconn()
            
            with conn.cursor() as cursor:
                # Upsert daily cost tracking
                cursor.execute("""
                INSERT INTO cost_tracking (
                    date, total_requests, total_tokens_used, total_cost_usd, openai_api_calls
                ) VALUES (CURRENT_DATE, 1, %s, %s, 1)
                ON CONFLICT (date) DO UPDATE SET
                    total_requests = cost_tracking.total_requests + 1,
                    total_tokens_used = cost_tracking.total_tokens_used + EXCLUDED.total_tokens_used,
                    total_cost_usd = cost_tracking.total_cost_usd + EXCLUDED.total_cost_usd,
                    openai_api_calls = cost_tracking.openai_api_calls + 1,
                    average_tokens_per_request = (cost_tracking.total_tokens_used + EXCLUDED.total_tokens_used)::DECIMAL / (cost_tracking.total_requests + 1),
                    cost_per_request = (cost_tracking.total_cost_usd + EXCLUDED.total_cost_usd)::DECIMAL / (cost_tracking.total_requests + 1),
                    budget_utilization_pct = ((cost_tracking.total_cost_usd + EXCLUDED.total_cost_usd) / cost_tracking.daily_budget_usd) * 100,
                    updated_at = CURRENT_TIMESTAMP
                """, (tokens_used, cost_usd))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update daily cost tracking: {str(e)}")
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def get_daily_stats(self, target_date: date = None) -> Dict[str, Any]:
        """Get daily fraud detection statistics"""
        if not target_date:
            target_date = date.today()
        
        try:
            conn = self.pool.getconn()
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                SELECT * FROM daily_fraud_summary 
                WHERE detection_date = %s
                """, (target_date,))
                
                result = cursor.fetchone()
                return dict(result) if result else {}
                
        except Exception as e:
            self.logger.error(f"Failed to get daily stats: {str(e)}")
            return {}
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def get_high_risk_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get high-risk orders requiring attention"""
        try:
            conn = self.pool.getconn()
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                SELECT * FROM high_risk_orders 
                LIMIT %s
                """, (limit,))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to get high-risk orders: {str(e)}")
            return []
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def get_system_performance(self) -> Dict[str, Any]:
        """Get real-time system performance metrics"""
        try:
            conn = self.pool.getconn()
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM system_dashboard")
                result = cursor.fetchone()
                
                performance_data = dict(result) if result else {}
                performance_data.update(self.stats)
                
                return performance_data
                
        except Exception as e:
            self.logger.error(f"Failed to get system performance: {str(e)}")
            return self.stats
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old fraud detection data"""
        try:
            conn = self.pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                DELETE FROM fraud_results 
                WHERE created_at < CURRENT_DATE - INTERVAL '%s days'
                """, (days_to_keep,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Cleaned up {deleted_count} old fraud detection records")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {str(e)}")
            return 0
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def close_pool(self) -> None:
        """Close connection pool"""
        if self.pool:
            self.pool.closeall()
            self.logger.info("PostgreSQL connection pool closed")

# Global instance
postgres_handler = PostgreSQLHandler()