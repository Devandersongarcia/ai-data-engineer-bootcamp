"""
Simplified Result Writer for Fraud Detection
Writes results to console, files, and optionally Kafka
"""

import logging
import os
from typing import Dict, Any, Optional
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
from config.settings import settings
import psycopg2
from psycopg2.extras import RealDictCursor
import json

logger = logging.getLogger(__name__)

class FraudResultWriter:
    """Write fraud detection results to various sinks"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.kafka_config = settings.kafka
        self._setup_postgres_table()
        
    def write_to_console(self, fraud_df: DataFrame) -> None:
        """Write fraud results to console for monitoring"""
        
        # Simple debug output - show available columns (without restaurant_id)
        debug_df = fraud_df.select(
            col("order_id"),
            col("user_id"),
            col("total_amount"),
            col("payment_method"),
            col("fraud_score"),
            col("fraud_prediction"),
            col("velocity_risk"),
            col("amount_risk"),
            col("account_risk"),
            col("payment_risk")
        )
        
        query = debug_df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .option("numRows", 5) \
            .trigger(processingTime='10 seconds') \
            .start()
            
        return query
    
    def write_to_files(self, fraud_df: DataFrame, output_path: str = "data/fraud_results") -> None:
        """Write fraud results to Parquet files"""
        
        # Add date partition for efficient querying
        partitioned_df = fraud_df.withColumn(
            "date", 
            date_format(col("detection_timestamp"), "yyyy-MM-dd")
        )
        
        query = partitioned_df.writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("path", output_path) \
            .option("checkpointLocation", f"{output_path}_checkpoint") \
            .partitionBy("date") \
            .trigger(processingTime='30 seconds') \
            .start()
            
        return query
    
    def write_to_kafka(self, fraud_df: DataFrame) -> None:
        """Write fraud results back to Kafka"""
        
        # Prepare data for Kafka - convert to JSON
        kafka_df = fraud_df.select(
            col("order_id").alias("key"),
            to_json(struct(
                col("order_id"),
                col("user_id"),
                col("fraud_score"),
                col("fraud_prediction"),
                col("confidence"),
                col("fraud_reasons"),
                col("detection_timestamp")
            )).alias("value")
        )
        
        kafka_options = {
            "kafka.bootstrap.servers": self.kafka_config.bootstrap_servers,
            "kafka.security.protocol": self.kafka_config.security_protocol,
            "kafka.sasl.mechanism": self.kafka_config.sasl_mechanism,
            "kafka.sasl.jaas.config": f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{self.kafka_config.sasl_username}" password="{self.kafka_config.sasl_password}";',
            "topic": "fraud-results"
        }
        
        query = kafka_df.writeStream \
            .outputMode("append") \
            .format("kafka") \
            .options(**kafka_options) \
            .trigger(processingTime='5 seconds') \
            .start()
            
        return query
    
    def write_fraud_alerts(self, fraud_df: DataFrame) -> None:
        """Write high-risk fraud alerts to separate stream"""
        
        # Filter only high-risk cases
        alerts_df = fraud_df.filter(col("fraud_prediction") == "HIGH_RISK") \
            .select(
                col("order_id"),
                col("user_id"), 
                col("fraud_score"),
                col("fraud_reasons"),
                lit("URGENT").alias("alert_level"),
                col("detection_timestamp")
            )
        
        query = alerts_df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .trigger(processingTime='1 second') \
            .start()
            
        return query
    
    def create_fraud_summary(self, fraud_df: DataFrame) -> None:
        """Create real-time fraud detection summary"""
        
        # Aggregate fraud statistics in sliding window
        summary_df = fraud_df \
            .withWatermark("detection_timestamp", "1 minute") \
            .groupBy(
                window(col("detection_timestamp"), "1 minute", "30 seconds"),
                col("fraud_prediction")
            ) \
            .agg(
                count("*").alias("count"),
                avg("fraud_score").alias("avg_fraud_score"),
                max("fraud_score").alias("max_fraud_score")
            ) \
            .select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("fraud_prediction"),
                col("count"),
                round(col("avg_fraud_score"), 3).alias("avg_fraud_score"),
                round(col("max_fraud_score"), 3).alias("max_fraud_score")
            )
        
        query = summary_df.writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .trigger(processingTime='30 seconds') \
            .start()
            
        return query
    
    def _setup_postgres_table(self):
        """Create PostgreSQL table for fraud results if it doesn't exist"""
        try:
            # Use fraud_detection database connection
            postgres_conn_string = 'postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/fraud_detection'
                
            conn = psycopg2.connect(postgres_conn_string)
            cursor = conn.cursor()
            
            # Create table matching your enhanced fraud generator output
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS fraud_results (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(100) UNIQUE NOT NULL,
                user_id VARCHAR(100),
                restaurant_id VARCHAR(100),
                total_amount DECIMAL(10,2),
                payment_method VARCHAR(50),
                account_age_days INTEGER,
                total_orders INTEGER,
                avg_order_value DECIMAL(10,2),
                fraud_score DECIMAL(5,3),
                fraud_prediction VARCHAR(20),
                fraud_reasons TEXT[],
                confidence DECIMAL(5,3),
                velocity_risk DECIMAL(5,3),
                amount_risk DECIMAL(5,3),
                account_risk DECIMAL(5,3),
                payment_risk DECIMAL(5,3),
                requires_agent_analysis BOOLEAN,
                agent_decision VARCHAR(20),
                agent_confidence DECIMAL(5,3),
                agent_reasoning TEXT,
                processing_timestamp TIMESTAMP,
                detection_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_fraud_results_order_id ON fraud_results(order_id);
            CREATE INDEX IF NOT EXISTS idx_fraud_results_fraud_score ON fraud_results(fraud_score);
            CREATE INDEX IF NOT EXISTS idx_fraud_results_timestamp ON fraud_results(detection_timestamp);
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("✅ PostgreSQL fraud_results table ready")
            
        except Exception as e:
            logger.error(f"❌ Error setting up PostgreSQL table: {e}")
    
    def _postgres_batch_writer(self, batch_df, batch_id):
        """Custom batch writer for PostgreSQL"""
        try:
            # Convert Spark DataFrame to Python list of dicts
            batch_data = batch_df.collect()
            
            if not batch_data:
                logger.info(f"Batch {batch_id}: No data to write")
                return
            
            # Connect to PostgreSQL - Use fraud_detection database
            postgres_conn_string = 'postgresql://postgres:XgfyZnwLEDuSDPAmMJchvdlpSKwpqRTb@maglev.proxy.rlwy.net:54891/fraud_detection'
            conn = psycopg2.connect(postgres_conn_string)
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO fraud_results (
                order_id, user_id, restaurant_id, total_amount, payment_method,
                account_age_days, total_orders, avg_order_value,
                fraud_score, fraud_prediction, fraud_reasons, confidence,
                velocity_risk, amount_risk, account_risk, payment_risk,
                requires_agent_analysis, agent_decision, agent_confidence, agent_reasoning,
                processing_timestamp, detection_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (order_id) DO UPDATE SET
                fraud_score = EXCLUDED.fraud_score,
                fraud_prediction = EXCLUDED.fraud_prediction,
                agent_decision = EXCLUDED.agent_decision,
                agent_confidence = EXCLUDED.agent_confidence,
                agent_reasoning = EXCLUDED.agent_reasoning,
                detection_timestamp = EXCLUDED.detection_timestamp
            """
            
            # Safe conversion functions
            def safe_float(val, default=0.0):
                return float(val) if val is not None else default
            
            def safe_int(val, default=0):
                return int(val) if val is not None else default
            
            # Prepare batch data with NULL handling
            records = []
            for row in batch_data:
                row_dict = row.asDict()
                records.append((
                    row_dict.get('order_id'),
                    row_dict.get('user_id'),
                    row_dict.get('restaurant_id'),
                    safe_float(row_dict.get('total_amount')),
                    row_dict.get('payment_method'),
                    safe_int(row_dict.get('account_age_days')),
                    safe_int(row_dict.get('total_orders')),
                    safe_float(row_dict.get('avg_order_value')),
                    safe_float(row_dict.get('fraud_score')),
                    row_dict.get('fraud_prediction'),
                    row_dict.get('fraud_reasons', []),
                    safe_float(row_dict.get('confidence')),
                    safe_float(row_dict.get('velocity_risk')),
                    safe_float(row_dict.get('amount_risk')),
                    safe_float(row_dict.get('account_risk')),
                    safe_float(row_dict.get('payment_risk')),
                    row_dict.get('requires_agent_analysis', False),
                    row_dict.get('agent_decision'),
                    safe_float(row_dict.get('agent_confidence')) if row_dict.get('agent_confidence') is not None else None,
                    row_dict.get('agent_reasoning'),
                    row_dict.get('processing_timestamp'),
                    row_dict.get('detection_timestamp')
                ))
            
            # Execute batch insert
            cursor.executemany(insert_sql, records)
            conn.commit()
            
            logger.info(f"✅ Batch {batch_id}: Inserted {len(records)} fraud results to PostgreSQL")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Error writing batch {batch_id} to PostgreSQL: {e}")
    
    def write_to_postgres(self, fraud_df: DataFrame):
        """Write fraud results to PostgreSQL using foreachBatch"""
        
        query = fraud_df.writeStream \
            .outputMode("append") \
            .foreachBatch(self._postgres_batch_writer) \
            .option("checkpointLocation", "./checkpoint/postgres") \
            .trigger(processingTime='15 seconds') \
            .start()
            
        logger.info("🗄️ PostgreSQL writer started")
        return query
    
    def setup_multiple_sinks(self, fraud_df: DataFrame) -> Dict[str, Any]:
        """Setup multiple output sinks for comprehensive monitoring"""
        
        logger.info("Setting up multiple output sinks")
        
        queries = {}
        
        # 1. Console output for monitoring
        queries['console'] = self.write_to_console(fraud_df)
        
        # 2. File output for persistence  
        queries['files'] = self.write_to_files(fraud_df)
        
        # 3. Kafka output for downstream systems
        # queries['kafka'] = self.write_to_kafka(fraud_df)
        
        # 4. High-risk alerts
        queries['alerts'] = self.write_fraud_alerts(fraud_df)
        
        # 5. Real-time summary
        queries['summary'] = self.create_fraud_summary(fraud_df)
        
        # 6. PostgreSQL output for persistence
        queries['postgres'] = self.write_to_postgres(fraud_df)
        
        logger.info(f"Started {len(queries)} output streams")
        return queries