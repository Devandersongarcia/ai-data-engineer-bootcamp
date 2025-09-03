"""Configuration settings for the UberEats Multi-Agent System.

This module provides centralized configuration management using Pydantic settings,
supporting environment variables and .env files for secure credential management.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from pathlib import Path

current_dir = Path(__file__).parent
env_file = current_dir.parent.parent / ".env"

class Settings(BaseSettings):
    """Enhanced application settings and configuration for Agno 1.1+ implementation.
    
    This class defines all configuration parameters for the UberEats Multi-Agent System,
    including API keys, database connections, performance tuning, and business logic
    parameters. All settings can be overridden via environment variables.
    
    Attributes:
        agno_monitoring_enabled: Enable Agno framework monitoring.
        default_model: Primary LLM model for agent operations.
        database_url: PostgreSQL connection string.
        redis_url: Redis connection for agent memory and caching.
        langfuse_host: Langfuse observability platform endpoint.
    """
    
    # Agno Framework Configuration
    agno_monitoring_enabled: bool = Field(True, description="Enable Agno monitoring")
    agno_session_storage: str = Field("postgresql", description="Session storage backend")
    
    # LLM Model Configuration
    model_provider: str = Field("openai", description="Primary model provider")
    default_model: str = Field("gpt-4o-mini", description="Default LLM model")
    reasoning_model: str = Field("gpt-4o-mini", description="Model for complex reasoning")
    embedding_model: str = Field("text-embedding-3-small", description="Embedding model")
    max_tokens: int = Field(1000, description="Maximum tokens per request")
    temperature: float = Field(0.7, description="Model temperature")
    
    # API Keys
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    
    # Langfuse Configuration
    langfuse_secret_key: Optional[str] = Field(None, description="Langfuse secret key")
    langfuse_public_key: Optional[str] = Field(None, description="Langfuse public key")
    langfuse_host: str = Field("https://us.cloud.langfuse.com", description="Langfuse host URL")
    
    # Performance Settings
    max_concurrent_agents: int = Field(50, description="Maximum concurrent agents")
    agent_timeout: int = Field(300, description="Agent timeout in seconds")
    memory_limit_mb: int = Field(1024, description="Memory limit per agent in MB")
    
    # Database Configuration
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection URL (required via environment variable)"
    )
    mongodb_connection_string: Optional[str] = Field(
        default=None,
        description="MongoDB connection string (required via environment variable)"
    )
    mongodb_database: str = Field("ubereats_catalog", description="MongoDB database name")
    
    # Redis Configuration
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL for agent memory and caching (required via environment variable)"
    )
    redis_enabled: bool = Field(True, description="Enable Redis for agent memory")
    redis_cache_ttl: int = Field(3600, description="Redis cache TTL in seconds")
    redis_max_connections: int = Field(10, description="Maximum Redis connections per agent")
    
    # Vector Store Configuration
    qdrant_url: Optional[str] = Field("http://localhost:6333", description="Qdrant URL")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant API key")
    qdrant_collection_name: str = Field("ubereats_knowledge", description="Qdrant collection name")
    vector_dimension: int = Field(1536, description="Vector dimensions for text-embedding-3-small")
    top_k_retrieval: int = Field(10, description="Top K retrieval for RAG")
    similarity_threshold: float = Field(0.8, description="Similarity threshold")
    
    # Production Settings
    enable_monitoring: bool = Field(True, description="Enable monitoring")
    log_level: str = Field("INFO", description="Logging level")
    enable_caching: bool = Field(True, description="Enable response caching")
    cache_ttl: int = Field(3600, description="Cache TTL in seconds")
    
    # FastAPI Settings
    api_title: str = Field("UberEats Multi-Agent System", description="API title")
    api_version: str = Field("2.0.0", description="API version")
    api_host: str = Field("0.0.0.0", description="API host")
    api_port: int = Field(8000, description="API port")
    
    # Security Settings
    cors_origins: list[str] = Field(["*"], description="CORS allowed origins")
    rate_limit_per_minute: int = Field(100, description="Rate limit per minute")
    
    # UberEats Business Logic
    delivery_radius_km: float = Field(10.0, description="Maximum delivery radius in km")
    max_preparation_time_minutes: int = Field(60, description="Maximum preparation time")
    default_delivery_fee: float = Field(2.99, description="Default delivery fee")
    
    # Agent Team Settings
    enable_agent_teams: bool = Field(True, description="Enable Level 4 Agent Teams")
    enable_workflows: bool = Field(True, description="Enable Level 5 Agentic Workflows")
    workflow_max_retries: int = Field(3, description="Maximum workflow retry attempts")
    
    model_config = SettingsConfigDict(
        env_file=str(env_file),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

settings = Settings()