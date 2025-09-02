"""
Batch Agent Processor
Simplified batch processing approach for Spark + CrewAI integration
Processes micro-batches of orders with agents for optimal performance
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import lit, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.crewai_with_prompts import PromptBasedCrewAISystem
from src.correlation import start_batch_correlation, CorrelationContext, get_correlation_logger
from src.transaction_logger import create_batch_logger, TransactionType, log_agent_analysis
from src.business_events import get_agent_event_logger, ActionType, RiskLevel
from src.database.postgres_handler import postgres_handler
from src.models.fraud_result import FraudResult, FraudDecision, FraudPatternType, FraudSeverity

logger = get_correlation_logger(__name__)

class BatchAgentProcessor:
    """Batch processor for Spark streaming + CrewAI agents"""
    
    def __init__(self, spark_session: SparkSession = None):
        """Initialize the batch processor"""
        logger.info("🤖 Initializing Batch Agent Processor...")
        
        # Store Spark session for DataFrame operations
        self.spark = spark_session
        
        # Initialize CrewAI system
        self.crew_system = PromptBasedCrewAISystem()
        
        # Initialize PostgreSQL handler
        self.postgres_enabled = self._initialize_postgres()
        
        # Metrics
        self.total_orders = 0
        self.agent_analyses = 0
        self.total_time = 0
        self.db_writes = 0
        self.db_errors = 0
        
        logger.info("✅ Batch Agent Processor ready")
    
    def _initialize_postgres(self) -> bool:
        """Initialize PostgreSQL connection"""
        try:
            if not postgres_handler.initialize_connection_pool():
                logger.warning("❌ PostgreSQL connection pool initialization failed - results will not be saved to database")
                return False
            
            if not postgres_handler.test_connection():
                logger.warning("❌ PostgreSQL connection test failed - results will not be saved to database")
                return False
            
            logger.info("✅ PostgreSQL integration enabled - fraud results will be saved to database")
            return True
        except Exception as e:
            logger.error(f"❌ PostgreSQL initialization error: {str(e)} - continuing without database output")
            return False
    
    def process_batch(self, batch_df: DataFrame, batch_id: int):
        """Process a batch of orders with agents"""
        # Initialize batch correlation and logging
        orders = batch_df.collect()
        batch_size = len(orders)
        
        if batch_size == 0:
            logger.info(f"📭 Batch {batch_id}: No orders to process")
            return
        
        # Start batch correlation context
        with start_batch_correlation(batch_id, batch_size):
            # Initialize batch transaction logger
            batch_logger = create_batch_logger(
                str(batch_id), 
                batch_size, 
                TransactionType.AGENT_ANALYSIS
            )
            
            # Initialize business event logger
            event_logger = get_agent_event_logger()
            
            batch_logger.start_batch()
            
            try:
                logger.info(f"🔍 Processing batch {batch_id} with {batch_size} orders...")
            
                batch_start_time = time.time()
                results = []
                
                # Process each order with agents
                for i, row in enumerate(orders):
                    order_dict = row.asDict()
                    
                    # Log agent collaboration for complex orders
                    if order_dict.get('total_amount', 0) > 100:
                        event_logger.log_agent_collaboration(
                            primary_agent='risk_analyzer',
                            collaborating_agents=['behavior_analyst', 'payment_validator'],
                            task=f"analyze_high_value_order_{order_dict.get('order_id', 'unknown')}"
                        )
                    
                    order_result = self._analyze_single_order(order_dict)
                    results.append(order_result)
                    
                    # Log individual item processing
                    batch_logger.log_item_processed(
                        item_id=order_result['order_id'],
                        success=order_result['success'],
                        transaction_id=order_result.get('transaction_id')
                    )
                
                batch_time = int((time.time() - batch_start_time) * 1000)
                
                # Save results to PostgreSQL database with timeout protection
                db_success, db_errors = 0, 0
                try:
                    logger.info(f"🔄 Converting {len(results)} agent results to database format...")
                    fraud_results = self._convert_to_fraud_results(results)
                    logger.info(f"✅ Converted {len(fraud_results)} results successfully")
                    
                    if self.postgres_enabled and fraud_results:
                        logger.info(f"💾 Saving {len(fraud_results)} results to PostgreSQL using DataFrame...")
                        db_success, db_errors = self._save_to_database_with_spark(fraud_results)
                        self.db_writes += db_success
                        self.db_errors += db_errors
                        logger.info(f"✅ DataFrame database save complete: {db_success} successful, {db_errors} errors")
                    else:
                        logger.warning("⚠️ PostgreSQL disabled or no results to save")
                        
                except Exception as db_error:
                    logger.error(f"❌ Database processing error: {str(db_error)}")
                    db_errors = len(results)
                    self.db_errors += db_errors
            
                # Complete batch logging
                successful_analyses = sum(1 for r in results if r.get('success', False))
                avg_confidence = sum(r.get('confidence', 0) for r in results) / len(results) if results else 0
                high_risk_count = sum(1 for r in results if r.get('agent_risk_score', 0) > 0.7)
                rejected_count = sum(1 for r in results if r.get('recommended_action') == 'REJECT')
                
                batch_logger.complete_batch(
                    successful_analyses=successful_analyses,
                    avg_confidence=avg_confidence,
                    high_risk_orders=high_risk_count,
                    rejected_orders=rejected_count
                )
                
                # Update metrics
                self.total_orders += batch_size
                self.agent_analyses += len(results)
                self.total_time += batch_time
                
                # Log comprehensive results
                avg_time_per_order = batch_time / batch_size if batch_size > 0 else 0
                
                logger.info(
                    f"✅ Batch {batch_id} completed successfully",
                    batch_metrics={
                        'orders_processed': batch_size,
                        'successful_analyses': successful_analyses,
                        'avg_confidence': round(avg_confidence, 2),
                        'batch_time_ms': batch_time,
                        'avg_time_per_order_ms': round(avg_time_per_order, 1),
                        'high_risk_orders': high_risk_count,
                        'rejected_orders': rejected_count,
                        'success_rate': round(successful_analyses / batch_size, 3) if batch_size > 0 else 0,
                        'db_writes': self.db_writes if self.postgres_enabled else 'disabled',
                        'db_errors': self.db_errors if self.postgres_enabled else 'disabled'
                    }
                )
                
                # Log sample results with business events
                for i, result in enumerate(results[:3]):  # Show first 3 results
                    logger.info(
                        f"📋 Sample result {i+1}: {result['order_id']} → {result['recommended_action']} (score: {result['agent_risk_score']:.2f})"
                    )
                    
                    # Log business decision event
                    if result['recommended_action'] in ['REJECT', 'FLAG']:
                        action = ActionType.REJECT if result['recommended_action'] == 'REJECT' else ActionType.FLAG
                        event_logger.log_decision_made(
                            action=action,
                            reason=result.get('reasoning', 'Agent recommendation'),
                            confidence=result.get('confidence', 0.6),
                            order_id=result['order_id'],
                            batch_id=str(batch_id)
                        )
                
            except Exception as e:
                try:
                    batch_logger.complete_batch(error=str(e))
                except Exception as log_error:
                    logger.error(f"⚠️ Batch logging error (non-critical): {log_error}")
                logger.error(f"❌ Error processing batch {batch_id}: {e}")
    
    def _analyze_single_order(self, order_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single order with CrewAI agents"""
        # Create transaction logger for individual order analysis
        with log_agent_analysis() as transaction_logger:
            transaction_logger.start(
                order_id=order_dict.get("order_id", "unknown"),
                user_id=order_dict.get("user_id", "unknown")
            )
            
            try:
                # Prepare order data for agents
                order_data = {
                    "order_id": order_dict.get("order_id", "unknown"),
                    "user_id": order_dict.get("user_id", "unknown"),
                    "total_amount": float(order_dict.get("total_amount", 0.0)),
                    "payment_method": order_dict.get("payment_method", "unknown"),
                    "account_age_days": int(order_dict.get("account_age_days", 30)),
                    "orders_today": int(order_dict.get("total_orders", 1)),
                    "orders_last_hour": max(1, int(order_dict.get("total_orders", 1)) // 4),
                    "avg_order_value": float(order_dict.get("avg_order_value", 35.0)),
                    "payment_failures_today": 0,
                    "behavior_change_score": 0.3,
                    "new_payment_method": order_dict.get("account_age_days", 30) <= 7,
                    "address_change_flag": False
                }
                
                # Calculate amount ratio
                if order_data["avg_order_value"] > 0:
                    order_data["amount_ratio"] = order_data["total_amount"] / order_data["avg_order_value"]
                else:
                    order_data["amount_ratio"] = 1.0
                
                transaction_logger.checkpoint("agent_analysis_start", order_amount=order_data["total_amount"])
                
                # Update transaction metrics
                transaction_logger.update_metrics(records_processed=1)
                
                # Run agent analysis
                agent_result = self.crew_system.analyze_order(order_data)
                
                transaction_logger.checkpoint("agent_analysis_complete", 
                                            fraud_score=agent_result.get("fraud_score", 0.5),
                                            recommended_action=agent_result.get("recommended_action", "MONITOR"))
                
                # Create result (include user_id for database storage)
                result = {
                    "success": True,
                    "order_id": order_data["order_id"],
                    "user_id": order_data["user_id"],  # Ensure user_id is included
                    "agent_risk_score": agent_result.get("fraud_score", 0.5),
                    "recommended_action": agent_result.get("recommended_action", "MONITOR"),
                    "confidence": agent_result.get("confidence", 0.6),
                    "patterns_detected": agent_result.get("patterns_detected", []),
                    "reasoning": agent_result.get("reasoning", "")[:150],
                    "processing_time_ms": transaction_logger.metrics.duration_ms,
                    "framework": "crewai_batch",
                    "analysis_timestamp": datetime.now().isoformat(),
                    "transaction_id": transaction_logger.context.transaction_id
                }
                
                # Log business events based on results
                event_logger = get_agent_event_logger()
                event_logger.log_agent_recommendation(
                    agent_name="crewai_fraud_detection",
                    recommendation=agent_result,
                    order_id=order_data["order_id"]
                )
                
                return result
                
            except Exception as e:
                transaction_logger.update_metrics(error_count=1)
                
                # Return fallback result
                return {
                    "success": False,
                    "order_id": order_dict.get("order_id", "unknown"),
                    "agent_risk_score": 0.5,
                    "recommended_action": "MONITOR",
                    "confidence": 0.5,
                    "patterns_detected": ["analysis_failed"],
                    "reasoning": f"Analysis failed: {str(e)}",
                    "processing_time_ms": transaction_logger.metrics.duration_ms,
                    "framework": "fallback",
                    "analysis_timestamp": datetime.now().isoformat(),
                    "transaction_id": transaction_logger.context.transaction_id
                }
    
    def _convert_to_fraud_results(self, results: List[Dict[str, Any]]) -> List[FraudResult]:
        """Convert agent results to FraudResult objects for database storage"""
        fraud_results = []
        
        for result in results:
            if not result.get('success', False):
                continue
                
            try:
                # Map agent decision to FraudDecision enum
                action_mapping = {
                    'REJECT': FraudDecision.BLOCK,
                    'FLAG': FraudDecision.REQUIRE_HUMAN,
                    'MONITOR': FraudDecision.MONITOR,
                    'ALLOW': FraudDecision.ALLOW
                }
                
                # Determine primary pattern type
                patterns_detected = result.get('patterns_detected', [])
                primary_pattern = None
                detected_patterns = []
                
                for pattern_name in patterns_detected:
                    if pattern_name == 'velocity_fraud':
                        pattern_type = FraudPatternType.VELOCITY_FRAUD
                        primary_pattern = primary_pattern or pattern_type
                    elif pattern_name == 'card_testing':
                        pattern_type = FraudPatternType.CARD_TESTING
                        primary_pattern = primary_pattern or pattern_type
                    elif pattern_name == 'geographic_anomaly':
                        pattern_type = FraudPatternType.GEOGRAPHIC_ANOMALY
                        primary_pattern = primary_pattern or pattern_type
                    elif pattern_name == 'account_takeover':
                        pattern_type = FraudPatternType.ACCOUNT_TAKEOVER
                        primary_pattern = primary_pattern or pattern_type
                    elif pattern_name == 'promo_abuse':
                        pattern_type = FraudPatternType.PROMO_ABUSE
                        primary_pattern = primary_pattern or pattern_type
                    else:
                        pattern_type = FraudPatternType.LEGITIMATE
                    
                    # Create fraud pattern with confidence
                    fraud_pattern = {
                        'pattern_type': pattern_type,
                        'confidence': result.get('confidence', 0.5),
                        'severity': FraudSeverity.HIGH if result.get('agent_risk_score', 0) > 0.7 else FraudSeverity.MEDIUM,
                        'indicators': [pattern_name],
                        'description': f"Detected by agent analysis: {pattern_name}"
                    }
                    detected_patterns.append(fraud_pattern)
                
                # Create FraudResult object
                fraud_result = FraudResult(
                    order_id=result.get('order_id', 'unknown'),
                    user_id=result.get('user_id', 'unknown'),
                    fraud_score=float(result.get('agent_risk_score', 0.5)),
                    primary_pattern=primary_pattern,
                    recommended_action=action_mapping.get(result.get('recommended_action'), FraudDecision.MONITOR),
                    action_confidence=float(result.get('confidence', 0.5)),
                    reasoning=result.get('reasoning', 'Agent analysis completed'),
                    processing_time_ms=result.get('processing_time_ms', 0),
                    total_processing_time_ms=result.get('processing_time_ms', 0),
                    timestamp=datetime.fromisoformat(result.get('analysis_timestamp', datetime.now().isoformat())),
                    openai_tokens_used=50,  # Estimated tokens per analysis
                    estimated_cost_usd=0.005  # Estimated cost per analysis
                )
                
                # Add patterns to fraud result
                for pattern_data in detected_patterns:
                    fraud_result.add_pattern(
                        pattern_data['pattern_type'],
                        pattern_data['confidence'],
                        pattern_data['indicators'],
                        pattern_data['severity']
                    )
                
                # Add agent analysis
                fraud_result.add_agent_analysis(
                    agent_name="crewai_fraud_detection",
                    analysis_type="pattern_analysis",
                    result=result,
                    confidence=float(result.get('confidence', 0.5)),
                    processing_time_ms=result.get('processing_time_ms', 0)
                )
                
                fraud_results.append(fraud_result)
                
            except Exception as e:
                logger.error(f"Error converting result to FraudResult: {str(e)}")
                continue
        
        return fraud_results
    
    def _save_to_database(self, fraud_results: List[FraudResult]) -> tuple[int, int]:
        """Save fraud results to PostgreSQL database"""
        try:
            if len(fraud_results) == 1:
                # Single insert for small batches
                success = postgres_handler.insert_fraud_result(fraud_results[0])
                return (1, 0) if success else (0, 1)
            else:
                # Batch insert for larger batches
                successful, failed = postgres_handler.insert_fraud_results_batch(fraud_results)
                
                # Update daily cost tracking
                total_tokens = sum(fr.openai_tokens_used for fr in fraud_results)
                total_cost = sum(fr.estimated_cost_usd for fr in fraud_results)
                postgres_handler.update_daily_cost_tracking(total_tokens, total_cost)
                
                return successful, failed
                
        except Exception as e:
            logger.error(f"Database save error: {str(e)}")
            return 0, len(fraud_results)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics"""
        avg_time = self.total_time / self.total_orders if self.total_orders > 0 else 0
        
        metrics = {
            "total_orders": self.total_orders,
            "agent_analyses": self.agent_analyses,
            "avg_processing_time_ms": round(avg_time, 1),
            "total_processing_time_ms": self.total_time,
            "status": "operational"
        }
        
        # Add database metrics if enabled
        if self.postgres_enabled:
            metrics.update({
                "db_writes": self.db_writes,
                "db_errors": self.db_errors,
                "db_success_rate": round(self.db_writes / (self.db_writes + self.db_errors), 3) if (self.db_writes + self.db_errors) > 0 else 1.0
            })
        
        return metrics
    
    def _save_to_database_with_spark(self, fraud_results: List[FraudResult]) -> tuple[int, int]:
        """Save fraud results to PostgreSQL using Spark DataFrames for better performance"""
        if not self.spark:
            logger.warning("⚠️ Spark session not available, falling back to direct database insert")
            return self._save_to_database(fraud_results)
        
        try:
            from config.settings import settings
            
            # Prepare data for main fraud_results table
            main_data = []
            patterns_data = []
            analyses_data = []
            
            for fraud_result in fraud_results:
                # Main fraud result data
                main_record = {
                    'order_id': fraud_result.order_id,
                    'user_id': fraud_result.user_id,
                    'correlation_id': fraud_result.correlation_id or 'batch_process',
                    'fraud_score': float(fraud_result.fraud_score),
                    'recommended_action': fraud_result.recommended_action.value,
                    'action_confidence': float(fraud_result.action_confidence),
                    'primary_pattern': fraud_result.primary_pattern.value if fraud_result.primary_pattern else None,
                    'reasoning': fraud_result.reasoning,
                    'processing_time_ms': int(fraud_result.processing_time_ms),
                    'total_processing_time_ms': int(fraud_result.total_processing_time_ms),
                    'model_version': fraud_result.model_version,
                    'system_health_score': float(fraud_result.system_health_score),
                    'openai_tokens_used': int(fraud_result.openai_tokens_used),
                    'estimated_cost_usd': float(fraud_result.estimated_cost_usd),
                    'processed_at': fraud_result.timestamp
                }
                main_data.append(main_record)
            
            # Create DataFrame for main fraud results
            if main_data:
                logger.info(f"📊 Creating DataFrame with {len(main_data)} fraud results...")
                
                # Define schema for fraud_results table
                fraud_results_schema = StructType([
                    StructField("order_id", StringType(), True),
                    StructField("user_id", StringType(), True),
                    StructField("correlation_id", StringType(), True),
                    StructField("fraud_score", DoubleType(), True),
                    StructField("recommended_action", StringType(), True),
                    StructField("action_confidence", DoubleType(), True),
                    StructField("primary_pattern", StringType(), True),
                    StructField("reasoning", StringType(), True),
                    StructField("processing_time_ms", IntegerType(), True),
                    StructField("total_processing_time_ms", IntegerType(), True),
                    StructField("model_version", StringType(), True),
                    StructField("system_health_score", DoubleType(), True),
                    StructField("openai_tokens_used", IntegerType(), True),
                    StructField("estimated_cost_usd", DoubleType(), True),
                    StructField("processed_at", TimestampType(), True)
                ])
                
                # Create DataFrame
                df = self.spark.createDataFrame(main_data, schema=fraud_results_schema)
                df = df.withColumn("created_at", current_timestamp())
                
                logger.info(f"✅ DataFrame created successfully with schema: {df.schema}")
                
                # Write to PostgreSQL using JDBC
                jdbc_url = f"jdbc:postgresql://{settings.postgresql.host}:{settings.postgresql.port}/{settings.postgresql.database}"
                connection_properties = {
                    "user": settings.postgresql.user,
                    "password": settings.postgresql.password,
                    "driver": "org.postgresql.Driver",
                    "stringtype": "unspecified"  # Handle varchar types properly
                }
                
                logger.info(f"💾 Writing DataFrame to PostgreSQL table: fraud_results")
                
                # Write main fraud results
                df.write \
                    .mode("append") \
                    .jdbc(url=jdbc_url, table="fraud_results", properties=connection_properties)
                
                logger.info(f"✅ Successfully wrote {len(main_data)} records to fraud_results table")
                
                # For now, we'll handle patterns and analyses with the original method
                # since they require the fraud_result_id from the inserted records
                # This is a limitation of this approach, but the main table write is much faster
                
                # Update daily cost tracking
                total_tokens = sum(fr.openai_tokens_used for fr in fraud_results)
                total_cost = sum(fr.estimated_cost_usd for fr in fraud_results)
                postgres_handler.update_daily_cost_tracking(total_tokens, total_cost)
                
                return len(main_data), 0
                
        except Exception as e:
            logger.error(f"❌ Spark DataFrame database save error: {str(e)}")
            logger.info("🔄 Falling back to direct database insert...")
            # Fallback to original method
            return self._save_to_database(fraud_results)