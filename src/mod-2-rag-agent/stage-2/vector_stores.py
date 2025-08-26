"""
Vector store ingestion module for Pinecone and Qdrant.

This module handles the ingestion of embedded chunks into
both Pinecone (cloud) and Qdrant (self-hosted) vector databases.
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime
import uuid

from pinecone import Pinecone, ServerlessSpec
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    CollectionStatus,
    OptimizersConfigDiff,
    CreateCollection,
    SearchRequest,
    Filter,
    FieldCondition,
    MatchValue,
    UpdateStatus
)
import numpy as np
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Settings, PineconeConfig, QdrantConfig
from chunking_strategies import Chunk, ChunkType


class PineconeIngester:
    """
    Manages ingestion of vectors into Pinecone cloud service.
    
    Handles index creation, batch uploading, and metadata filtering
    for efficient cloud-based vector storage.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize Pinecone ingester.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.config = settings.pinecone
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.config.api_key)
        
        # Initialize indexes
        self.indexes = {}
        self._initialize_indexes()
        
        # Statistics
        self.stats = {
            'total_ingested': 0,
            'failed_ingestions': 0,
            'total_batches': 0
        }
    
    def _initialize_indexes(self):
        """Create or connect to Pinecone indexes."""
        index_configs = {
            self.config.index_name_summaries: {
                'dimension': self.config.dimension,
                'metric': self.config.metric,
                'description': 'Document and section summaries'
            },
            self.config.index_name_chunks: {
                'dimension': self.config.dimension,
                'metric': self.config.metric,
                'description': 'Detailed text chunks'
            }
        }
        
        for index_name, config in index_configs.items():
            try:
                # Check if index exists
                if index_name not in self.pc.list_indexes().names():
                    logger.info(f"Creating Pinecone index: {index_name}")
                    self.pc.create_index(
                        name=index_name,
                        dimension=config['dimension'],
                        metric=config['metric'],
                        spec=ServerlessSpec(
                            cloud='aws',
                            region=self.config.environment
                        )
                    )
                
                # Connect to index
                self.indexes[index_name] = self.pc.Index(index_name)
                logger.info(f"Connected to Pinecone index: {index_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize index {index_name}: {e}")
                raise
    
    def _determine_index(self, chunk: Chunk) -> str:
        """
        Determine which index to use for a chunk.
        
        Args:
            chunk: Chunk to ingest
            
        Returns:
            Index name
        """
        if chunk.chunk_type in [ChunkType.DOCUMENT_SUMMARY, ChunkType.SECTION]:
            return self.config.index_name_summaries
        else:
            return self.config.index_name_chunks
    
    def _prepare_vector(self, chunk: Chunk, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare vector data for Pinecone ingestion.
        
        Args:
            chunk: Chunk with embedding
            namespace: Optional namespace
            
        Returns:
            Vector data dictionary
        """
        # Ensure embedding exists
        if chunk.embedding is None:
            raise ValueError(f"Chunk {chunk.id} has no embedding")
        
        # Prepare metadata (Pinecone has metadata size limits)
        metadata = {
            'text': chunk.text[:1000],  # Truncate for metadata limit
            'chunk_type': chunk.chunk_type.value,
            'parent_id': chunk.parent_id or '',
            'module': chunk.metadata.get('module', 'unknown'),
            'filename': chunk.metadata.get('filename', 'unknown'),
            'token_count': chunk.metadata.get('token_count', 0),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add additional metadata if within limits
        for key in ['section_title', 'primary_topic', 'keywords']:
            if key in chunk.metadata:
                value = chunk.metadata[key]
                if isinstance(value, list):
                    value = ','.join(value[:5])  # Limit list items
                metadata[key] = str(value)[:100]  # Limit string length
        
        return {
            'id': chunk.id,
            'values': chunk.embedding.tolist(),
            'metadata': metadata
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def ingest_chunk(self, chunk: Chunk, namespace: Optional[str] = None) -> bool:
        """
        Ingest single chunk into Pinecone.
        
        Args:
            chunk: Chunk to ingest
            namespace: Optional namespace
            
        Returns:
            Success status
        """
        try:
            index_name = self._determine_index(chunk)
            index = self.indexes[index_name]
            
            # Determine namespace based on module
            if namespace is None:
                module = chunk.metadata.get('module', 'default')
                namespace = f"{self.config.namespace_prefix}-{module}"
            
            # Prepare vector
            vector = self._prepare_vector(chunk, namespace)
            
            # Upsert to Pinecone
            index.upsert(
                vectors=[vector],
                namespace=namespace
            )
            
            self.stats['total_ingested'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest chunk {chunk.id}: {e}")
            self.stats['failed_ingestions'] += 1
            return False
    
    async def ingest_batch(
        self, 
        chunks: List[Chunk], 
        namespace: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Ingest batch of chunks into Pinecone.
        
        Args:
            chunks: List of chunks to ingest
            namespace: Optional namespace
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        # Group chunks by index
        chunks_by_index = {}
        for chunk in chunks:
            index_name = self._determine_index(chunk)
            if index_name not in chunks_by_index:
                chunks_by_index[index_name] = []
            chunks_by_index[index_name].append(chunk)
        
        successful = 0
        failed = 0
        
        # Process each index separately
        for index_name, index_chunks in chunks_by_index.items():
            index = self.indexes[index_name]
            
            # Process in batches
            batch_size = self.config.batch_size
            for i in range(0, len(index_chunks), batch_size):
                batch = index_chunks[i:i + batch_size]
                
                try:
                    # Prepare vectors
                    vectors = []
                    for chunk in batch:
                        if chunk.embedding is not None:
                            # Determine namespace
                            chunk_namespace = namespace
                            if chunk_namespace is None:
                                module = chunk.metadata.get('module', 'default')
                                chunk_namespace = f"{self.config.namespace_prefix}-{module}"
                            
                            vector = self._prepare_vector(chunk, chunk_namespace)
                            vectors.append(vector)
                    
                    if vectors:
                        # Upsert batch
                        index.upsert(
                            vectors=vectors,
                            namespace=chunk_namespace
                        )
                        successful += len(vectors)
                        self.stats['total_ingested'] += len(vectors)
                    
                except Exception as e:
                    logger.error(f"Failed to ingest batch: {e}")
                    failed += len(batch)
                    self.stats['failed_ingestions'] += len(batch)
                
                self.stats['total_batches'] += 1
        
        logger.info(f"Ingested {successful}/{len(chunks)} chunks to Pinecone")
        return successful, failed
    
    def query(
        self, 
        query_embedding: np.ndarray,
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Pinecone index.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            namespace: Optional namespace
            filter: Optional metadata filter
            
        Returns:
            List of matches
        """
        results = []
        
        for index_name, index in self.indexes.items():
            try:
                response = index.query(
                    vector=query_embedding.tolist(),
                    top_k=top_k,
                    namespace=namespace,
                    filter=filter,
                    include_metadata=True
                )
                
                for match in response['matches']:
                    results.append({
                        'id': match['id'],
                        'score': match['score'],
                        'metadata': match.get('metadata', {}),
                        'index': index_name
                    })
            
            except Exception as e:
                logger.error(f"Query failed for index {index_name}: {e}")
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get ingestion statistics.
        
        Returns:
            Statistics dictionary
        """
        index_stats = {}
        for name, index in self.indexes.items():
            try:
                stats = index.describe_index_stats()
                index_stats[name] = {
                    'total_vectors': stats.get('total_vector_count', 0),
                    'dimension': stats.get('dimension', 0),
                    'namespaces': stats.get('namespaces', {})
                }
            except:
                index_stats[name] = {}
        
        return {
            **self.stats,
            'indexes': index_stats
        }


class QdrantIngester:
    """
    Manages ingestion of vectors into Qdrant vector database.
    
    Handles collection creation, batch uploading, and advanced
    filtering for self-hosted or cloud Qdrant instances.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize Qdrant ingester.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.config = settings.qdrant
        
        # Initialize Qdrant client
        # Handle cloud URL format
        if self.config.host.startswith('https://'):
            self.client = QdrantClient(
                url=self.config.host,
                api_key=self.config.api_key
            )
        else:
            self.client = QdrantClient(
                host=self.config.host,
                port=self.config.port,
                api_key=self.config.api_key,
                https=self.config.use_https
            )
        
        # Initialize collection
        self._initialize_collection()
        
        # Statistics
        self.stats = {
            'total_ingested': 0,
            'failed_ingestions': 0,
            'total_batches': 0
        }
    
    def _initialize_collection(self):
        """Create or verify Qdrant collection."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.config.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: {self.config.collection_name}")
                
                # Create collection with configuration
                self.client.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=VectorParams(
                        size=self.config.vector_size,
                        distance=getattr(Distance, self.config.distance.upper())
                    ),
                    shard_number=self.config.shards if self.config.shards > 1 else None,
                    optimizers_config=OptimizersConfigDiff(
                        default_segment_number=2,
                        indexing_threshold=20000
                    ),
                    on_disk_payload=True  # For large payloads
                )
                
                # Create payload indexes for efficient filtering
                self._create_payload_indexes()
            
            # Get collection info
            collection_info = self.client.get_collection(self.config.collection_name)
            logger.info(
                f"Connected to Qdrant collection: {self.config.collection_name} "
                f"(vectors: {collection_info.vectors_count}, "
                f"status: {collection_info.status})"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise
    
    def _create_payload_indexes(self):
        """Create indexes on payload fields for faster filtering."""
        index_fields = [
            'chunk_type',
            'module',
            'filename',
            'primary_topic',
            'parent_id'
        ]
        
        for field in index_fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.config.collection_name,
                    field_name=field,
                    field_schema="keyword"
                )
                logger.debug(f"Created payload index for field: {field}")
            except Exception as e:
                logger.debug(f"Payload index for {field} might already exist: {e}")
    
    def _prepare_point(self, chunk: Chunk) -> PointStruct:
        """
        Prepare point for Qdrant ingestion.
        
        Args:
            chunk: Chunk with embedding
            
        Returns:
            Qdrant PointStruct
        """
        if chunk.embedding is None:
            raise ValueError(f"Chunk {chunk.id} has no embedding")
        
        # Prepare payload (Qdrant can handle larger payloads than Pinecone)
        payload = {
            'text': chunk.text,
            'chunk_type': chunk.chunk_type.value,
            'parent_id': chunk.parent_id or '',
            'child_ids': chunk.child_ids,
            'module': chunk.metadata.get('module', 'unknown'),
            'filename': chunk.metadata.get('filename', 'unknown'),
            'token_count': chunk.metadata.get('token_count', 0),
            'char_count': chunk.metadata.get('char_count', 0),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add all metadata
        for key, value in chunk.metadata.items():
            if key not in payload:
                # Convert lists to strings for indexing
                if isinstance(value, list):
                    payload[key] = ','.join(map(str, value))
                elif isinstance(value, dict):
                    # Flatten nested dicts
                    for sub_key, sub_value in value.items():
                        payload[f"{key}_{sub_key}"] = str(sub_value)
                else:
                    payload[key] = value
        
        # Use UUID based on chunk ID for consistent IDs
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.id))
        
        return PointStruct(
            id=point_id,
            vector=chunk.embedding.tolist(),
            payload=payload
        )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def ingest_chunk(self, chunk: Chunk) -> bool:
        """
        Ingest single chunk into Qdrant.
        
        Args:
            chunk: Chunk to ingest
            
        Returns:
            Success status
        """
        try:
            point = self._prepare_point(chunk)
            
            # Upsert point
            operation_info = self.client.upsert(
                collection_name=self.config.collection_name,
                points=[point]
            )
            
            if operation_info.status == UpdateStatus.COMPLETED:
                self.stats['total_ingested'] += 1
                return True
            else:
                logger.warning(f"Qdrant upsert status: {operation_info.status}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to ingest chunk {chunk.id} to Qdrant: {e}")
            self.stats['failed_ingestions'] += 1
            return False
    
    async def ingest_batch(self, chunks: List[Chunk]) -> Tuple[int, int]:
        """
        Ingest batch of chunks into Qdrant.
        
        Args:
            chunks: List of chunks to ingest
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        # Process in batches
        batch_size = 100  # Qdrant handles larger batches well
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            try:
                # Prepare points
                points = []
                for chunk in batch:
                    if chunk.embedding is not None:
                        try:
                            point = self._prepare_point(chunk)
                            points.append(point)
                        except Exception as e:
                            logger.error(f"Failed to prepare point for chunk {chunk.id}: {e}")
                            failed += 1
                
                if points:
                    # Upsert batch
                    operation_info = self.client.upsert(
                        collection_name=self.config.collection_name,
                        points=points
                    )
                    
                    if operation_info.status == UpdateStatus.COMPLETED:
                        successful += len(points)
                        self.stats['total_ingested'] += len(points)
                    else:
                        logger.warning(f"Qdrant batch upsert status: {operation_info.status}")
                        failed += len(points)
                
            except Exception as e:
                logger.error(f"Failed to ingest batch to Qdrant: {e}")
                failed += len(batch)
                self.stats['failed_ingestions'] += len(batch)
            
            self.stats['total_batches'] += 1
        
        logger.info(f"Ingested {successful}/{len(chunks)} chunks to Qdrant")
        return successful, failed
    
    def query(
        self, 
        query_embedding: np.ndarray,
        top_k: int = 10,
        filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Qdrant collection.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            filter: Optional filter conditions
            
        Returns:
            List of matches
        """
        try:
            # Build Qdrant filter from dict
            qdrant_filter = None
            if filter:
                conditions = []
                for key, value in filter.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    qdrant_filter = Filter(must=conditions)
            
            # Search
            results = self.client.search(
                collection_name=self.config.collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True
            )
            
            # Format results
            matches = []
            for result in results:
                matches.append({
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload,
                    'text': result.payload.get('text', '')
                })
            
            return matches
            
        except Exception as e:
            logger.error(f"Qdrant query failed: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            collection_info = self.client.get_collection(self.config.collection_name)
            
            return {
                **self.stats,
                'collection': {
                    'vectors_count': collection_info.vectors_count,
                    'points_count': collection_info.points_count,
                    'segments_count': collection_info.segments_count,
                    'status': str(collection_info.status),
                    'config': {
                        'vector_size': collection_info.config.params.vectors.size,
                        'distance': str(collection_info.config.params.vectors.distance),
                        'shard_number': collection_info.config.params.shard_number
                    }
                }
            }
        except Exception as e:
            logger.error(f"Failed to get Qdrant statistics: {e}")
            return self.stats
    
    def optimize_collection(self):
        """Optimize Qdrant collection for better performance."""
        try:
            self.client.update_collection(
                collection_name=self.config.collection_name,
                optimizer_config=OptimizersConfigDiff(
                    indexing_threshold=50000,
                    flush_interval_sec=5,
                    max_segment_size=200000
                )
            )
            logger.info("Optimized Qdrant collection configuration")
        except Exception as e:
            logger.error(f"Failed to optimize collection: {e}")


class DualVectorStoreManager:
    """
    Manages ingestion into both Pinecone and Qdrant simultaneously.
    
    Provides unified interface for dual vector store operations
    with fallback and redundancy support.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize dual vector store manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.pinecone_ingester = PineconeIngester(settings)
        self.qdrant_ingester = QdrantIngester(settings)
    
    async def ingest_chunks(
        self, 
        chunks: List[Chunk],
        strategy: str = "both"
    ) -> Dict[str, Any]:
        """
        Ingest chunks into vector stores based on strategy.
        
        Args:
            chunks: List of chunks to ingest
            strategy: Ingestion strategy (both, pinecone, qdrant, failover)
            
        Returns:
            Ingestion results
        """
        results = {
            'pinecone': {'successful': 0, 'failed': 0},
            'qdrant': {'successful': 0, 'failed': 0},
            'strategy': strategy,
            'total_chunks': len(chunks)
        }
        
        if strategy in ["both", "pinecone"]:
            try:
                success, fail = await self.pinecone_ingester.ingest_batch(chunks)
                results['pinecone']['successful'] = success
                results['pinecone']['failed'] = fail
            except Exception as e:
                logger.error(f"Pinecone ingestion failed: {e}")
                results['pinecone']['error'] = str(e)
        
        if strategy in ["both", "qdrant"]:
            try:
                success, fail = await self.qdrant_ingester.ingest_batch(chunks)
                results['qdrant']['successful'] = success
                results['qdrant']['failed'] = fail
            except Exception as e:
                logger.error(f"Qdrant ingestion failed: {e}")
                results['qdrant']['error'] = str(e)
        
        if strategy == "failover":
            # Try Pinecone first, fall back to Qdrant on failure
            try:
                success, fail = await self.pinecone_ingester.ingest_batch(chunks)
                results['pinecone']['successful'] = success
                results['pinecone']['failed'] = fail
                results['primary_store'] = 'pinecone'
            except Exception as e:
                logger.warning(f"Pinecone failed, falling back to Qdrant: {e}")
                try:
                    success, fail = await self.qdrant_ingester.ingest_batch(chunks)
                    results['qdrant']['successful'] = success
                    results['qdrant']['failed'] = fail
                    results['primary_store'] = 'qdrant'
                except Exception as e2:
                    logger.error(f"Both stores failed: Pinecone: {e}, Qdrant: {e2}")
                    results['error'] = "Both stores failed"
        
        return results
    
    def query_both(
        self, 
        query_embedding: np.ndarray,
        top_k: int = 10,
        filter: Optional[Dict] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query both vector stores.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results per store
            filter: Optional filter conditions
            
        Returns:
            Results from both stores
        """
        results = {}
        
        try:
            results['pinecone'] = self.pinecone_ingester.query(
                query_embedding, top_k, filter=filter
            )
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            results['pinecone'] = []
        
        try:
            results['qdrant'] = self.qdrant_ingester.query(
                query_embedding, top_k, filter=filter
            )
        except Exception as e:
            logger.error(f"Qdrant query failed: {e}")
            results['qdrant'] = []
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics from both vector stores.
        
        Returns:
            Combined statistics
        """
        return {
            'pinecone': self.pinecone_ingester.get_statistics(),
            'qdrant': self.qdrant_ingester.get_statistics()
        }