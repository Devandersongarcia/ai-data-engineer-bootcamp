"""
Agentic Fraud Processor
Integrates CrewAI agents with Spark Streaming for real-time intelligent fraud detection
"""

import builtins
import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

from src.agents.crewai_with_prompts import PromptBasedCrewAISystem
from src.database.unified_postgres_writer import unified_postgres_writer
from src.utils.circuit_breaker import circuit_breaker_manager, CircuitBreakerError

logger = logging.getLogger(__name__)

@dataclass
class FraudAnalysisRequest:
    """Request for agent analysis"""
    order_id: str
    order_data: Dict[str, Any]
    spark_risk_score: float
    priority: str  # HIGH, MEDIUM, LOW
    timestamp: datetime

@dataclass 
class AgentAnalysisResult:
    """Result from agent analysis"""
    order_id: str
    agent_risk_score: float
    recommended_action: str
    confidence: float
    patterns_detected: List[str]
    reasoning: str
    processing_time_ms: int
    framework: str

class AgenticFraudProcessor:
    """Processes fraud cases using intelligent agent routing"""
    
    def __init__(self, spark: SparkSession, max_concurrent_agents: int = 3):
        """
        Initialize the agentic processor
        
        Args:
            spark: Spark session
            max_concurrent_agents: Maximum number of concurrent agent analyses
        """
        self.spark = spark
        self.max_concurrent_agents = max_concurrent_agents
        
        # Lazy initialization of CrewAI system (to prevent startup hang)
        logger.info("🤖 CrewAI Agent System will be initialized on first use...")
        self.crew_system = None
        self._crew_initialized = False
        
        # Thread pool for concurrent agent execution
        self.agent_executor = ThreadPoolExecutor(max_workers=max_concurrent_agents)
        
        # Request queue for batching (with size limit to prevent memory leaks)
        self.pending_requests = []
        self.max_pending_requests = 1000  # Prevent unbounded growth
        self.processing_lock = threading.Lock()
        
        # Metrics (with periodic cleanup to prevent memory leaks)
        self.metrics = {
            "total_processed": 0,
            "agent_analyses": 0,
            "high_priority_cases": 0,
            "blocked_orders": 0,
            "avg_processing_time": 0.0
        }
        
        # Initialize circuit breaker for agent processing with reduced timeout
        self.agent_circuit_breaker = circuit_breaker_manager.get_circuit_breaker(
            name="agent_processing",
            failure_threshold=3,  # Fail faster than before
            recovery_timeout=30.0,  # Shorter recovery time
            expected_exception=(Exception,),
            success_threshold=2  # Need fewer successes to recover
        )
        
        logger.info(f"✅ Agentic Fraud Processor initialized (max concurrent: {max_concurrent_agents})")
    
    def create_intelligent_triage_udf(self):
        """Create UDF for intelligent risk triage"""
        
        def intelligent_triage(
            order_id: str,
            spark_risk_score: float,
            total_amount: float,
            account_age_days: int,
            total_orders: int,
            payment_method: str
        ) -> str:
            """
            Determine if order needs agent analysis with NULL handling
            
            Returns: 'AGENT_ANALYSIS', 'AUTO_ALLOW', 'AUTO_BLOCK'
            """
            
            # Handle NULL values safely
            risk_score = float(spark_risk_score) if spark_risk_score is not None else 0.0
            amount = float(total_amount) if total_amount is not None else 0.0
            age_days = int(account_age_days) if account_age_days is not None else 365
            orders = int(total_orders) if total_orders is not None else 0
            payment = str(payment_method) if payment_method is not None else 'unknown'
            
            # Auto-block criteria (obvious fraud)
            if (risk_score >= 0.9 and age_days <= 1) or \
               (amount > 500 and age_days <= 3) or \
               (risk_score >= 0.95):
                return 'AUTO_BLOCK'
            
            # Auto-allow criteria (very low risk)
            if (risk_score <= 0.2 and age_days >= 90) or \
               (risk_score <= 0.3 and age_days >= 30 and orders >= 10):
                return 'AUTO_ALLOW'
            
            # Agent analysis criteria (suspicious cases)
            if (risk_score >= 0.5) or \
               (amount >= 200) or \
               (age_days <= 7) or \
               (payment in ['credit_card'] and risk_score >= 0.4):
                return 'AGENT_ANALYSIS'
            
            # Default: allow with monitoring
            return 'AUTO_ALLOW'
        
        return udf(intelligent_triage, StringType())
    
    def create_priority_scoring_udf(self):
        """Create UDF for priority scoring"""
        
        def calculate_priority(
            spark_risk_score: float,
            total_amount: float,
            account_age_days: int
        ) -> str:
            """Calculate processing priority with NULL handling"""
            
            # Handle NULL values safely
            risk_score = float(spark_risk_score) if spark_risk_score is not None else 0.0
            amount = float(total_amount) if total_amount is not None else 0.0
            age_days = int(account_age_days) if account_age_days is not None else 365
            
            # High priority: High risk or high value
            if (risk_score >= 0.8) or \
               (amount >= 300) or \
               (age_days <= 2 and risk_score >= 0.6):
                return 'HIGH'
            
            # Medium priority: Moderate risk
            elif (risk_score >= 0.6) or \
                 (amount >= 100) or \
                 (age_days <= 7):
                return 'MEDIUM'
            
            # Low priority: Everything else
            else:
                return 'LOW'
        
        return udf(calculate_priority, StringType())
    
    def add_intelligent_routing(self, fraud_results: DataFrame) -> DataFrame:
        """Add intelligent routing decisions to fraud results"""
        
        # Create UDFs
        triage_udf = self.create_intelligent_triage_udf()
        priority_udf = self.create_priority_scoring_udf()
        
        # Add routing decisions
        routed_df = fraud_results \
            .withColumn("triage_decision", 
                       triage_udf(
                           col("order_id"),
                           col("fraud_score"),
                           col("total_amount"),
                           col("account_age_days"),
                           col("total_orders"),
                           col("payment_method")
                       )) \
            .withColumn("priority_level",
                       priority_udf(
                           col("fraud_score"),
                           col("total_amount"),
                           col("account_age_days")
                       )) \
            .withColumn("requires_agent_analysis",
                       col("triage_decision") == lit("AGENT_ANALYSIS")) \
            .withColumn("routing_timestamp", current_timestamp())
        
        return routed_df
    
    def _ensure_crew_system_initialized(self):
        """Initialize CrewAI system if not already done (thread-safe)"""
        if not self._crew_initialized:
            with self.processing_lock:
                if not self._crew_initialized:  # Double-check locking
                    try:
                        logger.info("🤖 Initializing CrewAI system on first use...")
                        self.crew_system = PromptBasedCrewAISystem()
                        self._crew_initialized = True
                        logger.info("✅ CrewAI system initialized successfully!")
                    except Exception as e:
                        logger.error(f"❌ Failed to initialize CrewAI system: {e}", exc_info=True)
                        self.crew_system = None
                        self._crew_initialized = False
                        raise
    
    def process_agent_analysis_batch(self, batch_df: DataFrame, batch_id: int):
        """Process a batch of orders requiring agent analysis"""
        
        logger.info(f"🤖 AGENT BATCH PROCESSING CALLED - Batch {batch_id}")
        
        try:
            # Get all orders in this batch
            total_orders = batch_df.count()
            
            # Filter orders requiring agent analysis with explicit criteria
            agent_orders = batch_df.filter(
                (col("requires_agent_analysis") == True) & 
                (col("triage_decision") == "AGENT_ANALYSIS")
            ).collect()
            
            logger.info(f"🔍 Agent Batch {batch_id}: {total_orders} total orders, {len(agent_orders)} need agent analysis")
            
            if not agent_orders:
                logger.debug(f"Batch {batch_id}: No orders require agent analysis")
                return
            
            logger.info(f"🤖 Batch {batch_id}: Processing {len(agent_orders)} orders with agents")
            
            # Create analysis requests
            requests = []
            for row in agent_orders:
                # Helper function to safely get row values
                def safe_get(row, field, default):
                    try:
                        return row[field] if row[field] is not None else default
                    except (KeyError, IndexError):
                        return default
                
                order_data = {
                    "order_id": row["order_id"],
                    "user_id": safe_get(row, "user_id", "unknown"),
                    "total_amount": safe_get(row, "total_amount", 0.0),
                    "payment_method": safe_get(row, "payment_method", "unknown"),
                    "account_age_days": safe_get(row, "account_age_days", 30),
                    "orders_today": safe_get(row, "total_orders", 1),
                    "orders_last_hour": builtins.max(1, safe_get(row, "total_orders", 1) // 4),
                    "avg_order_value": safe_get(row, "avg_order_value", 35.0),
                    "payment_failures_today": 0 if safe_get(row, "fraud_score", 0.5) < 0.5 else 2,
                    "behavior_change_score": builtins.min(safe_get(row, "fraud_score", 0.5), 0.8),
                    "new_payment_method": safe_get(row, "account_age_days", 30) <= 7,
                    "address_change_flag": False
                }
                
                request = FraudAnalysisRequest(
                    order_id=row["order_id"],
                    order_data=order_data,
                    spark_risk_score=row["fraud_score"],
                    priority=row["priority_level"],
                    timestamp=datetime.now()
                )
                requests.append(request)
            
            # Process requests concurrently by priority with batch limits
            high_priority = [r for r in requests if r.priority == 'HIGH']
            medium_priority = [r for r in requests if r.priority == 'MEDIUM']
            low_priority = [r for r in requests if r.priority == 'LOW']
            
            # Process high priority first, then others with batch size limits
            all_results = []
            max_batch_size = 5  # Limit concurrent processing to 5 agents max
            
            for priority_batch in [high_priority, medium_priority, low_priority]:
                if priority_batch:
                    # Process in smaller batches to avoid timeout
                    for i in range(0, len(priority_batch), max_batch_size):
                        batch_slice = priority_batch[i:i + max_batch_size]
                        logger.info(f"Processing {len(batch_slice)} agents in batch slice")
                        batch_results = self._process_concurrent_requests(batch_slice)
                        all_results.extend(batch_results)
            
            # Update metrics with memory management
            self.metrics["total_processed"] += len(agent_orders)
            self.metrics["agent_analyses"] += len(all_results)
            self.metrics["high_priority_cases"] += len(high_priority)
            
            # Manage pending_requests size to prevent memory leaks
            if len(self.pending_requests) > self.max_pending_requests:
                # Keep only the most recent half
                self.pending_requests = self.pending_requests[-500:]
                logger.warning(f"Trimmed pending_requests to prevent memory leak (kept last 500)")
            
            # Save results to PostgreSQL and log
            agent_results_for_db = []
            for result in all_results:
                logger.info(f"🎯 Agent Analysis - Order: {result.order_id}, "
                           f"Risk: {result.agent_risk_score:.3f}, "
                           f"Action: {result.recommended_action}, "
                           f"Time: {result.processing_time_ms}ms")
                
                if result.recommended_action == "BLOCK":
                    self.metrics["blocked_orders"] += 1
                
                # Prepare agent result for database
                agent_result_dict = {
                    "fraud_score": result.agent_risk_score,
                    "recommended_action": result.recommended_action,
                    "confidence": result.confidence,
                    "patterns_detected": result.patterns_detected,
                    "reasoning": result.reasoning,
                    "processing_time_ms": result.processing_time_ms,
                    "framework": result.framework,
                    "success": True
                }
                agent_results_for_db.append((result.order_id, agent_result_dict))
            
            # Save agent results to PostgreSQL using unified writer
            if agent_results_for_db:
                try:
                    saved_count = unified_postgres_writer.write_agent_analysis_batch(agent_results_for_db)
                    logger.info(f"💾 Saved {saved_count} agent results to PostgreSQL")
                except Exception as e:
                    logger.error(f"❌ Failed to save agent results to PostgreSQL: {e}")
            
            # Calculate average processing time  
            if all_results:
                processing_times = [r.processing_time_ms for r in all_results]
                avg_time = builtins.sum(processing_times) / len(processing_times) if processing_times else 0
                self.metrics["avg_processing_time"] = avg_time
                
                logger.info(f"📊 Batch {batch_id} Summary: "
                           f"{len(all_results)} analyzed, "
                           f"avg time: {avg_time:.1f}ms")
            
        except Exception as e:
            logger.error(f"❌ Error processing agent batch {batch_id}: {e}", exc_info=True)
    
    def _process_concurrent_requests(self, requests: List[FraudAnalysisRequest]) -> List[AgentAnalysisResult]:
        """Process multiple requests concurrently"""
        
        if not requests:
            return []
        
        results = []
        
        # Submit all requests to thread pool
        future_to_request = {
            self.agent_executor.submit(self._analyze_single_order, request): request
            for request in requests
        }
        
        # Collect results as they complete (reduced timeout for real-time processing)
        for future in as_completed(future_to_request, timeout=30):
            request = future_to_request[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"❌ Agent analysis failed for {request.order_id}: {e}")
                # Create fallback result
                fallback_result = AgentAnalysisResult(
                    order_id=request.order_id,
                    agent_risk_score=request.spark_risk_score,
                    recommended_action="MONITOR",
                    confidence=0.5,
                    patterns_detected=[],
                    reasoning=f"Agent analysis failed: {str(e)}",
                    processing_time_ms=0,
                    framework="fallback"
                )
                results.append(fallback_result)
        
        return results
    
    def _analyze_single_order(self, request: FraudAnalysisRequest) -> AgentAnalysisResult:
        """Analyze a single order using CrewAI agents with circuit breaker protection"""
        
        start_time = time.time()
        
        try:
            # Use circuit breaker to protect against agent failures
            agent_result = self.agent_circuit_breaker.call(
                self._protected_agent_analysis, 
                request.order_data
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Convert to our result format
            result = AgentAnalysisResult(
                order_id=request.order_id,
                agent_risk_score=agent_result.get("fraud_score", request.spark_risk_score),
                recommended_action=agent_result.get("recommended_action", "MONITOR"),
                confidence=agent_result.get("confidence", 0.6),
                patterns_detected=agent_result.get("patterns_detected", []),
                reasoning=agent_result.get("reasoning", "")[:200],  # Truncate for logging
                processing_time_ms=processing_time,
                framework=agent_result.get("framework", "crewai_with_prompts")
            )
            
            return result
            
        except CircuitBreakerError as e:
            logger.warning(f"⚡ Circuit breaker open for {request.order_id}: {e}")
            return self._create_fallback_result(request, "Circuit breaker open")
            
        except Exception as e:
            logger.error(f"❌ Agent analysis failed for {request.order_id}: {e}")
            
            # Return fallback based on Spark score
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentAnalysisResult(
                order_id=request.order_id,
                agent_risk_score=request.spark_risk_score,
                recommended_action="FLAG" if request.spark_risk_score > 0.7 else "MONITOR",
                confidence=0.5,
                patterns_detected=["spark_based_scoring"],
                reasoning=f"Agent analysis failed, using Spark score: {request.spark_risk_score:.3f}",
                processing_time_ms=processing_time,
                framework="spark_fallback"
            )
    
    def _protected_agent_analysis(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Protected agent analysis method for circuit breaker use"""
        # Ensure CrewAI system is initialized
        self._ensure_crew_system_initialized()
        
        # Run agent analysis - this is the actual call that can fail
        return self.crew_system.analyze_order(order_data)
    
    def _create_fallback_result(self, request: FraudAnalysisRequest, reason: str = "Circuit breaker open") -> AgentAnalysisResult:
        """Create fallback result when circuit breaker is open"""
        return AgentAnalysisResult(
            order_id=request.order_id,
            agent_risk_score=request.spark_risk_score,
            recommended_action="MONITOR" if request.spark_risk_score < 0.7 else "FLAG",
            confidence=0.3,  # Lower confidence for fallback
            patterns_detected=["circuit_breaker_fallback"],
            reasoning=f"{reason} - using Spark-based fallback",
            processing_time_ms=10,  # Minimal processing time for fallback
            framework="circuit_breaker_fallback"
        )
    
    def create_agent_analysis_sink(self, agent_orders_df: DataFrame) -> Any:
        """Create a streaming sink for agent analysis"""
        
        logger.info("🤖 Setting up agent analysis sink with filters:")
        logger.info("   - requires_agent_analysis = True")
        logger.info("   - triage_decision = AGENT_ANALYSIS")
        
        # Filter for orders requiring agent analysis with explicit conditions
        agent_filtered_df = agent_orders_df.filter(
            (col("requires_agent_analysis") == True) & 
            (col("triage_decision") == "AGENT_ANALYSIS")
        )
        
        logger.info("🤖 Agent analysis sink filter applied - starting stream...")
        
        return agent_filtered_df \
            .writeStream \
            .outputMode("append") \
            .foreachBatch(self.process_agent_analysis_batch) \
            .option("checkpointLocation", "/tmp/spark-streaming/checkpoint-agent-analysis-fresh-v2") \
            .trigger(processingTime="10 seconds") \
            .start()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics"""
        return {
            **self.metrics,
            "timestamp": datetime.now().isoformat(),
            "agent_system_status": "operational" if self.crew_system else "error"
        }
    
    def shutdown(self):
        """Gracefully shutdown the processor with proper cleanup"""
        logger.info("🛑 Shutting down Agentic Fraud Processor...")
        
        # Shutdown thread pool (compatible with all Python versions)
        self.agent_executor.shutdown(wait=True)
        
        # Clean up memory to prevent leaks
        with self.processing_lock:
            self.pending_requests.clear()
            self.metrics.clear()
            logger.info("💾 Cleared pending requests and metrics")
        
        logger.info("✅ Agentic Fraud Processor shutdown complete")

# Integration Schema for results
AGENT_RESULT_SCHEMA = StructType([
    StructField("order_id", StringType(), False),
    StructField("agent_risk_score", DoubleType(), False),
    StructField("recommended_action", StringType(), False),
    StructField("confidence", DoubleType(), False),
    StructField("patterns_detected", ArrayType(StringType()), False),
    StructField("reasoning", StringType(), False),
    StructField("processing_time_ms", IntegerType(), False),
    StructField("framework", StringType(), False),
    StructField("analysis_timestamp", TimestampType(), False)
])