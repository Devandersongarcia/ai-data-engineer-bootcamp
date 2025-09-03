"""Comprehensive testing suite for the modernized UberEats Multi-Agent System.

Tests cover:
- Base agent functionality and performance
- Agent team collaboration
- Workflow execution and state management
- Monitoring and observability features
- API endpoints and integration
"""
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.agents.base_agent import UberEatsBaseAgent
from src.config.settings import settings
from src.monitoring.observability import monitoring_system
from src.orchestration.agent_teams import UberEatsAgentTeam
from src.orchestration.agentic_workflows import UberEatsAgenticWorkflow, WorkflowState

@pytest.fixture
def test_settings():
    """Test configuration settings.
    
    Returns:
        Dictionary with test-specific configuration values.
    """
    return {
        "openai_api_key": "test_openai_key",
        "anthropic_api_key": "test_anthropic_key", 
        "database_url": "postgresql://test:test@localhost:5432/test_ubereats",
        "mongodb_connection_string": "mongodb://localhost:27017/test_ubereats",
        "qdrant_url": "http://localhost:6333",
        "log_level": "DEBUG",
        "enable_monitoring": True,
        "enable_agent_teams": True,
        "enable_workflows": True
    }

class TestBaseAgent:
    """Test the modernized base agent architecture.
    
    Validates Agno 1.1+ features including:
    - Agent initialization and configuration
    - Performance monitoring
    - Memory management
    - Error handling and timeouts
    """
    
    @pytest.mark.asyncio
    async def test_base_agent_initialization(self, test_settings):
        """Test proper base agent initialization with Agno 1.1+ features.
        
        Validates:
        - Model selection and configuration
        - Tool initialization
        - Memory system setup
        - Performance metrics initialization
        """
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.agents.base_agent.OpenAIChat') as mock_openai:
                mock_model = MagicMock()
                mock_openai.return_value = mock_model
                
                agent = UberEatsBaseAgent(
                    agent_id="test_agent",
                    instructions="Test instructions",
                    model_name="gpt-4o",
                    enable_reasoning=True,
                    enable_memory=True
                )
                
                # Verify agent properties
                assert agent.agent_id == "test_agent"
                assert agent.performance_metrics["requests_processed"] == 0
                assert agent.timeout == getattr(settings, 'agent_timeout', 300)
                assert hasattr(agent, 'memory')
                assert hasattr(agent, 'storage')
    
    @pytest.mark.asyncio
    async def test_agent_request_processing_with_metrics(self, test_settings):
        """Test agent request processing with performance tracking"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.agents.base_agent.OpenAIChat') as mock_openai, \
                 patch('src.agents.base_agent.PostgresStorage') as mock_storage, \
                 patch('src.agents.base_agent.AgentMemory') as mock_memory:
                
                # Setup mocks
                mock_model = MagicMock()
                mock_model.arun = AsyncMock(return_value="Test response")
                mock_openai.return_value = mock_model
                
                agent = UberEatsBaseAgent(
                    agent_id="test_agent",
                    instructions="Test instructions",
                    enable_reasoning=True,
                    enable_memory=True
                )
                agent.model = mock_model  # Direct assignment for testing
                
                # Test request processing
                request = {"message": "Test request", "priority": "normal"}
                result = await agent.process_request_with_metrics(request)
                
                # Verify result structure
                assert result["success"] is True
                assert "response" in result
                assert "processing_time" in result
                assert "agent_id" in result
                assert result["agent_id"] == "test_agent"
                
                # Verify metrics were updated
                assert agent.performance_metrics["requests_processed"] == 1
                assert agent.performance_metrics["last_activity"] is not None
    
    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, test_settings):
        """Test agent timeout protection"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.agents.base_agent.OpenAIChat') as mock_openai:
                
                # Mock a slow response that will timeout
                mock_model = MagicMock()
                mock_model.arun = AsyncMock(side_effect=asyncio.TimeoutError())
                mock_openai.return_value = mock_model
                
                agent = UberEatsBaseAgent(
                    agent_id="test_agent",
                    instructions="Test instructions"
                )
                agent.model = mock_model
                agent.timeout = 0.1  # Very short timeout for testing
                
                request = {"message": "Test timeout request"}
                result = await agent.process_request_with_metrics(request)
                
                # Verify timeout handling
                assert result["success"] is False
                assert "timeout" in result["error"].lower()
                assert result["error_type"] == "timeout"
    
    def test_agent_health_status(self, test_settings):
        """Test agent health status reporting"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.agents.base_agent.OpenAIChat') as mock_openai:
                mock_openai.return_value = MagicMock()
                
                agent = UberEatsBaseAgent(
                    agent_id="test_agent",
                    instructions="Test instructions"
                )
                
                # Test initial health status
                health = agent.get_health_status()
                
                assert health["agent_id"] == "test_agent"
                assert health["status"] == "healthy"  # No requests yet, so healthy
                assert "metrics" in health
                assert "capabilities" in health
                assert "configuration" in health

class TestAgentTeams:
    """Test Level 4 Agent Teams implementation"""
    
    @pytest.mark.asyncio
    async def test_agent_team_initialization(self, test_settings):
        """Test proper agent team initialization"""
        
        with patch('src.config.settings.settings', test_settings), \
             patch('src.orchestration.agent_teams.Claude') as mock_claude, \
             patch('src.orchestration.agent_teams.OpenAIChat') as mock_openai:
            
            # Mock model creation
            mock_claude.return_value = MagicMock()
            mock_openai.return_value = MagicMock()
            
            team = UberEatsAgentTeam()
            
            # Allow async initialization
            await asyncio.sleep(0.1)
            
            # Verify team structure
            assert hasattr(team, 'team_lead')
            assert hasattr(team, 'specialized_agents')
            assert hasattr(team, 'team_metrics')
    
    @pytest.mark.asyncio
    async def test_agent_involvement_determination(self, test_settings):
        """Test intelligent agent involvement logic"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agent_teams.Claude'), \
                 patch('src.orchestration.agent_teams.OpenAIChat'):
                
                team = UberEatsAgentTeam()
                await asyncio.sleep(0.1)  # Allow initialization
                
                # Test customer service request
                customer_request = {
                    "message": "I want to cancel my order and get a refund",
                    "customer_id": "test_customer"
                }
                agents = await team._determine_agent_involvement(customer_request, "test plan")
                assert "customer" in agents
                assert "order" in agents  # Cancel involves order processing
                
                # Test restaurant operations request
                restaurant_request = {
                    "message": "What's the preparation time for pizza?",
                    "customer_id": "test_customer"
                }
                agents = await team._determine_agent_involvement(restaurant_request, "test plan")
                assert "restaurant" in agents
                
                # Test delivery request
                delivery_request = {
                    "message": "Where is my delivery driver?",
                    "customer_id": "test_customer"
                }
                agents = await team._determine_agent_involvement(delivery_request, "test plan")
                assert "delivery" in agents
    
    @pytest.mark.asyncio
    async def test_team_collaboration_processing(self, test_settings):
        """Test end-to-end team collaboration"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agent_teams.Claude') as mock_claude, \
                 patch('src.orchestration.agent_teams.OpenAIChat') as mock_openai:
                
                # Setup mock responses
                mock_orchestrator = MagicMock()
                mock_orchestrator.arun = AsyncMock(return_value="Orchestration plan")
                mock_claude.return_value = mock_orchestrator
                
                mock_agent_model = MagicMock()
                mock_agent_model.arun = AsyncMock(return_value="Agent response")
                mock_openai.return_value = mock_agent_model
                
                team = UberEatsAgentTeam()
                team.team_lead = mock_orchestrator
                
                # Create mock specialized agents
                team.specialized_agents = {
                    'customer': MagicMock(),
                    'order': MagicMock()
                }
                
                # Mock agent processing
                for agent in team.specialized_agents.values():
                    agent.arun = AsyncMock(return_value="Mock agent response")
                
                # Test request processing
                request = {
                    "message": "Help with order cancellation",
                    "customer_id": "test_customer",
                    "session_id": "test_session"
                }
                
                result = await team.process_request(request)
                
                # Verify result structure
                assert "session_id" in result
                assert "final_response" in result
                assert "involved_agents" in result
                assert "orchestration_plan" in result
                assert "collaboration_type" in result

class TestAgenticWorkflows:
    """Test Level 5 Agentic Workflows implementation"""
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, test_settings):
        """Test workflow engine initialization"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agentic_workflows.Claude') as mock_claude, \
                 patch('src.orchestration.agentic_workflows.OpenAIChat') as mock_openai:
                
                mock_claude.return_value = MagicMock()
                mock_openai.return_value = MagicMock()
                
                workflow = UberEatsAgenticWorkflow()
                
                # Verify workflow components
                assert hasattr(workflow, 'analyzer_agent')
                assert hasattr(workflow, 'coordinator_agent')
                assert hasattr(workflow, 'qa_agent')
                assert hasattr(workflow, 'current_state')
                assert hasattr(workflow, 'performance_metrics')
    
    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, test_settings):
        """Test deterministic workflow state transitions"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agentic_workflows.Claude'), \
                 patch('src.orchestration.agentic_workflows.OpenAIChat'):
                
                workflow = UberEatsAgenticWorkflow()
                workflow_id = "test_workflow_001"
                
                # Test state transition
                await workflow._transition_state(
                    WorkflowState.ANALYZING, 
                    workflow_id, 
                    {"test": "context"}
                )
                
                assert workflow.current_state == WorkflowState.ANALYZING
                assert workflow_id in workflow.state_transitions
                assert len(workflow.state_transitions[workflow_id]) > 0
                
                # Verify transition data
                transition = workflow.state_transitions[workflow_id][0]
                assert transition["to_state"] == WorkflowState.ANALYZING.value
                assert transition["workflow_id"] == workflow_id
                assert "timestamp" in transition
    
    @pytest.mark.asyncio
    async def test_workflow_execution_stages(self, test_settings):
        """Test workflow execution through all stages"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agentic_workflows.Claude') as mock_claude, \
                 patch('src.orchestration.agentic_workflows.OpenAIChat') as mock_openai:
                
                # Setup mock agents
                mock_agent = MagicMock()
                mock_agent.arun = AsyncMock(return_value="Mock stage response")
                mock_claude.return_value = mock_agent
                mock_openai.return_value = mock_agent
                
                workflow = UberEatsAgenticWorkflow()
                workflow.analyzer_agent = mock_agent
                workflow.coordinator_agent = mock_agent
                workflow.qa_agent = mock_agent
                
                # Test execution
                request = {
                    "request_type": "test_workflow",
                    "data": {"test": "data"},
                    "session_id": "test_session"
                }
                
                result = await workflow.execute_workflow(request)
                
                # Verify execution stages
                assert "execution_stages" in result
                stages = result["execution_stages"]
                assert "analysis" in stages
                assert "processing" in stages
                assert "synthesis" in stages
                assert "validation" in stages
    
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, test_settings):
        """Test workflow error handling and recovery"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agentic_workflows.Claude') as mock_claude:
                
                # Mock failing agent
                mock_agent = MagicMock()
                mock_agent.arun = AsyncMock(side_effect=Exception("Test error"))
                mock_claude.return_value = mock_agent
                
                workflow = UberEatsAgenticWorkflow()
                workflow.analyzer_agent = mock_agent
                
                # Test error handling
                request = {
                    "request_type": "test_workflow",
                    "data": {"test": "data"}
                }
                
                result = await workflow.execute_workflow(request)
                
                # Verify error handling
                assert result["success"] is False
                assert "error" in result
                assert "recovery_options" in result
    
    @pytest.mark.asyncio
    async def test_workflow_performance_metrics(self, test_settings):
        """Test workflow performance tracking"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agentic_workflows.Claude'), \
                 patch('src.orchestration.agentic_workflows.OpenAIChat'):
                
                workflow = UberEatsAgenticWorkflow()
                
                # Test metrics update
                workflow._update_performance_metrics(5.2, True)
                workflow._update_performance_metrics(3.8, True)
                workflow._update_performance_metrics(10.1, False)
                
                metrics = workflow.get_performance_metrics()
                
                assert metrics["total_workflows"] == 3
                assert metrics["successful_workflows"] == 2
                assert metrics["failed_workflows"] == 1
                assert metrics["success_rate"] == (2/3) * 100
                assert metrics["average_execution_time"] > 0

class TestMonitoringSystem:
    """Test comprehensive monitoring and observability"""
    
    def test_monitoring_initialization(self):
        """Test monitoring system initialization"""
        
        # Monitoring system is a global instance
        assert hasattr(monitoring_system, 'agent_metrics')
        assert hasattr(monitoring_system, 'workflow_metrics')
        assert hasattr(monitoring_system, 'system_alerts')
        assert hasattr(monitoring_system, 'performance_baselines')
    
    def test_agent_metrics_recording(self):
        """Test agent metrics recording"""
        
        # Record some test metrics
        monitoring_system.record_agent_request("test_agent", 1.5, True, "normal")
        monitoring_system.record_agent_request("test_agent", 2.0, True, "high")
        monitoring_system.record_agent_request("test_agent", 0.5, False, "normal")
        
        # Verify metrics
        metrics = monitoring_system.agent_metrics["test_agent"]
        assert metrics.requests_processed == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.success_rate == (2/3) * 100
        assert metrics.avg_response_time > 0
    
    def test_workflow_metrics_recording(self):
        """Test workflow metrics recording"""
        
        # Record workflow execution
        monitoring_system.record_workflow_execution(
            "test_workflow_001",
            "order_processing", 
            8.5,
            0.95,
            ["customer_agent", "order_agent"],
            True
        )
        
        # Verify workflow metrics
        workflow_metrics = monitoring_system.workflow_metrics["test_workflow_001"]
        assert workflow_metrics.workflow_type == "order_processing"
        assert workflow_metrics.execution_time == 8.5
        assert workflow_metrics.quality_score == 0.95
        assert workflow_metrics.success is True
        assert "customer_agent" in workflow_metrics.agents_involved
    
    def test_system_health_calculation(self):
        """Test system health score calculation"""
        
        # Add some test data
        monitoring_system.record_agent_request("agent1", 1.0, True)
        monitoring_system.record_agent_request("agent2", 2.0, True) 
        monitoring_system.record_agent_request("agent3", 1.5, False)
        
        health_score = monitoring_system.calculate_system_health()
        
        assert 0.0 <= health_score <= 1.0
        assert isinstance(health_score, float)
    
    def test_monitoring_dashboard_data(self):
        """Test monitoring dashboard data generation"""
        
        # Add test data
        monitoring_system.record_agent_request("dashboard_agent", 1.2, True)
        monitoring_system.record_workflow_execution(
            "dashboard_workflow", "test_type", 5.0, 0.9, ["dashboard_agent"], True
        )
        
        dashboard_data = monitoring_system.get_monitoring_dashboard_data()
        
        # Verify dashboard structure
        assert "system_health" in dashboard_data
        assert "agent_metrics" in dashboard_data
        assert "workflow_metrics" in dashboard_data
        assert "recent_alerts" in dashboard_data
        assert "performance_baselines" in dashboard_data
        assert "timestamp" in dashboard_data

class TestProductionAPI:
    """Test production FastAPI endpoints"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock the API dependencies"""
        mock_team = MagicMock()
        mock_team.process_request = AsyncMock(return_value={
            "session_id": "test_session",
            "final_response": "Test response",
            "involved_agents": ["customer"],
            "processing_time": 1.5,
            "success": True
        })
        mock_team.get_team_health_status = AsyncMock(return_value={
            "orchestrator": {"status": "healthy"},
            "specialized_agents": {"customer": {"status": "healthy"}},
            "team_health_score": 0.95
        })
        
        mock_workflow = MagicMock()
        mock_workflow.execute_workflow = AsyncMock(return_value={
            "workflow_id": "test_workflow",
            "final_result": {"response": "Test workflow result"},
            "execution_time": 5.2,
            "quality_score": 0.96,
            "success": True,
            "execution_stages": {}
        })
        mock_workflow.get_performance_metrics = MagicMock(return_value={
            "success_rate": 95.0,
            "active_workflows": 0
        })
        
        return mock_team, mock_workflow
    
    def test_api_initialization(self):
        """Test FastAPI app initialization"""
        
        from src.api.production_api import app
        
        assert app.title == settings.api_title
        assert app.version == settings.api_version
    
    def test_health_check_endpoint(self, mock_dependencies):
        """Test health check endpoint"""
        
        mock_team, mock_workflow = mock_dependencies
        
        with patch('src.api.production_api.agent_team', mock_team), \
             patch('src.api.production_api.workflow_engine', mock_workflow):
            
            from src.api.production_api import app
            client = TestClient(app)
            
            response = client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "agents_healthy" in data
            assert "workflows_active" in data
            assert "system_metrics" in data

class TestPerformanceBenchmarks:
    """Performance and load testing"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_agent_response_time_benchmark(self, test_settings):
        """Benchmark agent response times for Agno 1.1+ performance"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.agents.base_agent.OpenAIChat') as mock_openai:
                
                # Mock fast model response
                mock_model = MagicMock()
                mock_model.arun = AsyncMock(return_value="Fast response")
                mock_openai.return_value = mock_model
                
                agent = UberEatsBaseAgent(
                    agent_id="benchmark_agent",
                    instructions="Test instructions"
                )
                agent.model = mock_model
                
                # Benchmark multiple requests
                import time
                response_times = []
                
                for i in range(10):
                    start_time = time.time()
                    result = await agent.process_request_with_metrics({
                        "message": f"Benchmark request {i}"
                    })
                    end_time = time.time()
                    
                    if result.get("success"):
                        response_times.append(end_time - start_time)
                
                # Verify performance meets Agno 1.1+ expectations
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                # With mocked responses, should be very fast
                assert avg_response_time < 0.1  # Less than 100ms
                assert max_response_time < 0.2  # No response over 200ms
                
                print(f"Benchmark Results:")
                print(f"  Average Response Time: {avg_response_time:.4f}s")
                print(f"  Max Response Time: {max_response_time:.4f}s")
                print(f"  Total Requests: {len(response_times)}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, test_settings):
        """Test concurrent request processing capability"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agent_teams.Claude') as mock_claude, \
                 patch('src.orchestration.agent_teams.OpenAIChat') as mock_openai:
                
                # Setup mock responses
                mock_model = MagicMock()
                mock_model.arun = AsyncMock(return_value="Concurrent response")
                mock_claude.return_value = mock_model
                mock_openai.return_value = mock_model
                
                team = UberEatsAgentTeam()
                team.team_lead = mock_model
                team.specialized_agents = {'customer': mock_model}
                
                # Create concurrent requests
                async def make_request(request_id):
                    return await team.process_request({
                        "message": f"Concurrent request {request_id}",
                        "session_id": f"concurrent_session_{request_id}"
                    })
                
                # Execute 20 concurrent requests
                start_time = time.time()
                tasks = [make_request(i) for i in range(20)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                # Analyze results
                successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success")]
                failed_results = [r for r in results if isinstance(r, Exception) or not r.get("success")]
                
                total_time = end_time - start_time
                success_rate = len(successful_results) / len(results) * 100
                
                print(f"Concurrent Processing Results:")
                print(f"  Total Requests: {len(results)}")
                print(f"  Successful: {len(successful_results)}")
                print(f"  Failed: {len(failed_results)}")
                print(f"  Success Rate: {success_rate:.1f}%")
                print(f"  Total Time: {total_time:.3f}s")
                print(f"  Throughput: {len(results)/total_time:.1f} req/s")
                
                # Verify concurrent processing capability
                assert success_rate > 90  # At least 90% success rate
                assert total_time < 30    # Complete within 30 seconds

# Integration tests
class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_order_processing(self, test_settings):
        """Test complete order processing flow"""
        
        with patch('src.config.settings.settings', test_settings):
            with patch('src.orchestration.agent_teams.Claude') as mock_claude, \
                 patch('src.orchestration.agent_teams.OpenAIChat') as mock_openai, \
                 patch('src.orchestration.agentic_workflows.Claude') as mock_wf_claude, \
                 patch('src.orchestration.agentic_workflows.OpenAIChat') as mock_wf_openai:
                
                # Setup mocks
                mock_agent = MagicMock()
                mock_agent.arun = AsyncMock(return_value="Integration test response")
                mock_claude.return_value = mock_agent
                mock_openai.return_value = mock_agent
                mock_wf_claude.return_value = mock_agent
                mock_wf_openai.return_value = mock_agent
                
                # Initialize systems
                agent_team = UberEatsAgentTeam()
                workflow_engine = UberEatsAgenticWorkflow()
                
                await asyncio.sleep(0.1)  # Allow initialization
                
                # Mock the internal components
                agent_team.team_lead = mock_agent
                agent_team.specialized_agents = {
                    'customer': mock_agent,
                    'restaurant': mock_agent,
                    'order': mock_agent
                }
                
                workflow_engine.analyzer_agent = mock_agent
                workflow_engine.coordinator_agent = mock_agent
                workflow_engine.qa_agent = mock_agent
                
                # Test order processing through agent team
                order_request = {
                    "message": "I want to place an order for 2 pizzas from Tony's Restaurant",
                    "customer_id": "integration_customer_001",
                    "session_id": "integration_session_001"
                }
                
                team_result = await agent_team.process_request(order_request)
                assert team_result.get("success") is True
                
                # Test order processing through workflow
                workflow_request = {
                    "request_type": "order_processing",
                    "data": {
                        "customer_id": "integration_customer_001",
                        "restaurant_id": "tonys_restaurant",
                        "items": [{"name": "Margherita Pizza", "quantity": 2}]
                    },
                    "session_id": "integration_workflow_001"
                }
                
                workflow_result = await workflow_engine.execute_workflow(workflow_request)
                assert workflow_result.get("success") is True
                
                # Verify monitoring captured the activities
                dashboard_data = monitoring_system.get_monitoring_dashboard_data()
                assert dashboard_data["system_health"]["score"] > 0

# Run tests with coverage
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--asyncio-mode=auto",
        "-m", "not performance"  # Skip performance tests by default
    ])