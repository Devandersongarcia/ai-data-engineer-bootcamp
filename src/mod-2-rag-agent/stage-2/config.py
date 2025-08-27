"""
Configuration module for RAG pipeline.

This module handles all configuration loading from environment variables
using Pydantic Settings for type safety and validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


class MinIOConfig(BaseSettings):
    """MinIO S3-compatible storage configuration."""
    
    endpoint: str = Field(default="http://localhost:9000", alias="MINIO_ENDPOINT")
    access_key: str = Field(alias="MINIO_ACCESS_KEY")
    secret_key: str = Field(alias="MINIO_SECRET_KEY")
    bucket_name: str = Field(default="docx-documents", alias="MINIO_BUCKET_NAME")
    secure: bool = Field(default=False, alias="MINIO_SECURE")
    region: str = Field(default="us-east-1", alias="MINIO_REGION")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class OpenAIConfig(BaseSettings):
    """OpenAI API configuration for embeddings and LLM."""
    
    api_key: str = Field(alias="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-large", alias="OPENAI_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=3072, alias="OPENAI_EMBEDDING_DIMENSIONS")
    llm_model: str = Field(default="gpt-4o", alias="OPENAI_LLM_MODEL")
    embedding_batch_size: int = Field(default=100, alias="OPENAI_EMBEDDING_BATCH_SIZE")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class PineconeConfig(BaseSettings):
    """Pinecone vector database configuration."""
    
    api_key: str = Field(alias="PINECONE_API_KEY")
    environment: str = Field(default="us-east-1", alias="PINECONE_ENVIRONMENT")
    index_name_summaries: str = Field(default="module-summaries", alias="PINECONE_INDEX_NAME_SUMMARIES")
    index_name_chunks: str = Field(default="detailed-chunks", alias="PINECONE_INDEX_NAME_CHUNKS")
    dimension: int = Field(default=3072, alias="PINECONE_DIMENSION")
    metric: str = Field(default="cosine", alias="PINECONE_METRIC")
    batch_size: int = Field(default=100, alias="PINECONE_BATCH_SIZE")
    namespace_prefix: str = Field(default="mod", alias="PINECONE_NAMESPACE_PREFIX")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class QdrantConfig(BaseSettings):
    """Qdrant vector database configuration."""
    
    host: str = Field(default="localhost", alias="QDRANT_HOST")
    port: int = Field(default=6333, alias="QDRANT_PORT")
    api_key: Optional[str] = Field(default=None, alias="QDRANT_API_KEY")
    collection_name: str = Field(default="semantic_chunks", alias="QDRANT_COLLECTION_NAME")
    vector_size: int = Field(default=3072, alias="QDRANT_VECTOR_SIZE")
    distance: str = Field(default="Cosine", alias="QDRANT_DISTANCE")
    use_https: bool = Field(default=False, alias="QDRANT_USE_HTTPS")
    quantization_enabled: bool = Field(default=True, alias="QDRANT_QUANTIZATION_ENABLED")
    shards: int = Field(default=2, alias="QDRANT_SHARDS")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class ChunkingConfig(BaseSettings):
    """Text chunking configuration."""
    
    min_size: int = Field(default=100, alias="CHUNK_MIN_SIZE")
    max_size: int = Field(default=512, alias="CHUNK_MAX_SIZE")
    overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    semantic_breakpoint_threshold: int = Field(default=95, alias="SEMANTIC_BREAKPOINT_THRESHOLD")
    semantic_buffer_size: int = Field(default=1, alias="SEMANTIC_BUFFER_SIZE")
    hierarchical_levels: str = Field(default="document,section,paragraph,sentence", alias="HIERARCHICAL_LEVELS")
    
    @property
    def hierarchical_levels_list(self) -> list[str]:
        """Get hierarchical levels as a list."""
        return [level.strip() for level in self.hierarchical_levels.split(",")]
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class MetadataConfig(BaseSettings):
    """Metadata extraction configuration."""
    
    extract_titles: bool = Field(default=True, alias="EXTRACT_TITLES")
    extract_keywords: bool = Field(default=True, alias="EXTRACT_KEYWORDS")
    extract_summaries: bool = Field(default=True, alias="EXTRACT_SUMMARIES")
    extract_entities: bool = Field(default=True, alias="EXTRACT_ENTITIES")
    extract_questions: bool = Field(default=True, alias="EXTRACT_QUESTIONS")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class CacheConfig(BaseSettings):
    """Cache configuration for pipeline optimization."""
    
    enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_dir: Path = Field(default=Path("./pipeline_cache"), alias="CACHE_DIR")
    ttl: int = Field(default=86400, alias="CACHE_TTL")
    
    def ensure_cache_dir_exists(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class PerformanceConfig(BaseSettings):
    """Performance and resource configuration."""
    
    max_workers: int = Field(default=4, alias="MAX_WORKERS")
    batch_processing: bool = Field(default=True, alias="BATCH_PROCESSING")
    memory_limit_gb: int = Field(default=4, alias="MEMORY_LIMIT_GB")
    processing_timeout: int = Field(default=300, alias="PROCESSING_TIMEOUT_SECONDS")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


class Settings(BaseSettings):
    """Main settings aggregator."""
    
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    pinecone: PineconeConfig = Field(default_factory=PineconeConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Path = Field(default=Path("./logs/rag_pipeline.log"), alias="LOG_FILE")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    
    def ensure_log_dir_exists(self) -> None:
        """Ensure log directory exists."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore"
    }


def load_settings() -> Settings:
    """
    Load and validate all settings from environment.
    
    Returns:
        Settings: Validated configuration object
    """
    settings = Settings()
    # Ensure directories exist
    settings.ensure_log_dir_exists()
    settings.cache.ensure_cache_dir_exists()
    return settings