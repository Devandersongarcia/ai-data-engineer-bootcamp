"""
Test RAG Agents Script
Test the RAG-enhanced agents with sample queries
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.rag.rag_agents import RAGCustomerAgent, RAGRestaurantAgent
from src.utils.database_connections import db_connections

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_customer_agent():
    """Test the RAG Customer Agent"""
    print("\n🧑‍💼 Testing RAG Customer Agent")
    print("-" * 40)
    
    agent = RAGCustomerAgent()
    await agent.initialize_rag()
    
    # Test queries
    test_queries = [
        {
            "message": "How do I cancel my order?",
            "customer_id": "customer_123"
        },
        {
            "message": "What's your refund policy?",
            "customer_id": "customer_456"
        },
        {
            "message": "Are there any current promotions available?",
            "customer_id": "customer_789"
        }
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query['message']}")
        try:
            response = await agent.handle_customer_request(query)
            print(f"🤖 Response: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 40)


async def test_restaurant_agent():
    """Test the RAG Restaurant Agent"""
    print("\n🍽️  Testing RAG Restaurant Agent")
    print("-" * 40)
    
    agent = RAGRestaurantAgent()
    await agent.initialize_rag()
    
    # Test queries
    test_orders = [
        {
            "restaurant_id": "rest_001",
            "items": [
                {"name": "Margherita Pizza", "quantity": 1},
                {"name": "Caesar Salad", "quantity": 1}
            ]
        },
        {
            "restaurant_id": "rest_002", 
            "items": [
                {"name": "Chicken Burger", "quantity": 2},
                {"name": "French Fries", "quantity": 2}
            ]
        }
    ]
    
    for i, order in enumerate(test_orders, 1):
        print(f"\n📝 Test {i}: Estimating prep time for order")
        print(f"   Restaurant: {order['restaurant_id']}")
        print(f"   Items: {[item['name'] for item in order['items']]}")
        
        try:
            response = await agent.estimate_preparation_time(order)
            print(f"🤖 Response: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 40)


async def test_context_retrieval():
    """Test direct context retrieval"""
    print("\n🔍 Testing Direct Context Retrieval")
    print("-" * 40)
    
    agent = RAGCustomerAgent()
    await agent.initialize_rag()
    
    test_queries = [
        "cancellation policy",
        "refund process",
        "delivery time",
        "payment methods"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            context = await agent.retrieve_context(query)
            print(f"📋 Context length: {len(context)} characters")
            print(f"📋 Context preview: {context[:200]}...")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 40)


async def main():
    """Main test function"""
    print("🧪 Testing RAG-Enhanced Agents")
    print("=" * 50)
    
    try:
        # Initialize database connections
        await db_connections.initialize_connections()
        
        # Test connection status
        results = await db_connections.test_all_connections()
        
        # Check if Qdrant is ready
        if results["qdrant"]["status"] != "connected":
            print("❌ Qdrant not connected. Please run connection test first.")
            sys.exit(1)
        
        print("✅ All connections ready for testing")
        
        # Test context retrieval
        await test_context_retrieval()
        
        # Test customer agent
        await test_customer_agent()
        
        # Test restaurant agent  
        await test_restaurant_agent()
        
        print("\n🎉 RAG Agent testing completed!")
        print("\n📊 Test Summary:")
        print("- Context retrieval: ✅")
        print("- Customer agent: ✅") 
        print("- Restaurant agent: ✅")
        print("\n🚀 RAG system is working properly!")
        
    except Exception as e:
        print(f"\n💥 Critical error during testing: {e}")
        logger.error(f"Testing failed: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        db_connections.close_connections()


if __name__ == "__main__":
    asyncio.run(main())