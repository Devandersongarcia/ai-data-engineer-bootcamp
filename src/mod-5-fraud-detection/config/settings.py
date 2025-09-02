"""Configuration Settings for UberEats Fraud Detection System

Centralized configuration management using Pydantic settings with environment
variable support and comprehensive validation.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

load_dotenv()

class OpenAIConfig(BaseSettings):
    """OpenAI API configuration with rate limiting controls.
    
    Attributes:
        api_key: OpenAI API key from environment
        embedding_model: Model for text embeddings
        llm_model: Large language model for analysis
        max_tokens: Maximum tokens per request (optimized for speed)
        temperature: Response randomness (low for consistency)
        max_requests_per_minute: Rate limiting for API calls
        request_delay_seconds: Delay between requests
    """
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    embedding_model: str = Field(default="text-embedding-3-small")
    llm_model: str = Field(default="gpt-4o-mini")
    max_tokens: int = Field(default=50, ge=10, le=1000)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    
    max_requests_per_minute: int = Field(default=20, ge=1, le=100)
    request_delay_seconds: float = Field(default=3.0, ge=0.1, le=10.0)
    
    class Config:
        env_prefix = "OPENAI_"

class KafkaConfig(BaseSettings):
    """Kafka configuration for Confluent Cloud integration.
    
    Manages connection settings, authentication, and performance tuning
    for real-time order processing from Kafka topics.
    """
    bootstrap_servers: str = Field(default="pkc-619z3.us-east1.gcp.confluent.cloud:9092")
    input_topics: str = Field(default="kafka-orders")
    output_topic: str = Field(default="fraud-results")
    consumer_group: str = Field(default="fraud-detection-group")
    auto_offset_reset: str = Field(default="latest")
    
    security_protocol: str = Field(default="SASL_SSL")
    sasl_mechanism: str = Field(default="PLAIN")
    sasl_username: str = Field(default_factory=lambda: os.getenv('KAFKA_SASL_USERNAME'))
    sasl_password: str = Field(default_factory=lambda: os.getenv('KAFKA_SASL_PASSWORD'))
    
    session_timeout_ms: int = Field(default=45000, ge=1000, le=300000)
    max_poll_records: int = Field(default=500, ge=1, le=10000)
    fetch_min_bytes: int = Field(default=1, ge=1)
    fetch_max_wait_ms: int = Field(default=500, ge=0, le=60000)
    
    @field_validator('sasl_username')
    @classmethod
    def validate_sasl_username(cls, v: str) -> str:
        """Validate SASL username is provided."""
        if not v or v.strip() == "":
            raise ValueError('KAFKA_SASL_USERNAME environment variable is required')
        return v
    
    @field_validator('sasl_password')
    @classmethod
    def validate_sasl_password(cls, v: str) -> str:
        """Validate SASL password is provided."""
        if not v or v.strip() == "":
            raise ValueError('KAFKA_SASL_PASSWORD environment variable is required')
        return v
    
    def get_bootstrap_servers_list(self) -> list[str]:
        """Get bootstrap servers as a list.
        
        Returns:
            List of bootstrap server addresses
        """
        if isinstance(self.bootstrap_servers, str):
            return (
                [self.bootstrap_servers] 
                if ',' not in self.bootstrap_servers 
                else self.bootstrap_servers.split(',')
            )
        return self.bootstrap_servers
    
    def get_input_topics_list(self) -> list[str]:
        """Get input topics as a list.
        
        Returns:
            List of Kafka topic names
        """
        return (
            self.input_topics.split(',') 
            if isinstance(self.input_topics, str)
            else self.input_topics
        )
    
    def get_kafka_connection_config(self) -> dict[str, str]:
        """Get complete Kafka connection configuration for Confluent Cloud.
        
        Returns:
            Dictionary with Kafka connection parameters
        """
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "sasl.mechanisms": self.sasl_mechanism,
            "sasl.username": self.sasl_username,
            "sasl.password": self.sasl_password,
            "session.timeout.ms": str(self.session_timeout_ms),
            "max.poll.records": str(self.max_poll_records),
            "fetch.min.bytes": str(self.fetch_min_bytes),
            "fetch.max.wait.ms": str(self.fetch_max_wait_ms)
        }
    
    def get_spark_kafka_options(self) -> dict[str, str]:
        """Get Kafka options for Spark Structured Streaming with Confluent Cloud.
        
        Returns:
            Dictionary with Spark-compatible Kafka options
        """
        return {
            "kafka.bootstrap.servers": self.bootstrap_servers,
            "kafka.security.protocol": self.security_protocol,
            "kafka.sasl.mechanism": self.sasl_mechanism,
            "kafka.sasl.jaas.config": f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{self.sasl_username}" password="{self.sasl_password}";',
            "kafka.session.timeout.ms": str(self.session_timeout_ms),
            "kafka.max.poll.records": str(self.max_poll_records),
            "kafka.fetch.min.bytes": str(self.fetch_min_bytes),
            "kafka.fetch.max.wait.ms": str(self.fetch_max_wait_ms)
        }
    
    class Config:
        env_prefix = "KAFKA_"

class SparkConfig(BaseSettings):
    """Spark configuration for streaming fraud detection.
    
    Optimized settings for low-latency processing while maintaining
    resource efficiency and fault tolerance.
    """
    app_name: str = Field(default="uberats-fraud-detection")
    processing_time: str = Field(default="5 seconds")
    executor_memory: str = Field(default="2g")
    executor_cores: int = Field(default=2, ge=1, le=8)
    max_cores_per_executor: int = Field(default=4, ge=1, le=16)
    executor_instances: int = Field(default=2, ge=1, le=10)
    
    max_offsets_per_trigger: int = Field(default=50, ge=1, le=1000)
    shuffle_partitions: int = Field(default=4, ge=1, le=200)
    adaptive_query_execution: bool = Field(default=True)
    coalesce_partitions: bool = Field(default=True)
    
    watermark_delay: str = Field(default="10 seconds")
    checkpoint_location: str = Field(default="tmp/spark-checkpoint")
    
    class Config:
        env_prefix = "SPARK_"

class FraudConfig(BaseSettings):
    """Fraud detection configuration with 3-tier risk assessment.
    
    Implements BLOCK/REQUIRE_HUMAN/MONITOR decision tiers with
    sensitive pattern detection for comprehensive fraud prevention.
    """
    risk_threshold_block: float = Field(default=0.70, ge=0.0, le=1.0)
    risk_threshold_human: float = Field(default=0.40, ge=0.0, le=1.0)
    risk_threshold_monitor: float = Field(default=0.00, ge=0.0, le=1.0)
    max_detection_latency_ms: int = Field(default=200, ge=50, le=5000)
    min_system_accuracy: float = Field(default=0.90, ge=0.5, le=1.0)
    max_daily_cost_usd: float = Field(default=100.00, ge=0.0)
    
    velocity_fraud_speed_threshold_ms: int = Field(default=500, ge=100, le=10000)
    card_testing_order_threshold: int = Field(default=3, ge=1, le=20)
    card_testing_time_window_minutes: int = Field(default=5, ge=1, le=60)
    geographic_anomaly_distance_km: int = Field(default=300, ge=1, le=10000)
    
    @field_validator('risk_threshold_block')
    @classmethod
    def validate_block_threshold(cls, v, info):
        if 'risk_threshold_human' in info.data and v <= info.data['risk_threshold_human']:
            raise ValueError('Block threshold must be higher than human review threshold')
        return v
    
    class Config:
        env_prefix = "FRAUD_"

class MonitoringConfig(BaseSettings):
    """Monitoring and alerting configuration.
    
    Configures dashboard ports, logging levels, and refresh intervals
    for system observability and performance tracking.
    """
    streamlit_port: int = Field(default=8501, ge=1000, le=65535)
    api_port: int = Field(default=8000, ge=1000, le=65535)
    prometheus_port: int = Field(default=9090, ge=1000, le=65535)
    log_level: str = Field(default="INFO")
    debug_mode: bool = Field(default=True)
    
    dashboard_auto_refresh: bool = Field(default=True)
    dashboard_refresh_interval_seconds: int = Field(default=5, ge=1, le=300)
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v
    
    class Config:
        env_prefix = "MONITORING_"

class RAGConfig(BaseSettings):
    """RAG (Retrieval-Augmented Generation) system configuration.
    
    Manages knowledge base paths, chunking strategies, and similarity
    search parameters for context-aware fraud detection.
    """
    knowledge_base_path: str = Field(default="fraud_knowledge/")
    embeddings_cache_path: str = Field(default="data/embeddings/")
    chunk_size: int = Field(default=512, ge=50, le=2000)
    chunk_overlap: int = Field(default=100, ge=0, le=500)
    similarity_top_k: int = Field(default=3, ge=1, le=20)
    embedding_dimensions: int = Field(default=1536, ge=384, le=3072)
    
    class Config:
        env_prefix = "RAG_"

class QdrantConfig(BaseSettings):
    """Qdrant vector database configuration.
    
    Manages connection settings and performance parameters for
    vector similarity search in fraud pattern analysis.
    """
    url: str = Field(default_factory=lambda: os.getenv('QDRANT_URL', 'http://localhost:6333'))
    api_key: str = Field(default_factory=lambda: os.getenv('QDRANT_API_KEY', ''))
    collection_name: str = Field(default="rag_fraud_analysis")
    vector_size: int = Field(default=1536, ge=1)
    distance_metric: str = Field(default="Cosine")
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    batch_size: int = Field(default=50, ge=1, le=1000)
    replication_factor: int = Field(default=1, ge=1, le=10)
    
    hnsw_config_m: int = Field(default=16, ge=4, le=64)
    hnsw_config_ef_construct: int = Field(default=200, ge=16, le=1000)
    
    @field_validator('distance_metric')
    @classmethod
    def validate_distance_metric(cls, v):
        valid_metrics = ['Cosine', 'Euclidean', 'Dot', 'Manhattan']
        if v not in valid_metrics:
            raise ValueError(f'Distance metric must be one of: {valid_metrics}')
        return v
    
    class Config:
        env_prefix = "QDRANT_"

class RedisConfig(BaseSettings):
    """Redis memory store configuration"""
    url: str = Field(default_factory=lambda: os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    password: str = Field(default_factory=lambda: os.getenv('REDIS_PASSWORD', ''))
    db: int = Field(default=0)
    max_connections: int = Field(default=10)
    timeout: int = Field(default=5)
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v:
            raise ValueError('REDIS_URL environment variable is required')
        if not v.startswith(('redis://', 'rediss://')):
            raise ValueError('REDIS_URL must be a valid Redis URL (redis:// or rediss://)')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate Redis password when authentication is required."""
        # Password is optional for local development but should be set in production
        return v
    
    class Config:
        env_prefix = "REDIS_"

class AgentConfig(BaseSettings):
    """Agent system configuration for multi-agent fraud detection.
    
    Manages timeouts, memory settings, and concurrency controls for
    the pattern analyzer, risk assessor, decision maker, and action executor agents.
    """
    max_execution_time_seconds: int = Field(default=75, ge=10, le=300)
    agent_memory: bool = Field(default=True)
    verbose_logging: bool = Field(default=False)
    memory_enabled: bool = Field(default_factory=lambda: os.getenv('AGENT_MEMORY_ENABLED', 'true').lower() == 'true')
    memory_provider: str = Field(default_factory=lambda: os.getenv('AGENT_MEMORY_PROVIDER', 'redis'))
    
    pattern_analyzer_timeout: int = Field(default=15, ge=5, le=60)
    risk_assessor_timeout: int = Field(default=12, ge=5, le=60)
    decision_maker_timeout: int = Field(default=10, ge=5, le=60)
    action_executor_timeout: int = Field(default=8, ge=5, le=60)
    
    processing_timeout: float = Field(default=15.0, ge=1.0, le=120.0)
    enable_retry_on_timeout: bool = Field(default=True)
    max_retry_attempts: int = Field(default=2, ge=0, le=5)
    retry_backoff_seconds: float = Field(default=1.0, ge=0.1, le=10.0)
    
    reduced_token_mode: bool = Field(default=True)
    max_tokens_per_agent: int = Field(default=50, ge=10, le=500)
    
    max_concurrent_agents: int = Field(default=1, ge=1, le=10)
    enable_rate_limiting: bool = Field(default=True)
    sequential_processing: bool = Field(default=True)
    disable_agents: bool = Field(default=False)
    
    @field_validator('memory_provider')
    @classmethod
    def validate_memory_provider(cls, v):
        valid_providers = ['redis', 'memory', 'file']
        if v not in valid_providers:
            raise ValueError(f'Memory provider must be one of: {valid_providers}')
        return v
    
    class Config:
        env_prefix = "AGENT_"

class PostgreSQLConfig(BaseSettings):
    """PostgreSQL configuration for fraud results storage"""
    connection_string: str = Field(default_factory=lambda: os.getenv('POSTGRES_CONNECTION_STRING'))
    table_name: str = Field(default="fraud_results")
    pool_size: int = Field(default=5)
    batch_size: int = Field(default=100)
    enable_batch_writing: bool = Field(default=True)
    connection_timeout: int = Field(default=30)
    
    @field_validator('connection_string')
    @classmethod
    def validate_connection_string(cls, v: str) -> str:
        """Validate PostgreSQL connection string is provided."""
        if not v or v.strip() == "":
            raise ValueError('POSTGRES_CONNECTION_STRING environment variable is required')
        if not v.startswith('postgresql://'):
            raise ValueError('POSTGRES_CONNECTION_STRING must be a valid PostgreSQL URL')
        return v
    
    class Config:
        env_prefix = "POSTGRES_"

class Settings:
    """Main settings class combining all configurations.
    
    Aggregates all configuration sections and provides validation
    methods for the complete system configuration.
    """
    
    def __init__(self):
        self.openai = OpenAIConfig()
        self.kafka = KafkaConfig()
        self.spark = SparkConfig()
        self.fraud = FraudConfig()
        self.monitoring = MonitoringConfig()
        self.rag = RAGConfig()
        self.qdrant = QdrantConfig()
        self.redis = RedisConfig()
        self.agent = AgentConfig()
        self.postgresql = PostgreSQLConfig()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate all configuration settings.
        
        Returns:
            Dictionary with validation status, errors, and warnings
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not self.openai.api_key:
            validation_results["errors"].append("OpenAI API key is required")
            validation_results["valid"] = False
        
        if self.fraud.risk_threshold_block <= self.fraud.risk_threshold_human:
            validation_results["warnings"].append(
                "Block threshold should be higher than human review threshold"
            )
        
        if self.fraud.risk_threshold_human <= self.fraud.risk_threshold_monitor:
            validation_results["warnings"].append(
                "Human review threshold should be higher than monitor threshold"
            )
        
        if self.fraud.max_detection_latency_ms > 500:
            validation_results["warnings"].append(
                "Detection latency target is higher than recommended (>500ms)"
            )
        
        return validation_results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization.
        
        Returns:
            Complete configuration as nested dictionary
        """
        return {
            "openai": self.openai.model_dump(),
            "kafka": self.kafka.model_dump(),
            "spark": self.spark.model_dump(),
            "fraud": self.fraud.model_dump(),
            "monitoring": self.monitoring.model_dump(),
            "rag": self.rag.model_dump(),
            "qdrant": self.qdrant.model_dump(),
            "redis": self.redis.model_dump(),
            "agent": self.agent.model_dump(),
            "postgresql": self.postgresql.model_dump()
        }

settings = Settings()

validation_result = settings.validate_configuration()
if not validation_result["valid"]:
    print(f"Configuration errors: {validation_result['errors']}")
if validation_result["warnings"]:
    print(f"Configuration warnings: {validation_result['warnings']}")