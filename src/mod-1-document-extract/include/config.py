"""Configuration management using environment variables and YAML."""
import os
from pathlib import Path
from typing import Dict, Any
import yaml
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Centralized configuration management."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.config_path = self.base_path / "config"
        
    @lru_cache(maxsize=32)
    def load_yaml(self, name: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(self.config_path / f"{name}.yaml") as f:
            return yaml.safe_load(f)
    
    @property
    def openai(self) -> Dict[str, Any]:
        """OpenAI configuration."""
        return {
            'api_key': os.getenv('OPENAI_API_KEY'),
            'classifier_model': os.getenv('OPENAI_MODEL_CLASSIFIER', 'gpt-4-vision-preview'),
            'extractor_model': os.getenv('OPENAI_MODEL_EXTRACTOR', 'gpt-4-turbo-preview'),
            'classifier_temp': float(os.getenv('OPENAI_TEMPERATURE_CLASSIFIER', '0.1')),
            'extractor_temp': float(os.getenv('OPENAI_TEMPERATURE_EXTRACTOR', '0.0'))
        }
    
    @property
    def s3(self) -> Dict[str, Any]:
        """S3/MinIO configuration."""
        return {
            'endpoint': os.getenv('MINIO_ENDPOINT', 'http://localhost:9000'),
            'access_key': os.getenv('MINIO_ACCESS_KEY'),
            'secret_key': os.getenv('MINIO_SECRET_KEY'),
            'bucket': os.getenv('MINIO_BUCKET_NAME', 'invoices'),
            'incoming': os.getenv('MINIO_INCOMING_PREFIX', 'incoming/'),
            'processed': os.getenv('MINIO_PROCESSED_PREFIX', 'processed/'),
            'failed': os.getenv('MINIO_FAILED_PREFIX', 'failed/')
        }
    
    @property
    def postgres(self) -> Dict[str, Any]:
        """PostgreSQL configuration."""
        return {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'invoice_db'),
            'user': os.getenv('POSTGRES_USER', 'invoice_user'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }
    
    @property
    def processing(self) -> Dict[str, Any]:
        """Processing configuration."""
        return {
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'retry_delay_minutes': int(os.getenv('RETRY_DELAY_MINUTES', '5')),
            'max_active_runs': int(os.getenv('MAX_ACTIVE_RUNS', '5'))
        }

config = Config()