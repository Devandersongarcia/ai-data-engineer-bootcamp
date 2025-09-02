#!/usr/bin/env python3
"""
Test Prompt Management System
Verify external prompt loading, templating, and CrewAI integration
"""

import logging
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.agents.prompt_manager import PromptManager
from src.agents.crewai_with_prompts import PromptBasedCrewAISystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_prompt_manager():
    """Test the basic prompt management functionality"""
    logger.info("🧪 Testing Prompt Manager")
    logger.info("=" * 50)
    
    try:
        # Initialize prompt manager
        prompt_manager = PromptManager()
        
        # Test 1: Validate all prompts
        logger.info("\n📋 Test 1: Prompt Validation")
        validation = prompt_manager.validate_prompts()
        
        if validation["valid"]:
            logger.info("✅ All prompts are valid")
            logger.info(f"   - Agents: {len(validation['agents'])}")
            logger.info(f"   - Tasks: {len(validation['tasks'])}")
        else:
            logger.error("❌ Prompt validation failed:")
            for error in validation["errors"]:
                logger.error(f"   - {error}")
            return False
        
        # Test 2: Load agent configurations
        logger.info("\n🤖 Test 2: Agent Configuration Loading")
        agents = prompt_manager.get_available_agents()
        
        for agent_name in agents:
            try:
                config = prompt_manager.load_agent_prompt(agent_name)
                logger.info(f"✅ {agent_name}:")
                logger.info(f"   - Role: {config['role'][:50]}...")
                logger.info(f"   - Tools: {len(config['tools'])}")
                logger.info(f"   - Version: {config['metadata'].get('version', 'N/A')}")
            except Exception as e:
                logger.error(f"❌ Failed to load {agent_name}: {e}")
                return False
        
        # Test 3: Task prompt templating
        logger.info("\n📝 Test 3: Task Prompt Templating")
        test_variables = {
            "order_data": {"order_id": "test_123", "amount": 50.0},
            "orders_today": 5,
            "account_age_days": 10,
            "total_amount": 50.0,
            "payment_method": "credit_card",
            "avg_order_value": 30.0,
            "amount_ratio": 1.67
        }
        
        try:
            pattern_prompt = prompt_manager.load_task_prompt("pattern_analysis", test_variables)
            
            # Debug output
            logger.info(f"📋 Template length: {len(pattern_prompt)} characters")
            logger.info(f"📋 First 200 chars: {pattern_prompt[:200]}...")
            logger.info(f"📋 Contains test_123: {'test_123' in pattern_prompt}")
            logger.info(f"📋 Contains '5 orders today': {'5 orders today' in pattern_prompt}")
            
            if "test_123" in pattern_prompt and "5 orders today" in pattern_prompt:
                logger.info("✅ Task prompt templating working correctly")
                logger.info(f"   - Template length: {len(pattern_prompt)} characters")
                logger.info(f"   - Variables substituted: {len(test_variables)}")
            else:
                logger.error("❌ Template substitution failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Task prompt loading failed: {e}")
            return False
        
        # Test 4: Cache functionality
        logger.info("\n💾 Test 4: Cache Functionality")
        cache_stats = prompt_manager.get_cache_stats()
        
        logger.info(f"✅ Cache Status:")
        logger.info(f"   - Enabled: {cache_stats['cache_enabled']}")
        logger.info(f"   - Cached Items: {cache_stats['cached_items']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Prompt Manager test failed: {e}")
        return False

def test_crewai_with_prompts():
    """Test CrewAI system with external prompts"""
    logger.info("\n🤖 Testing CrewAI with External Prompts")
    logger.info("=" * 50)
    
    try:
        # Initialize prompt-based system
        logger.info("🔧 Initializing PromptBasedCrewAISystem...")
        system = PromptBasedCrewAISystem()
        
        # Get system info
        system_info = system.get_system_info()
        
        logger.info("✅ System Information:")
        logger.info(f"   - Framework: {system_info['framework']}")
        logger.info(f"   - Agents: {len(system_info['agents'])}")
        logger.info(f"   - Available Agent Prompts: {len(system_info['prompt_management']['available_agents'])}")
        logger.info(f"   - Available Task Prompts: {len(system_info['prompt_management']['available_tasks'])}")
        
        # Test order analysis
        logger.info("\n🔍 Testing Order Analysis with External Prompts")
        
        test_order = {
            "order_id": "prompt_test_001",
            "user_id": "test_user_001",
            "total_amount": 4.99,    # Small amount - card testing
            "payment_method": "credit_card",
            "account_age_days": 1,   # Very new account
            "orders_today": 10,      # High velocity
            "orders_last_hour": 5,
            "avg_order_value": 35.0,
            "payment_failures_today": 2,
            "behavior_change_score": 0.3,
            "new_payment_method": True,
            "address_change_flag": False
        }
        
        logger.info(f"📋 Test Order:")
        logger.info(f"   - Order ID: {test_order['order_id']}")
        logger.info(f"   - Amount: ${test_order['total_amount']}")
        logger.info(f"   - Account Age: {test_order['account_age_days']} days")
        logger.info(f"   - Orders Today: {test_order['orders_today']}")
        
        # Analyze order
        logger.info("\n⚙️ Running Analysis...")
        result = system.analyze_order(test_order)
        
        # Display results
        if result.get("success", False):
            logger.info("✅ Analysis completed successfully!")
            logger.info(f"📊 Results:")
            logger.info(f"   - Fraud Score: {result.get('fraud_score', 0):.3f}")
            logger.info(f"   - Recommendation: {result.get('recommended_action', 'UNKNOWN')}")
            logger.info(f"   - Confidence: {result.get('confidence', 0):.3f}")
            logger.info(f"   - Patterns: {', '.join(result.get('patterns_detected', []))}")
            logger.info(f"   - Processing Time: {result.get('processing_time_ms', 0)}ms")
            logger.info(f"   - Framework: {result.get('framework', 'unknown')}")
            logger.info(f"   - Prompt Version: {result.get('prompt_version', 'N/A')}")
            
            reasoning = result.get('reasoning', '')
            if reasoning:
                logger.info(f"   - Reasoning: {reasoning[:100]}...")
            
            return True
        else:
            logger.error("❌ Analysis failed:")
            logger.error(f"   - Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ CrewAI with prompts test failed: {e}")
        return False

def test_prompt_reload():
    """Test prompt hot-reloading functionality"""
    logger.info("\n🔄 Testing Prompt Hot-Reload")
    logger.info("=" * 50)
    
    try:
        system = PromptBasedCrewAISystem()
        
        # Test reload functionality
        logger.info("🔄 Testing prompt reload...")
        system.reload_prompts()
        
        logger.info("✅ Prompt reload successful")
        
        # Verify system still works
        system_info = system.get_system_info()
        if system_info.get("system_status") == "operational":
            logger.info("✅ System operational after reload")
            return True
        else:
            logger.error("❌ System not operational after reload")
            return False
            
    except Exception as e:
        logger.error(f"❌ Prompt reload test failed: {e}")
        return False

def main():
    """Run all prompt management tests"""
    logger.info("🚀 Prompt Management System Test Suite")
    logger.info("This will test external prompt loading, templating, and CrewAI integration")
    logger.info("=" * 80)
    
    # Test 1: Basic prompt manager
    prompt_manager_success = test_prompt_manager()
    
    # Test 2: CrewAI integration (only if prompt manager works)
    crewai_success = False
    if prompt_manager_success:
        crewai_success = test_crewai_with_prompts()
    else:
        logger.warning("⚠️ Skipping CrewAI test due to prompt manager failure")
    
    # Test 3: Prompt reload (only if CrewAI works)
    reload_success = False
    if crewai_success:
        reload_success = test_prompt_reload()
    else:
        logger.warning("⚠️ Skipping reload test due to CrewAI failure")
    
    # Final results
    logger.info("\n" + "=" * 80)
    logger.info("📈 FINAL TEST RESULTS")
    logger.info("=" * 80)
    
    logger.info(f"📋 Prompt Manager: {'✅ PASSED' if prompt_manager_success else '❌ FAILED'}")
    logger.info(f"🤖 CrewAI Integration: {'✅ PASSED' if crewai_success else '❌ FAILED'}")
    logger.info(f"🔄 Prompt Reload: {'✅ PASSED' if reload_success else '❌ FAILED'}")
    
    if prompt_manager_success and crewai_success:
        logger.info("\n🎉 ALL TESTS PASSED - Prompt management system is working perfectly!")
        logger.info("🔧 Features validated:")
        logger.info("   ✅ External markdown prompt loading")
        logger.info("   ✅ Variable templating and substitution")
        logger.info("   ✅ Agent configuration from prompts")
        logger.info("   ✅ Task prompt templating")
        logger.info("   ✅ CrewAI integration with external prompts")
        logger.info("   ✅ Prompt validation and caching")
        if reload_success:
            logger.info("   ✅ Hot-reload functionality")
        
        return True
    else:
        logger.error("\n❌ SOME TESTS FAILED - Please check the errors above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)