"""
Agentic Spark Streaming Fraud Detection Application
Combines Spark Structured Streaming with CrewAI agents for intelligent real-time fraud detection
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from typing import Dict, Any, Optional

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, current_timestamp, from_json, when, lit, 
    coalesce, hash as spark_hash, abs as spark_abs
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType

from src.streaming.fraud_detector import SparkFraudDetector
from src.streaming.result_writer import FraudResultWriter
from src.streaming.agentic_fraud_processor import AgenticFraudProcessor
from src.streaming.unified_result_processor import unified_result_processor
from config.settings import settings

logger = logging.getLogger(__name__)

class AgenticSparkFraudApp:
    """Intelligent real-time fraud detection with CrewAI agent integration.
    
    Combines Spark Structured Streaming with multi-agent AI systems for
    comprehensive fraud analysis and automated decision making.
    
    Attributes:
        spark: Spark session for streaming operations
        queries: Dictionary of running streaming queries
        running: Application state flag
        agentic_processor: AI agent processor for complex case analysis
    """
    
    def __init__(self) -> None:
        """Initialize the fraud detection application."""
        self.spark: Optional[SparkSession] = None
        self.queries: Dict[str, Any] = {}
        self.running: bool = True
        self.agentic_processor: Optional[Any] = None
        
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Configure graceful shutdown signal handlers."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number received
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
        self._stop_all_queries()
    
    def _create_spark_session(self) -> SparkSession:
        """Create optimized Spark session for agentic streaming"""
        
        spark = SparkSession.builder \
            .appName("UberEats-Agentic-Fraud-Detection-Fresh-v2") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0") \
            .config("spark.sql.streaming.metricsEnabled", "true") \
            .config("spark.sql.streaming.checkpointLocation.deleteOnExit", "true") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
            .config("spark.sql.streaming.statefulOperator.checkCorrectness.enabled", "false") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info(f"🚀 Agentic Spark session created: {spark.version}")
        return spark
    
    def run_test_mode(self):
        """Test mode with sample data for agent analysis"""
        try:
            logger.info("🧪 Starting Agentic Test Mode")
            
            # Create Spark session
            self.spark = self._create_spark_session()
            
            # Initialize agentic processor
            self.agentic_processor = AgenticFraudProcessor(
                spark=self.spark,
                max_concurrent_agents=2
            )
            
            # Create test data with various risk profiles
            test_data = [
                # High risk case - should trigger agent analysis
                {
                    "order_id": "agentic_test_001",
                    "user_id": "new_user_001",
                    "total_amount": 299.99,
                    "payment_method": "credit_card",
                    "account_age_days": 1,
                    "total_orders": 8,
                    "avg_order_value": 25.0
                },
                # Medium risk case
                {
                    "order_id": "agentic_test_002", 
                    "user_id": "user_002",
                    "total_amount": 89.50,
                    "payment_method": "pix",
                    "account_age_days": 5,
                    "total_orders": 3,
                    "avg_order_value": 45.0
                },
                # Low risk case - should auto-allow
                {
                    "order_id": "agentic_test_003",
                    "user_id": "trusted_user_003", 
                    "total_amount": 32.75,
                    "payment_method": "pix",
                    "account_age_days": 120,
                    "total_orders": 45,
                    "avg_order_value": 35.0
                }
            ]
            
            # Create test DataFrame
            test_df = self.spark.createDataFrame(test_data)
            test_df = test_df.withColumn("processing_timestamp", current_timestamp())
            
            # Apply fraud detection
            fraud_detector = SparkFraudDetector(self.spark)
            fraud_results = fraud_detector.detect_fraud(test_df)
            
            # Add intelligent routing
            routed_results = self.agentic_processor.add_intelligent_routing(fraud_results)
            
            logger.info("🔍 Initial Spark Analysis Results:")
            routed_results.show(truncate=False)
            
            # Test agent analysis on cases that require it
            agent_cases = routed_results.filter(col("requires_agent_analysis") == True)
            agent_count = agent_cases.count()
            
            logger.info(f"🤖 Found {agent_count} cases requiring agent analysis")
            
            if agent_count > 0:
                logger.info("⏳ Running agent analysis...")
                
                # Process with agents
                self.agentic_processor.process_agent_analysis_batch(
                    agent_cases, 
                    batch_id=0
                )
                
                # Show final metrics
                metrics = self.agentic_processor.get_metrics()
                logger.info("🎯 Final Agent Metrics:")
                for key, value in metrics.items():
                    if key != 'timestamp':
                        logger.info(f"   {key}: {value}")
            
            logger.info("✅ Agentic test mode completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error in agentic test mode: {e}", exc_info=True)
        finally:
            if self.agentic_processor:
                self.agentic_processor.shutdown()
            if self.spark:
                self.spark.stop()
    
    def run_streaming_mode(self):
        """Full streaming mode with Confluent Cloud and agent analysis"""
        try:
            logger.info("🚀 Starting Full Agentic Streaming Mode")
            logger.info("📡 Connecting to Confluent Cloud...")
            
            # Create Spark session
            self.spark = self._create_spark_session()
            
            # Initialize agentic processor
            logger.info("🔧 Initializing agentic processor...")
            self.agentic_processor = AgenticFraudProcessor(
                spark=self.spark,
                max_concurrent_agents=2  # Reduced to prevent timeout issues
            )
            logger.info("✅ Agentic processor initialized!")
            
            # Get Confluent Cloud Kafka configuration
            kafka_options = {
                "kafka.bootstrap.servers": settings.kafka.bootstrap_servers,
                "kafka.security.protocol": "SASL_SSL",
                "kafka.sasl.mechanism": "PLAIN",
                "kafka.sasl.jaas.config": f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{settings.kafka.sasl_username}" password="{settings.kafka.sasl_password}";'
            }
            
            logger.info(f"🔐 Connecting to: {settings.kafka.bootstrap_servers}")
            logger.info(f"📥 Reading from topic: {settings.kafka.input_topics}")
            
            # Create Kafka streaming source
            kafka_stream = self.spark \
                .readStream \
                .format("kafka")
            
            # Add Kafka options
            for key, value in kafka_options.items():
                kafka_stream = kafka_stream.option(key, value)
            
            # Configure stream
            raw_stream = kafka_stream \
                .option("subscribe", settings.kafka.input_topics) \
                .option("startingOffsets", "earliest") \
                .option("maxOffsetsPerTrigger", 100) \
                .option("failOnDataLoss", "false") \
                .load()
            
            logger.info("✅ Confluent Cloud connection established")
            
            # Parse incoming JSON orders and extract fields
            from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
            
            # Define complete schema matching actual Kafka message structure
            order_schema = StructType([
                # Core order fields
                StructField("order_id", StringType(), True),
                StructField("user_key", StringType(), True),
                StructField("restaurant_key", StringType(), True),
                StructField("driver_key", StringType(), True),
                StructField("payment_key", StringType(), True),
                StructField("total_amount", DoubleType(), True),
                StructField("item_count", IntegerType(), True),
                StructField("order_date", StringType(), True),
                StructField("dt_current_timestamp", StringType(), True),
                
                # Restaurant and delivery fields
                StructField("restaurant_rating", DoubleType(), True),
                StructField("estimated_delivery_minutes", IntegerType(), True),
                StructField("restaurant_distance_km", DoubleType(), True),
                StructField("restaurant_prep_time", IntegerType(), True),
                
                # Order details
                StructField("order_source", StringType(), True),
                StructField("currency", StringType(), True),
                StructField("platform_fee", DoubleType(), True),
                StructField("delivery_fee", DoubleType(), True),
                StructField("tax_amount", DoubleType(), True),
                StructField("tip_amount", DoubleType(), True),
                
                # Status fields
                StructField("order_status", StringType(), True),
                StructField("payment_status", StringType(), True),
                
                # Customer fields
                StructField("customer_notes", StringType(), True),
                StructField("order_channel", StringType(), True),
                StructField("is_favorite_restaurant", StringType(), True),
                StructField("delivery_address_type", StringType(), True),
                StructField("delivery_instructions", StringType(), True),
                
                # Environmental
                StructField("weather_condition", StringType(), True)
            ])
            
            # Parse JSON and extract order data with proper mappings
            logger.info("🔧 Parsing JSON stream...")
            try:
                parsed_stream = raw_stream.select(
                    col("key").cast("string").alias("order_key"),
                    from_json(col("value").cast("string"), order_schema).alias("order_data"),
                    col("topic"),
                    col("partition"),
                    col("offset"),
                    col("timestamp").alias("kafka_timestamp")
                ).select(
                    # Map Kafka fields to expected database fields
                    col("order_data.order_id"),
                    coalesce(col("order_data.user_key"), lit("unknown")).alias("user_id"),
                    col("order_data.total_amount"),
                    
                    # Derive payment method from order source and status
                    when(col("order_data.payment_status") == "completed", 
                         when(col("order_data.order_source") == "website", "credit_card")
                         .when(col("order_data.order_source") == "mobile", "mobile_payment")
                         .otherwise("credit_card"))
                    .otherwise("unknown").alias("payment_method"),
                    
                    # Add mock enrichment data for fraud detection (will be replaced by enrichment service)
                    when(col("order_data.user_key").isNotNull(), 
                         hash(col("order_data.user_key")) % 365).otherwise(0).alias("account_age_days"),
                    when(col("order_data.user_key").isNotNull(), 
                         abs(hash(col("order_data.user_key")) % 50) + 1).otherwise(1).alias("total_orders"),
                    when(col("order_data.total_amount").isNotNull(), 
                         col("order_data.total_amount") * 0.8).otherwise(25.0).alias("avg_order_value"),
                    
                    col("kafka_timestamp")
                ).withColumn("processing_timestamp", current_timestamp())
                logger.info("✅ JSON parsing configured!")
                
                # Filter out null orders (invalid JSON) with proper validation
                logger.info("🔧 Applying data validation filters...")
                valid_orders = parsed_stream.filter(
                    col("order_id").isNotNull() & 
                    col("user_id").isNotNull()
                ).filter(
                    col("user_id") != lit("unknown")
                )
                logger.info("✅ Data validation filters applied!")
                
            except Exception as e:
                logger.error(f"❌ Failed during stream parsing setup: {e}", exc_info=True)
                raise
            
            logger.info("⚡ Starting complete fraud detection pipeline...")
            
            # Apply fraud detection
            logger.info("🔧 Initializing fraud detector...")
            fraud_detector = SparkFraudDetector(self.spark)
            logger.info("🔧 Running fraud detection...")
            fraud_results = fraud_detector.detect_fraud(valid_orders)
            logger.info("✅ Fraud detection completed!")
            
            # Add intelligent routing with agents
            logger.info("🔧 Adding intelligent routing...")
            routed_results = self.agentic_processor.add_intelligent_routing(fraud_results)
            logger.info("✅ Intelligent routing completed!")
            
            # Setup PostgreSQL sink for fraud results (main table)
            logger.info("🔧 Creating PostgreSQL fraud results sink...")
            fraud_results_query = unified_result_processor.create_fraud_detection_sink(routed_results)
            logger.info("✅ PostgreSQL fraud results sink created!")
            
            # Setup agent analysis sink (simplified approach)
            logger.info("🔧 About to create agent analysis sink...")
            agent_analysis_query = None
            try:
                # Direct creation with immediate timeout handling
                logger.info("🤖 Creating agent analysis sink directly...")
                agent_analysis_query = self.agentic_processor.create_agent_analysis_sink(routed_results)
                logger.info("✅ Agent analysis sink created successfully!")
            except Exception as e:
                logger.error(f"❌ Agent analysis sink creation failed: {e}", exc_info=True)
                logger.info("🔄 Continuing without agent sink - fraud detection will work normally")
                agent_analysis_query = None
            
            # Setup additional sinks (files, etc) 
            logger.info("🔧 Setting up additional file sinks...")
            result_writer = FraudResultWriter(self.spark)
            file_queries = result_writer.setup_multiple_sinks(routed_results)
            logger.info("✅ File sinks created!")
            
            logger.info("🔧 Assembling query dictionary...")
            queries = {
                "fraud_results_postgres": fraud_results_query,
                **file_queries
            }
            
            # Only add agent analysis query if it was created successfully
            if agent_analysis_query is not None:
                queries["agent_analysis"] = agent_analysis_query
                logger.info("✅ Agent analysis query added to pipeline!")
            else:
                logger.warning("⚠️  Agent analysis query not added (was None)")
                logger.info("🔄 Implementing fallback: Direct agent processing via batch trigger...")
                # Fallback: Add a separate mechanism to periodically process agent-required orders
                self._setup_fallback_agent_processing(routed_results)
            
            # Add console query for monitoring
            logger.info("🔧 Creating console monitoring query...")
            console_query = routed_results.select(
                col("order_id"),
                col("user_id"),
                col("total_amount"),
                col("fraud_score"),
                col("fraud_prediction"),
                col("requires_agent_analysis"),
                col("triage_decision"),
                col("processing_timestamp")
            ).writeStream \
                .outputMode("append") \
                .format("console") \
                .option("truncate", "false") \
                .option("numRows", 10) \
                .trigger(processingTime='15 seconds') \
                .start()
            logger.info("✅ Console monitoring query created!")
            
            logger.info("🔧 Updating queries registry...")
            queries["console_monitor"] = console_query
            self.queries.update(queries)
            logger.info("✅ Queries registry updated!")
            
            logger.info("🎯 Agentic fraud detection pipeline started successfully!")
            logger.info("📊 Monitoring incoming orders...")
            logger.info("🤖 Agents ready for high-risk case analysis")
            logger.info("⏹️  Press Ctrl+C to stop")
            
            # Keep running until interrupted
            try:
                while self.running:
                    time.sleep(1)
                    # Check if any queries failed
                    for name, query in self.queries.items():
                        if query.exception() is not None:
                            logger.error(f"Query {name} failed: {query.exception()}")
                            self.running = False
                            break
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal")
                self.running = False
            
            logger.info("🔄 Shutting down streaming queries...")
            self._stop_all_queries()
            
        except Exception as e:
            logger.error(f"❌ Error in streaming mode: {e}", exc_info=True)
        finally:
            if self.agentic_processor:
                self.agentic_processor.shutdown()
            if self.spark:
                self.spark.stop()
                
    def _setup_fallback_agent_processing(self, routed_results: DataFrame):
        """Setup fallback agent processing if main sink fails"""
        logger.info("🔧 Setting up fallback agent processing mechanism...")
        try:
            # Create a simple sink that will trigger agent processing periodically
            fallback_query = routed_results.filter(
                (col("requires_agent_analysis") == True) & 
                (col("triage_decision") == "AGENT_ANALYSIS")
            ).writeStream \
                .outputMode("append") \
                .format("console") \
                .option("truncate", "false") \
                .option("numRows", 5) \
                .trigger(processingTime='30 seconds') \
                .foreachBatch(self._fallback_agent_batch_processor) \
                .start()
            
            self.queries["fallback_agent_processing"] = fallback_query
            logger.info("✅ Fallback agent processing setup complete!")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup fallback agent processing: {e}", exc_info=True)
    
    def _fallback_agent_batch_processor(self, batch_df: DataFrame, batch_id: int):
        """Fallback batch processor for agent analysis"""
        try:
            logger.info(f"🔄 Fallback agent processor triggered - Batch {batch_id}")
            
            # Process the batch using the agentic processor
            if self.agentic_processor and batch_df.count() > 0:
                logger.info(f"📝 Processing {batch_df.count()} orders via fallback mechanism")
                self.agentic_processor.process_agent_analysis_batch(batch_df, batch_id)
            else:
                logger.info("🔕 No orders to process in fallback batch")
                
        except Exception as e:
            logger.error(f"❌ Fallback agent batch processing failed: {e}", exc_info=True)

    def _stop_all_queries(self):
        """Stop all running streaming queries"""
        for name, query in self.queries.items():
            try:
                logger.info(f"Stopping query: {name}")
                query.stop()
            except Exception as e:
                logger.error(f"Error stopping query {name}: {e}")
        self.queries.clear()

def main():
    """Main entry point for agentic fraud detection"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = AgenticSparkFraudApp()
    
    # Check if running in test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        app.run_test_mode()
    else:
        logger.info("🔄 Starting full streaming mode with Confluent Cloud")
        app.run_streaming_mode()

if __name__ == "__main__":
    main()