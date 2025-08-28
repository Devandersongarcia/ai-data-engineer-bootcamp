"""
Configuration management for MindsDB Streamlit App
Handles environment variables and app settings
"""
import os
from typing import Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class MindsDBSettings:
    """MindsDB application settings extracted from environment variables and defaults."""
    
    # MindsDB Settings
    mindsdb_server_url: str = "http://127.0.0.1:47334"
    agent_name: str = "brasil_invoice_expert"
    
    # Database Connection
    postgres_host: Optional[str] = None
    postgres_port: int = 5432
    postgres_database: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    
    # Vector Database
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "restaurant_menus"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    # App Settings
    log_level: str = "INFO"
    chat_timeout: int = 60
    max_chat_history: int = 50
    
    # Streamlit Settings
    app_title: str = "Brasil Invoice Expert Chat"
    app_icon: str = "🧠"
    app_layout: str = "wide"
    
    # Performance Settings
    max_retries: int = 3
    connection_timeout: int = 30
    enable_performance_tracking: bool = True
    
    # Security Settings
    allowed_sql_keywords: Optional[List[str]] = None
    dangerous_sql_keywords: Optional[List[str]] = None
    
    def __post_init__(self) -> None:
        """Initialize settings from environment variables."""
        # MindsDB
        self.mindsdb_server_url = os.getenv("MINDSDB_SERVER_URL", self.mindsdb_server_url)
        self.agent_name = os.getenv("AGENT_NAME", self.agent_name)
        
        # Database
        self.postgres_host = os.getenv("POSTGRES_HOST", self.postgres_host)
        self.postgres_port = int(os.getenv("POSTGRES_PORT", str(self.postgres_port)))
        self.postgres_database = os.getenv("POSTGRES_DATABASE", self.postgres_database)
        self.postgres_user = os.getenv("POSTGRES_USER", self.postgres_user)
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", self.postgres_password)
        
        # Vector Database
        self.qdrant_url = os.getenv("QDRANT_URL", self.qdrant_url)
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", self.qdrant_api_key)
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", self.qdrant_collection)
        
        # OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.openai_model = os.getenv("OPENAI_MODEL", self.openai_model)
        
        # App settings
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.chat_timeout = int(os.getenv("CHAT_TIMEOUT", str(self.chat_timeout)))
        self.max_chat_history = int(os.getenv("MAX_CHAT_HISTORY", str(self.max_chat_history)))
        
        # Performance settings
        self.max_retries = int(os.getenv("MAX_RETRIES", str(self.max_retries)))
        self.connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", str(self.connection_timeout)))
        self.enable_performance_tracking = os.getenv("ENABLE_PERFORMANCE_TRACKING", str(self.enable_performance_tracking)).lower() == "true"
        
        # Security keywords
        if self.allowed_sql_keywords is None:
            self.allowed_sql_keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT"]
        
        if self.dangerous_sql_keywords is None:
            self.dangerous_sql_keywords = [
                "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
                "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE"
            ]
    
    def validate_required_env(self) -> List[str]:
        """Check for required environment variables."""
        missing = []
        
        # Check if we have minimum required config
        if not self.mindsdb_server_url:
            missing.append("MINDSDB_SERVER_URL")
        if not self.agent_name:
            missing.append("AGENT_NAME")
            
        return missing
    
    def has_database_config(self) -> bool:
        """Check if database configuration is available."""
        return all([
            self.postgres_host,
            self.postgres_database,
            self.postgres_user,
            self.postgres_password
        ])
    
    def has_qdrant_config(self) -> bool:
        """Check if Qdrant configuration is available."""
        return bool(self.qdrant_url and self.qdrant_api_key)
    
    def has_openai_config(self) -> bool:
        """Check if OpenAI configuration is available."""
        return bool(self.openai_api_key)
    
    def validate(self) -> bool:
        """Validate that required settings are present."""
        required_fields = ["mindsdb_server_url", "agent_name"]
        
        for field in required_fields:
            value = getattr(self, field)
            if not value or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Required setting '{field}' is missing or empty")
        
        return True

# Global settings instance
_settings: Optional[MindsDBSettings] = None

def get_settings() -> MindsDBSettings:
    """Get application settings (singleton pattern)."""
    global _settings
    
    if _settings is None:
        _settings = MindsDBSettings()
        _settings.validate()
    
    return _settings

def reload_settings() -> MindsDBSettings:
    """Force reload of settings (useful for testing)."""
    global _settings
    _settings = None
    return get_settings()

# Create global config instance for backward compatibility
config = get_settings()