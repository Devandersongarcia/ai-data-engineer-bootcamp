# examples/redis_memory_demo.py - Redis Memory Integration Demo
"""
Demo script showing Redis memory integration with UberEats agents.

This demonstrates:
1. Redis connection and basic operations
2. Agent memory storage and retrieval
3. Memory tagging and search
4. Performance monitoring
5. Memory management features
"""

import asyncio
import json
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.eta_prediction_agent import SmartETAPredictionAgent
from src.memory.redis_memory import create_agent_memory, get_agent_memory
from src.config.settings import settings


async def test_redis_connection():
    """Test basic Redis connection"""
    print("🔧 Testing Redis Connection")
    print("=" * 40)
    
    try:
        # Test Redis memory creation
        agent_memory = create_agent_memory("test_agent")
        
        # Test basic operations
        test_data = {"message": "Hello Redis!", "timestamp": datetime.now().isoformat()}
        
        # Store data
        success = await agent_memory.store("test_key", test_data, ttl=300)
        print(f"✅ Store operation: {'Success' if success else 'Failed'}")
        
        # Retrieve data
        retrieved = await agent_memory.retrieve("test_key")
        print(f"✅ Retrieve operation: {'Success' if retrieved else 'Failed'}")
        
        if retrieved:
            print(f"   Retrieved: {json.dumps(retrieved, indent=2)}")
        
        # Get memory stats
        stats = await agent_memory.get_memory_stats()
        print(f"✅ Memory stats: {json.dumps(stats, indent=2)}")
        
        # Clean up
        await agent_memory.delete("test_key")
        print("✅ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection test failed: {e}")
        return False


async def test_agent_memory_integration():
    """Test Redis memory integration with agents"""
    print("\n🤖 Testing Agent Memory Integration")
    print("=" * 40)
    
    try:
        # Create agent with Redis memory
        agent = SmartETAPredictionAgent()
        
        print(f"Agent created: {agent.name}")
        print(f"Redis memory available: {agent.redis_memory is not None}")
        
        if not agent.redis_memory:
            print("❌ Agent does not have Redis memory enabled")
            return False
        
        # Test memory operations through agent
        test_data = {
            "order_id": "order_test_123",
            "prediction": "30 minutes",
            "confidence": 0.85,
            "factors": ["Good traffic", "Available driver"]
        }
        
        # Store conversation context
        conversation_id = "conv_123"
        context_success = await agent.store_conversation_context(
            conversation_id, 
            test_data,
            ttl=3600
        )
        print(f"✅ Store conversation context: {'Success' if context_success else 'Failed'}")
        
        # Retrieve conversation context
        retrieved_context = await agent.retrieve_conversation_context(conversation_id)
        print(f"✅ Retrieve conversation context: {'Success' if retrieved_context else 'Failed'}")
        
        if retrieved_context:
            print(f"   Context: {json.dumps(retrieved_context, indent=2)}")
        
        # Store task result
        task_id = "task_eta_prediction_001"
        task_result = {
            "task_type": "eta_prediction",
            "result": test_data,
            "processing_time": 2.5,
            "success": True
        }
        
        task_success = await agent.store_task_result(task_id, task_result)
        print(f"✅ Store task result: {'Success' if task_success else 'Failed'}")
        
        # Store learning data
        learning_key = "eta_accuracy_improvement"
        learning_data = {
            "accuracy_before": 0.75,
            "accuracy_after": 0.85,
            "improvement_factors": ["Better traffic data", "Enhanced algorithms"],
            "timestamp": datetime.now().isoformat()
        }
        
        learning_success = await agent.store_learning_data(learning_key, learning_data)
        print(f"✅ Store learning data: {'Success' if learning_success else 'Failed'}")
        
        # Test memory search by tag
        conversation_keys = await agent.search_memory_by_tag("conversation")
        print(f"✅ Search by 'conversation' tag: Found {len(conversation_keys)} keys")
        
        task_keys = await agent.search_memory_by_tag("task")
        print(f"✅ Search by 'task' tag: Found {len(task_keys)} keys")
        
        learning_keys = await agent.search_memory_by_tag("learning")
        print(f"✅ Search by 'learning' tag: Found {len(learning_keys)} keys")
        
        # Get memory statistics
        memory_stats = await agent.get_memory_stats()
        print(f"✅ Memory statistics:")
        print(f"   {json.dumps(memory_stats, indent=4)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent memory integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_performance():
    """Test memory performance with multiple operations"""
    print("\n⚡ Testing Memory Performance")
    print("=" * 40)
    
    try:
        agent = SmartETAPredictionAgent()
        
        if not agent.redis_memory:
            print("❌ Redis memory not available")
            return False
        
        # Performance test - store multiple entries
        start_time = datetime.now()
        
        tasks = []
        for i in range(100):
            task_data = {
                "order_id": f"perf_test_order_{i}",
                "timestamp": datetime.now().isoformat(),
                "data": f"Performance test data {i}"
            }
            
            # Store with different TTL and tags
            ttl = 1800  # 30 minutes
            tags = ["performance_test", f"batch_{i // 10}"]
            
            tasks.append(agent.store_memory(f"perf_test_{i}", task_data, ttl, tags))
        
        # Execute all store operations
        results = await asyncio.gather(*tasks)
        successful_stores = sum(1 for result in results if result)
        
        store_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Stored {successful_stores}/100 entries in {store_time:.2f} seconds")
        print(f"   Average: {(store_time/100)*1000:.2f} ms per operation")
        
        # Performance test - retrieve entries
        start_time = datetime.now()
        
        retrieve_tasks = []
        for i in range(100):
            retrieve_tasks.append(agent.retrieve_memory(f"perf_test_{i}"))
        
        retrieve_results = await asyncio.gather(*retrieve_tasks)
        successful_retrieves = sum(1 for result in retrieve_results if result is not None)
        
        retrieve_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Retrieved {successful_retrieves}/100 entries in {retrieve_time:.2f} seconds")
        print(f"   Average: {(retrieve_time/100)*1000:.2f} ms per operation")
        
        # Test tag search performance
        start_time = datetime.now()
        
        search_results = await agent.search_memory_by_tag("performance_test")
        search_time = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Tag search found {len(search_results)} keys in {search_time:.3f} seconds")
        
        # Clean up performance test data
        cleanup_tasks = []
        for i in range(100):
            cleanup_tasks.append(agent.delete_memory(f"perf_test_{i}"))
        
        cleanup_results = await asyncio.gather(*cleanup_tasks)
        successful_cleanups = sum(1 for result in cleanup_results if result)
        
        print(f"✅ Cleaned up {successful_cleanups}/100 test entries")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


async def demonstrate_memory_features():
    """Demonstrate advanced memory features"""
    print("\n🚀 Demonstrating Advanced Memory Features")
    print("=" * 50)
    
    try:
        agent = SmartETAPredictionAgent()
        
        if not agent.redis_memory:
            print("❌ Redis memory not available")
            return False
        
        print("1. Memory with TTL (Time To Live)")
        short_lived_data = {"message": "This will expire in 10 seconds", "type": "temporary"}
        await agent.store_memory("short_lived", short_lived_data, ttl=10, tags=["temporary"])
        print("   ✅ Stored data with 10-second TTL")
        
        print("\n2. Memory with Tags for Organization")
        # Store user preferences
        await agent.store_memory("user_pref_123", 
                               {"preferred_delivery_time": "evening", "dietary_restrictions": ["vegetarian"]}, 
                               tags=["user_preferences", "customer_123"])
        
        # Store order history
        await agent.store_memory("order_history_123", 
                               {"last_orders": ["pizza", "salad", "pasta"], "frequency": "weekly"}, 
                               tags=["order_history", "customer_123"])
        
        # Search customer data
        customer_keys = await agent.search_memory_by_tag("customer_123")
        print(f"   ✅ Found {len(customer_keys)} customer-related memory entries")
        
        print("\n3. Conversation Context Management")
        conversations = [
            {"id": "chat_001", "context": {"topic": "delivery_delay", "sentiment": "concerned"}},
            {"id": "chat_002", "context": {"topic": "order_modification", "sentiment": "neutral"}},
            {"id": "chat_003", "context": {"topic": "feedback", "sentiment": "positive"}}
        ]
        
        for conv in conversations:
            await agent.store_conversation_context(conv["id"], conv["context"])
        
        print("   ✅ Stored 3 conversation contexts")
        
        # Retrieve specific conversation
        chat_001_context = await agent.retrieve_conversation_context("chat_001")
        print(f"   ✅ Retrieved chat_001 context: {chat_001_context}")
        
        print("\n4. Learning Data Storage")
        learning_examples = [
            {"key": "route_optimization", "data": {"algorithm": "A*", "improvement": "15%"}},
            {"key": "demand_prediction", "data": {"model": "LSTM", "accuracy": "89%"}},
            {"key": "driver_allocation", "data": {"strategy": "greedy", "efficiency": "92%"}}
        ]
        
        for example in learning_examples:
            await agent.store_learning_data(example["key"], example["data"])
        
        learning_keys = await agent.search_memory_by_tag("learning")
        print(f"   ✅ Stored {len(learning_examples)} learning data entries")
        print(f"   ✅ Found {len(learning_keys)} learning-tagged entries")
        
        print("\n5. Memory Statistics and Health")
        final_stats = await agent.get_memory_stats()
        print(f"   📊 Final memory statistics:")
        print(f"      Total keys: {final_stats.get('total_keys', 'N/A')}")
        print(f"      Cache hit rate: {final_stats.get('cache_hit_rate_percent', 'N/A')}%")
        print(f"      Redis connection: {final_stats.get('redis_connection', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Advanced features test failed: {e}")
        return False


async def main():
    """Main demo function"""
    print("🚀 Redis Memory Integration Demo")
    print("=" * 60)
    print("Testing Redis memory integration with UberEats agents")
    print("=" * 60)
    
    # Show configuration
    print(f"\n⚙️  Configuration:")
    print(f"   Redis URL: {settings.redis_url[:50]}..." if settings.redis_url else "   Redis URL: Not set")
    print(f"   Redis enabled: {settings.redis_enabled}")
    print(f"   Cache TTL: {settings.redis_cache_ttl} seconds")
    print(f"   Max connections: {settings.redis_max_connections}")
    
    tests_passed = 0
    total_tests = 4
    
    try:
        # Test 1: Basic Redis connection
        if await test_redis_connection():
            tests_passed += 1
        
        # Test 2: Agent memory integration  
        if await test_agent_memory_integration():
            tests_passed += 1
        
        # Test 3: Performance testing
        if await test_memory_performance():
            tests_passed += 1
        
        # Test 4: Advanced features
        if await demonstrate_memory_features():
            tests_passed += 1
        
        print(f"\n🎉 Demo Results")
        print("=" * 30)
        print(f"Tests passed: {tests_passed}/{total_tests}")
        
        if tests_passed == total_tests:
            print("✅ All tests passed! Redis memory is working perfectly.")
            print("\n🚀 Your agents now have:")
            print("   • Persistent memory with Redis")
            print("   • Automatic TTL management")
            print("   • Memory tagging and search")
            print("   • Performance optimization")
            print("   • Context management")
            print("   • Learning data storage")
        else:
            print("⚠️  Some tests failed. Check Redis configuration and connection.")
        
        print(f"\n🔗 Next steps:")
        print("   1. Your agents now have Redis memory integration")
        print("   2. Memory will persist across agent restarts")
        print("   3. Use agent.store_memory() and agent.retrieve_memory() in your code")
        print("   4. Monitor memory usage with agent.get_memory_stats()")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())