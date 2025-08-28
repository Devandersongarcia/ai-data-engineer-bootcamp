"""Development environment settings and configuration management."""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class DevSettings:
    """Development environment settings extracted from environment variables and defaults."""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    temperature: float = 0
    
    # Database Configuration  
    database_url: Optional[str] = None
    
    # Langfuse Configuration
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = True
    langfuse_tracing_enabled: bool = True
    langfuse_sample_rate: float = 1.0  # Trace 100% of requests
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "../../ubereats_brasil.log"
    
    # Application Configuration
    app_title: str = "UberEats Brasil - Consulta de Notas Fiscais"
    app_icon: str = "🍔"
    app_layout: str = "centered"
    
    # Performance Configuration
    max_retries: int = 3
    connection_timeout: int = 30
    query_timeout: int = 120


def get_dev_settings() -> DevSettings:
    """Get development settings with environment variable overrides."""
    return DevSettings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        temperature=float(os.getenv("TEMPERATURE", "0")),
        database_url=os.getenv("DATABASE_URL"),
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        langfuse_enabled=os.getenv("LANGFUSE_ENABLED", "true").lower() == "true",
        langfuse_tracing_enabled=os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() == "true",
        langfuse_sample_rate=float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "../../ubereats_brasil.log"),
        app_title=os.getenv("APP_TITLE", "UberEats Brasil - Consulta de Notas Fiscais"),
        app_icon=os.getenv("APP_ICON", "🍔"),
        app_layout=os.getenv("APP_LAYOUT", "centered"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        connection_timeout=int(os.getenv("CONNECTION_TIMEOUT", "30")),
        query_timeout=int(os.getenv("QUERY_TIMEOUT", "120"))
    )