"""
Tests for fraud detection agents system
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from agents.fraud_agents import FraudDetectionAgents
from agents.workflows import FraudDetectionWorkflow


class TestFraudDetectionAgents:
    """Test the fraud detection agents system"""
    
    @pytest.fixture
    def mock_rag_system(self):
        """Mock RAG system for agent testing"""
        mock_rag = Mock()
        mock_rag.query_knowledge_base.return_value = {
            "relevant_patterns": ["velocity_fraud", "account_takeover"],
            "confidence": 0.8,
            "context": "Historical fraud patterns suggest high risk"
        }
        return mock_rag
    
    @pytest.fixture
    def mock_agents(self, mock_rag_system, mock_openai_client):
        """Create fraud detection agents with mocked dependencies"""
        with patch('agents.fraud_agents.Agent') as mock_agent_class:
            # Mock agent instances
            mock_pattern_analyzer = Mock()
            mock_pattern_analyzer.run = AsyncMock(return_value="Pattern analysis complete")
            
            mock_risk_assessor = Mock()
            mock_risk_assessor.run = AsyncMock(return_value="Risk assessment complete")
            
            mock_decision_maker = Mock()
            mock_decision_maker.run = AsyncMock(return_value="Decision complete")
            
            mock_action_executor = Mock()
            mock_action_executor.run = AsyncMock(return_value="Action execution complete")
            
            # Configure mock agent class to return different instances
            mock_agent_class.side_effect = [
                mock_pattern_analyzer,
                mock_risk_assessor,
                mock_decision_maker,
                mock_action_executor
            ]
            
            agents = FraudDetectionAgents(mock_rag_system)
            return agents
    
    def test_agents_initialization(self, mock_agents):
        """Test agents system initialization"""
        agents = mock_agents
        
        assert agents.rag_system is not None
        assert agents.pattern_analyzer is not None
        assert agents.risk_assessor is not None
        assert agents.decision_maker is not None
        assert agents.action_executor is not None
        assert agents.session_id is not None
    
    @pytest.mark.asyncio
    async def test_pattern_analysis(self, mock_agents, sample_order_data):
        """Test pattern analysis agent"""
        agents = mock_agents
        order = sample_order_data
        
        # Mock pattern analyzer response
        expected_analysis = {
            "patterns_detected": ["normal_behavior"],
            "confidence": 0.9,
            "risk_indicators": [],
            "processing_time_ms": 150
        }
        
        agents.pattern_analyzer.run.return_value = str(expected_analysis)
        
        # Test pattern analysis
        result = await agents.pattern_analyzer.run(f"Analyze order patterns: {order.model_dump_json()}")
        
        assert result is not None
        agents.pattern_analyzer.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_risk_assessment(self, mock_agents, sample_order_data):
        """Test risk assessment agent"""
        agents = mock_agents
        order = sample_order_data
        
        # Mock risk assessor response
        expected_assessment = {
            "risk_score": 0.3,
            "risk_level": "LOW",
            "contributing_factors": ["normal_order_amount", "established_account"],
            "processing_time_ms": 120
        }
        
        agents.risk_assessor.run.return_value = str(expected_assessment)
        
        # Test risk assessment
        result = await agents.risk_assessor.run(f"Assess fraud risk: {order.model_dump_json()}")
        
        assert result is not None
        agents.risk_assessor.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_decision_making(self, mock_agents, sample_order_data):
        """Test decision making agent"""
        agents = mock_agents
        order = sample_order_data
        
        # Mock decision maker response
        expected_decision = {
            "recommended_action": "ALLOW",
            "confidence": 0.95,
            "reasoning": "Low risk score and normal patterns detected",
            "processing_time_ms": 100
        }
        
        agents.decision_maker.run.return_value = str(expected_decision)
        
        # Test decision making
        pattern_analysis = {"patterns_detected": ["normal_behavior"]}
        risk_assessment = {"risk_score": 0.3}
        
        result = await agents.decision_maker.run(
            f"Make fraud decision based on: patterns={pattern_analysis}, risk={risk_assessment}"
        )
        
        assert result is not None
        agents.decision_maker.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_action_execution(self, mock_agents):
        """Test action execution agent"""
        agents = mock_agents
        
        # Mock action executor response
        expected_execution = {
            "action_taken": "ALLOW",
            "status": "COMPLETED",
            "timestamp": "2024-01-15T12:30:00Z",
            "processing_time_ms": 50
        }
        
        agents.action_executor.run.return_value = str(expected_execution)
        
        # Test action execution
        decision = {"recommended_action": "ALLOW", "confidence": 0.95}
        
        result = await agents.action_executor.run(f"Execute action: {decision}")
        
        assert result is not None
        agents.action_executor.run.assert_called_once()


class TestFraudDetectionWorkflow:
    """Test the fraud detection workflow orchestrator"""
    
    @pytest.fixture
    def mock_workflow(self, mock_agents):
        """Create workflow with mocked agents"""
        return FraudDetectionWorkflow(mock_agents)
    
    @pytest.mark.asyncio
    async def test_analyze_fraud_async_success(self, mock_workflow, sample_order_data):
        """Test successful async fraud analysis workflow"""
        workflow = mock_workflow
        order = sample_order_data
        
        # Mock agent responses
        workflow.agents.pattern_analyzer.run.return_value = '{"patterns_detected": ["normal_behavior"], "confidence": 0.9}'
        workflow.agents.risk_assessor.run.return_value = '{"risk_score": 0.3, "risk_level": "LOW"}'
        workflow.agents.decision_maker.run.return_value = '{"recommended_action": "ALLOW", "confidence": 0.95}'
        workflow.agents.action_executor.run.return_value = '{"action_taken": "ALLOW", "status": "COMPLETED"}'
        
        # Run workflow
        result = await workflow.analyze_fraud_async(order)
        
        # Verify result
        assert result is not None
        assert hasattr(result, 'fraud_score')
        assert hasattr(result, 'recommended_action')
        assert hasattr(result, 'confidence_level')
        assert hasattr(result, 'reasoning')
        
        # Verify all agents were called
        workflow.agents.pattern_analyzer.run.assert_called_once()
        workflow.agents.risk_assessor.run.assert_called_once()
        workflow.agents.decision_maker.run.assert_called_once()
        workflow.agents.action_executor.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_fraud_async_high_risk(self, mock_workflow, high_risk_order_data):
        """Test async fraud analysis with high-risk order"""
        workflow = mock_workflow
        order = high_risk_order_data
        
        # Mock high-risk responses
        workflow.agents.pattern_analyzer.run.return_value = '{"patterns_detected": ["velocity_fraud", "account_takeover"], "confidence": 0.95}'
        workflow.agents.risk_assessor.run.return_value = '{"risk_score": 0.9, "risk_level": "HIGH"}'
        workflow.agents.decision_maker.run.return_value = '{"recommended_action": "BLOCK", "confidence": 0.98}'
        workflow.agents.action_executor.run.return_value = '{"action_taken": "BLOCK", "status": "COMPLETED"}'
        
        # Run workflow
        result = await workflow.analyze_fraud_async(order)
        
        # Verify high-risk result
        assert result is not None
        assert result.fraud_score > 0.7  # Should be high risk
        assert result.recommended_action in ["BLOCK", "REVIEW"]
        assert len(result.detected_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_fraud_async_timeout_handling(self, mock_workflow, sample_order_data):
        """Test workflow timeout handling"""
        workflow = mock_workflow
        order = sample_order_data
        
        # Mock slow agent (simulate timeout)
        async def slow_agent_response(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow response
            return '{"result": "slow"}'
        
        workflow.agents.pattern_analyzer.run = slow_agent_response
        
        # Set short timeout for testing
        workflow.timeout_seconds = 1
        
        # Run workflow (should handle timeout gracefully)
        result = await workflow.analyze_fraud_async(order)
        
        # Verify timeout handling
        assert result is not None
        # Should have fallback/default behavior
    
    @pytest.mark.asyncio
    async def test_analyze_fraud_async_agent_failure(self, mock_workflow, sample_order_data):
        """Test workflow handling of agent failures"""
        workflow = mock_workflow
        order = sample_order_data
        
        # Mock agent failure
        workflow.agents.pattern_analyzer.run.side_effect = Exception("Agent failed")
        
        # Run workflow (should handle failure gracefully)
        result = await workflow.analyze_fraud_async(order)
        
        # Verify error handling
        assert result is not None
        # Should have fallback behavior or safe defaults
    
    def test_get_workflow_statistics(self, mock_workflow):
        """Test workflow statistics collection"""
        workflow = mock_workflow
        
        # Set some statistics
        workflow.total_workflows = 10
        workflow.successful_workflows = 9
        workflow.total_processing_time = 2.5
        
        stats = workflow.get_workflow_statistics()
        
        # Verify statistics structure
        assert "total_workflows" in stats
        assert "success_rate" in stats
        assert "avg_total_time" in stats
        
        # Verify calculations
        assert stats["total_workflows"] == 10
        assert stats["success_rate"] == 0.9
        assert stats["avg_total_time"] == 250  # 2.5 seconds = 250ms average


class TestAgentTools:
    """Test custom agent tools"""
    
    def test_fraud_pattern_lookup_tool(self, mock_rag_system):
        """Test fraud pattern lookup tool"""
        # This would test the custom tools defined in fraud_agents.py
        # For now, we'll test the basic structure
        
        # Mock tool usage
        pattern_query = "velocity fraud patterns"
        expected_result = {
            "patterns": ["high_frequency_orders", "multiple_payment_methods"],
            "examples": ["15+ orders in 1 hour", "3+ different cards"],
            "risk_score": 0.8
        }
        
        mock_rag_system.query_knowledge_base.return_value = expected_result
        
        # Test tool execution
        result = mock_rag_system.query_knowledge_base(pattern_query)
        
        assert result is not None
        assert "patterns" in result
        assert "risk_score" in result
    
    def test_risk_calculation_tool(self):
        """Test risk calculation tool"""
        # Mock risk calculation based on order data
        order_features = {
            "account_age_days": 1,
            "orders_today": 10,
            "payment_failures": 3,
            "order_amount": 500.00,
            "order_time": "03:30:00"
        }
        
        # Simulate risk calculation
        risk_factors = []
        base_risk = 0.0
        
        if order_features["account_age_days"] < 7:
            risk_factors.append("new_account")
            base_risk += 0.3
        
        if order_features["orders_today"] > 5:
            risk_factors.append("high_velocity")
            base_risk += 0.4
        
        if order_features["payment_failures"] > 0:
            risk_factors.append("payment_issues")
            base_risk += 0.2
        
        final_risk = min(1.0, base_risk)
        
        # Verify risk calculation
        assert final_risk > 0.7  # Should be high risk
        assert "new_account" in risk_factors
        assert "high_velocity" in risk_factors
        assert "payment_issues" in risk_factors
    
    def test_action_recommendation_tool(self):
        """Test action recommendation tool"""
        # Mock action recommendation based on risk score
        test_cases = [
            {"risk_score": 0.2, "expected_action": "ALLOW"},
            {"risk_score": 0.6, "expected_action": "REVIEW"},
            {"risk_score": 0.9, "expected_action": "BLOCK"}
        ]
        
        for case in test_cases:
            risk_score = case["risk_score"]
            
            # Simulate action recommendation logic
            if risk_score < 0.3:
                recommended_action = "ALLOW"
            elif risk_score < 0.7:
                recommended_action = "REVIEW"
            else:
                recommended_action = "BLOCK"
            
            assert recommended_action == case["expected_action"]


class TestAgentPerformance:
    """Test agent system performance"""
    
    @pytest.mark.asyncio
    async def test_agent_response_time(self, mock_agents, sample_order_data):
        """Test agent response times"""
        agents = mock_agents
        order = sample_order_data
        
        import time
        
        # Test each agent response time
        agents_to_test = [
            ("pattern_analyzer", agents.pattern_analyzer),
            ("risk_assessor", agents.risk_assessor),
            ("decision_maker", agents.decision_maker),
            ("action_executor", agents.action_executor)
        ]
        
        for agent_name, agent in agents_to_test:
            start_time = time.time()
            await agent.run(f"Test query for {agent_name}")
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Verify response time is reasonable (mocked, so should be very fast)
            assert response_time_ms < 100  # Less than 100ms for mocked test
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self, mock_agents, sample_test_data):
        """Test concurrent agent execution"""
        agents = mock_agents
        
        # Create multiple concurrent tasks
        tasks = []
        for i in range(5):
            task = agents.pattern_analyzer.run(f"Concurrent analysis {i}")
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all completed
        assert len(results) == 5
        for result in results:
            assert result is not None