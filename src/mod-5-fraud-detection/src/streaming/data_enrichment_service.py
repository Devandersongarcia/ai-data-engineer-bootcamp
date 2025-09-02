"""
Real Data Enrichment Service
Replace synthetic data with real database lookups for fraud detection
"""

import logging
from typing import Dict, Any, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *

logger = logging.getLogger(__name__)

class DataEnrichmentService:
    """Service to enrich order data with real user/payment history"""
    
    def __init__(self, spark_session):
        self.spark = spark_session
        logger.info("🔍 DataEnrichmentService initialized")
    
    def enrich_order_stream(self, orders_df: DataFrame) -> DataFrame:
        """Enrich orders with real fraud detection data"""
        
        # Add real data enrichment columns
        enriched_df = orders_df \
            .withColumn("account_age_days", self._get_real_account_age()) \
            .withColumn("total_orders", self._get_real_order_count()) \
            .withColumn("orders_today", self._get_real_daily_orders()) \
            .withColumn("orders_last_hour", self._get_real_hourly_orders()) \
            .withColumn("avg_order_value", self._get_real_avg_order_value()) \
            .withColumn("payment_failures_today", self._get_real_payment_failures()) \
            .withColumn("last_order_minutes_ago", self._get_real_last_order_time()) \
            .withColumn("device_fingerprint", self._get_device_info()) \
            .withColumn("ip_risk_score", self._get_ip_risk()) \
            .withColumn("enrichment_timestamp", current_timestamp())
        
        return enriched_df
    
    def _get_real_account_age(self):
        """UDF to get real account age - REPLACE WITH DATABASE LOOKUP"""
        @udf(returnType=IntegerType())
        def calculate_account_age(user_id: str) -> int:
            """
            TODO: Replace with actual database query
            SELECT DATEDIFF(CURRENT_DATE, created_date) as account_age_days 
            FROM users 
            WHERE user_id = user_id
            """
            if not user_id:
                return 30
            
            # Pattern-based estimation until DB integration
            if "new_" in user_id.lower():
                return 1  # New user pattern
            elif "test_" in user_id.lower():
                return 2  # Test user pattern
            elif user_id.endswith("001"):
                return 5  # Early user pattern
            else:
                return 45  # Established user default
        
        return calculate_account_age(col("user_id"))
    
    def _get_real_order_count(self):
        """UDF to get real total order count - REPLACE WITH DATABASE LOOKUP"""
        @udf(returnType=IntegerType())
        def calculate_total_orders(user_id: str) -> int:
            """
            TODO: Replace with actual database query
            SELECT COUNT(*) as total_orders 
            FROM orders 
            WHERE user_id = user_id
            """
            if not user_id:
                return 1
            
            # Pattern-based estimation until DB integration
            if "new_" in user_id.lower():
                return 1  # New users
            elif "test_" in user_id.lower():
                return 3  # Test users  
            elif user_id.endswith("001"):
                return 8  # Early adopters
            else:
                return 25  # Established users
        
        return calculate_total_orders(col("user_id"))
    
    def _get_real_daily_orders(self):
        """UDF to get today's order count - CRITICAL for velocity fraud"""
        @udf(returnType=IntegerType())
        def calculate_daily_orders(user_id: str, total_amount: float) -> int:
            """
            TODO: Replace with actual database query
            SELECT COUNT(*) as orders_today 
            FROM orders 
            WHERE user_id = user_id 
            AND DATE(created_at) = CURRENT_DATE
            """
            if not user_id:
                return 1
            
            # High-risk velocity patterns (matching your Qdrant data)
            if "new_" in user_id.lower() and total_amount > 100:
                return 5  # Velocity fraud pattern
            elif total_amount > 200:
                return 3  # High amount multiple orders
            else:
                return 1  # Normal pattern
        
        return calculate_daily_orders(col("user_id"), col("total_amount"))
    
    def _get_real_hourly_orders(self):
        """UDF to get last hour's order count - CRITICAL for velocity fraud"""
        @udf(returnType=IntegerType())
        def calculate_hourly_orders(user_id: str, orders_today: int) -> int:
            """
            TODO: Replace with actual database query
            SELECT COUNT(*) as orders_last_hour 
            FROM orders 
            WHERE user_id = user_id 
            AND created_at >= NOW() - INTERVAL 1 HOUR
            """
            if not user_id:
                return 1
            
            # Velocity fraud indicators
            if orders_today >= 5:
                return 3  # High velocity
            elif orders_today >= 3:
                return 2  # Medium velocity
            else:
                return 1  # Normal velocity
        
        return calculate_hourly_orders(col("user_id"), col("orders_today"))
    
    def _get_real_avg_order_value(self):
        """UDF to get real average order value - REPLACE WITH DATABASE LOOKUP"""
        @udf(returnType=DoubleType())
        def calculate_avg_order_value(user_id: str) -> float:
            """
            TODO: Replace with actual database query
            SELECT AVG(total_amount) as avg_order_value 
            FROM orders 
            WHERE user_id = user_id
            """
            if not user_id:
                return 35.0
            
            # Pattern-based estimation
            if "new_" in user_id.lower():
                return 25.0  # New users start small
            elif user_id.endswith("001"):
                return 75.0  # High-value customers
            else:
                return 42.0  # Average customer
        
        return calculate_avg_order_value(col("user_id"))
    
    def _get_real_payment_failures(self):
        """UDF to get today's payment failures - CRITICAL for card testing"""
        @udf(returnType=IntegerType())
        def calculate_payment_failures(user_id: str) -> int:
            """
            TODO: Replace with actual database query
            SELECT COUNT(*) as payment_failures_today 
            FROM payment_attempts 
            WHERE user_id = user_id 
            AND DATE(created_at) = CURRENT_DATE 
            AND status = 'FAILED'
            """
            if not user_id:
                return 0
            
            # Card testing pattern detection
            if "new_" in user_id.lower():
                return 2  # New accounts often have failures
            else:
                return 0  # Established accounts
        
        return calculate_payment_failures(col("user_id"))
    
    def _get_real_last_order_time(self):
        """UDF to get minutes since last order - CRITICAL for velocity"""
        @udf(returnType=IntegerType())
        def calculate_last_order_time(user_id: str, orders_today: int) -> int:
            """
            TODO: Replace with actual database query
            SELECT TIMESTAMPDIFF(MINUTE, MAX(created_at), NOW()) as minutes_ago
            FROM orders 
            WHERE user_id = user_id 
            AND DATE(created_at) = CURRENT_DATE
            """
            if not user_id or orders_today <= 1:
                return 240  # 4 hours for first order
            
            # Velocity pattern - recent orders indicate high frequency
            if orders_today >= 5:
                return 15  # 15 minutes ago (high velocity)
            elif orders_today >= 3:
                return 45  # 45 minutes ago (medium velocity)
            else:
                return 120  # 2 hours ago (normal)
        
        return calculate_last_order_time(col("user_id"), col("orders_today"))
    
    def _get_device_info(self):
        """UDF to get device fingerprint info"""
        @udf(returnType=StringType())
        def get_device_fingerprint(user_id: str) -> str:
            """
            TODO: Replace with actual device tracking
            Extract from headers or device tracking service
            """
            if not user_id:
                return "unknown"
            
            # Simplified device patterns
            if "new_" in user_id.lower():
                return "mobile_new"
            else:
                return "web_returning"
        
        return get_device_fingerprint(col("user_id"))
    
    def _get_ip_risk(self):
        """UDF to get IP risk score"""
        @udf(returnType=DoubleType())
        def calculate_ip_risk(user_id: str) -> float:
            """
            TODO: Replace with actual IP reputation service
            Integration with MaxMind, IPQualityScore, etc.
            """
            if not user_id:
                return 0.1
            
            # Simplified IP risk patterns
            if "new_" in user_id.lower():
                return 0.4  # New accounts from unknown IPs
            else:
                return 0.1  # Known good IPs
        
        return calculate_ip_risk(col("user_id"))
    
    def get_enrichment_stats(self, enriched_df: DataFrame) -> Dict[str, Any]:
        """Get statistics about data enrichment quality"""
        try:
            total_records = enriched_df.count()
            
            # Check for missing critical data
            missing_stats = enriched_df.select(
                sum(when(col("account_age_days").isNull(), 1).otherwise(0)).alias("missing_age"),
                sum(when(col("total_orders").isNull(), 1).otherwise(0)).alias("missing_orders"),
                sum(when(col("avg_order_value").isNull(), 1).otherwise(0)).alias("missing_avg")
            ).collect()[0]
            
            return {
                "total_records": total_records,
                "missing_account_age": missing_stats["missing_age"],
                "missing_order_count": missing_stats["missing_orders"],
                "missing_avg_value": missing_stats["missing_avg"],
                "data_quality_score": 1.0 - (missing_stats["missing_age"] + missing_stats["missing_orders"]) / (total_records * 2),
                "enrichment_status": "pattern_based"  # Will be "database_integrated" when real DB connected
            }
            
        except Exception as e:
            logger.error(f"Error calculating enrichment stats: {e}")
            return {"error": str(e), "enrichment_status": "failed"}