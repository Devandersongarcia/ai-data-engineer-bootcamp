"""Application settings and configuration management."""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class AppSettings:
    """Application settings extracted from environment variables and defaults."""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    embedding_model: str = "text-embedding-ada-002"
    
    # Database Configuration
    database_url: Optional[str] = None
    
    # Qdrant Configuration
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    qdrant_collection_menu: str = "restaurant_menus"
    qdrant_collection_ubereats: str = "ubereats_brasil_vectors"
    
    # ChromaDB Configuration
    chroma_collection_name: str = "ubereats_brasil_production"
    chroma_path: str = "data/chromadb"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "../../ubereats_brasil_vanna.log"
    log_file_cross_db: str = "../../ubereats_brasil_cross_db.log"
    log_file_multi_db: str = "../../ubereats_brasil_multi_db.log"
    
    # Application Configuration
    app_title: str = "UberEats Brasil"
    app_icon: str = "🍔"
    app_layout: str = "centered"  # or "wide"
    
    # Performance Configuration
    max_retries: int = 3
    connection_timeout: int = 30
    query_timeout: int = 120
    
    # Phase 3: Performance & Caching Configuration
    db_pool_size: int = 10
    db_max_overflow: int = 20
    query_cache_size: int = 500
    max_concurrent_queries: int = 10
    qdrant_pool_size: int = 5
    enable_performance_tracking: bool = True
    
    # Security Configuration
    allowed_sql_keywords: list = None
    dangerous_sql_keywords: list = None
    
    def __post_init__(self):
        """Initialize settings from environment variables."""
        # OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        
        # Database
        self.database_url = os.getenv("DATABASE_URL")
        
        # Qdrant
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        # Security keywords
        if self.allowed_sql_keywords is None:
            self.allowed_sql_keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT"]
        
        if self.dangerous_sql_keywords is None:
            self.dangerous_sql_keywords = [
                "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
                "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE"
            ]
        
        # Phase 3: Performance settings from environment
        self.db_pool_size = int(os.getenv("DB_POOL_SIZE", str(self.db_pool_size)))
        self.db_max_overflow = int(os.getenv("DB_MAX_OVERFLOW", str(self.db_max_overflow)))
        self.query_cache_size = int(os.getenv("QUERY_CACHE_SIZE", str(self.query_cache_size)))
        self.max_concurrent_queries = int(os.getenv("MAX_CONCURRENT_QUERIES", str(self.max_concurrent_queries)))
        self.qdrant_pool_size = int(os.getenv("QDRANT_POOL_SIZE", str(self.qdrant_pool_size)))
        self.enable_performance_tracking = os.getenv("ENABLE_PERFORMANCE_TRACKING", str(self.enable_performance_tracking).lower()).lower() == "true"
    
    def validate(self) -> bool:
        """Validate that required settings are present."""
        required_fields = ["openai_api_key", "database_url", "qdrant_url", "qdrant_api_key"]
        
        for field in required_fields:
            value = getattr(self, field)
            if not value or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Required setting '{field}' is missing or empty")
        
        return True


# Global settings instance
_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Get application settings (singleton pattern)."""
    global _settings
    
    if _settings is None:
        _settings = AppSettings()
        _settings.validate()
    
    return _settings


def reload_settings() -> AppSettings:
    """Force reload of settings (useful for testing)."""
    global _settings
    _settings = None
    return get_settings()