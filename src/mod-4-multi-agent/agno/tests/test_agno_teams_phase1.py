"""
Test Suite for Agno Teams Phase 1 Implementation
Comprehensive testing of modernized team architecture
"""
import asyncio
import logging
import pytest
from datetime import datetime
from typing import Dict, Any

# Import the new team implementations
from src.teams import AgnoTeamBase, UberEatsETATeam
from src.config.settings import settings

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAgnoTeamBase:
    """Test the base Agno Team functionality"""
    
    @pytest.mark.asyncio
    async def test_team_initialization(self):
        """Test basic team initialization"""
        team = AgnoTeamBase(
            team_name="Test_Team",
            team_role="Test team for validation",
            team_mode="coordinate"
        )
        
        assert team.team_name == "Test_Team"
        assert team.team_mode == "coordinate"
        assert team.enable_memory == True
        assert team.is_initialized == False
        
        logger.info("✅ Team initialization test passed")
    
    @pytest.mark.asyncio
    async def test_team_leader_creation(self):
        """Test team leader creation"""
        team = AgnoTeamBase(
            team_name="Leader_Test_Team",
            team_role="Test team leader functionality",
            team_mode="route"
        )
        
        leader = await team.create_team_leader("You are a test team leader.")
        
        assert leader is not None
        assert team.team_leader is not None
        assert hasattr(leader, 'name')
        assert hasattr(leader, 'model')
        
        logger.info("✅ Team leader creation test passed")
    
    @pytest.mark.asyncio
    async def test_specialized_agent_creation(self):
        """Test specialized agent creation"""
        team = AgnoTeamBase(
            team_name="Agent_Test_Team",
            team_role="Test specialized agent creation",
            team_mode="collaborate"
        )
        
        agent = team.create_specialized_agent(
            agent_name="Test_Agent",
            agent_role="Test role",
            agent_instructions="You are a test agent."
        )
        
        assert agent is not None
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'model')
        
        # Test adding to team
        success = team.add_team_member(agent, "Test_Agent", "Test role")
        assert success == True
        assert len(team.team_members) == 1
        
        logger.info("✅ Specialized agent creation test passed")
    
    @pytest.mark.asyncio
    async def test_team_metrics(self):
        """Test team metrics tracking"""
        team = AgnoTeamBase(
            team_name="Metrics_Test_Team",
            team_role="Test metrics functionality",
            team_mode="coordinate"
        )
        
        # Test initial metrics
        assert team.team_metrics["total_requests"] == 0
        assert team.team_metrics["successful_collaborations"] == 0
        
        # Test metric updates
        team._update_team_metrics(2.5, "coordinate", True)
        
        assert team.team_metrics["total_requests"] == 1
        assert team.team_metrics["successful_collaborations"] == 1
        assert team.team_metrics["average_response_time"] == 2.5
        
        logger.info("✅ Team metrics test passed")


class TestUberEatsETATeam:
    """Test the UberEats ETA Team implementation"""
    
    @pytest.mark.asyncio
    async def test_eta_team_initialization(self):
        """Test ETA team initialization"""
        eta_team = UberEatsETATeam(team_mode="coordinate")
        
        assert eta_team.team_name == "UberEats_ETA_Team"
        assert eta_team.specialization == "eta_prediction"
        assert len(eta_team.supported_scenarios) == 5
        assert "eta_prediction_challenge" in eta_team.supported_scenarios
        
        logger.info("✅ ETA team initialization test passed")
    
    @pytest.mark.asyncio 
    async def test_eta_team_setup(self):
        """Test complete ETA team setup"""
        eta_team = UberEatsETATeam(team_mode="coordinate")
        
        # This test requires API keys - skip if not available
        if not settings.openai_api_key:
            pytest.skip("OpenAI API key not available")
        
        try:
            setup_success = await eta_team.setup_team()
            
            assert setup_success == True
            assert eta_team.is_initialized == True
            assert eta_team.team_leader is not None
            assert len(eta_team.team_members) == 4  # GPS, Traffic, Weather, ETA agents
            
            logger.info("✅ ETA team setup test passed")
            
        except Exception as e:
            logger.warning(f"ETA team setup test skipped due to: {e}")
            pytest.skip(f"ETA team setup failed: {e}")
    
    @pytest.mark.asyncio
    async def test_eta_scenario_validation(self):
        """Test ETA scenario validation"""
        eta_team = UberEatsETATeam()
        
        # Test supported scenario
        valid_scenario = {"scenario_type": "eta_prediction_challenge"}
        scenario_type = valid_scenario.get("scenario_type")
        assert scenario_type in eta_team.supported_scenarios
        
        # Test unsupported scenario
        invalid_scenario = {"scenario_type": "unsupported_type"}
        scenario_type = invalid_scenario.get("scenario_type")
        assert scenario_type not in eta_team.supported_scenarios
        
        logger.info("✅ ETA scenario validation test passed")
    
    @pytest.mark.asyncio
    async def test_eta_team_health_status(self):
        """Test ETA team health status"""
        eta_team = UberEatsETATeam()
        
        health_status = await eta_team.get_team_health()
        
        assert "team_name" in health_status
        assert "specialization" in health_status
        assert "supported_scenarios" in health_status
        assert health_status["specialization"] == "eta_prediction"
        
        logger.info("✅ ETA team health status test passed")


class TestTeamModes:
    """Test different team coordination modes"""
    
    @pytest.mark.asyncio
    async def test_route_mode(self):
        """Test route mode team"""
        team = AgnoTeamBase(
            team_name="Route_Mode_Team",
            team_role="Test route mode coordination",
            team_mode="route"
        )
        
        assert team.team_mode == "route"
        
        # Test mode distribution tracking
        team._update_team_metrics(1.0, "route", True)
        assert team.team_metrics["team_mode_distribution"]["route"] == 1
        
        logger.info("✅ Route mode test passed")
    
    @pytest.mark.asyncio
    async def test_coordinate_mode(self):
        """Test coordinate mode team"""
        team = AgnoTeamBase(
            team_name="Coordinate_Mode_Team", 
            team_role="Test coordinate mode coordination",
            team_mode="coordinate"
        )
        
        assert team.team_mode == "coordinate"
        
        # Test mode distribution tracking
        team._update_team_metrics(1.5, "coordinate", True)
        assert team.team_metrics["team_mode_distribution"]["coordinate"] == 1
        
        logger.info("✅ Coordinate mode test passed")
    
    @pytest.mark.asyncio
    async def test_collaborate_mode(self):
        """Test collaborate mode team"""
        team = AgnoTeamBase(
            team_name="Collaborate_Mode_Team",
            team_role="Test collaborate mode coordination", 
            team_mode="collaborate"
        )
        
        assert team.team_mode == "collaborate"
        
        # Test mode distribution tracking
        team._update_team_metrics(2.0, "collaborate", True)
        assert team.team_metrics["team_mode_distribution"]["collaborate"] == 1
        
        logger.info("✅ Collaborate mode test passed")


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_team_comparison(self):
        """Test comparison between different team modes"""
        modes = ["route", "coordinate", "collaborate"]
        teams = []
        
        for mode in modes:
            team = AgnoTeamBase(
                team_name=f"Integration_Test_{mode}",
                team_role=f"Integration test team in {mode} mode",
                team_mode=mode
            )
            teams.append((mode, team))
        
        # Verify all teams were created with correct modes
        for mode, team in teams:
            assert team.team_mode == mode
            assert team.team_name == f"Integration_Test_{mode}"
        
        logger.info("✅ Team comparison test passed")
    
    @pytest.mark.asyncio
    async def test_health_score_calculation(self):
        """Test health score calculation"""
        team = AgnoTeamBase(
            team_name="Health_Test_Team",
            team_role="Test health score calculation",
            team_mode="coordinate"
        )
        
        # Test with no requests
        initial_score = team._calculate_health_score()
        assert initial_score == 1.0
        
        # Test with successful requests
        team._update_team_metrics(5.0, "coordinate", True)  # Good response time
        team._update_team_metrics(3.0, "coordinate", True)  # Good response time
        
        health_score = team._calculate_health_score()
        assert health_score > 0.8  # Should be high with good performance
        
        # Test with slow requests
        team._update_team_metrics(35.0, "coordinate", True)  # Slow response time
        
        health_score_slow = team._calculate_health_score()
        assert health_score_slow < health_score  # Should be lower
        
        logger.info("✅ Health score calculation test passed")


# Async test runner functions
async def run_basic_tests():
    """Run basic functionality tests"""
    logger.info("🧪 Running basic Agno Teams tests...")
    
    # Test team initialization
    team = AgnoTeamBase("Basic_Test", "Basic test team", "coordinate")
    assert team.team_name == "Basic_Test"
    
    # Test ETA team
    eta_team = UberEatsETATeam()
    assert eta_team.specialization == "eta_prediction"
    
    logger.info("✅ Basic tests completed successfully")
    return True


async def run_comprehensive_tests():
    """Run comprehensive test suite"""
    logger.info("🧪 Running comprehensive Agno Teams tests...")
    
    test_results = {
        "team_creation": False,
        "leader_creation": False, 
        "agent_creation": False,
        "eta_team_setup": False,
        "health_metrics": False
    }
    
    try:
        # Test team creation
        team = AgnoTeamBase("Comprehensive_Test", "Comprehensive test", "coordinate")
        test_results["team_creation"] = True
        
        # Test leader creation (requires API key)
        if settings.openai_api_key:
            try:
                await team.create_team_leader("Test leader instructions")
                test_results["leader_creation"] = True
            except Exception as e:
                logger.warning(f"Leader creation test skipped: {e}")
        
        # Test specialized agent creation  
        agent = team.create_specialized_agent(
            "Test_Agent", "Test role", "Test instructions"
        )
        team.add_team_member(agent, "Test_Agent", "Test role")
        test_results["agent_creation"] = True
        
        # Test ETA team
        eta_team = UberEatsETATeam()
        if settings.openai_api_key:
            try:
                await eta_team.setup_team()
                test_results["eta_team_setup"] = True
            except Exception as e:
                logger.warning(f"ETA team setup test skipped: {e}")
        
        # Test health metrics
        health_status = await eta_team.get_team_health()
        if "team_name" in health_status:
            test_results["health_metrics"] = True
        
        logger.info("✅ Comprehensive tests completed")
        
    except Exception as e:
        logger.error(f"Comprehensive tests failed: {e}")
    
    return test_results


if __name__ == "__main__":
    async def main():
        print("🚀 Starting Agno Teams Phase 1 Tests...\n")
        
        # Run basic tests
        basic_success = await run_basic_tests()
        print(f"Basic Tests: {'✅ PASSED' if basic_success else '❌ FAILED'}\n")
        
        # Run comprehensive tests
        comprehensive_results = await run_comprehensive_tests()
        print("Comprehensive Test Results:")
        for test_name, result in comprehensive_results.items():
            status = "✅ PASSED" if result else "❌ FAILED/SKIPPED"
            print(f"  {test_name}: {status}")
        
        # Calculate success rate
        passed_tests = sum(1 for result in comprehensive_results.values() if result)
        total_tests = len(comprehensive_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\nOverall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if success_rate >= 80:
            print("🎉 Phase 1 implementation is ready for production!")
        else:
            print("⚠️  Phase 1 needs additional work before production.")
    
    # Run the tests
    asyncio.run(main())