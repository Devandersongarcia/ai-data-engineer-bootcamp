from agno import Workflow
from agno.models.openai import OpenAIChat
from ..rag.rag_agents import RAGCustomerAgent, RAGRestaurantAgent, RAGDeliveryAgent, RAGOrderAgent
from ..models.ubereats_models import Order, OrderStatus
from ..config.settings import settings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class UberEatsRAGWorkflow(Workflow):
    """RAG-enhanced workflow orchestrating all UberEats agents with database knowledge."""
    
    def __init__(self):
        # Initialize model
        model = OpenAIChat(
            model=settings.default_model,
            api_key=settings.openai_api_key
        )
        
        # Initialize RAG-enhanced agents
        self.customer_agent = RAGCustomerAgent(model=model)
        self.restaurant_agent = RAGRestaurantAgent(model=model)
        self.delivery_agent = RAGDeliveryAgent(model=model)
        self.order_agent = RAGOrderAgent(model=model)
        
        super().__init__(
            name="UberEatsRAGWorkflow",
            agents=[
                self.customer_agent,
                self.restaurant_agent, 
                self.delivery_agent,
                self.order_agent
            ]
        )
        
        self.initialized = False
    
    async def initialize(self):
        """Initialize all RAG components for agents"""
        if not self.initialized:
            logger.info("Initializing RAG workflow...")
            await self.customer_agent.initialize_rag()
            await self.restaurant_agent.initialize_rag()
            await self.delivery_agent.initialize_rag()
            await self.order_agent.initialize_rag()
            self.initialized = True
            logger.info("RAG workflow initialized successfully")
    
    async def process_new_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new order through the complete RAG-enhanced workflow."""
        
        # Ensure RAG is initialized
        await self.initialize()
        
        logger.info(f"Processing order: {order_data.get('id', 'Unknown')}")
        
        try:
            # Step 1: Order validation and processing with RAG context
            order_result = await self.order_agent.retrieve_context(
                f"process order with items {order_data.get('items', [])} "
                f"for customer {order_data.get('customer_id', '')}"
            )
            
            # Step 2: Restaurant coordination with kitchen knowledge
            prep_time = await self.restaurant_agent.estimate_preparation_time(order_data)
            
            # Step 3: Delivery coordination with route optimization
            delivery_query = f"delivery time from {order_data.get('restaurant_address', '')} " \
                           f"to {order_data.get('delivery_address', '')}"
            delivery_context = await self.delivery_agent.retrieve_context(delivery_query)
            
            # Step 4: Customer communication with personalized context
            customer_update = await self.customer_agent.handle_customer_request({
                "message": "Order confirmation and delivery estimate",
                "customer_id": order_data.get("customer_id"),
                "order_id": order_data.get("id")
            })
            
            return {
                "order_processed": order_result,
                "preparation_time": prep_time,
                "delivery_context": delivery_context,
                "customer_notification": customer_update,
                "status": "confirmed",
                "workflow_type": "rag_enhanced"
            }
            
        except Exception as e:
            logger.error(f"Error processing order in RAG workflow: {e}")
            return {
                "error": str(e),
                "status": "failed",
                "workflow_type": "rag_enhanced"
            }
    
    async def handle_customer_inquiry(self, inquiry: Dict[str, Any]) -> Dict[str, Any]:
        """Handle customer inquiries with full RAG context"""
        await self.initialize()
        
        try:
            response = await self.customer_agent.handle_customer_request(inquiry)
            
            return {
                "inquiry": inquiry.get("message", ""),
                "response": response,
                "agent": "customer_agent",
                "enhanced_with_rag": True
            }
            
        except Exception as e:
            logger.error(f"Error handling customer inquiry: {e}")
            return {
                "error": str(e),
                "agent": "customer_agent",
                "enhanced_with_rag": False
            }
    
    async def get_restaurant_recommendations(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Get restaurant recommendations based on customer preferences"""
        await self.initialize()
        
        try:
            query = f"recommend restaurants for customer with preferences: {preferences}"
            recommendations = await self.restaurant_agent.retrieve_context(query)
            
            return {
                "preferences": preferences,
                "recommendations": recommendations,
                "agent": "restaurant_agent",
                "enhanced_with_rag": True
            }
            
        except Exception as e:
            logger.error(f"Error getting restaurant recommendations: {e}")
            return {
                "error": str(e),
                "agent": "restaurant_agent",
                "enhanced_with_rag": False
            }