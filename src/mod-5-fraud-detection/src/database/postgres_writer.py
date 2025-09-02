"""
PostgreSQL writer for fraud detection results
High-performance writer for streaming fraud results to PostgreSQL database
"""

import logging
import json
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from psycopg2 import sql
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time
import uuid
from threading import Lock

logger = logging.getLogger(__name__)

class PostgreSQLFraudWriter:
    """High-performance PostgreSQL writer for fraud detection results"""
    
    def __init__(self, connection_string: str, table_name: str = "fraud_results"):
        self.connection_string = connection_string
        self.table_name = table_name
        self.connection_pool = []
        self.pool_size = 5
        self.pool_lock = Lock()
        
        # Performance tracking
        self.write_count = 0
        self.total_write_time = 0.0
        self.batch_size = 100
        self.batch_buffer = []
        self.buffer_lock = Lock()
        
        # Initialize database
        self._initialize_database()
        self._initialize_connection_pool()
        
        logger.info(f"PostgreSQLFraudWriter initialized for table: {self.table_name}")
    
    def _initialize_database(self):
        """Initialize database schema"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create fraud results table with optimized schema
                    create_table_query = f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        order_id VARCHAR(100) NOT NULL,
                        user_key VARCHAR(100),
                        fraud_score DECIMAL(5,4) NOT NULL,
                        decision VARCHAR(20) NOT NULL,
                        reasoning TEXT,
                        detected_patterns JSONB,
                        risk_indicators JSONB,
                        processing_mode VARCHAR(20),
                        confidence DECIMAL(5,4),
                        escalation_level VARCHAR(20),
                        requires_manual_review BOOLEAN,
                        processing_time_ms INTEGER,
                        
                        -- Order details
                        total_amount DECIMAL(10,2),
                        account_age_days INTEGER,
                        orders_today INTEGER,
                        payment_method VARCHAR(50),
                        restaurant_key VARCHAR(100),
                        item_count INTEGER,
                        
                        -- System metadata
                        system_status VARCHAR(20),
                        agent_timeout BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Indexes for performance
                        CONSTRAINT fraud_results_decision_check CHECK (decision IN ('MONITOR', 'BLOCK', 'REQUIRE_HUMAN', 'ALLOW', 'FLAG'))
                    );
                    
                    """
                    
                    cursor.execute(create_table_query)
                    conn.commit()
                    
                    # Create performance indexes (separate transactions for compatibility)
                    indexes = [
                        f"CREATE INDEX IF NOT EXISTS idx_fraud_results_order_id ON {self.table_name} (order_id)",
                        f"CREATE INDEX IF NOT EXISTS idx_fraud_results_decision ON {self.table_name} (decision)",
                        f"CREATE INDEX IF NOT EXISTS idx_fraud_results_fraud_score ON {self.table_name} (fraud_score DESC)",
                        f"CREATE INDEX IF NOT EXISTS idx_fraud_results_created_at ON {self.table_name} (created_at DESC)",
                        f"CREATE INDEX IF NOT EXISTS idx_fraud_results_user_key ON {self.table_name} (user_key)",
                        f"CREATE INDEX IF NOT EXISTS idx_fraud_results_patterns_gin ON {self.table_name} USING GIN (detected_patterns)",
                        f"CREATE INDEX IF NOT EXISTS idx_fraud_results_indicators_gin ON {self.table_name} USING GIN (risk_indicators)"
                    ]
                    
                    for index_sql in indexes:
                        try:
                            cursor.execute(index_sql)
                            conn.commit()
                        except Exception as e:
                            logger.warning(f"Index creation warning (may already exist): {e}")
                            conn.rollback()  # Rollback and continue
                    
                    logger.info(f"✅ Database schema and indexes initialized for table: {self.table_name}")
                    
        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}")
            raise
    
    def _initialize_connection_pool(self):
        """Initialize connection pool for better performance"""
        try:
            with self.pool_lock:
                for _ in range(self.pool_size):
                    conn = psycopg2.connect(
                        self.connection_string,
                        cursor_factory=RealDictCursor
                    )
                    conn.autocommit = True
                    self.connection_pool.append(conn)
            
            logger.info(f"✅ Connection pool initialized with {self.pool_size} connections")
            
        except Exception as e:
            logger.error(f"❌ Error initializing connection pool: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """Get connection from pool"""
        conn = None
        try:
            with self.pool_lock:
                if self.connection_pool:
                    conn = self.connection_pool.pop()
                else:
                    # Create new connection if pool is empty
                    conn = psycopg2.connect(
                        self.connection_string,
                        cursor_factory=RealDictCursor
                    )
                    conn.autocommit = True
            
            yield conn
            
        finally:
            if conn:
                try:
                    # Return connection to pool if healthy
                    if conn.closed == 0:
                        with self.pool_lock:
                            if len(self.connection_pool) < self.pool_size:
                                self.connection_pool.append(conn)
                            else:
                                conn.close()
                    else:
                        conn.close()
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
    
    def write_fraud_result(self, result_data: Dict[str, Any]) -> bool:
        """Write single fraud result to PostgreSQL"""
        return self.write_fraud_results([result_data])
    
    def write_fraud_results(self, results: List[Dict[str, Any]]) -> bool:
        """Write multiple fraud results to PostgreSQL efficiently"""
        if not results:
            return True
        
        start_time = time.time()
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Prepare batch insert
                    insert_query = f"""
                    INSERT INTO {self.table_name} (
                        order_id, user_key, fraud_score, decision, reasoning,
                        detected_patterns, risk_indicators, processing_mode,
                        confidence, escalation_level, requires_manual_review,
                        processing_time_ms, total_amount, account_age_days,
                        orders_today, payment_method, restaurant_key, item_count,
                        system_status, agent_timeout, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    """
                    
                    # Prepare data tuples
                    data_tuples = []
                    for result in results:
                        data_tuple = (
                            result.get('order_id', ''),
                            result.get('user_key', ''),
                            float(result.get('fraud_score', 0.0)),
                            result.get('decision', 'MONITOR'),
                            result.get('reasoning', ''),
                            json.dumps(result.get('detected_patterns', [])),
                            json.dumps(result.get('risk_indicators', [])),
                            result.get('processing_mode', 'unknown'),
                            float(result.get('confidence', 0.0)),
                            result.get('escalation_level', 'none'),
                            bool(result.get('requires_manual_review', False)),
                            int(result.get('processing_time_ms', 0)),
                            float(result.get('total_amount', 0.0)),
                            int(result.get('account_age_days', 0)),
                            int(result.get('orders_today', 0)),
                            result.get('payment_method', ''),
                            result.get('restaurant_key', ''),
                            int(result.get('item_count', 0)),
                            result.get('system_status', 'unknown'),
                            bool(result.get('agent_timeout', False)),
                            datetime.now(timezone.utc)
                        )
                        data_tuples.append(data_tuple)
                    
                    # Execute batch insert
                    execute_batch(cursor, insert_query, data_tuples, page_size=100)
                    
                    # Update performance metrics
                    processing_time = time.time() - start_time
                    self.write_count += len(results)
                    self.total_write_time += processing_time
                    
                    logger.info(f"✅ Wrote {len(results)} fraud results to PostgreSQL in {processing_time:.3f}s")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error writing fraud results to PostgreSQL: {e}")
            return False
    
    def add_to_batch(self, result_data: Dict[str, Any]) -> bool:
        """Add result to batch buffer for efficient writing"""
        with self.buffer_lock:
            self.batch_buffer.append(result_data)
            
            # Write batch when buffer is full
            if len(self.batch_buffer) >= self.batch_size:
                batch_to_write = self.batch_buffer.copy()
                self.batch_buffer.clear()
                
                # Write batch asynchronously
                return self.write_fraud_results(batch_to_write)
        
        return True
    
    def flush_batch(self) -> bool:
        """Flush remaining items in batch buffer"""
        with self.buffer_lock:
            if self.batch_buffer:
                batch_to_write = self.batch_buffer.copy()
                self.batch_buffer.clear()
                return self.write_fraud_results(batch_to_write)
        return True
    
    def get_recent_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent fraud results for monitoring"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                    SELECT 
                        order_id, user_key, fraud_score, decision, reasoning,
                        detected_patterns, risk_indicators, processing_mode,
                        confidence, escalation_level, requires_manual_review,
                        processing_time_ms, total_amount, created_at,
                        system_status, agent_timeout
                    FROM {self.table_name}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """
                    
                    cursor.execute(query, (limit,))
                    results = cursor.fetchall()
                    
                    return [dict(row) for row in results]
                    
        except Exception as e:
            logger.error(f"Error getting recent results: {e}")
            return []
    
    def get_fraud_statistics(self) -> Dict[str, Any]:
        """Get fraud detection statistics"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get basic statistics
                    stats_query = f"""
                    SELECT 
                        COUNT(*) as total_orders,
                        AVG(fraud_score) as avg_fraud_score,
                        COUNT(CASE WHEN decision = 'BLOCK' THEN 1 END) as blocked_orders,
                        COUNT(CASE WHEN decision = 'REVIEW' THEN 1 END) as review_orders,
                        COUNT(CASE WHEN decision = 'MONITOR' THEN 1 END) as monitor_orders,
                        COUNT(CASE WHEN decision = 'ALLOW' THEN 1 END) as allowed_orders,
                        COUNT(CASE WHEN agent_timeout = true THEN 1 END) as timeout_orders,
                        AVG(processing_time_ms) as avg_processing_time_ms
                    FROM {self.table_name}
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
                    """
                    
                    cursor.execute(stats_query)
                    stats = cursor.fetchone()
                    
                    # Calculate rates
                    total_orders = stats['total_orders'] or 0
                    if total_orders > 0:
                        fraud_rate = (stats['blocked_orders'] + stats['review_orders']) / total_orders
                        timeout_rate = stats['timeout_orders'] / total_orders
                    else:
                        fraud_rate = 0.0
                        timeout_rate = 0.0
                    
                    return {
                        "total_orders_24h": total_orders,
                        "avg_fraud_score": float(stats['avg_fraud_score'] or 0),
                        "blocked_orders": stats['blocked_orders'] or 0,
                        "review_orders": stats['review_orders'] or 0,
                        "monitor_orders": stats['monitor_orders'] or 0,
                        "allowed_orders": stats['allowed_orders'] or 0,
                        "fraud_detection_rate": fraud_rate,
                        "timeout_orders": stats['timeout_orders'] or 0,
                        "timeout_rate": timeout_rate,
                        "avg_processing_time_ms": float(stats['avg_processing_time_ms'] or 0),
                        "writer_performance": {
                            "total_writes": self.write_count,
                            "avg_write_time_ms": (self.total_write_time / self.write_count * 1000) if self.write_count > 0 else 0,
                            "batch_buffer_size": len(self.batch_buffer)
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Error getting fraud statistics: {e}")
            return {"error": str(e)}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and performance"""
        try:
            start_time = time.time()
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    
                    # Test table access
                    cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                    count = cursor.fetchone()['count']
                    
            connection_time = time.time() - start_time
            
            return {
                "connection_status": "healthy",
                "connection_time_ms": int(connection_time * 1000),
                "table_accessible": True,
                "total_records": count,
                "pool_size": len(self.connection_pool),
                "batch_buffer_size": len(self.batch_buffer)
            }
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return {
                "connection_status": "failed",
                "error": str(e),
                "table_accessible": False
            }
    
    def close(self):
        """Close all connections in pool"""
        try:
            # Flush any remaining batch items
            self.flush_batch()
            
            # Close all connections
            with self.pool_lock:
                for conn in self.connection_pool:
                    try:
                        conn.close()
                    except Exception as e:
                        logger.error(f"Error closing connection: {e}")
                self.connection_pool.clear()
            
            logger.info("PostgreSQL writer closed")
            
        except Exception as e:
            logger.error(f"Error closing PostgreSQL writer: {e}")

# Global instance
postgres_writer = None

def get_postgres_writer(connection_string: str = None) -> PostgreSQLFraudWriter:
    """Get global PostgreSQL writer instance"""
    global postgres_writer
    
    if postgres_writer is None and connection_string:
        postgres_writer = PostgreSQLFraudWriter(connection_string)
    
    return postgres_writer

def initialize_postgres_writer(connection_string: str) -> PostgreSQLFraudWriter:
    """Initialize PostgreSQL writer with connection string"""
    global postgres_writer
    postgres_writer = PostgreSQLFraudWriter(connection_string)
    return postgres_writer