"""
Unified Result Processor
Handles writing both fraud detection results and agent analyses to PostgreSQL
Works with both agentic_fraud_schema and fraud_results_schema
"""

import logging
from typing import Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, current_timestamp
from src.database.unified_postgres_writer import unified_postgres_writer

logger = logging.getLogger(__name__)

class UnifiedResultProcessor:
    """Processes and writes fraud detection results using unified writer"""
    
    def __init__(self):
        self.unified_writer = unified_postgres_writer
        self.test_connection()
    
    def test_connection(self):
        """Test database connection on initialization"""
        if self.unified_writer.test_connection():
            logger.info("✅ Unified Result Processor connected to PostgreSQL")
        else:
            logger.error("❌ Failed to connect to PostgreSQL")
    
    def process_fraud_detection_batch(self, batch_df: DataFrame, batch_id: int):
        """Process fraud detection results batch"""
        try:
            # Add processing timestamp if not present
            if "processing_timestamp" not in batch_df.columns:
                batch_df = batch_df.withColumn("processing_timestamp", current_timestamp())
            
            if "detection_timestamp" not in batch_df.columns:
                batch_df = batch_df.withColumn("detection_timestamp", current_timestamp())
            
            # Write to database using unified writer
            self.unified_writer.write_fraud_detection_batch(batch_df, batch_id)
            
            # Log batch summary
            batch_size = batch_df.count()
            logger.info(f"📊 Batch {batch_id}: Processed {batch_size} fraud detection results")
            
        except Exception as e:
            logger.error(f"❌ Error processing fraud detection batch {batch_id}: {e}")
    
    def create_fraud_detection_sink(self, fraud_df: DataFrame) -> Any:
        """Create streaming sink for fraud detection results"""
        
        return fraud_df.writeStream \
            .outputMode("append") \
            .foreachBatch(self.process_fraud_detection_batch) \
            .option("checkpointLocation", "/tmp/spark-streaming/unified-fraud-results-fresh-v2") \
            .trigger(processingTime="15 seconds") \
            .start()
    
    def create_console_monitoring_sink(self, fraud_df: DataFrame) -> Any:
        """Create console sink for real-time monitoring"""
        
        # Select key columns for monitoring
        monitoring_df = fraud_df.select(
            col("order_id"),
            col("user_id"), 
            col("fraud_score"),
            col("fraud_prediction"),
            col("triage_decision"),
            col("requires_agent_analysis"),
            col("detection_timestamp")
        )
        
        return monitoring_df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .option("numRows", 10) \
            .trigger(processingTime="20 seconds") \
            .start()
    
    def create_high_risk_alerts_sink(self, fraud_df: DataFrame) -> Any:
        """Create sink for high-risk fraud alerts"""
        
        # Filter high-risk cases
        high_risk_df = fraud_df.filter(
            (col("fraud_score") >= 0.8) | 
            (col("triage_decision") == "AUTO_BLOCK") |
            (col("requires_agent_analysis") == True)
        ).select(
            col("order_id"),
            col("user_id"),
            col("fraud_score"),
            col("fraud_prediction"),
            col("triage_decision"),
            col("total_amount"),
            col("detection_timestamp")
        )
        
        return high_risk_df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .option("numRows", 5) \
            .queryName("HighRiskAlerts") \
            .trigger(processingTime="5 seconds") \
            .start()
    
    def setup_comprehensive_monitoring(self, fraud_df: DataFrame) -> Dict[str, Any]:
        """Setup comprehensive monitoring with multiple sinks"""
        
        logger.info("🔄 Setting up comprehensive fraud detection monitoring...")
        
        queries = {}
        
        # 1. Main fraud detection results to PostgreSQL
        queries['fraud_results'] = self.create_fraud_detection_sink(fraud_df)
        logger.info("✅ PostgreSQL fraud results sink started")
        
        # 2. Console monitoring for development
        queries['console'] = self.create_console_monitoring_sink(fraud_df)
        logger.info("✅ Console monitoring sink started")
        
        # 3. High-risk alerts
        queries['alerts'] = self.create_high_risk_alerts_sink(fraud_df)
        logger.info("✅ High-risk alerts sink started")
        
        logger.info(f"🚀 Started {len(queries)} monitoring streams")
        return queries
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.unified_writer.get_fraud_detection_stats()

# Global instance
unified_result_processor = UnifiedResultProcessor()