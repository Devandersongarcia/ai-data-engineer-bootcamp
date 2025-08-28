"""Database configuration management."""

import urllib.parse
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DatabaseType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    QDRANT = "qdrant"
    CHROMADB = "chromadb"


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    
    db_type: DatabaseType
    connection_string: str
    api_key: Optional[str] = None
    collection_name: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize additional configuration based on database type."""
        if self.additional_params is None:
            self.additional_params = {}
    
    @classmethod
    def from_postgresql_url(cls, url: str) -> 'DatabaseConfig':
        """Create PostgreSQL config from connection URL."""
        return cls(
            db_type=DatabaseType.POSTGRESQL,
            connection_string=url
        )
    
    @classmethod
    def from_qdrant_config(cls, url: str, api_key: str, collection_name: str = None) -> 'DatabaseConfig':
        """Create Qdrant config."""
        return cls(
            db_type=DatabaseType.QDRANT,
            connection_string=url,
            api_key=api_key,
            collection_name=collection_name
        )
    
    @classmethod
    def from_chromadb_config(cls, path: str, collection_name: str) -> 'DatabaseConfig':
        """Create ChromaDB config."""
        return cls(
            db_type=DatabaseType.CHROMADB,
            connection_string=path,
            collection_name=collection_name
        )
    
    def extract_postgres_params(self) -> Dict[str, Any]:
        """Extract PostgreSQL connection parameters from URL."""
        if self.db_type != DatabaseType.POSTGRESQL:
            raise ValueError("This method is only for PostgreSQL configurations")
        
        parsed = urllib.parse.urlparse(self.connection_string)
        
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'dbname': parsed.path.lstrip('/') if parsed.path else '',
            'user': parsed.username,
            'password': parsed.password
        }
    
    def validate(self) -> bool:
        """Validate database configuration."""
        if not self.connection_string:
            raise ValueError("Connection string is required")
        
        if self.db_type == DatabaseType.QDRANT and not self.api_key:
            raise ValueError("API key is required for Qdrant")
        
        if self.db_type == DatabaseType.CHROMADB and not self.collection_name:
            raise ValueError("Collection name is required for ChromaDB")
        
        return True


class DatabaseConnectionManager:
    """Manages database connections and configurations."""
    
    def __init__(self):
        self._configs: Dict[str, DatabaseConfig] = {}
    
    def add_config(self, name: str, config: DatabaseConfig) -> None:
        """Add a database configuration."""
        config.validate()
        self._configs[name] = config
    
    def get_config(self, name: str) -> DatabaseConfig:
        """Get a database configuration."""
        if name not in self._configs:
            raise KeyError(f"Database configuration '{name}' not found")
        return self._configs[name]
    
    def list_configs(self) -> Dict[str, DatabaseType]:
        """List all configured databases."""
        return {name: config.db_type for name, config in self._configs.items()}
    
    def remove_config(self, name: str) -> None:
        """Remove a database configuration."""
        if name in self._configs:
            del self._configs[name]


def create_default_database_manager() -> DatabaseConnectionManager:
    """Create database manager with default configurations."""
    from .settings import get_settings
    
    settings = get_settings()
    manager = DatabaseConnectionManager()
    
    # PostgreSQL configuration
    postgres_config = DatabaseConfig.from_postgresql_url(settings.database_url)
    manager.add_config("postgresql", postgres_config)
    
    # Qdrant configuration
    qdrant_config = DatabaseConfig.from_qdrant_config(
        settings.qdrant_url,
        settings.qdrant_api_key,
        settings.qdrant_collection_menu
    )
    manager.add_config("qdrant", qdrant_config)
    
    # ChromaDB configuration
    chromadb_config = DatabaseConfig.from_chromadb_config(
        settings.chroma_path,
        settings.chroma_collection_name
    )
    manager.add_config("chromadb", chromadb_config)
    
    return manager