#!/usr/bin/env python3
"""
Confluent Cloud Fraud Detection - Fixed Configuration
"""

import os
import sys
import logging
from pathlib import Path

# FORCE Confluent Cloud settings (override any environment variables)
os.environ.update({
    # Confluent Cloud Kafka settings
    "KAFKA_BOOTSTRAP_SERVERS": "pkc-lzvrd.us-west4.gcp.confluent.cloud:9092",
    "KAFKA_INPUT_TOPICS": "kafka-orders",
    "KAFKA_OUTPUT_TOPIC": "fraud-results",
    
    # Performance settings
    "SPARK_PROCESSING_TIME": "3 seconds",
    "SPARK_EXECUTOR_MEMORY": "2g", 
    "SPARK_EXECUTOR_CORES": "2",
    "SPARK_MAX_OFFSETS_PER_TRIGGER": "50",
    
    # Java settings for Spark 4.0
    "JAVA_HOME": "/opt/homebrew/opt/openjdk@17",
    "SPARK_HOME": "",  # Clear any conflicting Spark home
})

# Add Java 17 to PATH (critical for Spark 4.0)
java_path = "/opt/homebrew/opt/openjdk@17/bin"
current_path = os.environ.get("PATH", "")
if java_path not in current_path:
    os.environ["PATH"] = f"{java_path}:{current_path}"

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_confluent_fraud_detector():
    """Create fraud detection pipeline for Confluent Cloud"""
    
    logger.info("🚀 Starting Confluent Cloud Fraud Detection")
    logger.info("   ☁️ Connecting to Confluent Cloud")
    logger.info(f"   📡 Bootstrap servers: {settings.kafka.bootstrap_servers}")
    logger.info(f"   📥 Input topic: {settings.kafka.input_topics}")
    logger.info(f"   📤 Output topic: {settings.kafka.output_topic}")
    logger.info("=" * 60)
    
    # Create Spark session with Java 17
    logger.info("🔧 Creating Spark session with Java 17...")
    spark = SparkSession.builder \
        .appName("confluent-fraud-detection") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
        .config("spark.executor.memory", "2g") \
        .config("spark.executor.cores", "2") \
        .config("spark.sql.shuffle.partitions", "4") \
        .getOrCreate()
    
    logger.info("✅ Spark session created successfully")
    
    # Get Confluent Cloud Kafka options
    kafka_options = settings.kafka.get_spark_kafka_options()
    logger.info(f"🔐 Kafka authentication configured for user: {settings.kafka.sasl_username}")
    
    # Create Kafka stream
    logger.info("📡 Connecting to Confluent Cloud Kafka...")
    
    kafka_df = spark \
        .readStream \
        .format("kafka")
    
    # Add all Confluent Cloud options
    for key, value in kafka_options.items():
        kafka_df = kafka_df.option(key, value)
    
    # Configure stream
    stream_df = kafka_df \
        .option("subscribe", settings.kafka.input_topics) \
        .option("startingOffsets", "latest") \
        .option("maxOffsetsPerTrigger", 50) \
        .load()
    
    logger.info("✅ Confluent Cloud Kafka stream created successfully")
    
    # Parse JSON orders
    orders_df = stream_df.select(
        col("key").cast("string").alias("order_key"),
        col("value").cast("string").alias("order_json"),
        col("topic"),
        col("partition"), 
        col("offset"),
        col("timestamp").alias("kafka_timestamp")
    )
    
    # Simple fraud detection (no complex UDFs)
    fraud_df = orders_df.select(
        "*",
        # Extract basic fields from JSON for fast processing
        get_json_object(col("order_json"), "$.order_id").alias("order_id"),
        get_json_object(col("order_json"), "$.total_amount").cast("double").alias("total_amount"),
        get_json_object(col("order_json"), "$.account_age_days").cast("int").alias("account_age_days"),
        get_json_object(col("order_json"), "$.orders_today").cast("int").alias("orders_today"),
        
        # Fast fraud scoring using native Spark functions
        when(get_json_object(col("order_json"), "$.total_amount").cast("double") < 5.0, 0.9)
        .when(get_json_object(col("order_json"), "$.account_age_days").cast("int") < 1, 0.8)
        .when(get_json_object(col("order_json"), "$.orders_today").cast("int") > 15, 0.7)
        .otherwise(0.1).alias("fraud_score"),
        
        # Simple decision
        when(get_json_object(col("order_json"), "$.total_amount").cast("double") < 5.0, "FLAG")
        .when(get_json_object(col("order_json"), "$.account_age_days").cast("int") < 1, "REVIEW")
        .otherwise("ALLOW").alias("decision"),
        
        current_timestamp().alias("processed_at")
    )
    
    # Console output for monitoring
    console_query = fraud_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .option("numRows", 3) \
        .trigger(processingTime='3 seconds') \
        .start()
    
    logger.info("✅ Confluent Cloud fraud detection started")
    logger.info("   📺 Monitoring console for incoming orders...")
    logger.info("   🚨 Press Ctrl+C to stop")
    
    try:
        console_query.awaitTermination()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping Confluent Cloud fraud detection...")
        console_query.stop()
        spark.stop()

if __name__ == "__main__":
    create_confluent_fraud_detector()