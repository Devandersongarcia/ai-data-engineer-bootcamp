"""Spark-based fraud detection engine with ML-enhanced risk scoring.

Implements real-time fraud detection using rule-based algorithms combined
with behavioral analysis and risk assessment patterns.
"""

from __future__ import annotations

import logging
from typing import Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, when, current_timestamp, udf
)
from pyspark.sql.types import DoubleType, ArrayType, StringType

logger = logging.getLogger(__name__)

class SparkFraudDetector:
    """Real-time fraud detection engine using Apache Spark.
    
    Implements multi-layered fraud detection with velocity analysis,
    amount anomaly detection, account risk assessment, and payment method scoring.
    
    Attributes:
        spark: Spark session for distributed processing
    """
    
    def __init__(self, spark: SparkSession) -> None:
        """Initialize fraud detector with Spark session.
        
        Args:
            spark: Active Spark session for distributed processing
        """
        self.spark = spark
        
    def calculate_risk_features(self, orders_df: DataFrame) -> DataFrame:
        """Calculate comprehensive fraud risk features.
        
        Analyzes velocity patterns, amount anomalies, account age,
        and payment method risks using distributed Spark operations.
        
        Args:
            orders_df: Input DataFrame with order data
            
        Returns:
            DataFrame with calculated risk features
        """
        
        velocity_score_udf = self._create_velocity_score_udf()
        amount_score_udf = self._create_amount_score_udf()
        account_score_udf = self._create_account_score_udf()
        payment_score_udf = self._create_payment_score_udf()
        
        @udf(returnType=DoubleType())
        def calculate_amount_score(total_amount: float, avg_order_value: float) -> float:
            """Calculate amount anomaly score"""
            # Handle null values
            if total_amount is None:
                total_amount = 0.0
            if avg_order_value is None:
                avg_order_value = 0.0
                
            if avg_order_value <= 0:
                return 0.5
            
            ratio = total_amount / avg_order_value
            
            # Very high or very low amounts compared to average are suspicious
            if ratio > 5.0:  # Much higher than usual
                calculated_score = ratio * 0.1
                return calculated_score if calculated_score < 1.0 else 1.0
            elif ratio < 0.2:  # Much lower than usual (potential account testing)
                return 0.3
            else:
                return 0.0
        
        @udf(returnType=DoubleType())
        def calculate_account_score(account_age_days: int, total_orders: int) -> float:
            """Calculate new account risk score"""
            # Handle null values
            if account_age_days is None:
                account_age_days = 0
            if total_orders is None:
                total_orders = 0
                
            if account_age_days < 1:
                return 0.9  # Very new accounts are risky
            elif account_age_days < 7:
                return 0.6
            elif account_age_days < 30:
                return 0.3
            else:
                return 0.1
        
        @udf(returnType=DoubleType())
        def calculate_payment_score(payment_method: str) -> float:
            """Calculate payment method risk score"""
            # Handle null values
            if payment_method is None:
                payment_method = 'unknown'
                
            payment_risks = {
                'credit_card': 0.2,
                'debit_card': 0.1,
                'pix': 0.05,
                'cash': 0.1,
                'wallet': 0.15
            }
            return payment_risks.get(payment_method.lower(), 0.3)
        
        # Create UDF functions
        calculate_velocity_score = self._create_velocity_score_udf()
        calculate_amount_score = self._create_amount_score_udf()
        calculate_account_score = self._create_account_score_udf()
        calculate_payment_score = self._create_payment_score_udf()
        
        # Calculate risk features using flattened fields
        risk_df = orders_df.select(
            "*",
            # Velocity risk
            calculate_velocity_score(
                col("total_amount"), 
                col("account_age_days"), 
                col("total_orders")
            ).alias("velocity_risk"),
            
            # Amount anomaly risk
            calculate_amount_score(
                col("total_amount"), 
                col("avg_order_value")
            ).alias("amount_risk"),
            
            # New account risk
            calculate_account_score(
                col("account_age_days"), 
                col("total_orders")
            ).alias("account_risk"),
            
            # Payment risk
            calculate_payment_score(col("payment_method")).alias("payment_risk")
        )
        
        return risk_df
    
    def calculate_fraud_score(self, risk_df: DataFrame) -> DataFrame:
        """Calculate final fraud score and classification"""
        
        # Define composite fraud score calculation
        fraud_df = risk_df.withColumn(
            "fraud_score",
            (
                col("velocity_risk") * 0.3 +
                col("amount_risk") * 0.25 +
                col("account_risk") * 0.25 +
                col("payment_risk") * 0.2
            )
        )
        
        # Add fraud classification with more sensitive thresholds
        fraud_df = fraud_df.withColumn(
            "fraud_prediction",
            when(col("fraud_score") >= 0.3, "HIGH_RISK")
            .when(col("fraud_score") >= 0.2, "MEDIUM_RISK")
            .when(col("fraud_score") >= 0.1, "LOW_RISK")
            .otherwise("LEGITIMATE")
        )
        
        # Add confidence score adjusted for new thresholds
        fraud_df = fraud_df.withColumn(
            "confidence",
            when(col("fraud_score") >= 0.4, 0.95)
            .when(col("fraud_score") >= 0.3, 0.85)
            .when(col("fraud_score") >= 0.2, 0.75)
            .when(col("fraud_score") >= 0.1, 0.65)
            .otherwise(0.6)
        )
        
        return fraud_df
    
    def add_fraud_reasons(self, fraud_df: DataFrame) -> DataFrame:
        """Add human-readable fraud reasons"""
        
        @udf(returnType=ArrayType(StringType()))
        def generate_fraud_reasons(
            velocity_risk: float, 
            amount_risk: float, 
            account_risk: float, 
            payment_risk: float,
            fraud_score: float
        ) -> List[str]:
            """Generate list of fraud indicators"""
            # Handle null values
            if velocity_risk is None:
                velocity_risk = 0.0
            if amount_risk is None:
                amount_risk = 0.0
            if account_risk is None:
                account_risk = 0.0
            if payment_risk is None:
                payment_risk = 0.0
            if fraud_score is None:
                fraud_score = 0.0
                
            reasons = []
            
            if velocity_risk > 0.2:
                reasons.append("High order velocity detected")
            if amount_risk > 0.15:
                reasons.append("Unusual order amount pattern")
            if account_risk > 0.3:
                reasons.append("New or suspicious account")
            if payment_risk > 0.15:
                reasons.append("Risky payment method")
            if fraud_score > 0.3:
                reasons.append("Multiple fraud indicators present")
                
            if not reasons:
                reasons.append("Order appears legitimate")
                
            return reasons
        
        result_df = fraud_df.withColumn(
            "fraud_reasons",
            generate_fraud_reasons(
                col("velocity_risk"),
                col("amount_risk"), 
                col("account_risk"),
                col("payment_risk"),
                col("fraud_score")
            )
        )
        
        return result_df
    
    def detect_fraud(self, orders_df: DataFrame) -> DataFrame:
        """Complete fraud detection pipeline"""
        logger.info("Starting fraud detection pipeline")
        
        # Step 1: Calculate risk features
        risk_df = self.calculate_risk_features(orders_df)
        
        # Step 2: Calculate fraud scores
        fraud_df = self.calculate_fraud_score(risk_df)
        
        # Step 3: Add fraud reasons
        result_df = self.add_fraud_reasons(fraud_df)
        
        # Step 4: Add processing metadata
        final_df = result_df.select(
            col("order_id"),
            col("user_id"),
            col("total_amount"),
            col("payment_method"),
            col("account_age_days"),  # Preserve for agentic processor
            col("total_orders"),      # Preserve for agentic processor
            col("avg_order_value"),   # Preserve for agentic processor
            col("fraud_score"),
            col("fraud_prediction"),
            col("confidence"),
            col("fraud_reasons"),
            col("velocity_risk"),
            col("amount_risk"),
            col("account_risk"),
            col("payment_risk"),
            col("processing_timestamp"),
            current_timestamp().alias("detection_timestamp")
        )
        
        logger.info("Fraud detection pipeline completed")
        return final_df
    
    def _create_velocity_score_udf(self) -> Any:
        """Create velocity scoring UDF with null handling."""
        @udf(returnType=DoubleType())
        def calculate_velocity_score(
            total_amount: float, account_age_days: int, total_orders: int
        ) -> float:
            if not all([total_amount, account_age_days, total_orders]):
                return 1.0 if account_age_days == 0 else 0.5
                
            divisor = max(account_age_days, 1)
            order_frequency = total_orders / divisor
            amount_per_day = total_amount * order_frequency
            
            calculated_score = order_frequency * 0.1 + amount_per_day * 0.001
            return min(float(calculated_score), 1.0)
        
        return calculate_velocity_score
    
    def _create_amount_score_udf(self) -> Any:
        """Create amount anomaly scoring UDF."""
        @udf(returnType=DoubleType())
        def calculate_amount_score(total_amount: float, avg_order_value: float) -> float:
            if not all([total_amount, avg_order_value]) or avg_order_value <= 0:
                return 0.5
            
            ratio = total_amount / avg_order_value
            if ratio > 5.0:
                return min(ratio * 0.1, 1.0)
            elif ratio < 0.2:
                return 0.3
            return 0.0
        
        return calculate_amount_score
    
    def _create_account_score_udf(self) -> Any:
        """Create account risk scoring UDF."""
        @udf(returnType=DoubleType())
        def calculate_account_score(account_age_days: int, total_orders: int) -> float:
            age_days = account_age_days or 0
            
            if age_days < 1:
                return 0.9
            elif age_days < 7:
                return 0.6
            elif age_days < 30:
                return 0.3
            return 0.1
        
        return calculate_account_score
    
    def _create_payment_score_udf(self) -> Any:
        """Create payment method risk scoring UDF."""
        @udf(returnType=DoubleType())
        def calculate_payment_score(payment_method: str) -> float:
            PAYMENT_RISK_SCORES = {
                'credit_card': 0.2,
                'debit_card': 0.1,
                'pix': 0.05,
                'cash': 0.1,
                'wallet': 0.15
            }
            
            method = (payment_method or 'unknown').lower()
            return PAYMENT_RISK_SCORES.get(method, 0.3)
        
        return calculate_payment_score