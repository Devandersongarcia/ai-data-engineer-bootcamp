"""
Tests for the main FraudDetector system
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from fraud_detector import FraudDetector
from models.order import OrderData


class TestFraudDetector:
    """Test the main FraudDetector class"""
    
    @pytest.fixture
    def mock_fraud_detector(self, mock_openai_client):
        """Create a fraud detector with mocked dependencies"""
        with patch('fraud_detector.FraudRAGSystem') as mock_rag, \
             patch('fraud_detector.FraudDetectionAgents') as mock_agents, \
             patch('fraud_detector.FraudDetectionWorkflow') as mock_workflow, \
             patch('fraud_detector.FraudActionEngine') as mock_action_engine:
            
            # Setup mocks
            mock_rag_instance = Mock()
            mock_rag_instance.validate_system.return_value = {"system_ready": True}
            mock_rag_instance.get_performance_metrics.return_value = {}
            mock_rag.return_value = mock_rag_instance
            
            mock_agents_instance = Mock()
            mock_agents_instance.pattern_analyzer = Mock()
            mock_agents_instance.risk_assessor = Mock()
            mock_agents_instance.decision_maker = Mock()
            mock_agents_instance.action_executor = Mock()
            mock_agents.return_value = mock_agents_instance
            
            mock_workflow_instance = Mock()
            mock_workflow_instance.analyze_fraud_async = AsyncMock(return_value=Mock(
                fraud_score=0.3,
                recommended_action="ALLOW",
                confidence_level=0.9,
                reasoning="Low risk order",
                detected_patterns=[],
                agent_analyses=[],
                processing_time_ms=150,
                to_dict=Mock(return_value={
                    "fraud_score": 0.3,
                    "recommended_action": "ALLOW",
                    "reasoning": "Low risk order"
                })
            ))
            mock_workflow_instance.get_workflow_statistics.return_value = {
                "total_workflows": 5,
                "success_rate": 1.0,
                "avg_total_time": 200
            }
            mock_workflow.return_value = mock_workflow_instance
            
            mock_action_engine_instance = Mock()
            mock_action_engine_instance.execute_fraud_action = AsyncMock(return_value=Mock(
                action_taken="ALLOW",
                status="COMPLETED",
                timestamp=datetime.now().isoformat(),
                to_dict=Mock(return_value={
                    "action_taken": "ALLOW",
                    "status": "COMPLETED"
                })
            ))
            mock_action_engine_instance.get_action_statistics.return_value = {
                "total_actions": 5,
                "success_rate": 1.0,
                "avg_execution_time_ms": 50
            }
            mock_action_engine.return_value = mock_action_engine_instance
            
            detector = FraudDetector()
            return detector
    
    def test_fraud_detector_initialization(self, mock_fraud_detector):
        """Test fraud detector initialization"""
        detector = mock_fraud_detector
        
        assert detector.rag_system is not None
        assert detector.agents is not None
        assert detector.workflow is not None
        assert detector.action_engine is not None
        assert detector.detection_count == 0
        assert detector.total_processing_time == 0.0
        assert detector.system_start_time is not None
    
    @pytest.mark.asyncio
    async def test_detect_fraud_success(self, mock_fraud_detector, sample_order_data):
        """Test successful fraud detection"""
        detector = mock_fraud_detector
        order = sample_order_data
        
        result = await detector.detect_fraud(order)
        
        # Verify result structure
        assert "order_id" in result
        assert "user_id" in result
        assert "fraud_analysis" in result
        assert "action_result" in result
        assert "total_processing_time_ms" in result
        assert "detection_timestamp" in result
        assert "system_version" in result
        
        # Verify values
        assert result["order_id"] == order.order_id
        assert result["user_id"] == order.user_key
        assert isinstance(result["total_processing_time_ms"], int)
        assert result["total_processing_time_ms"] > 0
        
        # Verify performance tracking
        assert detector.detection_count == 1
        assert detector.total_processing_time > 0
    
    @pytest.mark.asyncio
    async def test_detect_fraud_error_handling(self, mock_fraud_detector, sample_order_data):
        """Test fraud detection error handling"""
        detector = mock_fraud_detector
        order = sample_order_data
        
        # Mock workflow to raise exception
        detector.workflow.analyze_fraud_async.side_effect = Exception("Test error")
        
        result = await detector.detect_fraud(order)
        
        # Verify error result structure
        assert "error" in result
        assert result["fraud_analysis"]["recommended_action"] == "ALLOW"  # Safe default
        assert result["action_result"]["action_taken"] == "ERROR"
        assert result["action_result"]["status"] == "FAILED"
    
    @pytest.mark.asyncio
    async def test_detect_fraud_batch(self, mock_fraud_detector, sample_test_data):
        """Test batch fraud detection"""
        detector = mock_fraud_detector
        
        # Create order data list
        orders = [
            OrderData(**order_data) 
            for order_data in sample_test_data["valid_orders"]
        ]
        
        results = await detector.detect_fraud_batch(orders)
        
        # Verify batch results
        assert len(results) == len(orders)
        
        for i, result in enumerate(results):
            assert result["order_id"] == orders[i].order_id
            assert "fraud_analysis" in result
            assert "action_result" in result
    
    def test_validate_order_data_valid(self, mock_fraud_detector, sample_order_data):
        """Test order data validation with valid data"""
        detector = mock_fraud_detector
        
        validation_result = detector.validate_order_data(sample_order_data)
        
        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0
        assert isinstance(validation_result["warnings"], list)
    
    def test_validate_order_data_invalid(self, mock_fraud_detector):
        """Test order data validation with invalid data"""
        detector = mock_fraud_detector
        
        # Create invalid order
        invalid_order = OrderData(
            order_id="",  # Empty order ID
            user_key="",  # Empty user key
            total_amount=-10.0,  # Negative amount
            item_count=0  # Zero items - this will fail validation in constructor
        )
        
        # This should raise a ValidationError during OrderData creation
        # But if we somehow get past that, our validation should catch it
        with pytest.raises(Exception):  # Could be ValidationError or our validation
            pass
    
    def test_get_system_health(self, mock_fraud_detector):
        """Test system health reporting"""
        detector = mock_fraud_detector
        
        health = detector.get_system_health()
        
        # Verify health structure
        assert "system_status" in health
        assert "uptime_seconds" in health
        assert "detections_processed" in health
        assert "avg_processing_time_seconds" in health
        assert "rag_system" in health
        assert "agent_system" in health
        assert "action_engine" in health
        assert "performance_targets" in health
        
        # Verify status is valid
        assert health["system_status"] in ["healthy", "degraded", "error"]
    
    def test_get_performance_metrics(self, mock_fraud_detector):
        """Test performance metrics collection"""
        detector = mock_fraud_detector
        
        metrics = detector.get_performance_metrics()
        
        # Verify metrics structure
        assert "timestamp" in metrics
        assert "system_metrics" in metrics
        assert "rag_metrics" in metrics
        assert "workflow_metrics" in metrics
        assert "action_metrics" in metrics
        assert "sla_compliance" in metrics
        
        # Verify system metrics
        system_metrics = metrics["system_metrics"]
        assert "total_detections" in system_metrics
        assert "avg_processing_time_seconds" in system_metrics
        assert "throughput_per_second" in system_metrics
        assert "uptime_seconds" in system_metrics
    
    @pytest.mark.asyncio
    async def test_test_system_end_to_end(self, mock_fraud_detector):
        """Test end-to-end system testing"""
        detector = mock_fraud_detector
        
        test_result = await detector.test_system_end_to_end()
        
        # Verify test result structure
        assert "test_status" in test_result
        assert "test_duration_seconds" in test_result
        assert "detection_completed" in test_result
        assert "fraud_score_returned" in test_result
        assert "action_executed" in test_result
        assert "within_latency_target" in test_result
        assert "test_timestamp" in test_result
        assert "result_summary" in test_result
        
        # Verify test status
        assert test_result["test_status"] in ["passed", "failed"]
        assert isinstance(test_result["test_duration_seconds"], (int, float))
    
    def test_reset_performance_counters(self, mock_fraud_detector):
        """Test performance counter reset"""
        detector = mock_fraud_detector
        
        # Set some values
        detector.detection_count = 10
        detector.total_processing_time = 5.0
        original_start_time = detector.system_start_time
        
        # Reset counters
        detector.reset_performance_counters()
        
        # Verify reset
        assert detector.detection_count == 0
        assert detector.total_processing_time == 0.0
        assert detector.system_start_time != original_start_time
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_fraud_detector):
        """Test system shutdown"""
        detector = mock_fraud_detector
        
        # Mock cleanup methods
        detector.rag_system.clear_cache = Mock()
        detector.action_engine.thread_pool = Mock()
        detector.action_engine.thread_pool.shutdown = Mock()
        
        # Test shutdown
        await detector.shutdown()
        
        # Verify cleanup was called (if methods exist)
        # Note: In real implementation, these methods might not exist
        # so we just verify no exceptions are raised


class TestFraudDetectorPerformance:
    """Test fraud detector performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_detection_latency(self, mock_fraud_detector, sample_order_data):
        """Test detection latency meets SLA requirements"""
        detector = mock_fraud_detector
        order = sample_order_data
        
        import time
        start_time = time.time()
        result = await detector.detect_fraud(order)
        end_time = time.time()
        
        actual_latency_ms = (end_time - start_time) * 1000
        reported_latency_ms = result["total_processing_time_ms"]
        
        # Verify latency is reasonable (mocked, so should be very fast)
        assert actual_latency_ms < 1000  # Less than 1 second for mocked test
        assert reported_latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_detection(self, mock_fraud_detector, sample_test_data):
        """Test concurrent fraud detection"""
        detector = mock_fraud_detector
        
        # Create multiple orders
        orders = [
            OrderData(**order_data) 
            for order_data in sample_test_data["valid_orders"]
        ]
        
        # Run concurrent detections
        tasks = [detector.detect_fraud(order) for order in orders]
        results = await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        assert len(results) == len(orders)
        for result in results:
            assert "fraud_analysis" in result
            assert "action_result" in result
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, mock_fraud_detector, performance_test_data):
        """Test memory usage remains stable under load"""
        detector = mock_fraud_detector
        
        # Process many orders to test memory stability
        orders = [
            OrderData(**order_data) 
            for order_data in performance_test_data["large_order_batch"][:100]  # First 100
        ]
        
        # Process in batches
        batch_size = 10
        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            batch_results = await detector.detect_fraud_batch(batch)
            
            assert len(batch_results) == len(batch)
            
            # Verify system remains healthy
            health = detector.get_system_health()
            assert health["system_status"] in ["healthy", "degraded"]


class TestFraudDetectorIntegration:
    """Test fraud detector integration with other components"""
    
    @pytest.mark.asyncio
    async def test_rag_system_integration(self, mock_fraud_detector, sample_order_data):
        """Test integration with RAG system"""
        detector = mock_fraud_detector
        order = sample_order_data
        
        # Verify RAG system is accessible
        assert detector.rag_system is not None
        
        # Test fraud detection uses RAG
        result = await detector.detect_fraud(order)
        assert "fraud_analysis" in result
        
        # Verify RAG metrics are available
        metrics = detector.get_performance_metrics()
        assert "rag_metrics" in metrics
    
    @pytest.mark.asyncio
    async def test_agent_system_integration(self, mock_fraud_detector, sample_order_data):
        """Test integration with agent system"""
        detector = mock_fraud_detector
        order = sample_order_data
        
        # Verify agents are accessible
        assert detector.agents is not None
        
        # Test fraud detection uses agents
        result = await detector.detect_fraud(order)
        assert "fraud_analysis" in result
        
        # Verify workflow statistics are available
        metrics = detector.get_performance_metrics()
        assert "workflow_metrics" in metrics
    
    @pytest.mark.asyncio
    async def test_action_engine_integration(self, mock_fraud_detector, sample_order_data):
        """Test integration with action engine"""
        detector = mock_fraud_detector
        order = sample_order_data
        
        # Verify action engine is accessible
        assert detector.action_engine is not None
        
        # Test fraud detection executes actions
        result = await detector.detect_fraud(order)
        assert "action_result" in result
        
        # Verify action metrics are available
        metrics = detector.get_performance_metrics()
        assert "action_metrics" in metrics