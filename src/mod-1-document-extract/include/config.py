"""Configuration management using environment variables and YAML.

This module provides a centralized configuration system that:
- Loads environment variables from .env files
- Caches YAML configurations for performance
- Provides typed access to all configuration values
- Implements singleton pattern to avoid repeated file I/O
"""
import os
from pathlib import Path
from typing import Dict, Any
import yaml
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Centralized configuration management using singleton pattern.
    
    What: Provides unified access to environment variables and YAML configs.
    Why: Centralizes configuration to avoid scattered os.getenv calls.
    How: Lazy loads and caches configurations with typed property access.
    """
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.config_path = self.base_path / "config"
        
    @lru_cache(maxsize=32)
    def load_yaml(self, name: str) -> Dict[str, Any]:
        """Load and cache YAML configuration file.
        
        What: Reads YAML configuration from disk.
        Why: External configuration allows changes without code modification.
        How: Uses LRU cache to avoid repeated file I/O operations.
        
        Args:
            name: Configuration file name without .yaml extension
            
        Returns:
            Parsed YAML content as dictionary
        """
        with open(self.config_path / f"{name}.yaml") as f:
            return yaml.safe_load(f)
    
    @property
    def openai(self) -> Dict[str, Any]:
        """OpenAI configuration with model and temperature settings.
        
        What: Returns OpenAI API configuration.
        Why: Centralizes LLM settings for consistent model behavior.
        How: Reads from environment with sensible defaults for production use.
        """
        return {
            'api_key': os.getenv('OPENAI_API_KEY'),
            'classifier_model': os.getenv('OPENAI_MODEL_CLASSIFIER', 'gpt-4-vision-preview'),
            'extractor_model': os.getenv('OPENAI_MODEL_EXTRACTOR', 'gpt-4-turbo-preview'),
            'classifier_temp': float(os.getenv('OPENAI_TEMPERATURE_CLASSIFIER', '0.1')),
            'extractor_temp': float(os.getenv('OPENAI_TEMPERATURE_EXTRACTOR', '0.0'))
        }
    
    def _get_env_config(self, prefix: str, config_map: Dict[str, tuple]) -> Dict[str, Any]:
        """Generic environment configuration getter to reduce repetition.
        
        What: Retrieves environment variables with type conversion.
        Why: Applies DRY principle to avoid repeated os.getenv patterns.
        How: Maps environment variables to typed values using config_map.
        
        Args:
            prefix: Environment variable prefix
            config_map: Dictionary mapping config keys to (env_var, default, type)
            
        Returns:
            Configuration dictionary with typed values
        """
        result = {}
        for key, (env_var, default, type_fn) in config_map.items():
            value = os.getenv(env_var, default)
            result[key] = type_fn(value) if value and type_fn else value
        return result
    
    @property
    def s3(self) -> Dict[str, Any]:
        """S3/MinIO object storage configuration."""
        return self._get_env_config('MINIO_', {
            'endpoint': ('MINIO_ENDPOINT', 'http://localhost:9000', str),
            'access_key': ('MINIO_ACCESS_KEY', None, str),
            'secret_key': ('MINIO_SECRET_KEY', None, str),
            'bucket': ('MINIO_BUCKET_NAME', 'invoices', str),
            'incoming': ('MINIO_INCOMING_PREFIX', 'incoming/', str),
            'processed': ('MINIO_PROCESSED_PREFIX', 'processed/', str),
            'failed': ('MINIO_FAILED_PREFIX', 'failed/', str)
        })
    
    @property
    def postgres(self) -> Dict[str, Any]:
        """PostgreSQL database configuration."""
        return self._get_env_config('POSTGRES_', {
            'host': ('POSTGRES_HOST', 'localhost', str),
            'port': ('POSTGRES_PORT', '5432', int),
            'database': ('POSTGRES_DB', 'invoice_db', str),
            'user': ('POSTGRES_USER', 'invoice_user', str),
            'password': ('POSTGRES_PASSWORD', None, str)
        })
    
    @property
    def processing(self) -> Dict[str, Any]:
        """DAG processing configuration."""
        return self._get_env_config('', {
            'max_retries': ('MAX_RETRIES', '3', int),
            'retry_delay_minutes': ('RETRY_DELAY_MINUTES', '5', int),
            'max_active_runs': ('MAX_ACTIVE_RUNS', '5', int)
        })

config = Config()