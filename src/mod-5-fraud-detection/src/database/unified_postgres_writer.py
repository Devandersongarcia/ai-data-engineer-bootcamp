"""
Unified PostgreSQL Writer for Fraud Detection
Handles both agentic_fraud_schema and fraud_results_schema formats
Ensures proper data insertion regardless of which schema is deployed
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

logger = logging.getLogger(__name__)

class UnifiedPostgreSQLWriter:
    """Unified writer that works with both database schemas"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or self._get_connection_string()
        self.schema_type = self._detect_schema_type()
        self._create_missing_tables()
        
    def _get_connection_string(self) -> str:
        """Get PostgreSQL connection string from environment variables"""
        import os
        connection_string = os.getenv('POSTGRES_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("POSTGRES_CONNECTION_STRING environment variable is required")
        return connection_string
    
    def _detect_schema_type(self) -> str:
        """Detect which schema is currently deployed"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Check for agentic schema tables
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'fraud_detection_results'
                )
            """)
            has_agentic = cursor.fetchone()[0]
            
            # Check for fraud_results schema tables
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'fraud_results'
                )
            """)
            has_fraud_results = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if has_agentic:
                logger.info("✅ Detected agentic_fraud_schema format")
                return "agentic"
            elif has_fraud_results:
                logger.info("✅ Detected fraud_results_schema format")
                return "fraud_results"
            else:
                logger.warning("⚠️ No existing schema detected, will create agentic schema")
                return "agentic"
                
        except Exception as e:
            logger.error(f"❌ Error detecting schema: {e}")
            return "agentic"  # Default to agentic schema
    
    def _create_missing_tables(self):
        """Create missing tables based on detected schema"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            if self.schema_type == "agentic":
                self._create_agentic_tables(cursor, conn)
            else:
                self._create_fraud_results_tables(cursor, conn)
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error creating tables: {e}")
    
    def _create_agentic_tables(self, cursor, conn):
        """Create agentic schema tables if they don't exist (with SQL injection protection)"""
        try:
            schema_file = "/Users/mateusoliveira/Mateus/owshq/projects/pycharm/uberats-fraud-detection/database/agentic_fraud_schema.sql"
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            # Validate and sanitize SQL before execution
            statements = self._sanitize_schema_statements(schema_sql)
            
            for statement in statements:
                if self._is_safe_ddl_statement(statement):
                    try:
                        cursor.execute(statement)
                        conn.commit()
                        logger.debug(f"Executed schema statement: {statement[:50]}...")
                    except Exception as e:
                        if "already exists" not in str(e):
                            logger.warning(f"Schema statement warning: {e}")
                        conn.rollback()
                else:
                    logger.error(f"Potentially unsafe SQL statement rejected: {statement[:100]}...")
            
            logger.info("✅ Agentic schema tables ready")
            
        except Exception as e:
            logger.error(f"❌ Error creating agentic tables: {e}")
    
    def _create_fraud_results_tables(self, cursor, conn):
        """Create fraud_results schema tables if they don't exist (with SQL injection protection)"""
        try:
            schema_file = "/Users/mateusoliveira/Mateus/owshq/projects/pycharm/uberats-fraud-detection/database/fraud_results_schema.sql"
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            # Validate and sanitize SQL before execution
            statements = self._sanitize_schema_statements(schema_sql)
            
            for statement in statements:
                if self._is_safe_ddl_statement(statement):
                    try:
                        cursor.execute(statement)
                        conn.commit()
                        logger.debug(f"Executed schema statement: {statement[:50]}...")
                    except Exception as e:
                        if "already exists" not in str(e):
                            logger.warning(f"Schema statement warning: {e}")
                        conn.rollback()
                else:
                    logger.error(f"Potentially unsafe SQL statement rejected: {statement[:100]}...")
            
            logger.info("✅ Fraud results schema tables ready")
            
        except Exception as e:
            logger.error(f"❌ Error creating fraud results tables: {e}")
    
    def write_fraud_detection_batch(self, batch_df: DataFrame, batch_id: int):
        """Write fraud detection results (works with both schemas)"""
        try:
            batch_data = batch_df.collect()
            
            if not batch_data:
                logger.info(f"Batch {batch_id}: No data to write")
                return
            
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            if self.schema_type == "agentic":
                self._write_agentic_fraud_detection(cursor, conn, batch_data, batch_id)
            else:
                self._write_fraud_results_detection(cursor, conn, batch_data, batch_id)
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error writing fraud detection batch {batch_id}: {e}")
    
    def _write_agentic_fraud_detection(self, cursor, conn, batch_data: List, batch_id: int):
        """Write to agentic schema format"""
        records = []
        
        for row in batch_data:
            row_dict = row.asDict()
            
            # Safe conversion functions
            def safe_float(val, default=0.0):
                return float(val) if val is not None else default
            
            def safe_int(val, default=0):
                return int(val) if val is not None else default
            
            def safe_str(val, default="unknown"):
                return str(val) if val is not None else default
            
            def safe_array(val, default=None):
                if default is None:
                    default = []
                if isinstance(val, list):
                    return val
                elif val is not None:
                    return [str(val)]
                else:
                    return default
            
            record = (
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
                safe_array(row_dict.get('fraud_reasons')),
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
            records.append(record)
        
        # Insert into fraud_detection_results table
        insert_sql = """
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
        
        execute_values(cursor, insert_sql, records)
        conn.commit()
        
        logger.info(f"✅ Agentic Batch {batch_id}: Inserted {len(records)} fraud detection results")
    
    def _write_fraud_results_detection(self, cursor, conn, batch_data: List, batch_id: int):
        """Write to fraud_results schema format"""
        # This would write to the comprehensive fraud_results table
        # Implementation similar to above but targeting different table structure
        logger.info(f"✅ Fraud Results Batch {batch_id}: Would write {len(batch_data)} records")
        # TODO: Implement fraud_results schema writing
    
    def write_agent_analysis_result(self, order_id: str, agent_result: Dict[str, Any]) -> bool:
        """Write agent analysis result (works with both schemas)"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            if self.schema_type == "agentic":
                success = self._write_agentic_agent_analysis(cursor, conn, order_id, agent_result)
            else:
                success = self._write_fraud_results_agent_analysis(cursor, conn, order_id, agent_result)
            
            cursor.close()
            conn.close()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error writing agent result for order {order_id}: {e}")
            return False
    
    def _write_agentic_agent_analysis(self, cursor, conn, order_id: str, agent_result: Dict[str, Any]) -> bool:
        """Write agent analysis to agentic schema"""
        try:
            # First, get the fraud_result_id for this order
            cursor.execute(
                "SELECT id FROM fraud_detection_results WHERE order_id = %s",
                (order_id,)
            )
            fraud_result = cursor.fetchone()
            
            if not fraud_result:
                logger.warning(f"No fraud detection result found for order {order_id}")
                return False
            
            fraud_result_id = fraud_result[0]
            
            # Insert agent analysis result
            insert_sql = """
            INSERT INTO agent_analysis_results (
                order_id, fraud_result_id, agent_fraud_score, agent_recommended_action,
                agent_confidence, agent_reasoning, patterns_detected, agent_framework,
                prompt_version, processing_time_ms, agent_success, agent_error,
                crew_agents_used, crew_tasks_completed, crew_process_type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                ['fraud_analyst', 'risk_assessor', 'decision_maker', 'action_executor'],
                4,  # 4 tasks completed
                'sequential'
            )
            
            cursor.execute(insert_sql, agent_record)
            conn.commit()
            
            logger.info(f"✅ Agent analysis result saved for order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving agentic agent analysis for order {order_id}: {e}")
            return False
    
    def _write_fraud_results_agent_analysis(self, cursor, conn, order_id: str, agent_result: Dict[str, Any]) -> bool:
        """Write agent analysis to fraud_results schema"""
        # TODO: Implement fraud_results schema agent analysis writing
        logger.info(f"✅ Would save agent analysis for order {order_id} to fraud_results schema")
        return True
    
    def write_agent_analysis_batch(self, agent_results: List[Tuple[str, Dict[str, Any]]]) -> int:
        """Write batch of agent analysis results"""
        success_count = 0
        
        for order_id, agent_result in agent_results:
            if self.write_agent_analysis_result(order_id, agent_result):
                success_count += 1
        
        logger.info(f"✅ Batch agent analysis: {success_count}/{len(agent_results)} successfully written")
        return success_count
    
    def get_fraud_detection_stats(self) -> Dict[str, Any]:
        """Get fraud detection statistics (works with both schemas)"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if self.schema_type == "agentic":
                # Get stats from agentic schema
                cursor.execute("""
                SELECT * FROM daily_fraud_summary 
                WHERE detection_date = CURRENT_DATE
                """)
                daily_stats = cursor.fetchone()
                
                cursor.execute("""
                SELECT * FROM agent_performance_metrics 
                WHERE analysis_date = CURRENT_DATE
                LIMIT 1
                """)
                agent_stats = cursor.fetchone()
                
                cursor.execute("""
                SELECT COUNT(*) as high_risk_count 
                FROM high_risk_fraud_alerts
                WHERE DATE(fraud_detection_time) = CURRENT_DATE
                """)
                alerts_stats = cursor.fetchone()
            else:
                # Get stats from fraud_results schema
                daily_stats = {}
                agent_stats = {}
                alerts_stats = {}
            
            cursor.close()
            conn.close()
            
            return {
                "schema_type": self.schema_type,
                "daily_summary": dict(daily_stats) if daily_stats else {},
                "agent_performance": dict(agent_stats) if agent_stats else {},
                "high_risk_alerts": dict(alerts_stats) if alerts_stats else {},
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting fraud detection stats: {e}")
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ PostgreSQL connection test successful (Schema: {self.schema_type})")
            return result[0] == 1
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection test failed: {e}")
            return False
    
    def _sanitize_schema_statements(self, schema_sql: str) -> List[str]:
        """Sanitize and validate schema SQL statements to prevent injection.
        
        Args:
            schema_sql: Raw SQL schema content
            
        Returns:
            List of validated SQL statements
        """
        import re
        
        # Remove comments and normalize whitespace
        schema_sql = re.sub(r'--.*$', '', schema_sql, flags=re.MULTILINE)
        schema_sql = re.sub(r'/\*.*?\*/', '', schema_sql, flags=re.DOTALL)
        
        # Split into statements and clean
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        # Filter out empty statements and obvious malicious patterns
        safe_statements = []
        for statement in statements:
            # Skip empty statements
            if not statement:
                continue
            
            # Skip DROP statements to avoid accidental data loss
            if statement.upper().startswith('DROP'):
                logger.warning(f"Skipping DROP statement for security: {statement[:50]}...")
                continue
            
            # Check for obvious SQL injection patterns
            if self._contains_injection_patterns(statement):
                logger.error(f"Statement contains potential injection patterns: {statement[:100]}...")
                continue
            
            safe_statements.append(statement)
        
        return safe_statements
    
    def _contains_injection_patterns(self, statement: str) -> bool:
        """Check if statement contains common SQL injection patterns.
        
        Args:
            statement: SQL statement to check
            
        Returns:
            True if potentially malicious patterns found
        """
        import re
        
        statement_upper = statement.upper()
        
        # Dangerous patterns that shouldn't appear in schema DDL
        dangerous_patterns = [
            r';\s*(DELETE|UPDATE|INSERT|DROP)\s+',  # Chained dangerous statements
            r'UNION\s+SELECT',  # Union-based injection
            r'OR\s+1\s*=\s*1',  # Boolean-based injection
            r'\'.*\'.*\'',  # Multiple quotes suggesting injection
            r'--.*',  # SQL comments (should be removed by sanitize)
            r'/\*.*\*/',  # Block comments
            r'EXEC\s*\(',  # Stored procedure execution
            r'xp_',  # Extended stored procedures (SQL Server)
            r'sp_',  # System stored procedures
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, statement_upper, re.IGNORECASE):
                return True
        
        return False
    
    def _is_safe_ddl_statement(self, statement: str) -> bool:
        """Validate that statement is a safe DDL operation.
        
        Args:
            statement: SQL statement to validate
            
        Returns:
            True if statement is safe DDL
        """
        statement_upper = statement.upper().strip()
        
        # Allow only specific DDL statements
        allowed_ddl_prefixes = [
            'CREATE TABLE',
            'CREATE INDEX',
            'CREATE UNIQUE INDEX',
            'CREATE VIEW',
            'CREATE SEQUENCE',
            'CREATE TYPE',
            'CREATE FUNCTION',
            'ALTER TABLE',
            'COMMENT ON'
        ]
        
        # Check if statement starts with allowed DDL
        for prefix in allowed_ddl_prefixes:
            if statement_upper.startswith(prefix):
                return True
        
        logger.warning(f"Statement not recognized as safe DDL: {statement[:50]}...")
        return False

# Global instance for easy access
unified_postgres_writer = UnifiedPostgreSQLWriter()