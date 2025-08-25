"""Configuration loader with environment variable support and caching."""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class EnvConfig:
    """Environment variable configuration handler."""
    
    @staticmethod
    def get(key: str, default: Optional[str] = None) -> str:
        """Retrieve environment variable with optional default."""
        return os.getenv(key, default)
    
    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        """Retrieve environment variable as integer."""
        return int(os.getenv(key, str(default)))
    
    @staticmethod
    def get_float(key: str, default: float = 0.0) -> float:
        """Retrieve environment variable as float."""
        return float(os.getenv(key, str(default)))
    
    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """Retrieve environment variable as boolean."""
        return os.getenv(key, str(default)).lower() in ('true', '1', 'yes')

class ConfigLoader:
    """Singleton configuration loader with environment variable support."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.config_path = Path("/usr/local/airflow/config")
        if not self.config_path.exists():
            self.config_path = Path(__file__).parent.parent / "config"
        self._configs = {}
        self.env = EnvConfig()
        self._initialized = True
    
    @lru_cache(maxsize=32)
    def load(self, name: str) -> Dict[str, Any]:
        """Load and cache YAML configuration with env variable substitution."""
        if name not in self._configs:
            config_file = self.config_path / f"{name}.yaml"
            with open(config_file) as f:
                content = f.read()
                for key, value in os.environ.items():
                    content = content.replace(f"${{{key}}}", value)
                self._configs[name] = yaml.safe_load(content)
        return self._configs[name]
    
    def get_model(self, model_id: str) -> Dict[str, Any]:
        """Retrieve model configuration."""
        return self.load("models")["models"].get(model_id, {})
    
    def get_prompt(self, key: str) -> str:
        """Retrieve prompt template."""
        keys = key.split(".")
        config = self.load("prompts")
        for k in keys:
            config = config.get(k, {})
        return config
    
    @property
    def openai_config(self) -> Dict[str, Any]:
        """OpenAI configuration from environment."""
        return {
            'api_key': self.env.get('OPENAI_API_KEY'),
            'classifier_model': self.env.get('OPENAI_MODEL_CLASSIFIER', 'gpt-4-vision-preview'),
            'extractor_model': self.env.get('OPENAI_MODEL_EXTRACTOR', 'gpt-4-turbo-preview'),
            'classifier_temp': self.env.get_float('OPENAI_TEMPERATURE_CLASSIFIER', 0.1),
            'extractor_temp': self.env.get_float('OPENAI_TEMPERATURE_EXTRACTOR', 0.0)
        }
    
    @property
    def minio_config(self) -> Dict[str, Any]:
        """MinIO configuration from environment."""
        return {
            'endpoint': self.env.get('MINIO_ENDPOINT', 'http://localhost:9000'),
            'access_key': self.env.get('MINIO_ACCESS_KEY'),
            'secret_key': self.env.get('MINIO_SECRET_KEY'),
            'bucket': self.env.get('MINIO_BUCKET_NAME', 'invoices'),
            'incoming_prefix': self.env.get('MINIO_INCOMING_PREFIX', 'incoming/'),
            'processed_prefix': self.env.get('MINIO_PROCESSED_PREFIX', 'processed/'),
            'failed_prefix': self.env.get('MINIO_FAILED_PREFIX', 'failed/')
        }
    
    @property
    def postgres_config(self) -> Dict[str, Any]:
        """PostgreSQL configuration from environment."""
        return {
            'host': self.env.get('POSTGRES_HOST', 'postgres'),
            'port': self.env.get_int('POSTGRES_PORT', 5432),
            'database': self.env.get('POSTGRES_DB', 'invoice_db'),
            'user': self.env.get('POSTGRES_USER', 'invoice_user'),
            'password': self.env.get('POSTGRES_PASSWORD')
        }
    
    @property
    def processing_config(self) -> Dict[str, Any]:
        """Processing configuration from environment."""
        return {
            'max_retries': self.env.get_int('MAX_RETRIES', 3),
            'retry_delay_minutes': self.env.get_int('RETRY_DELAY_MINUTES', 5),
            'max_active_runs': self.env.get_int('MAX_ACTIVE_RUNS', 5),
            'batch_size': self.env.get_int('BATCH_SIZE', 10)
        }