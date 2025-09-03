"""
RAG-Enhanced Agents with Database Integration
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from agno import Agent
from agno.models.openai import OpenAIChat
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Removed unused agents - focusing on delivery optimization
# from ..agents.customer_agent import CustomerAgent
# from ..agents.restaurant_agent import RestaurantAgent
# from ..agents.delivery_agent import DeliveryAgent  
# from ..agents.order_agent import OrderAgent
from ..utils.database_connections import db_connections
from ..config.settings import settings

logger = logging.getLogger(__name__)


class BaseRAGAgent:
    """Base class for RAG-enhanced agents"""
    
    def __init__(self, agent_id: str, model=None):
        self.agent_id = agent_id
        self.model = model or OpenAIChat(
            model=settings.default_model,
            api_key=settings.openai_api_key
        )
        
        # Initialize RAG components
        self.vector_store = None
        self.index = None
        self.query_engine = None
        self.embedding_model = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
        
    async def initialize_rag(self):
        """Initialize RAG components"""
        try:
            await db_connections.initialize_connections()
            
            # Setup Qdrant vector store
            self.vector_store = QdrantVectorStore(
                client=db_connections.qdrant_client,
                collection_name=settings.qdrant_collection_name,
                enable_hybrid=True
            )
            
            # Create index
            self.index = VectorStoreIndex.from_vector_store(
                self.vector_store,
                embed_model=self.embedding_model
            )
            
            # Create retriever with agent-specific filtering
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.top_k_retrieval,
                filters=self._get_agent_filter()
            )
            
            # Create query engine
            self.query_engine = RetrieverQueryEngine(
                retriever=retriever,
                node_postprocessors=[]
            )
            
            logger.info(f"RAG initialized for {self.agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG for {self.agent_id}: {e}")
            raise
    
    def _get_agent_filter(self) -> Filter:
        """Get Qdrant filter for this agent"""
        return Filter(
            must=[
                FieldCondition(
                    key="group_id",
                    match=MatchValue(value=self.agent_id)
                )
            ]
        )
    
    async def retrieve_context(self, query: str, filters: Optional[Dict] = None) -> str:
        """Retrieve relevant context for a query"""
        if not self.query_engine:
            await self.initialize_rag()
        
        try:
            # Add additional filters if provided
            query_filters = self._get_agent_filter()
            if filters:
                for key, value in filters.items():
                    query_filters.must.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
            
            # Query the knowledge base
            response = self.query_engine.query(query)
            
            # Extract context from response
            context = str(response)
            
            logger.debug(f"Retrieved context for {self.agent_id}: {len(context)} characters")
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving context for {self.agent_id}: {e}")
            return ""
    
    async def get_fresh_database_context(self, query: str) -> str:
        """Get fresh context directly from databases - override in subclasses"""
        return ""


class RAGCustomerAgent(BaseRAGAgent, CustomerAgent):
    """Customer agent enhanced with RAG capabilities"""
    
    def __init__(self, model=None, **kwargs):
        CustomerAgent.__init__(self, model=model, **kwargs)
        BaseRAGAgent.__init__(self, agent_id="customer_agent", model=self.model)
    
    async def get_fresh_database_context(self, query: str) -> str:
        """Get fresh customer-specific context from databases"""
        fresh_context = ""
        
        try:
            # Check for recent policy updates (last 24 hours)
            if any(keyword in query.lower() for keyword in ["policy", "cancel", "refund", "return"]):
                recent_policies = await db_connections.execute_sql_query("""
                    SELECT policy_name, policy_description, updated_at
                    FROM customer_policies 
                    WHERE active = true 
                    AND updated_at > NOW() - INTERVAL '24 hours'
                    ORDER BY updated_at DESC
                    LIMIT 5
                """)
                
                if not recent_policies.empty:
                    policy_text = "Recent Policy Updates:\n"
                    for _, policy in recent_policies.iterrows():
                        policy_text += f"- {policy['policy_name']}: {policy['policy_description']}\n"
                    fresh_context += policy_text + "\n"
            
            # Check for current promotions
            if "promotion" in query.lower() or "discount" in query.lower():
                current_promos = await db_connections.execute_sql_query("""
                    SELECT promo_name, promo_description, discount_amount, valid_until
                    FROM promotions 
                    WHERE active = true 
                    AND valid_from <= NOW() 
                    AND valid_until >= NOW()
                    ORDER BY discount_amount DESC
                    LIMIT 3
                """)
                
                if not current_promos.empty:
                    promo_text = "Current Promotions:\n"
                    for _, promo in current_promos.iterrows():
                        promo_text += f"- {promo['promo_name']}: {promo['promo_description']} " \
                                    f"({promo['discount_amount']}% off, valid until {promo['valid_until']})\n"
                    fresh_context += promo_text + "\n"
        
        except Exception as e:
            logger.warning(f"Error getting fresh customer context: {e}")
        
        return fresh_context
    
    async def handle_customer_request(self, request: Dict[str, Any]) -> str:
        """Enhanced customer request handling with RAG"""
        query = request.get("message", "")
        customer_id = request.get("customer_id")
        
        try:
            # Get RAG context
            rag_context = await self.retrieve_context(query)
            
            # Get fresh database context
            fresh_context = await self.get_fresh_database_context(query)
            
            # Get customer-specific context
            customer_context = ""
            if customer_id:
                customer_context = await self._get_customer_context(customer_id)
            
            # Combine all context
            full_context = f"""
RAG Knowledge Base Context:
{rag_context}

Fresh Database Context:
{fresh_context}

Customer Context:
{customer_context}

Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            # Enhanced prompt
            enhanced_prompt = f"""
Context: {full_context}

Customer Request: {query}

Provide a helpful, accurate response based on the context above. 
Be empathetic and solution-oriented. If you need to reference policies, 
use the most recent information provided in the context.
"""
            
            return self.run(enhanced_prompt)
            
        except Exception as e:
            logger.error(f"Error in RAG customer request handling: {e}")
            return self.run(f"Customer request: {query}")
    
    async def _get_customer_context(self, customer_id: str) -> str:
        """Get customer-specific information from databases"""
        try:
            # Get customer info from PostgreSQL
            customer_info = await db_connections.execute_sql_query("""
                SELECT 
                    c.customer_name,
                    c.membership_tier,
                    c.total_orders,
                    c.avg_order_value,
                    c.last_order_date
                FROM customers c
                WHERE c.id = %s
            """, [customer_id])
            
            context_parts = []
            if not customer_info.empty:
                row = customer_info.iloc[0]
                context_parts.append(f"Customer: {row['customer_name']}")
                context_parts.append(f"Membership: {row['membership_tier']}")
                context_parts.append(f"Total orders: {row['total_orders']}")
                context_parts.append(f"Average order value: ${row['avg_order_value']}")
                context_parts.append(f"Last order: {row['last_order_date']}")
            
            # Get preferences from MongoDB
            if db_connections.mongo_client:
                preferences = await db_connections.query_mongodb_collection(
                    "customer_preferences",
                    {"customer_id": customer_id},
                    limit=1
                )
                
                if preferences:
                    pref = preferences[0]
                    if pref.get('dietary_restrictions'):
                        context_parts.append(f"Dietary restrictions: {', '.join(pref['dietary_restrictions'])}")
                    if pref.get('favorite_cuisines'):
                        context_parts.append(f"Favorite cuisines: {', '.join(pref['favorite_cuisines'])}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting customer context: {e}")
            return ""


class RAGRestaurantAgent(BaseRAGAgent, RestaurantAgent):
    """Restaurant agent enhanced with RAG capabilities"""
    
    def __init__(self, model=None, **kwargs):
        RestaurantAgent.__init__(self, model=model, **kwargs)
        BaseRAGAgent.__init__(self, agent_id="restaurant_agent", model=self.model)
    
    async def get_fresh_database_context(self, query: str) -> str:
        """Get fresh restaurant-specific context from databases"""
        fresh_context = ""
        
        try:
            # Get recent menu updates (last 2 hours)
            if any(keyword in query.lower() for keyword in ["menu", "available", "item", "dish"]):
                recent_updates = await db_connections.execute_sql_query("""
                    SELECT 
                        r.restaurant_name,
                        mi.item_name,
                        mi.available,
                        mi.price,
                        mi.updated_at
                    FROM menu_items mi
                    JOIN restaurants r ON r.id = mi.restaurant_id
                    WHERE mi.updated_at > NOW() - INTERVAL '2 hours'
                    ORDER BY mi.updated_at DESC
                    LIMIT 10
                """)
                
                if not recent_updates.empty:
                    updates_text = "Recent Menu Updates:\n"
                    for _, item in recent_updates.iterrows():
                        status = "Available" if item['available'] else "Unavailable"
                        updates_text += f"- {item['restaurant_name']}: {item['item_name']} " \
                                      f"({status}, ${item['price']})\n"
                    fresh_context += updates_text + "\n"
            
            # Get current kitchen load from MongoDB
            if any(keyword in query.lower() for keyword in ["prep", "time", "kitchen", "busy"]):
                if db_connections.mongo_client:
                    today = datetime.now().strftime("%Y-%m-%d")
                    kitchen_status = await db_connections.query_mongodb_collection(
                        "kitchen_operations",
                        {"date": today},
                        limit=5
                    )
                    
                    if kitchen_status:
                        kitchen_text = "Current Kitchen Status:\n"
                        for status in kitchen_status:
                            kitchen_text += f"- {status.get('restaurant_name', 'Unknown')}: " \
                                          f"Efficiency {status.get('efficiency_score', 'N/A')}%, " \
                                          f"Avg prep time {status.get('avg_prep_time', 'N/A')} min\n"
                        fresh_context += kitchen_text + "\n"
        
        except Exception as e:
            logger.warning(f"Error getting fresh restaurant context: {e}")
        
        return fresh_context
    
    async def estimate_preparation_time(self, order: Dict[str, Any]) -> str:
        """Enhanced preparation time estimation with RAG"""
        restaurant_id = order.get("restaurant_id")
        items = order.get("items", [])
        
        try:
            # Build query for RAG
            item_names = [item.get("name", "") for item in items]
            query = f"preparation time cooking time for {', '.join(item_names)}"
            
            # Get RAG context
            rag_context = await self.retrieve_context(
                query, 
                filters={"restaurant_id": restaurant_id} if restaurant_id else None
            )
            
            # Get fresh context
            fresh_context = await self.get_fresh_database_context(query)
            
            # Get current kitchen status
            kitchen_context = ""
            if restaurant_id and db_connections.mongo_client:
                today = datetime.now().strftime("%Y-%m-%d")
                kitchen_ops = await db_connections.query_mongodb_collection(
                    "kitchen_operations",
                    {"restaurant_id": restaurant_id, "date": today},
                    limit=1
                )
                if kitchen_ops:
                    op = kitchen_ops[0]
                    kitchen_context = f"Current kitchen efficiency: {op.get('efficiency_score', 'N/A')}%, " \
                                    f"Current load: {op.get('current_orders', 'N/A')} orders"
            
            full_context = f"""
RAG Context:
{rag_context}

Fresh Menu Context:
{fresh_context}

Kitchen Status:
{kitchen_context}

Order Details: {order}
Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            enhanced_prompt = f"""
Context: {full_context}

Based on the context above, estimate the realistic preparation time for this order.
Consider:
1. Individual item preparation times
2. Kitchen efficiency and current load  
3. Order complexity
4. Time of day factors

Provide a specific time estimate in minutes with brief reasoning.
"""
            
            return self.run(enhanced_prompt)
            
        except Exception as e:
            logger.error(f"Error in RAG preparation time estimation: {e}")
            return self.run(f"Estimate preparation time for: {order}")


class RAGDeliveryAgent(BaseRAGAgent, DeliveryAgent):
    """Delivery agent enhanced with RAG capabilities"""
    
    def __init__(self, model=None, **kwargs):
        DeliveryAgent.__init__(self, model=model, **kwargs)
        BaseRAGAgent.__init__(self, agent_id="delivery_agent", model=self.model)


class RAGOrderAgent(BaseRAGAgent, OrderAgent):
    """Order agent enhanced with RAG capabilities"""
    
    def __init__(self, model=None, **kwargs):
        OrderAgent.__init__(self, model=model, **kwargs)
        BaseRAGAgent.__init__(self, agent_id="order_agent", model=self.model)