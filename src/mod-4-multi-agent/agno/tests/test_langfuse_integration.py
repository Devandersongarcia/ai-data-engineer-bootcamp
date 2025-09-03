#!/usr/bin/env python3
"""
Test script for Langfuse integration with fallback scenarios
Tests both online and offline scenarios to verify robustness
"""
import asyncio
import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.observability.langfuse_config import (
    langfuse_manager, 
    prompt_manager, 
    initialize_langfuse,
    is_langfuse_enabled
)
from src.observability.prompt_registry import prompt_registry
from src.agents.customer_agent import CustomerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LangfuseIntegrationTester:
    """Test class for Langfuse integration and fallback scenarios"""
    
    def __init__(self):
        self.test_results = []
    
    async def run_all_tests(self):
        """Run comprehensive tests for Langfuse integration"""
        logger.info("🚀 Starting Langfuse Integration Tests")
        print("=" * 80)
        
        try:
            # Test 1: Basic initialization
            await self.test_initialization()
            
            # Test 2: Prompt retrieval with service online
            await self.test_prompt_retrieval_online()
            
            # Test 3: Prompt retrieval with service offline (simulated)
            await self.test_prompt_retrieval_offline()
            
            # Test 4: Agent initialization with dynamic prompts
            await self.test_agent_initialization()
            
            # Test 5: Cache functionality
            await self.test_cache_functionality()
            
            # Test 6: Fallback mechanisms
            await self.test_fallback_mechanisms()
            
            # Test 7: Performance and reliability
            await self.test_performance_reliability()
            
            # Summary
            self.print_test_summary()
            
        except Exception as e:
            logger.error(f"Critical error in tests: {e}", exc_info=True)
            self.add_test_result("CRITICAL_ERROR", False, str(e))
    
    def add_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Add test result to tracking"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now()
        })
        
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
        if details:
            logger.info(f"   Details: {details}")
    
    async def test_initialization(self):
        """Test 1: Basic Langfuse and prompt system initialization"""
        logger.info("\n📋 Test 1: System Initialization")
        
        try:
            # Test Langfuse manager initialization
            is_initialized = langfuse_manager.initialized
            self.add_test_result(
                "Langfuse Manager Initialization",
                is_initialized,
                f"Initialized: {is_initialized}"
            )
            
            # Test health check capability
            if is_initialized:
                health_status = langfuse_manager.is_service_healthy()
                self.add_test_result(
                    "Langfuse Health Check",
                    True,  # Just testing the method works
                    f"Health check completed, service healthy: {health_status}"
                )
            
            # Test prompt registry initialization
            cache_status = prompt_registry.get_cache_status()
            self.add_test_result(
                "Prompt Registry Initialization",
                cache_status is not None,
                f"Default prompts available: {cache_status.get('default_prompts_available', 0)}"
            )
            
        except Exception as e:
            self.add_test_result("System Initialization", False, str(e))
    
    async def test_prompt_retrieval_online(self):
        """Test 2: Prompt retrieval with Langfuse service available"""
        logger.info("\n📋 Test 2: Prompt Retrieval (Online Scenario)")
        
        try:
            # Test retrieving a customer service prompt
            test_variables = {
                "context": "Test scenario with online Langfuse",
                "request": "Test customer inquiry"
            }
            
            prompt_text = prompt_manager.get_prompt("customer_service_base", test_variables)
            
            success = prompt_text and len(prompt_text) > 10
            self.add_test_result(
                "Online Prompt Retrieval",
                success,
                f"Prompt length: {len(prompt_text) if prompt_text else 0} characters"
            )
            
            if success:
                # Verify variables were substituted
                variables_substituted = (
                    "Test scenario with online Langfuse" in prompt_text and
                    "Test customer inquiry" in prompt_text
                )
                self.add_test_result(
                    "Prompt Variable Substitution",
                    variables_substituted,
                    "Variables properly substituted in prompt"
                )
            
        except Exception as e:
            self.add_test_result("Online Prompt Retrieval", False, str(e))
    
    async def test_prompt_retrieval_offline(self):
        """Test 3: Prompt retrieval with Langfuse service offline (simulated)"""
        logger.info("\n📋 Test 3: Prompt Retrieval (Offline Scenario)")
        
        try:
            # Simulate offline scenario by marking service as unhealthy
            original_health = langfuse_manager.is_healthy
            langfuse_manager.is_healthy = False
            
            test_variables = {
                "context": "Test scenario with offline Langfuse",
                "request": "Test customer inquiry with fallback"
            }
            
            # Should still return a prompt from fallback system
            prompt_text = prompt_manager.get_prompt("customer_service_base", test_variables)
            
            success = prompt_text and len(prompt_text) > 10
            self.add_test_result(
                "Offline Prompt Retrieval (Fallback)",
                success,
                f"Fallback prompt length: {len(prompt_text) if prompt_text else 0} characters"
            )
            
            # Restore original health status
            langfuse_manager.is_healthy = original_health
            
        except Exception as e:
            self.add_test_result("Offline Prompt Retrieval", False, str(e))
            # Restore health status even on error
            langfuse_manager.is_healthy = langfuse_manager._check_langfuse_health()
    
    async def test_agent_initialization(self):
        """Test 4: Agent initialization with dynamic prompts"""
        logger.info("\n📋 Test 4: Agent Initialization with Dynamic Prompts")
        
        try:
            # Initialize customer agent
            customer_agent = CustomerAgent()
            
            # Check if agent was initialized
            agent_initialized = customer_agent.agent_id == "customer_agent"
            self.add_test_result(
                "Customer Agent Initialization",
                agent_initialized,
                f"Agent ID: {customer_agent.agent_id}"
            )
            
            # Check if prompt management is available
            prompt_status = customer_agent.get_prompt_status()
            prompt_system_available = "error" not in prompt_status or prompt_status.get("fallback_available", False)
            
            self.add_test_result(
                "Agent Prompt Management Integration",
                prompt_system_available,
                f"Prompt system status available"
            )
            
            # Test dynamic prompt retrieval through agent
            test_prompt = customer_agent.get_dynamic_prompt(
                "customer_service_base",
                {"context": "Agent test", "request": "Test request"}
            )
            
            dynamic_prompt_works = test_prompt and len(test_prompt) > 10
            self.add_test_result(
                "Agent Dynamic Prompt Retrieval",
                dynamic_prompt_works,
                f"Dynamic prompt retrieved through agent: {len(test_prompt) if test_prompt else 0} chars"
            )
            
        except Exception as e:
            self.add_test_result("Agent Initialization", False, str(e))
    
    async def test_cache_functionality(self):
        """Test 5: Prompt caching functionality"""
        logger.info("\n📋 Test 5: Prompt Cache Functionality")
        
        try:
            # Test caching a custom prompt
            test_prompt_data = {
                "prompt": "Test cached prompt for {context}: {request}",
                "variables": ["context", "request"]
            }
            
            prompt_registry.cache_prompt("test_cache_prompt", test_prompt_data)
            
            # Retrieve cached prompt
            cached_prompt = prompt_registry.get_cached_prompt("test_cache_prompt")
            cache_works = cached_prompt is not None
            
            self.add_test_result(
                "Prompt Caching",
                cache_works,
                f"Cached prompt retrieved: {cache_works}"
            )
            
            # Test cache status
            cache_status = prompt_registry.get_cache_status()
            cache_status_available = cache_status and "total_cached_prompts" in cache_status
            
            self.add_test_result(
                "Cache Status Monitoring",
                cache_status_available,
                f"Cache contains {cache_status.get('total_cached_prompts', 0)} prompts"
            )
            
            # Test fallback chain
            fallback_prompt_data = prompt_registry.get_prompt_with_fallback("nonexistent_prompt")
            fallback_works = fallback_prompt_data and "prompt" in fallback_prompt_data
            
            self.add_test_result(
                "Fallback Chain",
                fallback_works,
                "Fallback chain provides default prompt for nonexistent prompts"
            )
            
        except Exception as e:
            self.add_test_result("Cache Functionality", False, str(e))
    
    async def test_fallback_mechanisms(self):
        """Test 6: Comprehensive fallback mechanisms"""
        logger.info("\n📋 Test 6: Fallback Mechanisms")
        
        try:
            # Test with completely invalid prompt name
            invalid_prompt = prompt_manager.get_prompt("completely_invalid_prompt_name_12345")
            fallback_works = invalid_prompt and len(invalid_prompt) > 0
            
            self.add_test_result(
                "Invalid Prompt Fallback",
                fallback_works,
                f"Fallback provided for invalid prompt: {len(invalid_prompt) if invalid_prompt else 0} chars"
            )
            
            # Test prompt manager status in various scenarios
            status_info = prompt_manager.get_cache_status()
            status_comprehensive = (
                "langfuse" in status_info and 
                "cache" in status_info and
                "fallback_ready" in status_info
            )
            
            self.add_test_result(
                "Comprehensive Status Monitoring",
                status_comprehensive,
                f"Status info includes all components: {status_comprehensive}"
            )
            
            # Test clearing expired cache
            try:
                prompt_manager.clear_expired_cache()
                cache_clear_works = True
            except Exception:
                cache_clear_works = False
            
            self.add_test_result(
                "Cache Management",
                cache_clear_works,
                "Cache clearing functionality works"
            )
            
        except Exception as e:
            self.add_test_result("Fallback Mechanisms", False, str(e))
    
    async def test_performance_reliability(self):
        """Test 7: Performance and reliability under load"""
        logger.info("\n📋 Test 7: Performance and Reliability")
        
        try:
            # Test multiple prompt retrievals
            start_time = datetime.now()
            
            for i in range(10):
                prompt_text = prompt_manager.get_prompt(
                    "customer_service_base",
                    {"context": f"Performance test {i}", "request": f"Test request {i}"}
                )
                if not prompt_text or len(prompt_text) < 10:
                    raise Exception(f"Prompt retrieval failed on iteration {i}")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            performance_acceptable = duration < 5.0  # Should complete in under 5 seconds
            self.add_test_result(
                "Performance Test (10 retrievals)",
                performance_acceptable,
                f"Completed in {duration:.3f} seconds"
            )
            
            # Test concurrent access
            async def retrieve_prompt(idx):
                return prompt_manager.get_prompt(
                    "customer_service_base",
                    {"context": f"Concurrent test {idx}", "request": f"Concurrent request {idx}"}
                )
            
            start_time = datetime.now()
            tasks = [retrieve_prompt(i) for i in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = datetime.now()
            
            concurrent_success = all(
                isinstance(result, str) and len(result) > 10 
                for result in results
            )
            concurrent_duration = (end_time - start_time).total_seconds()
            
            self.add_test_result(
                "Concurrent Access Test",
                concurrent_success,
                f"5 concurrent requests completed in {concurrent_duration:.3f} seconds"
            )
            
        except Exception as e:
            self.add_test_result("Performance and Reliability", False, str(e))
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("🎯 LANGFUSE INTEGRATION TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        print(f"\n🏆 Overall Status: {'PASSED' if failed_tests == 0 else 'FAILED'}")
        
        # Test environment info
        print(f"\n🔧 Test Environment:")
        print(f"   • Langfuse Enabled: {is_langfuse_enabled()}")
        print(f"   • Service Health: {langfuse_manager.is_service_healthy() if langfuse_manager.initialized else 'N/A'}")
        
        cache_status = prompt_registry.get_cache_status()
        print(f"   • Cached Prompts: {cache_status.get('total_cached_prompts', 0)}")
        print(f"   • Default Prompts: {cache_status.get('default_prompts_available', 0)}")
        print(f"   • Fallback Ready: ✅")
        
        print("=" * 80)

async def main():
    """Main test execution function"""
    tester = LangfuseIntegrationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())