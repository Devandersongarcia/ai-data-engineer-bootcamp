"""
Pytest configuration and shared fixtures for fraud detection system tests
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from models.order import OrderData
from models.fraud_result import FraudResult, FraudPattern, AgentAnalysis
from models.user_profile import UserBehaviorProfile
from models.action_result import ActionResult


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_order_data() -> OrderData:
    """Sample order data for testing"""
    return OrderData(
        order_id="test_order_123",
        user_key="test_user_456",
        total_amount=25.50,
        item_count=2,
        restaurant_id="rest_789",
        delivery_lat=37.7749,
        delivery_lng=-122.4194,
        order_timestamp="2024-01-15T12:30:00Z",
        payment_method="credit_card",
        account_age_days=90,
        orders_today=1,
        orders_week=3,
        orders_month=12,
        payment_failures_today=0,
        payment_failures_week=0,
        avg_order_value=28.75,
        order_creation_speed_ms=1500,
        device_id="device_abc123",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        session_id="session_xyz789",
        referrer_url="https://ubereats.com",
        promo_code="SAVE10",
        delivery_fee=2.99,
        service_fee=1.50,
        tip_amount=5.00,
        is_peak_hour=True,
        distance_from_restaurant_km=2.5,
        estimated_prep_time_min=20,
        estimated_delivery_time_min=35
    )


@pytest.fixture
def high_risk_order_data() -> OrderData:
    """High-risk order data for fraud testing"""
    return OrderData(
        order_id="fraud_order_999",
        user_key="suspicious_user_999",
        total_amount=250.00,  # High amount
        item_count=10,
        restaurant_id="rest_999",
        delivery_lat=40.7128,
        delivery_lng=-74.0060,
        order_timestamp="2024-01-15T03:30:00Z",  # Unusual time
        payment_method="new_credit_card",
        account_age_days=1,  # New account
        orders_today=15,  # Velocity fraud
        orders_week=15,
        orders_month=15,
        payment_failures_today=5,  # Payment issues
        payment_failures_week=5,
        avg_order_value=35.00,
        order_creation_speed_ms=500,  # Very fast
        device_id="device_suspicious",
        ip_address="10.0.0.1",  # VPN-like IP
        user_agent="curl/7.68.0",  # Bot-like
        session_id="session_fraud",
        referrer_url="",
        promo_code="FRAUD50",
        delivery_fee=0.00,  # Suspicious zero fee
        service_fee=0.00,
        tip_amount=0.00,
        is_peak_hour=False,
        distance_from_restaurant_km=25.0,  # Very far
        estimated_prep_time_min=5,  # Unrealistic
        estimated_delivery_time_min=120  # Very long
    )


@pytest.fixture
def sample_fraud_result() -> FraudResult:
    """Sample fraud detection result"""
    return FraudResult(
        fraud_score=0.75,
        recommended_action="REVIEW",
        confidence_level=0.85,
        reasoning="Multiple risk factors detected including high velocity and new account",
        detected_patterns=[
            FraudPattern(
                pattern_type="velocity_fraud",
                confidence=0.9,
                evidence=["15 orders today", "new account"],
                risk_score=0.8
            )
        ],
        agent_analyses=[
            AgentAnalysis(
                agent_name="pattern_analyzer",
                analysis_result="High velocity pattern detected",
                confidence=0.9,
                processing_time_ms=150
            )
        ],
        processing_time_ms=450
    )


@pytest.fixture
def sample_user_profile() -> UserBehaviorProfile:
    """Sample user behavior profile"""
    return UserBehaviorProfile(
        user_key="test_user_456",
        total_orders=25,
        avg_order_value=28.75,
        avg_order_frequency_days=3.5,
        preferred_restaurants=["rest_123", "rest_456"],
        preferred_payment_methods=["credit_card"],
        common_delivery_areas=[{"lat": 37.7749, "lng": -122.4194}],
        avg_order_time_hour=12,
        weekend_order_ratio=0.3,
        cancellation_rate=0.05,
        refund_rate=0.02,
        payment_failure_rate=0.01,
        account_age_days=90,
        last_order_timestamp="2024-01-14T18:45:00Z",
        risk_score=0.15,
        profile_last_updated="2024-01-15T10:00:00Z"
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('openai.OpenAI') as mock_client:
        # Mock embeddings response
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536  # Standard embedding size
        mock_client.return_value.embeddings.create.return_value.data = [mock_embedding]
        
        # Mock chat completion response
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = '{"fraud_score": 0.3, "reasoning": "Low risk order"}'
        mock_client.return_value.chat.completions.create.return_value = mock_completion
        
        yield mock_client.return_value


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer for testing"""
    with patch('kafka.KafkaConsumer') as mock_consumer:
        mock_instance = Mock()
        mock_instance.poll.return_value = {}
        mock_instance.close.return_value = None
        mock_consumer.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing"""
    with patch('kafka.KafkaProducer') as mock_producer:
        mock_instance = Mock()
        mock_instance.send.return_value = Mock()
        mock_instance.flush.return_value = None
        mock_instance.close.return_value = None
        mock_producer.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_spark_session():
    """Mock Spark session for testing"""
    with patch('pyspark.sql.SparkSession') as mock_spark:
        mock_session = Mock()
        mock_session.sparkContext.setLogLevel.return_value = None
        mock_session.readStream.format.return_value.option.return_value.load.return_value = Mock()
        mock_spark.builder.appName.return_value.getOrCreate.return_value = mock_session
        yield mock_session


@pytest.fixture
def test_config():
    """Test configuration override"""
    return {
        "openai": {
            "api_key": "test_key",
            "llm_model": "gpt-4o-mini",
            "embedding_model": "text-embedding-3-small"
        },
        "fraud": {
            "fraud_threshold": 0.7,
            "high_risk_threshold": 0.9,
            "max_detection_latency_ms": 200
        },
        "kafka": {
            "bootstrap_servers": "localhost:9092",
            "fraud_orders_topic": "test_fraud_orders",
            "fraud_results_topic": "test_fraud_results"
        }
    }


@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Mock environment variables for testing"""
    test_env = {
        "OPENAI_API_KEY": "test_openai_key",
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "LOG_LEVEL": "DEBUG"
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        yield


@pytest.fixture
def sample_test_data():
    """Sample test data for various test scenarios"""
    return {
        "valid_orders": [
            {
                "order_id": f"test_order_{i}",
                "user_key": f"test_user_{i}",
                "total_amount": 25.0 + i,
                "item_count": 2,
                "account_age_days": 30 + i,
                "orders_today": 1
            }
            for i in range(5)
        ],
        "fraud_orders": [
            {
                "order_id": f"fraud_order_{i}",
                "user_key": f"fraud_user_{i}",
                "total_amount": 500.0,
                "item_count": 20,
                "account_age_days": 1,
                "orders_today": 50,
                "payment_failures_today": 10
            }
            for i in range(3)
        ]
    }


@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing"""
    return {
        "large_order_batch": [
            {
                "order_id": f"perf_order_{i}",
                "user_key": f"perf_user_{i % 100}",  # 100 unique users
                "total_amount": 20.0 + (i % 50),
                "item_count": 1 + (i % 5),
                "account_age_days": 30 + (i % 365),
                "orders_today": 1 + (i % 10)
            }
            for i in range(1000)  # 1000 orders for performance testing
        ]
    }


class AsyncMock:
    """Helper class for async mocking"""
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __call__(self, *args, **kwargs):
        return self.return_value


@pytest.fixture
def async_mock():
    """Factory for creating async mocks"""
    return AsyncMock