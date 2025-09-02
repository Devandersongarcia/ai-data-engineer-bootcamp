"""
Final Simple Streaming App
Kafka → Spark → Batch Agent Processing
Low latency, minimal complexity, maximum intelligence
"""

import logging
import signal
import sys
import time
from pathlib import Path
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.streaming.batch_agent_processor import BatchAgentProcessor
from src.streaming.data_enrichment_service import DataEnrichmentService
from src.logging_config import setup_logging
from src.correlation import start_order_correlation, get_correlation_logger
from src.transaction_logger import create_transaction_logger, TransactionType
from src.business_events import get_business_event_logger
from config.settings import settings

# Initialize comprehensive logging
setup_logging(log_level='INFO', enable_file_logging=True)
logger = get_correlation_logger(__name__)

class FinalSimpleApp:
    """Final simplified Kafka → Spark → Agents application"""
    
    def __init__(self):
        self.spark = None
        self.queries = {}
        self.running = True
        self.agent_processor = None
        self.enrichment_service = None
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        self.running = False
        self._stop_queries()
    
    def _create_spark_session(self) -> SparkSession:
        """Create optimized Spark session"""
        spark = SparkSession.builder \
            .appName("Simple-Kafka-Spark-Agents") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.0,org.postgresql:postgresql:42.5.4") \
            .config("spark.sql.streaming.metricsEnabled", "true") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.streaming.checkpointLocation.deleteOnExit", "true") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        logger.info(f"🚀 Spark session ready: {spark.version}")
        return spark
    
    def _create_kafka_stream(self) -> DataFrame:
        """Create Kafka stream"""
        kafka_options = {
            "kafka.bootstrap.servers": settings.kafka.bootstrap_servers,
            "kafka.security.protocol": settings.kafka.security_protocol,
            "kafka.sasl.mechanism": settings.kafka.sasl_mechanism,
            "kafka.sasl.jaas.config": f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{settings.kafka.sasl_username}" password="{settings.kafka.sasl_password}";',
            "subscribe": "kafka-orders",
            "startingOffsets": "latest",
            "failOnDataLoss": "false"
        }
        
        return self.spark.readStream.format("kafka").options(**kafka_options).load()
    
    def _parse_orders(self, kafka_df: DataFrame) -> DataFrame:
        """Parse and enrich orders with complete fraud detection data"""
        # Complete Kafka message schema matching the actual data structure
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
            StructField("is_favorite_restaurant", BooleanType(), True),
            StructField("delivery_address_type", StringType(), True),
            StructField("delivery_instructions", StringType(), True),
            
            # Environmental
            StructField("weather_condition", StringType(), True)
        ])
        
        # Parse complete order data with proper field mappings
        basic_orders = kafka_df.select(
            from_json(col("value").cast("string"), order_schema).alias("order")
        ).select(
            # Core identifiers (handle NULLs with coalesce)
            col("order.order_id"),
            coalesce(col("order.user_key"), lit("unknown")).alias("user_id"),
            coalesce(col("order.restaurant_key"), lit("unknown")).alias("restaurant_id"),
            col("order.total_amount"),
            
            # Payment method derivation from available fields
            when(col("order.payment_status") == "completed", 
                 when(col("order.order_source") == "website", "credit_card")
                 .when(col("order.order_source") == "mobile", "mobile_payment")
                 .otherwise("credit_card"))
            .otherwise("unknown").alias("payment_method"),
            
            # Additional order details
            col("order.item_count"),
            col("order.restaurant_rating"),
            col("order.estimated_delivery_minutes"),
            col("order.restaurant_distance_km"),
            col("order.platform_fee"),
            col("order.delivery_fee"),
            col("order.tax_amount"),
            col("order.tip_amount"),
            col("order.order_status"),
            col("order.payment_status"),
            col("order.order_source"),
            col("order.currency"),
            col("order.is_favorite_restaurant"),
            col("order.delivery_address_type"),
            col("order.weather_condition"),
            
            current_timestamp().alias("processing_timestamp")
        )
        
        # Use enrichment service for real data
        enriched_orders = self.enrichment_service.enrich_order_stream(basic_orders)
        
        return enriched_orders
    
    def run_streaming(self):
        """Run the streaming pipeline"""
        # Create transaction logger for pipeline startup
        with create_transaction_logger(TransactionType.ORDER_INGESTION, component="streaming_pipeline") as pipeline_logger:
            pipeline_logger.start()
            
            try:
                logger.info("🚀 Starting Final Simple Streaming Pipeline")
                logger.info("📊 Pipeline: Kafka → Spark → Batch Agent Processing")
                
                # Initialize business event logger
                event_logger = get_business_event_logger("streaming_pipeline")
                
                pipeline_logger.checkpoint("spark_initialization")
                
                # Initialize components
                self.spark = self._create_spark_session()
                self.enrichment_service = DataEnrichmentService(self.spark)
                self.agent_processor = BatchAgentProcessor(spark_session=self.spark)
            
                pipeline_logger.checkpoint("kafka_stream_setup")
                
                # Create streams
                kafka_stream = self._create_kafka_stream()
                orders_stream = self._parse_orders(kafka_stream)
                
                pipeline_logger.checkpoint("agent_processing_setup")
                logger.info("🤖 Setting up agent processing stream...")
                
                # Agent processing stream
                agent_query = orders_stream \
                    .writeStream \
                    .outputMode("append") \
                    .foreachBatch(self.agent_processor.process_batch) \
                    .option("checkpointLocation", "./checkpoint/agent_processing") \
                    .trigger(processingTime="15 seconds") \
                    .start()
                
                # Console monitoring stream
                console_query = orders_stream \
                    .writeStream \
                    .outputMode("append") \
                    .format("console") \
                    .option("truncate", "false") \
                    .option("numRows", 5) \
                    .trigger(processingTime="30 seconds") \
                    .start()
                
                self.queries = {"agent_processing": agent_query, "console": console_query}
                
                pipeline_logger.checkpoint("pipeline_active")
                
                # Log pipeline startup event
                event_logger.log_compliance_event(
                    compliance_type="pipeline_startup",
                    status="active",
                    details={
                        "kafka_topic": "kafka-orders",
                        "processing_interval": "15 seconds",
                        "console_interval": "30 seconds",
                        "checkpoint_location": "./checkpoint/agent_processing"
                    }
                )
                
                logger.info("=" * 60)
                logger.info("✅ Simple Streaming Pipeline Active")
                logger.info("📡 Input: Kafka kafka-orders topic")
                logger.info("🧠 Processing: CrewAI agents every 15 seconds")  
                logger.info("📊 Output: Console + Agent analysis")
                logger.info("=" * 60)
                
                self._monitor()
                
            except Exception as e:
                pipeline_logger.update_metrics(error_count=1)
                event_logger.log_performance_anomaly(
                    metric_name="pipeline_startup",
                    current_value=0,
                    threshold=1
                )
                logger.error(f"❌ Streaming pipeline error: {e}")
                raise
            finally:
                self._cleanup()
    
    def _monitor(self):
        """Monitor the pipeline with comprehensive logging"""
        event_logger = get_business_event_logger("pipeline_monitor")
        
        while self.running:
            try:
                # Use built-in sum to avoid conflict with Spark functions
                active = len([q for q in self.queries.values() if q.isActive])
                
                # Log monitoring metrics
                logger.info(
                    f"📊 Pipeline health check",
                    monitoring_metrics={
                        'active_streams': active,
                        'total_streams': len(self.queries),
                        'pipeline_status': 'healthy' if active == len(self.queries) else 'degraded'
                    }
                )
                
                # Agent processor metrics
                if self.agent_processor:
                    metrics = self.agent_processor.get_metrics()
                    if metrics['total_orders'] > 0:
                        logger.info(
                            f"🤖 Agent processing metrics",
                            agent_metrics=metrics
                        )
                        
                        # Log performance anomaly if processing is slow
                        if metrics['avg_processing_time_ms'] > 5000:  # 5 seconds threshold
                            event_logger.log_performance_anomaly(
                                metric_name="agent_processing_time",
                                current_value=metrics['avg_processing_time_ms'],
                                threshold=5000.0
                            )
                
                # Check for stream failures
                if active == 0:
                    event_logger.log_compliance_event(
                        compliance_type="pipeline_shutdown",
                        status="streams_inactive",
                        details={'reason': 'all_streams_stopped'}
                    )
                    break
                elif active < len(self.queries):
                    event_logger.log_performance_anomaly(
                        metric_name="active_streams",
                        current_value=active,
                        threshold=len(self.queries)
                    )
                    
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 Pipeline shutdown requested by user")
                event_logger.log_compliance_event(
                    compliance_type="pipeline_shutdown",
                    status="user_requested",
                    details={'trigger': 'keyboard_interrupt'}
                )
                break
            except Exception as e:
                logger.error(f"❌ Monitor error: {e}")
                event_logger.log_performance_anomaly(
                    metric_name="monitor_errors",
                    current_value=1,
                    threshold=0
                )
                time.sleep(10)
    
    def _stop_queries(self):
        """Stop all queries"""
        for name, query in self.queries.items():
            try:
                if query.isActive:
                    logger.info(f"Stopping {name}")
                    query.stop()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
    
    def _cleanup(self):
        """Cleanup"""
        self._stop_queries()
        if self.spark:
            self.spark.stop()
        logger.info("🛑 Pipeline stopped")
    
    def run_test_mode(self):
        """Simple test mode"""
        try:
            logger.info("🧪 Starting Simple Test")
            
            self.spark = self._create_spark_session()
            self.agent_processor = BatchAgentProcessor(spark_session=self.spark)
            
            # Test data
            test_data = [
                {"order_id": "test001", "user_id": "new_user", "total_amount": 150.0, 
                 "payment_method": "credit_card", "account_age_days": 2, 
                 "total_orders": 5, "avg_order_value": 30.0},
                {"order_id": "test002", "user_id": "regular_user", "total_amount": 45.0,
                 "payment_method": "pix", "account_age_days": 90,
                 "total_orders": 20, "avg_order_value": 40.0}
            ]
            
            test_df = self.spark.createDataFrame(test_data)
            
            logger.info("🔍 Processing test orders with agents...")
            self.agent_processor.process_batch(test_df, 0)
            
            metrics = self.agent_processor.get_metrics()
            logger.info(f"📊 Test metrics: {metrics}")
            
            logger.info("✅ Test completed")
            
        except Exception as e:
            logger.error(f"❌ Test error: {e}")
        finally:
            if self.spark:
                self.spark.stop()

def main():
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    app = FinalSimpleApp()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        app.run_test_mode()
    else:
        app.run_streaming()

if __name__ == "__main__":
    main()