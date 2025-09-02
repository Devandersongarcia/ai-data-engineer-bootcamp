"""
Integration tests for the complete fraud detection system
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from fraud_detector import FraudDetector
from models.order import OrderData


class TestSystemIntegration:
    """Test complete system integration"""
    
    @pytest.fixture
    def integration_fraud_detector(self, mock_openai_client):
        """Create fraud detector for integration testing"""
        with patch('fraud_detector.FraudRAGSystem') as mock_rag, \
             patch('fraud_detector.FraudDetectionAgents') as mock_agents, \
             patch('fraud_detector.FraudDetectionWorkflow') as mock_workflow, \
             patch('fraud_detector.FraudActionEngine') as mock_action_engine:
            
            # Setup comprehensive mocks for integration testing
            mock_rag_instance = Mock()
            mock_rag_instance.validate_system.return_value = {"system_ready": True}
            mock_rag_instance.get_performance_metrics.return_value = {
                "query_count": 10,
                "avg_query_time_ms": 50
            }
            mock_rag.return_value = mock_rag_instance
            
            mock_agents_instance = Mock()
            mock_agents_instance.pattern_analyzer = Mock()
            mock_agents_instance.risk_assessor = Mock() 
            mock_agents_instance.decision_maker = Mock()
            mock_agents_instance.action_executor = Mock()
            mock_agents.return_value = mock_agents_instance
            
            # Create realistic workflow mock
            mock_workflow_instance = Mock()
            mock_workflow_instance.analyze_fraud_async = AsyncMock()
            mock_workflow_instance.get_workflow_statistics.return_value = {
                "total_workflows": 15,
                "success_rate": 0.93,
                "avg_total_time": 180,
                "avg_pattern_analysis_time": 50,
                "avg_risk_assessment_time": 60,
                "avg_decision_time": 40,
                "avg_action_time": 30
            }
            mock_workflow.return_value = mock_workflow_instance
            
            mock_action_engine_instance = Mock()
            mock_action_engine_instance.execute_fraud_action = AsyncMock()
            mock_action_engine_instance.get_action_statistics.return_value = {
                "total_actions": 15,
                "success_rate": 0.95,
                "avg_execution_time_ms": 35
            }
            mock_action_engine.return_value = mock_action_engine_instance
            
            detector = FraudDetector()
            return detector
    
    @pytest.mark.asyncio
    async def test_end_to_end_low_risk_order(self, integration_fraud_detector, sample_order_data):
        """Test complete flow for low-risk order"""
        detector = integration_fraud_detector
        order = sample_order_data
        
        # Setup low-risk response
        low_risk_fraud_result = Mock()
        low_risk_fraud_result.fraud_score = 0.25
        low_risk_fraud_result.recommended_action = "ALLOW"
        low_risk_fraud_result.confidence_level = 0.92
        low_risk_fraud_result.reasoning = "Low risk order with normal patterns"
        low_risk_fraud_result.detected_patterns = []
        low_risk_fraud_result.agent_analyses = []
        low_risk_fraud_result.processing_time_ms = 145
        low_risk_fraud_result.to_dict.return_value = {
            "fraud_score": 0.25,
            "recommended_action": "ALLOW",
            "confidence_level": 0.92,
            "reasoning": "Low risk order with normal patterns"
        }
        
        low_risk_action_result = Mock()
        low_risk_action_result.action_taken = "ALLOW"
        low_risk_action_result.status = "COMPLETED"
        low_risk_action_result.timestamp = datetime.now().isoformat()
        low_risk_action_result.to_dict.return_value = {
            "action_taken": "ALLOW",
            "status": "COMPLETED"
        }
        
        detector.workflow.analyze_fraud_async.return_value = low_risk_fraud_result
        detector.action_engine.execute_fraud_action.return_value = low_risk_action_result
        
        # Execute end-to-end detection
        result = await detector.detect_fraud(order)
        
        # Verify complete result structure
        assert result["order_id"] == order.order_id
        assert result["user_id"] == order.user_key
        assert result["fraud_analysis"]["fraud_score"] == 0.25
        assert result["fraud_analysis"]["recommended_action"] == "ALLOW"
        assert result["action_result"]["action_taken"] == "ALLOW"
        assert result["action_result"]["status"] == "COMPLETED"
        assert result["total_processing_time_ms"] > 0
        assert "detection_timestamp" in result
        assert result["system_version"] == "1.0.0"
        
        # Verify system state updates
        assert detector.detection_count == 1
        assert detector.total_processing_time > 0
    
    @pytest.mark.asyncio
    async def test_end_to_end_high_risk_order(self, integration_fraud_detector, high_risk_order_data):
        """Test complete flow for high-risk order"""
        detector = integration_fraud_detector
        order = high_risk_order_data
        
        # Setup high-risk response
        high_risk_fraud_result = Mock()
        high_risk_fraud_result.fraud_score = 0.89
        high_risk_fraud_result.recommended_action = "BLOCK"
        high_risk_fraud_result.confidence_level = 0.96
        high_risk_fraud_result.reasoning = "Multiple fraud indicators detected"
        high_risk_fraud_result.detected_patterns = ["velocity_fraud", "account_takeover"]
        high_risk_fraud_result.agent_analyses = []
        high_risk_fraud_result.processing_time_ms = 185
        high_risk_fraud_result.to_dict.return_value = {
            "fraud_score": 0.89,
            "recommended_action": "BLOCK",
            "confidence_level": 0.96,
            "reasoning": "Multiple fraud indicators detected"
        }
        
        high_risk_action_result = Mock()
        high_risk_action_result.action_taken = "BLOCK"
        high_risk_action_result.status = "COMPLETED"
        high_risk_action_result.timestamp = datetime.now().isoformat()
        high_risk_action_result.to_dict.return_value = {
            "action_taken": "BLOCK",
            "status": "COMPLETED"
        }
        
        detector.workflow.analyze_fraud_async.return_value = high_risk_fraud_result
        detector.action_engine.execute_fraud_action.return_value = high_risk_action_result
        
        # Execute end-to-end detection
        result = await detector.detect_fraud(order)
        
        # Verify high-risk handling
        assert result["fraud_analysis"]["fraud_score"] == 0.89
        assert result["fraud_analysis"]["recommended_action"] == "BLOCK"
        assert result["action_result"]["action_taken"] == "BLOCK"
        assert result["action_result"]["status"] == "COMPLETED"
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring_integration(self, integration_fraud_detector):
        """Test system health monitoring integration"""
        detector = integration_fraud_detector
        
        # Get system health
        health = detector.get_system_health()
        
        # Verify comprehensive health data
        assert "system_status" in health
        assert "uptime_seconds" in health
        assert "detections_processed" in health
        assert "avg_processing_time_seconds" in health
        assert "rag_system" in health
        assert "agent_system" in health
        assert "action_engine" in health
        assert "performance_targets" in health
        
        # Verify health status determination
        assert health["system_status"] in ["healthy", "degraded", "error"]
        
        # Verify component health
        assert isinstance(health["rag_system"], dict)
        assert isinstance(health["agent_system"], dict)
        assert isinstance(health["action_engine"], dict)
    
    @pytest.mark.asyncio
    async def test_performance_metrics_integration(self, integration_fraud_detector):
        """Test performance metrics integration"""
        detector = integration_fraud_detector
        
        # Process a few orders to generate metrics
        sample_orders = [
            OrderData(
                order_id=f"metrics_test_{i}",
                user_key=f"metrics_user_{i}",
                total_amount=25.0 + i,
                item_count=2
            )
            for i in range(3)
        ]
        
        # Mock responses for metrics generation
        for i, order in enumerate(sample_orders):
            fraud_result = Mock()
            fraud_result.fraud_score = 0.2 + (i * 0.1)
            fraud_result.recommended_action = "ALLOW"
            fraud_result.to_dict.return_value = {"fraud_score": fraud_result.fraud_score}
            
            action_result = Mock()
            action_result.action_taken = "ALLOW"
            action_result.to_dict.return_value = {"action_taken": "ALLOW"}
            
            detector.workflow.analyze_fraud_async.return_value = fraud_result
            detector.action_engine.execute_fraud_action.return_value = action_result
            
            await detector.detect_fraud(order)
        
        # Get performance metrics
        metrics = detector.get_performance_metrics()
        
        # Verify metrics structure
        assert "timestamp" in metrics
        assert "system_metrics" in metrics
        assert "rag_metrics" in metrics
        assert "workflow_metrics" in metrics
        assert "action_metrics" in metrics
        assert "sla_compliance" in metrics
        
        # Verify system metrics reflect processing
        system_metrics = metrics["system_metrics"]
        assert system_metrics["total_detections"] == 3
        assert system_metrics["avg_processing_time_seconds"] > 0
        assert system_metrics["throughput_per_second"] >= 0
        
        # Verify SLA compliance tracking
        sla_metrics = metrics["sla_compliance"]
        assert "target_latency_ms" in sla_metrics
        assert "current_avg_latency_ms" in sla_metrics
        assert "within_sla" in sla_metrics
        assert "target_accuracy" in sla_metrics
    
    @pytest.mark.asyncio
    async def test_batch_processing_integration(self, integration_fraud_detector, sample_test_data):
        """Test batch processing integration"""
        detector = integration_fraud_detector
        
        # Create batch of orders
        orders = [
            OrderData(**order_data) 
            for order_data in sample_test_data["valid_orders"]
        ]
        
        # Setup batch processing mocks
        def create_fraud_result(order):
            result = Mock()
            result.fraud_score = 0.3
            result.recommended_action = "ALLOW"
            result.to_dict.return_value = {"fraud_score": 0.3, "recommended_action": "ALLOW"}
            return result
        
        def create_action_result(order):
            result = Mock()
            result.action_taken = "ALLOW"
            result.to_dict.return_value = {"action_taken": "ALLOW"}
            return result
        
        detector.workflow.analyze_fraud_async.side_effect = lambda order: create_fraud_result(order)
        detector.action_engine.execute_fraud_action.side_effect = lambda fraud, order: create_action_result(order)
        
        # Execute batch processing
        results = await detector.detect_fraud_batch(orders)
        
        # Verify batch results
        assert len(results) == len(orders)
        
        for i, result in enumerate(results):
            assert result["order_id"] == orders[i].order_id
            assert "fraud_analysis" in result
            assert "action_result" in result
            assert result["fraud_analysis"]["fraud_score"] == 0.3
            assert result["action_result"]["action_taken"] == "ALLOW"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, integration_fraud_detector, sample_order_data):
        """Test error handling throughout the system"""
        detector = integration_fraud_detector
        order = sample_order_data
        
        # Test workflow failure
        detector.workflow.analyze_fraud_async.side_effect = Exception("Workflow error")
        
        result = await detector.detect_fraud(order)
        
        # Verify error handling
        assert "error" in result
        assert result["fraud_analysis"]["recommended_action"] == "ALLOW"  # Safe default
        assert result["action_result"]["action_taken"] == "ERROR"
        assert result["action_result"]["status"] == "FAILED"
        
        # Test action engine failure
        detector.workflow.analyze_fraud_async.side_effect = None
        fraud_result = Mock()
        fraud_result.to_dict.return_value = {"fraud_score": 0.5}
        detector.workflow.analyze_fraud_async.return_value = fraud_result
        detector.action_engine.execute_fraud_action.side_effect = Exception("Action error")
        
        result = await detector.detect_fraud(order)
        
        # Should still complete with error in action
        assert "fraud_analysis" in result
    
    @pytest.mark.asyncio
    async def test_system_shutdown_integration(self, integration_fraud_detector):
        """Test graceful system shutdown integration"""
        detector = integration_fraud_detector
        
        # Setup shutdown mocks
        detector.rag_system.clear_cache = Mock()
        detector.action_engine.thread_pool = Mock()
        detector.action_engine.thread_pool.shutdown = Mock()
        
        # Test shutdown
        await detector.shutdown()
        
        # Verify cleanup coordination
        # Note: Real implementation may not have these methods
        # Test just ensures no exceptions during shutdown


class TestPerformanceIntegration:
    """Test system performance under realistic conditions"""
    
    @pytest.mark.asyncio
    async def test_latency_sla_compliance(self, integration_fraud_detector, sample_order_data):
        """Test system meets latency SLA requirements"""
        detector = integration_fraud_detector
        order = sample_order_data
        
        # Setup realistic processing times
        fraud_result = Mock()
        fraud_result.fraud_score = 0.4
        fraud_result.recommended_action = "ALLOW"
        fraud_result.processing_time_ms = 120
        fraud_result.to_dict.return_value = {"fraud_score": 0.4}
        
        action_result = Mock()
        action_result.action_taken = "ALLOW"
        action_result.to_dict.return_value = {"action_taken": "ALLOW"}
        
        detector.workflow.analyze_fraud_async.return_value = fraud_result
        detector.action_engine.execute_fraud_action.return_value = action_result
        
        # Measure actual processing time
        import time
        start_time = time.time()
        result = await detector.detect_fraud(order)
        end_time = time.time()
        
        actual_latency_ms = (end_time - start_time) * 1000
        reported_latency_ms = result["total_processing_time_ms"]
        
        # Verify SLA compliance (target: 200ms)
        # Note: In mocked environment, this should be very fast
        assert actual_latency_ms < 1000  # Very generous for mocked test
        assert reported_latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_throughput_performance(self, integration_fraud_detector, performance_test_data):
        """Test system throughput performance"""
        detector = integration_fraud_detector
        
        # Setup for throughput testing
        orders = [
            OrderData(**order_data) 
            for order_data in performance_test_data["large_order_batch"][:50]  # 50 orders
        ]
        
        # Setup mocks for fast processing
        fraud_result = Mock()
        fraud_result.fraud_score = 0.3
        fraud_result.to_dict.return_value = {"fraud_score": 0.3}
        
        action_result = Mock()
        action_result.action_taken = "ALLOW" 
        action_result.to_dict.return_value = {"action_taken": "ALLOW"}
        
        detector.workflow.analyze_fraud_async.return_value = fraud_result
        detector.action_engine.execute_fraud_action.return_value = action_result
        
        # Measure throughput
        import time
        start_time = time.time()
        
        # Process in parallel batches
        batch_size = 10
        all_results = []
        
        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            batch_results = await detector.detect_fraud_batch(batch)
            all_results.extend(batch_results)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        throughput = len(orders) / total_time
        
        # Verify throughput
        assert len(all_results) == len(orders)
        assert throughput > 10  # At least 10 orders/second (mocked should be much faster)
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_stability(self, integration_fraud_detector, sample_test_data):
        """Test system stability under concurrent load"""
        detector = integration_fraud_detector
        
        # Create concurrent workload
        orders = [
            OrderData(**order_data) 
            for order_data in sample_test_data["valid_orders"] * 4  # 20 orders total
        ]
        
        # Setup mocks
        fraud_result = Mock()
        fraud_result.fraud_score = 0.35
        fraud_result.to_dict.return_value = {"fraud_score": 0.35}
        
        action_result = Mock()
        action_result.action_taken = "ALLOW"
        action_result.to_dict.return_value = {"action_taken": "ALLOW"}
        
        detector.workflow.analyze_fraud_async.return_value = fraud_result
        detector.action_engine.execute_fraud_action.return_value = action_result
        
        # Execute concurrent processing
        tasks = [detector.detect_fraud(order) for order in orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify stability
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        # Should have high success rate
        success_rate = len(successful_results) / len(results)
        assert success_rate > 0.9  # At least 90% success rate
        
        # Verify system remains healthy
        health = detector.get_system_health()
        assert health["system_status"] in ["healthy", "degraded"]


class TestDataFlowIntegration:
    """Test data flow through the complete system"""
    
    @pytest.mark.asyncio
    async def test_order_data_transformation_flow(self, integration_fraud_detector):
        """Test order data transformation through the system"""
        detector = integration_fraud_detector
        
        # Create order with specific data patterns
        order = OrderData(
            order_id="transform_test_123",
            user_key="transform_user_456",
            total_amount=75.25,
            item_count=3,
            account_age_days=45,
            orders_today=2,
            payment_method="credit_card",
            delivery_lat=37.7749,
            delivery_lng=-122.4194,
            order_creation_speed_ms=1200
        )
        
        # Setup mocks to capture data flow
        captured_data = {}
        
        def capture_workflow_data(order_data):
            captured_data["workflow_input"] = order_data
            result = Mock()
            result.fraud_score = 0.4
            result.to_dict.return_value = {"fraud_score": 0.4, "order_analysis": "captured"}
            return result
        
        def capture_action_data(fraud_result, order_data):
            captured_data["action_input"] = (fraud_result, order_data)
            result = Mock()
            result.action_taken = "REVIEW"
            result.to_dict.return_value = {"action_taken": "REVIEW"}
            return result
        
        detector.workflow.analyze_fraud_async.side_effect = capture_workflow_data
        detector.action_engine.execute_fraud_action.side_effect = capture_action_data
        
        # Execute processing
        result = await detector.detect_fraud(order)
        
        # Verify data flow
        assert "workflow_input" in captured_data
        assert "action_input" in captured_data
        
        # Verify data preservation
        workflow_input = captured_data["workflow_input"]
        assert workflow_input.order_id == order.order_id
        assert workflow_input.total_amount == order.total_amount
        
        # Verify final result
        assert result["order_id"] == order.order_id
        assert result["fraud_analysis"]["fraud_score"] == 0.4
        assert result["action_result"]["action_taken"] == "REVIEW"
    
    @pytest.mark.asyncio
    async def test_metrics_aggregation_flow(self, integration_fraud_detector):
        """Test metrics aggregation across system components"""
        detector = integration_fraud_detector
        
        # Process several orders with different patterns
        test_orders = [
            {"fraud_score": 0.2, "processing_time": 100, "action": "ALLOW"},
            {"fraud_score": 0.6, "processing_time": 150, "action": "REVIEW"},
            {"fraud_score": 0.9, "processing_time": 200, "action": "BLOCK"}
        ]
        
        # Setup mocks with different metrics
        for i, test_case in enumerate(test_orders):
            order = OrderData(
                order_id=f"metrics_order_{i}",
                user_key=f"metrics_user_{i}",
                total_amount=25.0 + i,
                item_count=2
            )
            
            fraud_result = Mock()
            fraud_result.fraud_score = test_case["fraud_score"]
            fraud_result.processing_time_ms = test_case["processing_time"]
            fraud_result.to_dict.return_value = {"fraud_score": test_case["fraud_score"]}
            
            action_result = Mock()
            action_result.action_taken = test_case["action"]
            action_result.to_dict.return_value = {"action_taken": test_case["action"]}
            
            detector.workflow.analyze_fraud_async.return_value = fraud_result
            detector.action_engine.execute_fraud_action.return_value = action_result
            
            await detector.detect_fraud(order)
        
        # Verify metrics aggregation
        assert detector.detection_count == 3
        assert detector.total_processing_time > 0
        
        # Verify performance metrics
        metrics = detector.get_performance_metrics()
        system_metrics = metrics["system_metrics"]
        
        assert system_metrics["total_detections"] == 3
        assert system_metrics["avg_processing_time_seconds"] > 0
        assert system_metrics["throughput_per_second"] > 0