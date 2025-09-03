import asyncio
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseConnections:
    """Manages all database connections for the UberEats RAG system"""
    
    def __init__(self):
        self.pg_engine = None
        self.pg_async_engine = None
        self.mongo_client = None
        self.mongo_async_client = None
        self.qdrant_client = None
        self.connections_tested = False
    
    async def initialize_connections(self):
        """Initialize all database connections"""
        try:
            # PostgreSQL connections
            if settings.database_url:
                self.pg_engine = create_engine(settings.database_url)
                # Convert to async URL for asyncpg
                async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
                self.pg_async_engine = create_async_engine(async_url)
                logger.info("PostgreSQL connections initialized")
            
            # MongoDB connections
            if settings.mongodb_connection_string:
                self.mongo_client = MongoClient(settings.mongodb_connection_string)
                self.mongo_async_client = AsyncIOMotorClient(settings.mongodb_connection_string)
                logger.info("MongoDB connections initialized")
            
            # Qdrant connection
            if settings.qdrant_url:
                self.qdrant_client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key,
                    timeout=60
                )
                logger.info("Qdrant connection initialized")
            
            # Test all connections
            await self.test_all_connections()
            
        except Exception as e:
            logger.error(f"Failed to initialize connections: {e}")
            raise
    
    async def test_all_connections(self) -> Dict[str, Any]:
        """Test all database connections and return status"""
        results = {
            "postgresql": {"status": "not_configured", "error": None},
            "mongodb": {"status": "not_configured", "error": None},
            "qdrant": {"status": "not_configured", "error": None}
        }
        
        # Test PostgreSQL
        if self.pg_engine:
            try:
                with self.pg_engine.connect() as conn:
                    result = conn.execute(text("SELECT 1")).scalar()
                    if result == 1:
                        results["postgresql"]["status"] = "connected"
                        logger.info("✅ PostgreSQL connection successful")
                    else:
                        results["postgresql"]["status"] = "failed"
            except Exception as e:
                results["postgresql"]["status"] = "failed"
                results["postgresql"]["error"] = str(e)
                logger.error(f"❌ PostgreSQL connection failed: {e}")
        
        # Test MongoDB
        if self.mongo_client:
            try:
                # Ping the MongoDB server
                self.mongo_client.admin.command('ping')
                results["mongodb"]["status"] = "connected"
                logger.info("✅ MongoDB connection successful")
                
                # List available databases
                db_list = self.mongo_client.list_database_names()
                logger.info(f"Available MongoDB databases: {db_list}")
                
            except Exception as e:
                results["mongodb"]["status"] = "failed"
                results["mongodb"]["error"] = str(e)
                logger.error(f"❌ MongoDB connection failed: {e}")
        
        # Test Qdrant
        if self.qdrant_client:
            try:
                collections = self.qdrant_client.get_collections()
                results["qdrant"]["status"] = "connected"
                logger.info("✅ Qdrant connection successful")
                logger.info(f"Existing collections: {[c.name for c in collections.collections]}")
                
            except Exception as e:
                results["qdrant"]["status"] = "failed"
                results["qdrant"]["error"] = str(e)
                logger.error(f"❌ Qdrant connection failed: {e}")
        
        self.connections_tested = True
        return results
    
    async def setup_qdrant_collection(self) -> bool:
        """Setup Qdrant collection for UberEats knowledge"""
        if not self.qdrant_client:
            logger.error("Qdrant client not initialized")
            return False
        
        try:
            collection_name = settings.qdrant_collection_name
            
            # Check if collection exists
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                logger.info(f"Collection '{collection_name}' already exists")
                return True
            except:
                logger.info(f"Collection '{collection_name}' does not exist, creating...")
            
            # Create collection
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.vector_dimension,
                    distance=Distance.COSINE
                )
            )
            
            # Create index on group_id for efficient filtering
            self.qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="group_id",
                field_schema="keyword"
            )
            
            logger.info(f"✅ Qdrant collection '{collection_name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Qdrant collection: {e}")
            return False
    
    async def get_postgresql_tables(self) -> List[str]:
        """Get list of PostgreSQL tables"""
        if not self.pg_engine:
            return []
        
        try:
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            df = pd.read_sql(query, self.pg_engine)
            return df['table_name'].tolist()
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL tables: {e}")
            return []
    
    async def get_mongodb_collections(self) -> List[str]:
        """Get list of MongoDB collections"""
        if not self.mongo_client:
            return []
        
        try:
            db = self.mongo_client[settings.mongodb_database]
            return db.list_collection_names()
        except Exception as e:
            logger.error(f"Failed to get MongoDB collections: {e}")
            return []
    
    async def execute_sql_query(self, query: str, params: Optional[List] = None) -> pd.DataFrame:
        """Execute SQL query and return DataFrame"""
        if not self.pg_engine:
            raise Exception("PostgreSQL not connected")
        
        try:
            return pd.read_sql(query, self.pg_engine, params=params)
        except Exception as e:
            logger.error(f"SQL query failed: {e}")
            raise
    
    async def query_mongodb_collection(
        self, 
        collection_name: str, 
        query: Optional[Dict] = None, 
        limit: int = 100
    ) -> list[Dict]:
        """Query MongoDB collection.
        
        Args:
            collection_name: Name of the collection to query.
            query: MongoDB query filter (defaults to empty filter).
            limit: Maximum number of documents to return.
            
        Returns:
            List of matching documents.
            
        Raises:
            Exception: If MongoDB is not connected or query fails.
        """
        if not self.mongo_client:
            raise Exception("MongoDB not connected")
        
        try:
            db = self.mongo_client[settings.mongodb_database]
            collection = db[collection_name]
            
            query = query or {}
            
            return list(collection.find(query).limit(limit))
        except Exception as e:
            logger.error(f"MongoDB query failed: {e}")
            raise
    
    def close_connections(self):
        """Close all database connections"""
        if self.mongo_client:
            self.mongo_client.close()
        if self.mongo_async_client:
            self.mongo_async_client.close()
        if self.pg_engine:
            self.pg_engine.dispose()
        if self.pg_async_engine:
            asyncio.create_task(self.pg_async_engine.dispose())
        
        logger.info("All database connections closed")


# Global instance
db_connections = DatabaseConnections()