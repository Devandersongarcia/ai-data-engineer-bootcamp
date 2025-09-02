"""
Tests for streaming components (Kafka and Spark)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from streaming.kafka_reader import KafkaStreamReader
from streaming.fraud_processor import FraudProcessor
from streaming.rule_engine import RuleEngine
from streaming.stream_writer import StreamWriter


class TestKafkaStreamReader:
    """Test Kafka stream reader functionality"""
    
    @pytest.fixture
    def mock_spark_session(self):
        """Mock Spark session for testing"""
        mock_spark = Mock()
        mock_readstream = Mock()
        mock_spark.readStream = mock_readstream
        
        # Chain method calls
        mock_readstream.format.return_value = mock_readstream
        mock_readstream.option.return_value = mock_readstream
        mock_readstream.load.return_value = Mock()  # Mock DataFrame
        
        return mock_spark
    
    def test_kafka_reader_initialization(self, mock_spark_session):
        """Test Kafka reader initialization"""
        with patch('streaming.kafka_reader.SparkSession') as mock_spark_class:
            mock_spark_class.builder.appName.return_value.getOrCreate.return_value = mock_spark_session
            
            reader = KafkaStreamReader()
            
            assert reader.spark is not None
            assert reader.bootstrap_servers == "localhost:9092"
    
    def test_create_fraud_order_stream(self, mock_spark_session):
        """Test creation of fraud order stream"""
        with patch('streaming.kafka_reader.SparkSession') as mock_spark_class:
            mock_spark_class.builder.appName.return_value.getOrCreate.return_value = mock_spark_session
            
            reader = KafkaStreamReader()
            
            # Mock the stream creation
            mock_df = Mock()
            mock_spark_session.readStream.format.return_value.option.return_value.load.return_value = mock_df
            
            stream_df = reader.create_fraud_order_stream()
            
            assert stream_df is not None
            mock_spark_session.readStream.format.assert_called_with("kafka")
    
    def test_parse_order_data_valid(self):
        """Test parsing valid order data"""
        reader = KafkaStreamReader()
        
        # Sample order JSON
        sample_order = {
            "order_id": "test_123",
            "user_key": "user_456",
            "total_amount": 25.50,
            "item_count": 2,
            "order_timestamp": "2024-01-15T12:30:00Z"
        }
        
        order_json = json.dumps(sample_order)
        
        # Test parsing (this would be called as UDF in Spark)
        # For testing, we'll simulate the UDF behavior
        parsed_order = reader.parse_order_data(order_json)
        
        assert parsed_order is not None
        # In real implementation, this would return structured data
    
    def test_parse_order_data_invalid(self):
        """Test parsing invalid order data"""
        reader = KafkaStreamReader()
        
        # Invalid JSON
        invalid_json = "{'invalid': json}"
        
        # Should handle gracefully
        result = reader.parse_order_data(invalid_json)
        
        # Should return None or error indicator for invalid data
        assert result is None or "error" in str(result).lower()


class TestFraudProcessor:
    """Test Spark fraud processor"""
    
    @pytest.fixture
    def mock_fraud_processor(self, mock_spark_session):
        """Create fraud processor with mocked dependencies"""
        with patch('streaming.fraud_processor.SparkSession') as mock_spark_class:
            mock_spark_class.builder.appName.return_value.getOrCreate.return_value = mock_spark_session
            
            processor = FraudProcessor()
            
            # Mock dependencies
            processor.rag_system = Mock()
            processor.agent_system = Mock()
            processor.action_executor = Mock()
            
            return processor
    
    def test_fraud_processor_initialization(self, mock_fraud_processor):
        """Test fraud processor initialization"""
        processor = mock_fraud_processor
        
        assert processor.spark is not None
        assert processor.kafka_reader is not None
        assert processor.rule_engine is not None
        assert processor.stream_writer is not None
    
    def test_inject_dependencies(self, mock_fraud_processor):
        """Test dependency injection"""
        processor = mock_fraud_processor
        
        mock_rag = Mock()
        mock_agents = Mock()
        mock_action_engine = Mock()
        
        processor.inject_dependencies(
            rag_system=mock_rag,
            agent_system=mock_agents,
            action_executor=mock_action_engine
        )
        
        assert processor.rag_system == mock_rag
        assert processor.agent_system == mock_agents
        assert processor.action_executor == mock_action_engine
    
    def test_start_streaming(self, mock_fraud_processor):
        """Test starting the streaming process"""
        processor = mock_fraud_processor
        
        # Mock stream operations
        mock_stream = Mock()
        mock_stream.writeStream = Mock()
        mock_query = Mock()
        mock_stream.writeStream.trigger.return_value.outputMode.return_value.start.return_value = mock_query
        
        with patch.object(processor, 'process_fraud_detection_stream', return_value=mock_stream):
            processor.start_streaming()
            
            # Verify streaming was started
            assert processor.streaming_query is not None
    
    def test_stop_streaming(self, mock_fraud_processor):
        """Test stopping the streaming process"""
        processor = mock_fraud_processor
        
        # Mock active query
        mock_query = Mock()
        processor.streaming_query = mock_query
        
        processor.stop_streaming()
        
        # Verify stop was called
        mock_query.stop.assert_called_once()
    
    def test_process_fraud_detection_stream(self, mock_fraud_processor):
        """Test the main fraud detection stream processing"""
        processor = mock_fraud_processor
        
        # Mock input stream
        mock_input_stream = Mock()
        processor.kafka_reader.create_fraud_order_stream.return_value = mock_input_stream
        
        # Mock processing steps
        with patch.object(processor, 'apply_rule_based_detection') as mock_rules, \
             patch.object(processor, 'apply_agent_based_detection') as mock_agents:
            
            mock_rules.return_value = mock_input_stream
            mock_agents.return_value = mock_input_stream
            
            result_stream = processor.process_fraud_detection_stream()
            
            assert result_stream is not None
            mock_rules.assert_called_once()
            mock_agents.assert_called_once()


class TestRuleEngine:
    """Test rule-based fraud detection engine"""
    
    def test_rule_engine_initialization(self):
        """Test rule engine initialization"""
        engine = RuleEngine()
        
        assert engine.velocity_threshold == 10
        assert engine.amount_threshold == 500.0
        assert engine.geographic_radius_km == 50.0
    
    def test_check_velocity_fraud_normal(self):
        """Test velocity fraud check with normal behavior"""
        engine = RuleEngine()
        
        order_data = {
            "orders_today": 3,
            "orders_last_hour": 1,
            "avg_order_frequency_hours": 24
        }
        
        result = engine.check_velocity_fraud(order_data)
        
        assert result["is_fraud"] is False
        assert result["risk_score"] < 0.5
    
    def test_check_velocity_fraud_high_velocity(self):
        """Test velocity fraud check with high velocity"""
        engine = RuleEngine()
        
        order_data = {
            "orders_today": 25,
            "orders_last_hour": 15,
            "avg_order_frequency_hours": 0.5
        }
        
        result = engine.check_velocity_fraud(order_data)
        
        assert result["is_fraud"] is True
        assert result["risk_score"] > 0.7
        assert "high_velocity" in result["reasons"]
    
    def test_check_amount_fraud_normal(self):
        """Test amount-based fraud check with normal amounts"""
        engine = RuleEngine()
        
        order_data = {
            "total_amount": 25.50,
            "avg_order_value": 28.75,
            "max_order_value": 45.00
        }
        
        result = engine.check_amount_fraud(order_data)
        
        assert result["is_fraud"] is False
        assert result["risk_score"] < 0.5
    
    def test_check_amount_fraud_suspicious_amount(self):
        """Test amount-based fraud check with suspicious amounts"""
        engine = RuleEngine()
        
        order_data = {
            "total_amount": 750.00,
            "avg_order_value": 25.00,
            "max_order_value": 40.00
        }
        
        result = engine.check_amount_fraud(order_data)
        
        assert result["is_fraud"] is True
        assert result["risk_score"] > 0.7
        assert "unusual_amount" in result["reasons"]
    
    def test_check_geographic_fraud_normal(self):
        """Test geographic fraud check with normal location"""
        engine = RuleEngine()
        
        order_data = {
            "delivery_lat": 37.7749,
            "delivery_lng": -122.4194,
            "user_common_locations": [
                {"lat": 37.7849, "lng": -122.4094}  # Close location
            ]
        }
        
        result = engine.check_geographic_fraud(order_data)
        
        assert result["is_fraud"] is False
        assert result["risk_score"] < 0.5
    
    def test_check_geographic_fraud_suspicious_location(self):
        """Test geographic fraud check with suspicious location"""
        engine = RuleEngine()
        
        order_data = {
            "delivery_lat": 40.7128,  # NYC
            "delivery_lng": -74.0060,
            "user_common_locations": [
                {"lat": 37.7749, "lng": -122.4194}  # SF - very far
            ]
        }
        
        result = engine.check_geographic_fraud(order_data)
        
        assert result["is_fraud"] is True
        assert result["risk_score"] > 0.7
        assert "geographic_anomaly" in result["reasons"]
    
    def test_check_payment_fraud_normal(self):
        """Test payment fraud check with normal payment behavior"""
        engine = RuleEngine()
        
        order_data = {
            "payment_method": "credit_card",
            "payment_failures_today": 0,
            "payment_failures_week": 1,
            "card_age_days": 365
        }
        
        result = engine.check_payment_fraud(order_data)
        
        assert result["is_fraud"] is False
        assert result["risk_score"] < 0.5
    
    def test_check_payment_fraud_suspicious_payments(self):
        """Test payment fraud check with suspicious payment behavior"""
        engine = RuleEngine()
        
        order_data = {
            "payment_method": "new_credit_card",
            "payment_failures_today": 8,
            "payment_failures_week": 15,
            "card_age_days": 1
        }
        
        result = engine.check_payment_fraud(order_data)
        
        assert result["is_fraud"] is True
        assert result["risk_score"] > 0.7
        assert "payment_failures" in result["reasons"]
    
    def test_check_account_fraud_normal(self):
        """Test account fraud check with normal account"""
        engine = RuleEngine()
        
        order_data = {
            "account_age_days": 180,
            "total_orders": 25,
            "avg_order_value": 28.50,
            "cancellation_rate": 0.05
        }
        
        result = engine.check_account_fraud(order_data)
        
        assert result["is_fraud"] is False
        assert result["risk_score"] < 0.5
    
    def test_check_account_fraud_suspicious_account(self):
        """Test account fraud check with suspicious account"""
        engine = RuleEngine()
        
        order_data = {
            "account_age_days": 1,
            "total_orders": 50,
            "avg_order_value": 500.00,
            "cancellation_rate": 0.8
        }
        
        result = engine.check_account_fraud(order_data)
        
        assert result["is_fraud"] is True
        assert result["risk_score"] > 0.7
        assert "new_account" in result["reasons"]
    
    def test_calculate_composite_score(self):
        """Test composite fraud score calculation"""
        engine = RuleEngine()
        
        rule_results = [
            {"is_fraud": False, "risk_score": 0.2},
            {"is_fraud": True, "risk_score": 0.8},
            {"is_fraud": False, "risk_score": 0.3},
            {"is_fraud": True, "risk_score": 0.9},
            {"is_fraud": False, "risk_score": 0.1}
        ]
        
        composite_score = engine.calculate_composite_score(rule_results)
        
        # Should be weighted average of scores
        expected_score = (0.2 + 0.8 + 0.3 + 0.9 + 0.1) / 5
        assert abs(composite_score - expected_score) < 0.1


class TestStreamWriter:
    """Test stream writing functionality"""
    
    @pytest.fixture
    def mock_stream_writer(self, mock_kafka_producer):
        """Create stream writer with mocked Kafka producer"""
        with patch('streaming.stream_writer.KafkaProducer') as mock_producer_class:
            mock_producer_class.return_value = mock_kafka_producer
            
            writer = StreamWriter()
            return writer
    
    def test_stream_writer_initialization(self, mock_stream_writer):
        """Test stream writer initialization"""
        writer = mock_stream_writer
        
        assert writer.producer is not None
        assert writer.fraud_results_topic == "fraud-results"
        assert writer.fraud_alerts_topic == "fraud-alerts"
    
    def test_write_fraud_result(self, mock_stream_writer, sample_fraud_result):
        """Test writing fraud result to Kafka"""
        writer = mock_stream_writer
        result = sample_fraud_result
        
        writer.write_fraud_result("test_order_123", result)
        
        # Verify Kafka producer was called
        writer.producer.send.assert_called_once()
        
        # Verify message structure
        call_args = writer.producer.send.call_args
        assert call_args[0][0] == "fraud-results"  # Topic
        assert "test_order_123" in str(call_args[1]["key"])  # Key
    
    def test_write_fraud_alert(self, mock_stream_writer):
        """Test writing fraud alert to Kafka"""
        writer = mock_stream_writer
        
        alert_data = {
            "order_id": "fraud_order_999",
            "alert_type": "HIGH_RISK",
            "fraud_score": 0.95,
            "recommended_action": "BLOCK",
            "timestamp": "2024-01-15T12:30:00Z"
        }
        
        writer.write_fraud_alert(alert_data)
        
        # Verify alert was sent
        writer.producer.send.assert_called()
        
        # Verify alert topic
        call_args = writer.producer.send.call_args
        assert call_args[0][0] == "fraud-alerts"
    
    def test_close_writer(self, mock_stream_writer):
        """Test closing the stream writer"""
        writer = mock_stream_writer
        
        writer.close()
        
        # Verify producer was closed
        writer.producer.close.assert_called_once()


class TestStreamingIntegration:
    """Test integration between streaming components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_streaming_flow(self, mock_kafka_consumer, mock_kafka_producer):
        """Test end-to-end streaming flow"""
        # This would test the complete flow from Kafka consumer to producer
        # For now, we'll test the component interactions
        
        # Mock order message from Kafka
        order_message = {
            "order_id": "test_integration_123",
            "user_key": "integration_user",
            "total_amount": 45.00,
            "item_count": 3
        }
        
        # Simulate processing pipeline
        # 1. Read from Kafka (mocked)
        raw_message = json.dumps(order_message)
        
        # 2. Parse message
        parsed_order = json.loads(raw_message)
        assert parsed_order["order_id"] == "test_integration_123"
        
        # 3. Apply rule engine
        rule_engine = RuleEngine()
        rule_result = rule_engine.check_velocity_fraud({
            "orders_today": 2,
            "orders_last_hour": 1
        })
        assert rule_result["is_fraud"] is False
        
        # 4. Write result (mocked)
        # This would write to Kafka topics
        
        # Verify integration works
        assert parsed_order is not None
        assert rule_result is not None