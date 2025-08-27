"""
Embedding generation module for creating and managing vector representations.

This module handles embedding generation with caching, batching, and
optimization strategies for efficient vector creation.
"""

from __future__ import annotations

import asyncio
import hashlib
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from typing import Dict, Tuple

import numpy as np
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings import BaseEmbedding
from loguru import logger
import redis
from tenacity import retry, stop_after_attempt, wait_exponential
import tiktoken

from config import Settings, OpenAIConfig, CacheConfig
from chunking_strategies import Chunk, ChunkType


class EmbeddingCache:
    """
    Cache manager for embeddings using Redis or file system.
    
    Provides persistent caching to avoid regenerating embeddings
    for identical content.
    """
    
    def __init__(self, config: CacheConfig) -> None:
        """
        Initialize embedding cache.
        
        Args:
            config: Cache configuration
        """
        self.config = config
        self.cache_dir = Path(config.cache_dir) / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to connect to Redis if available
        self.redis_client = self._init_redis()
        self.use_redis = self.redis_client is not None
    
    def _init_redis(self) -> Optional[redis.Redis]:
        """
        Initialize Redis connection if available.
        
        Returns:
            Redis client or None if not available
        """
        try:
            client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=False,
                socket_connect_timeout=1
            )
            client.ping()
            logger.info("Connected to Redis for embedding cache")
            return client
        except (redis.ConnectionError, redis.TimeoutError):
            logger.info("Redis not available, using file-based cache")
            return None
    
    def get_cache_key(self, text: str, model: str) -> str:
        """
        Generate cache key for text and model combination.
        
        Args:
            text: Input text
            model: Embedding model name
            
        Returns:
            Cache key
        """
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[np.ndarray]:
        """
        Retrieve embedding from cache.
        
        Args:
            text: Input text
            model: Embedding model name
            
        Returns:
            Cached embedding or None
        """
        if not self.config.enabled:
            return None
        
        key = self.get_cache_key(text, model)
        
        # Try Redis first
        if self.use_redis:
            try:
                data = self.redis_client.get(f"emb:{key}")
                if data:
                    return pickle.loads(data)
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")
        
        # Fall back to file cache
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            try:
                with cache_file.open('rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.debug(f"File cache get failed: {e}")
        
        return None
    
    def set(self, text: str, model: str, embedding: np.ndarray) -> None:
        """
        Store embedding in cache.
        
        Args:
            text: Input text
            model: Embedding model name
            embedding: Embedding vector
        """
        if not self.config.enabled:
            return
        
        key = self.get_cache_key(text, model)
        data = pickle.dumps(embedding)
        
        # Store in Redis if available
        if self.use_redis:
            try:
                self.redis_client.setex(
                    f"emb:{key}",
                    self.config.ttl,
                    data
                )
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")
        
        # Also store in file cache
        cache_file = self.cache_dir / f"{key}.pkl"
        try:
            with cache_file.open('wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            logger.debug(f"File cache set failed: {e}")
    
    def clear(self) -> None:
        """Clear all cached embeddings."""
        # Clear Redis cache
        if self.use_redis:
            try:
                keys = self.redis_client.keys("emb:*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} Redis cache entries")
            except Exception as e:
                logger.error(f"Failed to clear Redis cache: {e}")
        
        # Clear file cache
        cache_files = list(self.cache_dir.glob("*.pkl"))
        for cache_file in cache_files:
            try:
                cache_file.unlink()
            except Exception as e:
                logger.debug(f"Failed to delete {cache_file}: {e}")
        logger.info(f"Cleared {len(cache_files)} file cache entries")


class OptimizedEmbeddingGenerator:
    """
    Optimized embedding generator with batching and caching.
    
    Provides efficient embedding generation with multiple strategies
    for cost and performance optimization.
    """
    
    def __init__(self, settings: Settings) -> None:
        """
        Initialize optimized embedding generator.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.openai_config = settings.openai
        self.cache_config = settings.cache
        self.performance_config = settings.performance
        
        # Initialize embedding models
        self.primary_model = OpenAIEmbedding(
            api_key=self.openai_config.api_key,
            model=self.openai_config.embedding_model,
            embed_batch_size=self.openai_config.embedding_batch_size
        )
        
        # Secondary model for cost optimization (smaller model)
        self.secondary_model = OpenAIEmbedding(
            api_key=self.openai_config.api_key,
            model="text-embedding-3-small",
            embed_batch_size=self.openai_config.embedding_batch_size
        )
        
        # Initialize cache
        self.cache = EmbeddingCache(self.cache_config)
        
        # Tokenizer for length validation
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        
        # Statistics
        self.stats = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'total_tokens': 0
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_embedding(
        self, 
        text: str, 
        use_secondary: bool = False
    ) -> np.ndarray:
        """
        Generate embedding for single text with retry logic.
        
        Args:
            text: Input text
            use_secondary: Whether to use secondary (cheaper) model
            
        Returns:
            Embedding vector
        """
        model_name = "text-embedding-3-small" if use_secondary else self.openai_config.embedding_model
        
        # Check cache first
        cached = self.cache.get(text, model_name)
        if cached is not None:
            self.stats['cache_hits'] += 1
            return cached
        
        self.stats['cache_misses'] += 1
        
        # Generate embedding
        model = self.secondary_model if use_secondary else self.primary_model
        
        try:
            embedding = await model.aget_text_embedding(text)
            embedding_array = np.array(embedding)
            
            # Normalize embedding
            embedding_array = self._normalize_embedding(embedding_array)
            
            # Cache the result
            self.cache.set(text, model_name, embedding_array)
            
            # Update statistics
            self.stats['api_calls'] += 1
            self.stats['total_tokens'] += len(self.tokenizer.encode(text))
            self.stats['total_embeddings'] += 1
            
            return embedding_array
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: list[str],
        use_secondary: bool = False
    ) -> list[np.ndarray]:
        """
        Generate embeddings for batch of texts efficiently.
        
        Args:
            texts: List of input texts
            use_secondary: Whether to use secondary model
            
        Returns:
            List of embedding vectors
        """
        model_name = "text-embedding-3-small" if use_secondary else self.openai_config.embedding_model
        embeddings = []
        texts_to_embed = []
        cached_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cached = self.cache.get(text, model_name)
            if cached is not None:
                embeddings.append((i, cached))
                self.stats['cache_hits'] += 1
            else:
                texts_to_embed.append((i, text))
                self.stats['cache_misses'] += 1
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            model = self.secondary_model if use_secondary else self.primary_model
            
            # Process in batches
            batch_size = self.openai_config.embedding_batch_size
            for batch_start in range(0, len(texts_to_embed), batch_size):
                batch_end = min(batch_start + batch_size, len(texts_to_embed))
                batch = texts_to_embed[batch_start:batch_end]
                
                batch_texts = [text for _, text in batch]
                
                try:
                    # Generate batch embeddings
                    batch_embeddings = await model.aget_text_embedding_batch(batch_texts)
                    
                    # Process and cache each embedding
                    for (original_idx, text), embedding in zip(batch, batch_embeddings):
                        embedding_array = np.array(embedding)
                        embedding_array = self._normalize_embedding(embedding_array)
                        
                        embeddings.append((original_idx, embedding_array))
                        self.cache.set(text, model_name, embedding_array)
                        
                        self.stats['total_embeddings'] += 1
                        self.stats['total_tokens'] += len(self.tokenizer.encode(text))
                    
                    self.stats['api_calls'] += 1
                    
                except Exception as e:
                    logger.error(f"Batch embedding generation failed: {e}")
                    # Fall back to individual generation
                    for original_idx, text in batch:
                        try:
                            embedding = await self.generate_embedding(text, use_secondary)
                            embeddings.append((original_idx, embedding))
                        except Exception as inner_e:
                            logger.error(f"Individual embedding failed for text {original_idx}: {inner_e}")
                            # Use zero vector as fallback
                            embeddings.append((original_idx, np.zeros(self.openai_config.embedding_dimensions)))
        
        # Sort by original index to maintain order
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]
    
    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """
        L2 normalize embedding vector.
        
        Args:
            embedding: Embedding vector
            
        Returns:
            Normalized embedding
        """
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    async def generate_chunk_embeddings(
        self,
        chunks: list[Chunk],
        strategy: str = "adaptive"
    ) -> list[Chunk]:
        """
        Generate embeddings for chunks with strategy selection.
        
        Args:
            chunks: List of chunks to embed
            strategy: Embedding strategy (adaptive, primary, secondary)
            
        Returns:
            Chunks with embeddings attached
        """
        start_time = time.time()
        
        # Determine which model to use based on strategy
        use_secondary_map = self._determine_embedding_strategy(chunks, strategy)
        
        # Group chunks by model choice
        primary_chunks = []
        secondary_chunks = []
        
        for chunk in chunks:
            if use_secondary_map.get(chunk.id, False):
                secondary_chunks.append(chunk)
            else:
                primary_chunks.append(chunk)
        
        # Generate embeddings for each group
        if primary_chunks:
            primary_texts = [chunk.text for chunk in primary_chunks]
            primary_embeddings = await self.generate_embeddings_batch(primary_texts, use_secondary=False)
            for chunk, embedding in zip(primary_chunks, primary_embeddings):
                chunk.embedding = embedding
        
        if secondary_chunks:
            secondary_texts = [chunk.text for chunk in secondary_chunks]
            secondary_embeddings = await self.generate_embeddings_batch(secondary_texts, use_secondary=True)
            for chunk, embedding in zip(secondary_chunks, secondary_embeddings):
                chunk.embedding = embedding
        
        elapsed = time.time() - start_time
        logger.info(
            f"Generated embeddings for {len(chunks)} chunks in {elapsed:.2f}s "
            f"(Primary: {len(primary_chunks)}, Secondary: {len(secondary_chunks)})"
        )
        
        return chunks
    
    def _determine_embedding_strategy(
        self,
        chunks: list[Chunk],
        strategy: str
    ) -> Dict[str, bool]:
        """
        Determine which embedding model to use for each chunk.
        
        Args:
            chunks: List of chunks
            strategy: Strategy name
            
        Returns:
            Dictionary mapping chunk ID to use_secondary flag
        """
        use_secondary = {}
        
        if strategy == "secondary":
            # Use secondary for all
            for chunk in chunks:
                use_secondary[chunk.id] = True
                
        elif strategy == "primary":
            # Use primary for all
            for chunk in chunks:
                use_secondary[chunk.id] = False
                
        elif strategy == "adaptive":
            # Use primary for important chunks, secondary for others
            for chunk in chunks:
                # Use primary for document summaries and sections
                if chunk.chunk_type in [ChunkType.DOCUMENT_SUMMARY, ChunkType.SECTION]:
                    use_secondary[chunk.id] = False
                # Use primary for synthesis chunks
                elif chunk.chunk_type == ChunkType.SYNTHESIS:
                    use_secondary[chunk.id] = False
                # Use secondary for fine-grained chunks
                else:
                    use_secondary[chunk.id] = True
        
        return use_secondary
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get embedding generation statistics.
        
        Returns:
            Dictionary of statistics
        """
        cache_ratio = (
            self.stats['cache_hits'] / 
            (self.stats['cache_hits'] + self.stats['cache_misses'])
            if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0
            else 0
        )
        
        estimated_cost = (
            self.stats['total_tokens'] * 0.00002  # Rough estimate
        )
        
        return {
            **self.stats,
            'cache_hit_ratio': cache_ratio,
            'estimated_cost_usd': estimated_cost
        }
    
    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")


class EmbeddingValidator:
    """
    Validator for embedding quality and consistency.
    
    Ensures embeddings meet quality standards before ingestion.
    """
    
    def __init__(self, expected_dimensions: int = 3072) -> None:
        """
        Initialize embedding validator.
        
        Args:
            expected_dimensions: Expected embedding dimensions
        """
        self.expected_dimensions = expected_dimensions
    
    def validate_embedding(self, embedding: np.ndarray) -> Tuple[bool, List[str]]:
        """
        Validate single embedding.
        
        Args:
            embedding: Embedding vector
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        # Check dimensions
        if embedding.shape[0] != self.expected_dimensions:
            issues.append(f"Incorrect dimensions: {embedding.shape[0]} != {self.expected_dimensions}")
        
        # Check for NaN or Inf values
        if np.any(np.isnan(embedding)):
            issues.append("Contains NaN values")
        if np.any(np.isinf(embedding)):
            issues.append("Contains infinite values")
        
        # Check normalization (should be close to 1 for normalized vectors)
        norm = np.linalg.norm(embedding)
        if abs(norm - 1.0) > 0.01:
            issues.append(f"Not properly normalized: norm={norm}")
        
        # Check for zero vector
        if np.allclose(embedding, 0):
            issues.append("Zero vector detected")
        
        return len(issues) == 0, issues
    
    def validate_batch(self, embeddings: list[np.ndarray]) -> tuple[bool, Dict[int, list[str]]]:
        """
        Validate batch of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Tuple of (all_valid, dictionary of issues by index)
        """
        all_issues = {}
        all_valid = True
        
        for i, embedding in enumerate(embeddings):
            is_valid, issues = self.validate_embedding(embedding)
            if not is_valid:
                all_valid = False
                all_issues[i] = issues
        
        if not all_valid:
            logger.warning(f"Found issues in {len(all_issues)} out of {len(embeddings)} embeddings")
        
        return all_valid, all_issues
    
    def check_similarity_distribution(self, embeddings: list[np.ndarray]) -> Dict[str, float]:
        """
        Check similarity distribution of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            Dictionary of distribution statistics
        """
        if len(embeddings) < 2:
            return {}
        
        # Calculate pairwise similarities
        embeddings_matrix = np.array(embeddings)
        similarities = []
        
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = np.dot(embeddings_matrix[i], embeddings_matrix[j])
                similarities.append(sim)
        
        similarities = np.array(similarities)
        
        return {
            'mean_similarity': float(np.mean(similarities)),
            'std_similarity': float(np.std(similarities)),
            'min_similarity': float(np.min(similarities)),
            'max_similarity': float(np.max(similarities)),
            'median_similarity': float(np.median(similarities))
        }