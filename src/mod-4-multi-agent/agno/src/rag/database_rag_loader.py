"""
Database RAG Loader - Loads data from PostgreSQL and MongoDB into Qdrant for RAG
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json

from llama_index.core import Document
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.database_connections import db_connections
from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseRAGLoader:
    """Loads data from databases into Qdrant for RAG functionality"""
    
    def __init__(self):
        self.embedding_model = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
        self.processed_hashes = {}  # Track processed content to avoid duplicates
    
    async def initialize(self):
        """Initialize database connections"""
        await db_connections.initialize_connections()
        await db_connections.setup_qdrant_collection()
    
    def generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def load_customer_knowledge(self) -> List[Document]:
        """Load customer service knowledge from databases"""
        documents = []
        
        # PostgreSQL queries for customer knowledge
        pg_queries = {
            "customer_policies": """
                SELECT 
                    'policy' as doc_type,
                    policy_name as title,
                    policy_description as content,
                    created_at,
                    updated_at,
                    priority_level,
                    CONCAT('Policy: ', policy_name, ' - ', policy_description) as full_text
                FROM customer_policies 
                WHERE active = true
                ORDER BY priority_level DESC, updated_at DESC
            """,
            
            "faq_items": """
                SELECT 
                    'faq' as doc_type,
                    question as title,
                    answer as content,
                    category,
                    created_at,
                    updated_at,
                    CONCAT('Q: ', question, ' A: ', answer) as full_text
                FROM customer_faq 
                WHERE active = true
                ORDER BY category, created_at DESC
            """,
            
            "support_resolutions": """
                SELECT 
                    'resolution' as doc_type,
                    issue_category as title,
                    resolution_steps as content,
                    avg_resolution_time,
                    success_rate,
                    created_at,
                    updated_at,
                    CONCAT('Issue: ', issue_category, ' Resolution: ', resolution_steps) as full_text
                FROM support_resolutions 
                WHERE success_rate >= 0.8
                ORDER BY success_rate DESC
            """
        }
        
        try:
            # Load from PostgreSQL
            for query_name, query in pg_queries.items():
                try:
                    df = await db_connections.execute_sql_query(query)
                    
                    for _, row in df.iterrows():
                        content_hash = self.generate_content_hash(row['full_text'])
                        
                        if content_hash not in self.processed_hashes:
                            doc = Document(
                                text=row['full_text'],
                                metadata={
                                    "group_id": "customer_agent",
                                    "document_type": row['doc_type'],
                                    "title": row['title'],
                                    "source": "postgresql",
                                    "table": query_name,
                                    "content_hash": content_hash,
                                    "created_at": row.get('created_at', datetime.now()).isoformat(),
                                    "updated_at": row.get('updated_at', datetime.now()).isoformat(),
                                    **{k: v for k, v in row.items() if k not in ['full_text', 'content', 'title']}
                                }
                            )
                            documents.append(doc)
                            self.processed_hashes[content_hash] = query_name
                        
                except Exception as e:
                    logger.warning(f"Failed to load {query_name}: {e}")
                    continue
            
            # Load from MongoDB
            if db_connections.mongo_client:
                try:
                    # Customer interactions
                    interactions = await db_connections.query_mongodb_collection(
                        "customer_interactions",
                        {"status": "resolved", "satisfaction_score": {"$gte": 4}},
                        limit=100
                    )
                    
                    for interaction in interactions:
                        content = f"Customer Issue: {interaction.get('issue_summary', '')} " \
                                f"Resolution: {interaction.get('resolution', '')} " \
                                f"Satisfaction: {interaction.get('satisfaction_score', 0)}/5"
                        
                        content_hash = self.generate_content_hash(content)
                        
                        if content_hash not in self.processed_hashes:
                            doc = Document(
                                text=content,
                                metadata={
                                    "group_id": "customer_agent",
                                    "document_type": "interaction",
                                    "source": "mongodb",
                                    "collection": "customer_interactions",
                                    "content_hash": content_hash,
                                    "satisfaction_score": interaction.get('satisfaction_score', 0),
                                    "issue_category": interaction.get('category', 'general'),
                                    "created_at": interaction.get('created_at', datetime.now()).isoformat()
                                }
                            )
                            documents.append(doc)
                            self.processed_hashes[content_hash] = "customer_interactions"
                
                except Exception as e:
                    logger.warning(f"Failed to load MongoDB customer data: {e}")
        
        except Exception as e:
            logger.error(f"Error loading customer knowledge: {e}")
        
        logger.info(f"Loaded {len(documents)} customer knowledge documents")
        return documents
    
    async def load_restaurant_knowledge(self) -> List[Document]:
        """Load restaurant and menu knowledge from databases"""
        documents = []
        
        # PostgreSQL queries for restaurant knowledge
        pg_queries = {
            "menu_items": """
                SELECT 
                    'menu_item' as doc_type,
                    r.restaurant_name,
                    mi.item_name as title,
                    mi.description as content,
                    mi.category,
                    mi.prep_time_minutes,
                    mi.allergens,
                    mi.price,
                    mi.available,
                    mi.created_at,
                    mi.updated_at,
                    CONCAT(r.restaurant_name, ' - ', mi.item_name, ': ', 
                           COALESCE(mi.description, ''), 
                           ' (Category: ', mi.category, 
                           ', Prep time: ', mi.prep_time_minutes, ' min',
                           CASE WHEN mi.allergens IS NOT NULL THEN ', Allergens: ' || mi.allergens ELSE '' END,
                           ')') as full_text
                FROM menu_items mi
                JOIN restaurants r ON r.id = mi.restaurant_id
                WHERE mi.available = true AND r.active = true
                ORDER BY r.restaurant_name, mi.category, mi.item_name
            """,
            
            "restaurant_policies": """
                SELECT 
                    'restaurant_policy' as doc_type,
                    r.restaurant_name,
                    rp.policy_name as title,
                    rp.policy_description as content,
                    rp.policy_type,
                    rp.created_at,
                    rp.updated_at,
                    CONCAT('Restaurant: ', r.restaurant_name, 
                           ' Policy: ', rp.policy_name, ' - ', rp.policy_description) as full_text
                FROM restaurant_policies rp
                JOIN restaurants r ON r.id = rp.restaurant_id
                WHERE rp.active = true AND r.active = true
                ORDER BY r.restaurant_name, rp.policy_type
            """
        }
        
        try:
            # Load from PostgreSQL
            for query_name, query in pg_queries.items():
                try:
                    df = await db_connections.execute_sql_query(query)
                    
                    for _, row in df.iterrows():
                        content_hash = self.generate_content_hash(row['full_text'])
                        
                        if content_hash not in self.processed_hashes:
                            doc = Document(
                                text=row['full_text'],
                                metadata={
                                    "group_id": "restaurant_agent",
                                    "document_type": row['doc_type'],
                                    "title": row['title'],
                                    "restaurant_name": row.get('restaurant_name', ''),
                                    "source": "postgresql",
                                    "table": query_name,
                                    "content_hash": content_hash,
                                    "created_at": row.get('created_at', datetime.now()).isoformat(),
                                    "updated_at": row.get('updated_at', datetime.now()).isoformat(),
                                    **{k: v for k, v in row.items() if k not in ['full_text', 'content', 'title']}
                                }
                            )
                            documents.append(doc)
                            self.processed_hashes[content_hash] = query_name
                        
                except Exception as e:
                    logger.warning(f"Failed to load {query_name}: {e}")
                    continue
            
            # Load from MongoDB
            if db_connections.mongo_client:
                try:
                    # Kitchen operations
                    operations = await db_connections.query_mongodb_collection(
                        "kitchen_operations",
                        {"date": {"$gte": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")}},
                        limit=200
                    )
                    
                    for op in operations:
                        content = f"Kitchen Operations for {op.get('restaurant_name', 'Unknown')}: " \
                                f"Date: {op.get('date')}, " \
                                f"Average prep time: {op.get('avg_prep_time', 'N/A')} min, " \
                                f"Efficiency score: {op.get('efficiency_score', 'N/A')}, " \
                                f"Notes: {op.get('notes', '')}"
                        
                        content_hash = self.generate_content_hash(content)
                        
                        if content_hash not in self.processed_hashes:
                            doc = Document(
                                text=content,
                                metadata={
                                    "group_id": "restaurant_agent",
                                    "document_type": "kitchen_operations",
                                    "source": "mongodb",
                                    "collection": "kitchen_operations",
                                    "content_hash": content_hash,
                                    "restaurant_name": op.get('restaurant_name', ''),
                                    "date": op.get('date', ''),
                                    "efficiency_score": op.get('efficiency_score', 0),
                                    "created_at": op.get('created_at', datetime.now()).isoformat()
                                }
                            )
                            documents.append(doc)
                            self.processed_hashes[content_hash] = "kitchen_operations"
                
                except Exception as e:
                    logger.warning(f"Failed to load MongoDB restaurant data: {e}")
        
        except Exception as e:
            logger.error(f"Error loading restaurant knowledge: {e}")
        
        logger.info(f"Loaded {len(documents)} restaurant knowledge documents")
        return documents
    
    async def load_delivery_knowledge(self) -> List[Document]:
        """Load delivery and logistics knowledge from databases"""
        documents = []
        
        # PostgreSQL queries for delivery knowledge
        pg_queries = {
            "delivery_zones": """
                SELECT 
                    'delivery_zone' as doc_type,
                    zone_name as title,
                    zone_description as content,
                    delivery_fee,
                    avg_delivery_time_minutes,
                    created_at,
                    updated_at,
                    CONCAT('Delivery Zone: ', zone_name, ' - ', zone_description, 
                           ' (Fee: $', delivery_fee, 
                           ', Avg time: ', avg_delivery_time_minutes, ' min)') as full_text
                FROM delivery_zones 
                WHERE active = true
                ORDER BY zone_name
            """,
            
            "delivery_policies": """
                SELECT 
                    'delivery_policy' as doc_type,
                    policy_name as title,
                    policy_description as content,
                    applies_to_zone,
                    created_at,
                    updated_at,
                    CONCAT('Delivery Policy: ', policy_name, ' - ', policy_description,
                           CASE WHEN applies_to_zone IS NOT NULL THEN ' (Zone: ' || applies_to_zone || ')' ELSE '' END) as full_text
                FROM delivery_policies 
                WHERE active = true
                ORDER BY policy_name
            """
        }
        
        try:
            # Load from PostgreSQL
            for query_name, query in pg_queries.items():
                try:
                    df = await db_connections.execute_sql_query(query)
                    
                    for _, row in df.iterrows():
                        content_hash = self.generate_content_hash(row['full_text'])
                        
                        if content_hash not in self.processed_hashes:
                            doc = Document(
                                text=row['full_text'],
                                metadata={
                                    "group_id": "delivery_agent",
                                    "document_type": row['doc_type'],
                                    "title": row['title'],
                                    "source": "postgresql",
                                    "table": query_name,
                                    "content_hash": content_hash,
                                    "created_at": row.get('created_at', datetime.now()).isoformat(),
                                    "updated_at": row.get('updated_at', datetime.now()).isoformat(),
                                    **{k: v for k, v in row.items() if k not in ['full_text', 'content', 'title']}
                                }
                            )
                            documents.append(doc)
                            self.processed_hashes[content_hash] = query_name
                        
                except Exception as e:
                    logger.warning(f"Failed to load {query_name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error loading delivery knowledge: {e}")
        
        logger.info(f"Loaded {len(documents)} delivery knowledge documents")
        return documents
    
    async def load_order_knowledge(self) -> List[Document]:
        """Load order processing knowledge from databases"""
        documents = []
        
        # PostgreSQL queries for order knowledge
        pg_queries = {
            "order_statuses": """
                SELECT 
                    'order_status' as doc_type,
                    status_name as title,
                    status_description as content,
                    next_possible_statuses,
                    customer_notification_required,
                    created_at,
                    updated_at,
                    CONCAT('Order Status: ', status_name, ' - ', status_description,
                           CASE WHEN next_possible_statuses IS NOT NULL 
                           THEN ' (Next statuses: ' || next_possible_statuses || ')' 
                           ELSE '' END) as full_text
                FROM order_statuses 
                WHERE active = true
                ORDER BY status_name
            """,
            
            "payment_methods": """
                SELECT 
                    'payment_method' as doc_type,
                    method_name as title,
                    method_description as content,
                    processing_fee,
                    processing_time_minutes,
                    created_at,
                    updated_at,
                    CONCAT('Payment Method: ', method_name, ' - ', method_description,
                           ' (Fee: ', COALESCE(processing_fee::text, 'N/A'), 
                           ', Processing time: ', processing_time_minutes, ' min)') as full_text
                FROM payment_methods 
                WHERE active = true
                ORDER BY method_name
            """
        }
        
        try:
            # Load from PostgreSQL
            for query_name, query in pg_queries.items():
                try:
                    df = await db_connections.execute_sql_query(query)
                    
                    for _, row in df.iterrows():
                        content_hash = self.generate_content_hash(row['full_text'])
                        
                        if content_hash not in self.processed_hashes:
                            doc = Document(
                                text=row['full_text'],
                                metadata={
                                    "group_id": "order_agent",
                                    "document_type": row['doc_type'],
                                    "title": row['title'],
                                    "source": "postgresql",
                                    "table": query_name,
                                    "content_hash": content_hash,
                                    "created_at": row.get('created_at', datetime.now()).isoformat(),
                                    "updated_at": row.get('updated_at', datetime.now()).isoformat(),
                                    **{k: v for k, v in row.items() if k not in ['full_text', 'content', 'title']}
                                }
                            )
                            documents.append(doc)
                            self.processed_hashes[content_hash] = query_name
                        
                except Exception as e:
                    logger.warning(f"Failed to load {query_name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error loading order knowledge: {e}")
        
        logger.info(f"Loaded {len(documents)} order knowledge documents")
        return documents
    
    async def embed_and_store_documents(self, documents: List[Document]) -> bool:
        """Embed documents and store them in Qdrant"""
        if not documents:
            logger.warning("No documents to embed and store")
            return False
        
        try:
            # Generate embeddings in batches (increased for better performance)
            batch_size = 100
            points = []
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                texts = [doc.text for doc in batch]
                
                # Get embeddings
                embeddings = self.embedding_model.get_text_embedding_batch(texts)
                
                # Create points for Qdrant
                for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                    point_id = f"{doc.metadata['group_id']}_{doc.metadata['content_hash']}_{i+j}"
                    
                    points.append(PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=doc.metadata
                    ))
            
            # Store in Qdrant
            if points:
                db_connections.qdrant_client.upsert(
                    collection_name=settings.qdrant_collection_name,
                    points=points
                )
                logger.info(f"Successfully stored {len(points)} points in Qdrant")
                return True
            else:
                logger.warning("No points generated for storage")
                return False
                
        except Exception as e:
            logger.error(f"Error embedding and storing documents: {e}")
            return False
    
    async def load_all_knowledge(self) -> bool:
        """Load all knowledge from databases into Qdrant"""
        logger.info("Starting complete knowledge base loading...")
        
        try:
            await self.initialize()
            
            all_documents = []
            
            # Load knowledge for each agent
            logger.info("Loading customer knowledge...")
            customer_docs = await self.load_customer_knowledge()
            all_documents.extend(customer_docs)
            
            logger.info("Loading restaurant knowledge...")
            restaurant_docs = await self.load_restaurant_knowledge()
            all_documents.extend(restaurant_docs)
            
            logger.info("Loading delivery knowledge...")
            delivery_docs = await self.load_delivery_knowledge()
            all_documents.extend(delivery_docs)
            
            logger.info("Loading order knowledge...")
            order_docs = await self.load_order_knowledge()
            all_documents.extend(order_docs)
            
            logger.info(f"Total documents loaded: {len(all_documents)}")
            
            # Embed and store all documents
            if all_documents:
                success = await self.embed_and_store_documents(all_documents)
                if success:
                    logger.info("✅ Knowledge base loading completed successfully!")
                    return True
                else:
                    logger.error("❌ Failed to store documents in Qdrant")
                    return False
            else:
                logger.warning("No documents loaded from databases")
                return False
                
        except Exception as e:
            logger.error(f"Error during knowledge base loading: {e}")
            return False
        
        finally:
            db_connections.close_connections()